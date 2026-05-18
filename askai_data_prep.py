# askai_data_prep.py
# ══════════════════════════════════════════════════════════════════════
# AskAI Data Layer — Cricsheet-only BBB → Parquet Pipeline
# ══════════════════════════════════════════════════════════════════════
#
# Produces output files in AskAI_Data/ (relative to script):
#
#   players.parquet            — player aggregates (all prefixes)
#   team_match_records.parquet — one row per team per match (all leagues)
#   matchup/summary.parquet    — batter×bowler×comp×phase aggregates
#   matchup/by_batter/         — per-batter parquet files for fast AskAI queries
#   player_index.json          — name/alias → cricinfo_id for entity resolution
#   player_registry.parquet    — persisted cohort (skips re-scan on delta runs)
#
# Key design decisions:
#   • Cricsheet-only: no live xlsx, no scraper, no OVERALL_CUTOFF
#   • Delta mode (default): only new JSON files are parsed on each run
#   • Player spine: people.csv + optional manual overrides (no squad CSV gate)
#   • Cohort: IPL-ever OR T20I-top-tier-ever (~2,500 players)
#   • All T20 leagues in BBB_Dir included for team_match_records
#   • player_registry.parquet cached — delta runs skip the full JSON scan
#
# Run modes:
#   python askai_data_prep.py                → delta run (default)
#   python askai_data_prep.py --full         → full rebuild from scratch
#   python askai_data_prep.py --teams-only   → rebuild team_match_records only
#   python askai_data_prep.py --players-only → recompute player/matchup from
#                                              existing bbb_base (no JSON parse)
#
# Runtime estimates (ThinkPad E14, Ryzen 7):
#   Full rebuild: ~13 min
#   Delta run:    ~1–2 min  (registry loaded from cache, only new JSONs parsed)
#
# RUN ORDER (AskAI pipeline, independent of PythonAnywhere pipeline):
#   askai_data_prep.py   ← this file (run on new Cricsheet drops)
#
# ══════════════════════════════════════════════════════════════════════
#
# FIXES vs previous version:
#   1. agg_matchup() — removed dead `legal` variable
#   2. agg_matchup() — fixed stumped-off-wide dismissal (& is_legal guard removed)
#   3. parse_match() — season_year now parsed from info.season string, not date.year
#   4. parse_match() — early return on empty team2_name (abandoned/incomplete matches)
#   5. Registry      — persisted to player_registry.parquet; delta runs skip re-scan
#   6. main()        — writes player_index.json for AskAI entity resolution
#   7. CLI           — --players-only mode added (recompute from bbb_base, no parse)
#
# ══════════════════════════════════════════════════════════════════════

import os
import re
import sys
import json
import glob
import argparse
from datetime import date, datetime
from collections import defaultdict

import pandas as pd
import numpy as np

# ── Paths (all relative to script location) ────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
BBB_DIR    = os.path.join(BASE_DIR, "BBB_Dir")
PEOPLE_CSV = os.path.join(BBB_DIR, "people.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "AskAI_Data")
MATCHUP_DIR          = os.path.join(OUTPUT_DIR, "matchup")
MATCHUP_BY_BATTER    = os.path.join(MATCHUP_DIR, "by_batter")
SEEN_IDS_PATH        = os.path.join(OUTPUT_DIR, "seen_match_ids.json")
DELTA_META_PATH      = os.path.join(OUTPUT_DIR, "delta_meta.json")
BBB_BASE_PATH        = os.path.join(OUTPUT_DIR, "bbb_base.parquet")
PLAYERS_PATH         = os.path.join(OUTPUT_DIR, "players.parquet")
TEAM_RECORDS_PATH    = os.path.join(OUTPUT_DIR, "team_match_records.parquet")
MATCHUP_SUMMARY_PATH = os.path.join(MATCHUP_DIR, "summary.parquet")
REGISTRY_PATH        = os.path.join(OUTPUT_DIR, "player_registry.parquet")  # FIX 5
PLAYER_INDEX_PATH    = os.path.join(OUTPUT_DIR, "player_index.json")        # FIX 6

# ── Folders to skip (red-ball competitions) ────────────────────────
SKIP_FOLDERS = {"ssh_male_json", "mlt_male_json"}

GLOB_PATTERN = "**/*.json"

# ── Top-tier T20I nations (for cohort filtering) ───────────────────
# Full ICC members + Associate nations with T20 WC appearances
TOP_TIER_NATIONS = {
    "Afghanistan", "Australia", "Bangladesh", "England", "India",
    "Ireland", "Netherlands", "New Zealand", "Namibia", "Pakistan",
    "Scotland", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe",
    "Papua New Guinea", "Oman", "Uganda", "USA", "Nepal", "Canada",
}

# ── IPL team canonical names ───────────────────────────────────────
IPL_TEAMS = {
    "Chennai Super Kings", "Delhi Capitals", "Gujarat Titans",
    "Kolkata Knight Riders", "Lucknow Super Giants", "Mumbai Indians",
    "Punjab Kings", "Rajasthan Royals", "Royal Challengers Bengaluru",
    "Sunrisers Hyderabad",
}

# Historical IPL name variants → canonical
TEAM_CANON = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Kings XI Punjab":             "Punjab Kings",
    "Delhi Daredevils":            "Delhi Capitals",
    "Rising Pune Supergiant":      None,
    "Rising Pune Supergiants":     None,
    "Pune Warriors":               None,
    "Kochi Tuskers Kerala":        None,
    "Deccan Chargers":             None,
}

# ── Wicket kind sets (matching existing pipeline exactly) ──────────
BOWLER_WICKET_KINDS = {
    "bowled", "caught", "caught and bowled",
    "lbw", "stumped", "hit wicket"
}
BATTER_OUT_KINDS = BOWLER_WICKET_KINDS | {
    "run out", "retired out", "obstructing the field"
}

# ── Phase boundaries ───────────────────────────────────────────────
PHASE_MAP = {"PP": range(0, 6), "MID": range(6, 15), "DEATH": range(15, 20)}


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — HELPERS
# ══════════════════════════════════════════════════════════════════════

def safe_div(num, denom, decimals=2):
    if not denom:
        return None
    return round(num / denom, decimals)


def phase_of(over_num):
    for phase, rng in PHASE_MAP.items():
        if over_num in rng:
            return phase
    return None


def canon_ipl_team(name):
    if name in IPL_TEAMS:
        return name
    return TEAM_CANON.get(name, None)


def is_ipl_folder(folder_name):
    return folder_name.lower().startswith("ipl")


def is_t20i_folder(folder_name):
    return folder_name.lower() in {"t20s_male_json", "t20s_female_json"}


def source_to_competition(folder_name, event_name=""):
    """Map source folder → human-readable competition label."""
    mapping = {
        "ipl_male_json":  "IPL",
        "t20s_male_json": "T20I",
        "bbl_male_json":  "BBL",
        "bpl_male_json":  "BPL",
        "cpl_male_json":  "CPL",
        "ctc_male_json":  "CSA T20 Challenge",
        "hnd_male_json":  "The Hundred",
        "ilt_male_json":  "ILT20",
        "lpl_male_json":  "LPL",
        "mlc_male_json":  "MLC",
        "msl_male_json":  "MSL",
        "ntb_male_json":  "T20 Blast",
        "psl_male_json":  "PSL",
        "sat_male_json":  "SA20",
        "ssm_male_json":  "Super Smash",
    }
    return mapping.get(folder_name, event_name or folder_name)


def parse_season_year(season_raw, fallback_year):
    """
    FIX 3: Extract the first 4-digit year from info.season string.

    Handles formats: "2026", "2020/21", "2025-26", "2024-25 (T20 WC)"
    Falls back to match_date.year only if season field is absent/unparseable.

    This is more reliable than match_date.year for tournaments that span
    a calendar year boundary (e.g. BBL Dec–Feb, T20 WC Nov–Dec).
    """
    m = re.match(r"(\d{4})", str(season_raw).strip())
    if m:
        return int(m.group(1))
    return fallback_year


def ensure_dirs():
    for d in [OUTPUT_DIR, MATCHUP_DIR, MATCHUP_BY_BATTER]:
        os.makedirs(d, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — PLAYER REGISTRY (people.csv spine)
# ══════════════════════════════════════════════════════════════════════

def load_people_csv(people_csv_path):
    """
    Load Cricsheet people.csv and return a DataFrame with:
      unique_name   — the name used in Cricsheet JSON files
      cricinfo_id   — numeric Cricinfo ID (may be NaN for ~0.2%)
      identifier    — "Lastname, Firstname" from people.csv
      display_name  — resolved display name ("Virat Kohli")
    """
    if not os.path.exists(people_csv_path):
        print(f"  WARNING: people.csv not found at {people_csv_path}")
        print("  Download from https://cricsheet.org/downloads/people.csv")
        return pd.DataFrame()

    df = pd.read_csv(people_csv_path, encoding="utf-8")

    # people.csv columns vary slightly by version; normalise
    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in {"key_cricinfo", "cricinfo"}:
            col_map[col] = "cricinfo_id"
        elif cl == "unique_name":
            col_map[col] = "unique_name"
        elif cl == "identifier":
            col_map[col] = "identifier"
        elif cl in {"name", "full_name"}:
            col_map[col] = "display_name"

    df = df.rename(columns=col_map)

    if "unique_name" not in df.columns:
        print("  ERROR: people.csv missing 'unique_name' column.")
        return pd.DataFrame()

    # Build display name: prefer explicit name field, else derive from identifier
    if "display_name" not in df.columns:
        if "identifier" in df.columns:
            # "Kohli, Virat" → "Virat Kohli"
            def _flip(ident):
                if pd.isna(ident):
                    return ""
                parts = str(ident).split(",", 1)
                if len(parts) == 2:
                    return f"{parts[1].strip()} {parts[0].strip()}"
                return ident.strip()
            df["display_name"] = df["identifier"].apply(_flip)
        else:
            df["display_name"] = df["unique_name"]

    if "cricinfo_id" in df.columns:
        df["cricinfo_id"] = pd.to_numeric(df["cricinfo_id"], errors="coerce")

    print(f"  people.csv: {len(df):,} players loaded")
    coverage = df["cricinfo_id"].notna().sum() if "cricinfo_id" in df.columns else 0
    print(f"  Cricinfo ID coverage: {coverage:,} / {len(df):,} "
          f"({coverage/len(df)*100:.1f}%)")
    return df


def build_player_registry(bbb_dir, people_df):
    """
    Auto-discover all players from Cricsheet JSONs.
    Cohort: appeared in ipl_male_json OR (appeared in t20s_male_json AND
            their team is in TOP_TIER_NATIONS).

    Returns a dict: unique_name → {display_name, cricinfo_id, ipl_ever,
                                    t20i_ever, nation}
    """
    print("\n[Registry] Scanning JSONs for player appearances ...")
    files = glob.glob(os.path.join(bbb_dir, GLOB_PATTERN), recursive=True)
    files = [fp for fp in files
             if os.path.basename(os.path.dirname(fp)) not in SKIP_FOLDERS]

    ipl_players  = set()   # unique_names in ipl_male_json
    t20i_players = {}      # unique_name → nation

    for fp in files:
        folder = os.path.basename(os.path.dirname(fp))
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        info = data.get("info", {})
        players_info = info.get("players", {})  # {team: [name, ...]}

        if is_ipl_folder(folder):
            for team_players in players_info.values():
                for p in team_players:
                    ipl_players.add(p)
            # Also catch players appearing in deliveries (older files may lack players block)
            for inn in data.get("innings", []):
                for ov in inn.get("overs", []):
                    for d in ov.get("deliveries", []):
                        ipl_players.add(d.get("batter", ""))
                        ipl_players.add(d.get("bowler", ""))
            ipl_players.discard("")

        elif is_t20i_folder(folder):
            for team_name, team_players in players_info.items():
                if team_name in TOP_TIER_NATIONS:
                    for p in team_players:
                        if p not in t20i_players:
                            t20i_players[p] = team_name
            # Also catch via deliveries
            for inn in data.get("innings", []):
                inn_team = inn.get("team", "")
                if inn_team in TOP_TIER_NATIONS:
                    for ov in inn.get("overs", []):
                        for d in ov.get("deliveries", []):
                            for field in ("batter", "bowler", "non_striker"):
                                p = d.get(field, "")
                                if p and p not in t20i_players:
                                    t20i_players[p] = inn_team

    # Cohort union
    cohort_names = ipl_players | set(t20i_players.keys())
    cohort_names.discard("")
    print(f"  IPL-ever players:   {len(ipl_players):,}")
    print(f"  T20I top-tier:      {len(t20i_players):,}")
    print(f"  Combined cohort:    {len(cohort_names):,}")

    # Build name → people.csv row lookup
    if not people_df.empty:
        people_lookup = {
            str(row["unique_name"]).strip(): row
            for _, row in people_df.iterrows()
        }
    else:
        people_lookup = {}

    registry = {}
    no_id_count = 0
    for name in cohort_names:
        people_row = people_lookup.get(name, {})
        if isinstance(people_row, pd.Series):
            cricinfo_id  = people_row.get("cricinfo_id")
            display_name = people_row.get("display_name", name)
        else:
            cricinfo_id  = None
            display_name = name

        if pd.isna(cricinfo_id) if cricinfo_id is not None else True:
            cricinfo_id = None
            no_id_count += 1

        registry[name] = {
            "unique_name":  name,
            "display_name": display_name if display_name else name,
            "cricinfo_id":  cricinfo_id,
            "ipl_ever":     name in ipl_players,
            "t20i_ever":    name in t20i_players,
            "nation":       t20i_players.get(name, ""),
        }

    print(f"  Players without Cricinfo ID: {no_id_count:,} "
          f"({no_id_count/len(registry)*100:.1f}%)")
    return registry


def save_registry(registry):
    """FIX 5: Persist registry dict to parquet so delta runs can skip re-scan."""
    rows = list(registry.values())
    df = pd.DataFrame(rows)
    # Ensure cricinfo_id is stored as nullable Int64 (handles None/NaN cleanly)
    if "cricinfo_id" in df.columns:
        df["cricinfo_id"] = pd.to_numeric(df["cricinfo_id"], errors="coerce")
    df.to_parquet(REGISTRY_PATH, index=False)
    print(f"  ✓ player_registry.parquet saved ({len(df):,} players)")


def load_registry(registry_path):
    """FIX 5: Load persisted registry from parquet → dict."""
    df = pd.read_parquet(registry_path)
    registry = {}
    for _, row in df.iterrows():
        cid = row.get("cricinfo_id")
        registry[row["unique_name"]] = {
            "unique_name":  row["unique_name"],
            "display_name": row.get("display_name", row["unique_name"]),
            "cricinfo_id":  None if pd.isna(cid) else cid,
            "ipl_ever":     bool(row.get("ipl_ever", False)),
            "t20i_ever":    bool(row.get("t20i_ever", False)),
            "nation":       row.get("nation", ""),
        }
    print(f"  Loaded player_registry.parquet: {len(registry):,} players (cached)")
    return registry


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — DELTA STATE (seen_match_ids.json)
# ══════════════════════════════════════════════════════════════════════

def load_seen_ids():
    if os.path.exists(SEEN_IDS_PATH):
        with open(SEEN_IDS_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids):
    with open(SEEN_IDS_PATH, "w") as f:
        json.dump(sorted(seen_ids), f)


def save_delta_meta(n_new, n_total):
    meta = {
        "last_run":      datetime.now().isoformat(),
        "matches_added": n_new,
        "total_seen":    n_total,
    }
    with open(DELTA_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — CORE JSON PARSER
# Produces two streams per match:
#   delivery_rows — for players.parquet and matchup files
#   team_rows     — for team_match_records.parquet
# ══════════════════════════════════════════════════════════════════════

def parse_match(fp, registry_names):
    """
    Parse a single Cricsheet JSON.
    Returns (delivery_rows, team_match_rows) or ([], []) on skip.

    delivery_rows: one row per delivery (batter OR bowler in registry)
    team_match_rows: two rows per match (one per team), all leagues
    """
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return [], []

    info  = data.get("info", {})
    dates = info.get("dates", [])
    if not dates:
        return [], []

    match_date = date.fromisoformat(str(dates[0]))
    match_id   = os.path.splitext(os.path.basename(fp))[0]
    folder     = os.path.basename(os.path.dirname(fp))
    is_ipl     = is_ipl_folder(folder)
    is_t20i    = is_t20i_folder(folder)

    # FIX 3: use info.season string for year, not match_date.year
    season_year = parse_season_year(info.get("season", ""), match_date.year)

    event      = info.get("event", {})
    event_name = (event.get("name", "") if isinstance(event, dict) else str(event))
    competition = source_to_competition(folder, event_name)

    # ── Match metadata ─────────────────────────────────────────────
    venue = str(info.get("venue", "Unknown")).strip()
    city  = str(info.get("city", "")).strip()

    toss          = info.get("toss", {})
    toss_winner   = toss.get("winner", "")
    toss_decision = toss.get("decision", "")

    outcome    = info.get("outcome", {})
    winner_raw = outcome.get("winner", "")
    win_by     = outcome.get("by", {})
    result_str = outcome.get("result", "")

    if winner_raw:
        win_result         = "win"
        win_margin_runs    = win_by.get("runs")
        win_margin_wickets = win_by.get("wickets")
        win_type = ("runs" if win_margin_runs else
                    "wickets" if win_margin_wickets else "other")
    elif result_str == "tie":
        win_result, win_type = "tie", "tie"
        win_margin_runs = win_margin_wickets = None
    else:
        win_result, win_type = "no result", "no result"
        win_margin_runs = win_margin_wickets = None

    has_super_over    = any(inn.get("super_over", False)
                            for inn in data.get("innings", []))
    super_over_winner = outcome.get("eliminator", None)

    pom             = info.get("player_of_match", [])
    player_of_match = pom[0] if pom else None

    # ── Innings structure ─────────────────────────────────────────
    innings_list = [inn for inn in data.get("innings", [])
                    if not inn.get("super_over", False)]

    if len(innings_list) < 1:
        return [], []

    inn1_team_raw = innings_list[0].get("team", "")
    inn2_team_raw = innings_list[1].get("team", "") if len(innings_list) > 1 else ""

    # FIX 4: abandoned/incomplete match — can't build team records without two teams
    if not inn1_team_raw or not inn2_team_raw:
        return [], []

    # For IPL: canonicalise team names
    if is_ipl:
        team1_name = canon_ipl_team(inn1_team_raw) or inn1_team_raw
        team2_name = canon_ipl_team(inn2_team_raw) or inn2_team_raw
        winner_can = canon_ipl_team(winner_raw) if winner_raw else None
    else:
        team1_name = inn1_team_raw
        team2_name = inn2_team_raw
        winner_can = winner_raw if winner_raw else None

    # ── Per-innings phase accumulators (for team_match_records) ───
    # Only non-SO innings are accumulated into the main team metrics.
    # Super over data is captured separately in team row assembly.
    team_del = {
        team1_name: {
            "bat":  defaultdict(lambda: {"runs":0,"balls":0,"wkts":0,"fours":0,"sixes":0,"dots":0,"extras":0}),
            "bowl": defaultdict(lambda: {"runs":0,"balls":0,"wkts":0,"fours":0,"sixes":0,"dots":0}),
        },
        team2_name: {
            "bat":  defaultdict(lambda: {"runs":0,"balls":0,"wkts":0,"fours":0,"sixes":0,"dots":0,"extras":0}),
            "bowl": defaultdict(lambda: {"runs":0,"balls":0,"wkts":0,"fours":0,"sixes":0,"dots":0}),
        },
    }

    runs_by_over     = {team1_name: [None]*20, team2_name: [None]*20}
    wickets_timeline = {team1_name: [],         team2_name: []}
    team_total_runs  = {team1_name: 0,          team2_name: 0}
    team_total_wkts  = {team1_name: 0,          team2_name: 0}
    team_legal_balls = {team1_name: 0,          team2_name: 0}
    team_extras      = {team1_name: 0,          team2_name: 0}
    team_fours       = {team1_name: 0,          team2_name: 0}
    team_sixes       = {team1_name: 0,          team2_name: 0}

    delivery_rows = []

    for inn_data in data.get("innings", []):
        is_so   = inn_data.get("super_over", False)
        bat_raw = inn_data.get("team", "")
        bat_team = (canon_ipl_team(bat_raw) if is_ipl else bat_raw) or bat_raw

        if bat_team == team1_name:
            bowl_team = team2_name
        elif bat_team == team2_name:
            bowl_team = team1_name
        else:
            bowl_team = None

        over_runs_this_inn = {}

        for over_data in inn_data.get("overs", []):
            over_num = int(over_data.get("over", 0))
            phase    = phase_of(over_num)

            for delivery in over_data.get("deliveries", []):
                batter      = delivery.get("batter", "")
                bowler      = delivery.get("bowler", "")

                extras_dict = delivery.get("extras", {})
                is_wide     = "wides"   in extras_dict
                is_noball   = "noballs" in extras_dict
                is_legal    = not is_wide and not is_noball

                runs_obj    = delivery.get("runs", {})
                runs_batter = runs_obj.get("batter", 0)
                runs_extras = runs_obj.get("extras", 0)
                runs_total  = runs_obj.get("total", 0)

                is_four = (runs_batter == 4) and not is_wide
                is_six  = (runs_batter == 6) and not is_wide
                is_dot  = is_legal and (runs_batter == 0)

                wickets      = delivery.get("wickets", [])
                bat_dismissed = (not is_wide) and any(
                    w.get("kind", "") in BATTER_OUT_KINDS and
                    w.get("player_out", "") == batter
                    for w in wickets
                )
                # is_legal guard deliberately absent — stumped off a wide still
                # credits the bowler (confirmed: R Ashwin, IPL 2025, match 1473448)
                bowl_wicket = any(
                    w.get("kind", "") in BOWLER_WICKET_KINDS
                    for w in wickets
                )

                # ── Delivery record for players/matchup ───────────
                if batter in registry_names or bowler in registry_names:
                    delivery_rows.append({
                        "match_id":      match_id,
                        "match_date":    match_date,
                        "season":        season_year,
                        "competition":   competition,
                        "is_ipl":        is_ipl,
                        "is_t20i":       is_t20i,
                        "venue":         venue,
                        "batting_team":  bat_team,
                        "bowling_team":  bowl_team,
                        "batter":        batter,
                        "bowler":        bowler,
                        "over":          over_num,
                        "phase":         phase,
                        "runs_batter":   runs_batter,
                        "runs_extras":   runs_extras,
                        "runs_total":    runs_total,
                        "is_wide":       is_wide,
                        "is_noball":     is_noball,
                        "is_legal":      is_legal,
                        "is_four":       is_four,
                        "is_six":        is_six,
                        "is_dot":        is_dot,
                        "bat_dismissed": bat_dismissed,
                        "bowl_wicket":   bowl_wicket,
                        "is_super_over": is_so,
                    })

                # ── Team phase accumulators (non-SO only) ─────────
                if not is_so and phase and bat_team in team_del:
                    ph = phase
                    team_del[bat_team]["bat"][ph]["runs"]   += runs_batter
                    team_del[bat_team]["bat"][ph]["extras"] += runs_extras
                    if is_legal:
                        team_del[bat_team]["bat"][ph]["balls"] += 1
                    if bat_dismissed:
                        team_del[bat_team]["bat"][ph]["wkts"]  += 1
                    if is_four:
                        team_del[bat_team]["bat"][ph]["fours"] += 1
                    if is_six:
                        team_del[bat_team]["bat"][ph]["sixes"] += 1
                    if is_dot:
                        team_del[bat_team]["bat"][ph]["dots"]  += 1

                    if bowl_team and bowl_team in team_del:
                        team_del[bowl_team]["bowl"][ph]["runs"]  += runs_batter + runs_extras
                        if is_legal:
                            team_del[bowl_team]["bowl"][ph]["balls"] += 1
                        if bowl_wicket:
                            team_del[bowl_team]["bowl"][ph]["wkts"]  += 1
                        if is_four:
                            team_del[bowl_team]["bowl"][ph]["fours"] += 1
                        if is_six:
                            team_del[bowl_team]["bowl"][ph]["sixes"] += 1
                        if is_dot:
                            team_del[bowl_team]["bowl"][ph]["dots"]  += 1

                    team_total_runs[bat_team]  += runs_batter
                    team_total_wkts[bat_team]  += int(bat_dismissed)
                    team_extras[bat_team]      += runs_extras
                    team_fours[bat_team]       += int(is_four)
                    team_sixes[bat_team]       += int(is_six)
                    if is_legal:
                        team_legal_balls[bat_team] += 1

                    over_runs_this_inn[over_num] = (
                        over_runs_this_inn.get(over_num, 0) + runs_total
                    )

                    if bat_dismissed:
                        wickets_timeline[bat_team].append({
                            "over":       over_num,
                            "batter_out": batter,
                            "kind":       next(
                                (w.get("kind", "") for w in wickets
                                 if w.get("player_out", "") == batter), ""),
                            "bowler":     bowler,
                            "runs_at_fall": team_total_runs[bat_team],
                        })

            # Store over runs (non-SO only)
            if not is_so and bat_team in runs_by_over:
                runs_by_over[bat_team][over_num] = over_runs_this_inn.get(over_num)

    # ── Assemble team_match_rows ───────────────────────────────────
    team_match_rows = []
    for inn_team in [team1_name, team2_name]:
        bowl_team     = team2_name if inn_team == team1_name else team1_name
        batting_first = (inn_team == team1_name)
        won           = (winner_can == inn_team) if winner_can else False

        row = {
            # ── Context ────────────────────────────────────────────
            "match_id":        match_id,
            "match_date":      match_date,
            "season":          season_year,
            "competition":     competition,
            "is_ipl":          is_ipl,
            "is_t20i":         is_t20i,
            "venue":           venue,
            "city":            city,
            "source_folder":   folder,
            "has_super_over":  has_super_over,
            "player_of_match": player_of_match,

            # ── Toss ───────────────────────────────────────────────
            "toss_winner":    toss_winner,
            "toss_decision":  toss_decision,
            "toss_won":       (toss_winner == inn_team),
            "toss_elected_to": (toss_decision if toss_winner == inn_team
                                else ("bat" if toss_decision == "field" else "field")),

            # ── Teams ──────────────────────────────────────────────
            "team":          inn_team,
            "opponent":      bowl_team,
            "batting_first": batting_first,

            # ── Outcome ────────────────────────────────────────────
            "result":             ("win" if won else
                                   win_result if win_result in ("tie", "no result")
                                   else "loss"),
            "won":                won,
            "win_margin_runs":    win_margin_runs    if won else None,
            "win_margin_wickets": win_margin_wickets if won else None,
            "win_type":           win_type if won else None,
            "super_over_winner":  super_over_winner,
            "batting_first_won":  won and batting_first,
            "toss_winner_won":    (toss_winner == inn_team) and won,

            # ── Batting totals ──────────────────────────────────────
            "runs_total":   team_total_runs.get(inn_team, 0),
            "wickets_lost": team_total_wkts.get(inn_team, 0),
            "legal_balls":  team_legal_balls.get(inn_team, 0),
            "extras_total": team_extras.get(inn_team, 0),
            "fours":        team_fours.get(inn_team, 0),
            "sixes":        team_sixes.get(inn_team, 0),
            "run_rate":     safe_div(
                                team_total_runs.get(inn_team, 0) * 6,
                                team_legal_balls.get(inn_team, 0), 2),

            # ── Phase batting ───────────────────────────────────────
            **{f"bat_{ph}_{k}": team_del[inn_team]["bat"][ph][k]
               for ph in ("PP", "MID", "DEATH")
               for k in ("runs", "balls", "wkts", "fours", "sixes", "dots", "extras")},

            # ── Phase bowling ───────────────────────────────────────
            **{f"bowl_{ph}_{k}": team_del[inn_team]["bowl"][ph][k]
               for ph in ("PP", "MID", "DEATH")
               for k in ("runs", "balls", "wkts", "fours", "sixes", "dots")},

            # ── Over-by-over & timeline (JSON strings) ──────────────
            "runs_by_over":     json.dumps(runs_by_over.get(inn_team, [None]*20)),
            "wickets_timeline": json.dumps(wickets_timeline.get(inn_team, [])),
        }

        # Derived phase run rates and dot percentages
        for ph in ("PP", "MID", "DEATH"):
            row[f"bat_{ph}_rr"]      = safe_div(row[f"bat_{ph}_runs"] * 6,   row[f"bat_{ph}_balls"], 2)
            row[f"bowl_{ph}_econ"]   = safe_div(row[f"bowl_{ph}_runs"] * 6,  row[f"bowl_{ph}_balls"], 2)
            row[f"bat_{ph}_dot_pct"] = safe_div(row[f"bat_{ph}_dots"] * 100, row[f"bat_{ph}_balls"], 1)

        team_match_rows.append(row)

    return delivery_rows, team_match_rows


# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — BBB PARSE LOOP (delta-aware)
# ══════════════════════════════════════════════════════════════════════

def parse_new_files(bbb_dir, seen_ids, registry_names):
    """
    Parse only JSON files not in seen_ids.
    Returns (delivery_df, team_match_df, new_match_ids).
    """
    files = glob.glob(os.path.join(bbb_dir, GLOB_PATTERN), recursive=True)
    files = [fp for fp in files
             if os.path.basename(os.path.dirname(fp)) not in SKIP_FOLDERS]

    print(f"  Total JSON files found: {len(files):,}")

    new_files = []
    for fp in files:
        mid = os.path.splitext(os.path.basename(fp))[0]
        if mid not in seen_ids:
            new_files.append((mid, fp))

    print(f"  New (unprocessed) files: {len(new_files):,}")
    if not new_files:
        print("  Nothing new — pipeline is up to date.")
        return pd.DataFrame(), pd.DataFrame(), set()

    all_deliveries = []
    all_team_rows  = []
    new_ids        = set()
    parsed = skipped = 0

    for mid, fp in new_files:
        deliveries, team_rows = parse_match(fp, registry_names)
        if not deliveries and not team_rows:
            skipped += 1
            continue
        all_deliveries.extend(deliveries)
        all_team_rows.extend(team_rows)
        new_ids.add(mid)
        parsed += 1
        if parsed % 200 == 0:
            print(f"    {parsed:,} matches parsed, {len(all_deliveries):,} deliveries ...")

    print(f"  Parsed: {parsed:,} new matches | "
          f"Deliveries: {len(all_deliveries):,} | "
          f"Team rows: {len(all_team_rows):,} | "
          f"Skipped: {skipped}")

    del_df  = pd.DataFrame(all_deliveries) if all_deliveries else pd.DataFrame()
    team_df = pd.DataFrame(all_team_rows)  if all_team_rows  else pd.DataFrame()
    return del_df, team_df, new_ids


# ══════════════════════════════════════════════════════════════════════
# SECTION 6 — PLAYER AGGREGATE BUILDER
# ══════════════════════════════════════════════════════════════════════

def compute_player_agg(del_df, registry):
    """
    Compute per-player aggregates across multiple prefixes from delivery df.
    Returns DataFrame with one row per player (all prefixes as columns).

    Prefixes:
      Overall — all T20s, all time
      IPL     — all IPL seasons, 2008 onwards
      T20I    — all T20 Internationals
      2025    — Jan 2025 onwards (form window)
      IPL26   — IPL 2026 season
    """
    if del_df.empty:
        return pd.DataFrame()

    def prefix_filter(df, prefix):
        # Always exclude super over deliveries from all aggregates.
        # Official stats (Cricinfo/ESPNcricinfo) never include super overs.
        df = df[~df["is_super_over"]]
        if prefix == "Overall":
            return df
        elif prefix == "IPL":
            # season >= 2008: IPL started in 2008; pre-2008 matches in
            # ipl_male_json are Champions League or other non-IPL events
            return df[df["is_ipl"] & (df["season"] >= 2007)]
        elif prefix == "T20I":
            return df[df["is_t20i"]]
        elif prefix == "2025":
            return df[df["match_date"] >= date(2025, 1, 1)]
        elif prefix == "IPL26":
            return df[df["is_ipl"] & (df["season"] == 2026)]
        return df

    def bat_stats(grp):
        no_wide = grp[~grp["is_wide"]]
        balls   = len(no_wide)    # no-balls count as balls faced; wides don't
        runs    = int(no_wide["runs_batter"].sum())
        dis     = int(no_wide["bat_dismissed"].sum())
        fours   = int(no_wide["is_four"].sum())
        sixes   = int(no_wide["is_six"].sum())
        inns    = no_wide["match_id"].nunique()
        return {
            "Innings":     inns,
            "Runs":        runs,
            "Balls_Faced": balls,
            "Dismissed":   dis,
            "Batting_Avg": safe_div(runs, dis, 1),
            "Batting_SR":  safe_div(runs * 100, balls, 1),
            "Fours":       fours,
            "Sixes":       sixes,
            "Dot_Pct":     safe_div(int(no_wide["is_dot"].sum()) * 100, balls, 1),
        }

    def bowl_stats(grp):
        legal = grp[grp["is_legal"]]
        balls = len(legal)
        wkts  = int(grp["bowl_wicket"].sum())
        runs_conceded = (
            int(grp["runs_batter"].sum()) +
            int(grp[grp["is_wide"]]["runs_extras"].sum()) +
            int(grp[grp["is_noball"]]["runs_extras"].sum())
        )
        inns = grp["match_id"].nunique()
        return {
            "Bowl_Innings":  inns,
            "Wickets":       wkts,
            "Balls_Bowled":  balls,
            "Runs_Conceded": runs_conceded,
            "Econ":          safe_div(runs_conceded * 6, balls, 2),
            "Bowling_Avg":   safe_div(runs_conceded, wkts, 1),
            "Bowling_SR":    safe_div(balls, wkts, 1),
        }

    prefixes    = ["Overall", "IPL", "T20I", "2025", "IPL26"]
    player_rows = {}

    for prefix in prefixes:
        pf_df = prefix_filter(del_df, prefix)
        if pf_df.empty:
            continue

        # Batting
        bat_df = pf_df[pf_df["batter"].isin(registry)]
        if not bat_df.empty:
            for batter_name, grp in bat_df.groupby("batter"):
                stats = bat_stats(grp)
                entry = player_rows.setdefault(batter_name, {})
                for k, v in stats.items():
                    entry[f"{k}_{prefix}"] = v

        # Bowling
        bowl_df = pf_df[pf_df["bowler"].isin(registry)]
        if not bowl_df.empty:
            for bowler_name, grp in bowl_df.groupby("bowler"):
                stats = bowl_stats(grp)
                entry = player_rows.setdefault(bowler_name, {})
                for k, v in stats.items():
                    entry[f"{k}_{prefix}"] = v

    # Build final DataFrame
    rows = []
    for unique_name, reg_info in registry.items():
        if unique_name not in player_rows:
            continue
        row = {
            "unique_name":  unique_name,
            "display_name": reg_info["display_name"],
            "cricinfo_id":  reg_info["cricinfo_id"],
            "ipl_ever":     reg_info["ipl_ever"],
            "t20i_ever":    reg_info["t20i_ever"],
            "nation":       reg_info["nation"],
        }
        row.update(player_rows[unique_name])
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("display_name")
    print(f"  Player rows built: {len(df):,}")
    return df


# ══════════════════════════════════════════════════════════════════════
# SECTION 7 — MATCHUP BUILDER
# ══════════════════════════════════════════════════════════════════════

def compute_matchups(del_df, registry):
    """
    Build batter×bowler matchup aggregates (career + by competition).
    Writes:
      matchup/summary.parquet              — batter×bowler×comp×phase aggregates
      matchup/by_batter/{unique_name}.parquet — per-batter slice for fast AskAI queries
    """
    if del_df.empty:
        return

    reg_names = set(registry.keys())

    # Filter to deliveries where both batter and bowler are in registry,
    # excluding super overs
    both = del_df[
        del_df["batter"].isin(reg_names) &
        del_df["bowler"].isin(reg_names) &
        ~del_df["is_super_over"]
    ].copy()

    if both.empty:
        print("  No registry-vs-registry deliveries found for matchups.")
        return

    # Add "ALL" phase rows by duplicating (for cross-phase career totals)
    all_phase = both.copy()
    all_phase["phase"] = "ALL"
    combined = pd.concat([both, all_phase], ignore_index=True)

    grp = combined.groupby(["batter", "bowler", "competition", "phase"])

    def agg_matchup(g):
        # FIX 1: removed dead `legal` variable
        # FIX 2: removed `& g["is_legal"]` guard from dismissed count —
        #        stumped off a wide still credits the bowler (see bowl_wicket note)
        balls    = int((g["is_legal"] | g["is_noball"]).sum())
        runs     = int(g["runs_batter"].sum())
        dots     = int(g["is_dot"].sum())
        fours    = int(g["is_four"].sum())
        sixes    = int(g["is_six"].sum())
        dis      = int(g["bowl_wicket"].sum())   # FIX 2: no is_legal gate
        return pd.Series({
            "balls":        balls,
            "runs":         runs,
            "dots":         dots,
            "fours":        fours,
            "sixes":        sixes,
            "dismissed":    dis,
            "sr":           safe_div(runs * 100, balls, 1),
            "dot_pct":      safe_div(dots * 100, balls, 1),
            "dismiss_rate": safe_div(dis * 100, balls, 1),
        })

    summary = grp.apply(agg_matchup, include_groups=False).reset_index()

    # Add career rows (across all competitions)
    career_grp = combined.groupby(["batter", "bowler", "phase"])
    career     = career_grp.apply(agg_matchup, include_groups=False).reset_index()
    career["competition"] = "Career"
    summary = pd.concat([summary, career], ignore_index=True)

    # Add display names for readability
    summary["batter_display"] = summary["batter"].map(
        lambda x: registry.get(x, {}).get("display_name", x))
    summary["bowler_display"] = summary["bowler"].map(
        lambda x: registry.get(x, {}).get("display_name", x))

    # Filter noise: minimum 6 balls for any row
    summary = summary[summary["balls"] >= 6]

    print(f"  Matchup summary rows: {len(summary):,}")
    summary.to_parquet(MATCHUP_SUMMARY_PATH, index=False)
    print(f"  ✓ matchup/summary.parquet written")

    # Write per-batter files (fast lookup for AskAI: load one file per batter query)
    written = 0
    for batter_name, grp in summary.groupby("batter"):
        safe_name = batter_name.replace(" ", "_").replace("/", "-")
        out_path  = os.path.join(MATCHUP_BY_BATTER, f"{safe_name}.parquet")
        grp.to_parquet(out_path, index=False)
        written += 1
    print(f"  ✓ {written:,} per-batter parquet files written")


# ══════════════════════════════════════════════════════════════════════
# SECTION 8 — PLAYER INDEX (entity resolution for AskAI)
# ══════════════════════════════════════════════════════════════════════

def write_player_index(registry, path):
    """
    FIX 6: Write name/alias → cricinfo_id lookup for AskAI entity resolution.

    Indexed by (in priority order):
      1. unique_name (Cricsheet canonical form, e.g. "V Kohli")
      2. display_name (Firstname Lastname, e.g. "Virat Kohli")
      3. lowercase display_name
      4. last name only (lowest priority — never overwrites an existing entry,
         because "Perera", "Khan", "Singh" are heavily colliding)

    All keys stored lowercase for case-insensitive lookup.
    Value is always the numeric cricinfo_id (int), or None if unknown.
    """
    index = {}

    for unique_name, info in registry.items():
        cid = info.get("cricinfo_id")
        dn  = info.get("display_name", "").strip()

        # 1. unique_name (Cricsheet form)
        index[unique_name.lower()] = cid

        # 2 & 3. display_name variants
        if dn:
            index[dn.lower()] = cid
            # e.g. "virat kohli" already covered by dn.lower()

        # 4. Last name only — only if not already claimed by another player
        parts = dn.split()
        if parts:
            last = parts[-1].lower()
            if last not in index:
                index[last] = cid

    # Sort for reproducible diffs
    index_sorted = dict(sorted(index.items()))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(index_sorted, f, indent=2)

    total    = len(index_sorted)
    with_id  = sum(1 for v in index_sorted.values() if v is not None)
    print(f"  ✓ player_index.json written ({total:,} entries, "
          f"{with_id:,} with cricinfo_id)")


# ══════════════════════════════════════════════════════════════════════
# SECTION 9 — MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════

def main(full_rebuild=False, teams_only=False, players_only=False):
    print("=" * 65)
    print("AskAI Data Layer — Cricsheet BBB Pipeline")
    mode = ("FULL REBUILD"   if full_rebuild  else
            "TEAMS ONLY"     if teams_only    else
            "PLAYERS ONLY"   if players_only  else
            "DELTA")
    print(f"Mode: {mode}")
    print("=" * 65)

    ensure_dirs()

    # ── Step 1: Load people.csv ────────────────────────────────────
    print("\n[1/6] Loading people.csv ...")
    people_df = load_people_csv(PEOPLE_CSV)

    # ── Step 2: Build or load player registry ─────────────────────
    # FIX 5: On delta/players-only runs, load the cached registry parquet
    # instead of re-scanning all 9,000+ JSONs (~30-45s saved per run).
    # The registry is rebuilt from scratch on --full only.
    print("\n[2/6] Loading player registry ...")
    if full_rebuild or not os.path.exists(REGISTRY_PATH):
        registry = build_player_registry(BBB_DIR, people_df)
        save_registry(registry)
    else:
        registry = load_registry(REGISTRY_PATH)

    registry_names = set(registry.keys())
    print(f"  Registry size: {len(registry):,} players")

    # ── Step 3: Determine files to parse ──────────────────────────
    print("\n[3/6] Determining files to parse ...")
    if players_only:
        # Skip JSON parsing entirely — recompute from existing bbb_base
        print("  --players-only: skipping JSON parse, using existing bbb_base.")
        seen_ids = load_seen_ids()
        new_ids  = set()
        new_del_df = new_team_df = pd.DataFrame()
    elif full_rebuild:
        seen_ids = set()
        for p in [BBB_BASE_PATH, PLAYERS_PATH, TEAM_RECORDS_PATH, MATCHUP_SUMMARY_PATH]:
            if os.path.exists(p):
                os.remove(p)
        for f in glob.glob(os.path.join(MATCHUP_BY_BATTER, "*.parquet")):
            os.remove(f)
        print("  Full rebuild: cleared existing parquet files.")
        # ── Step 4: Parse all files ────────────────────────────────
        print("\n[4/6] Parsing Cricsheet JSONs ...")
        new_del_df, new_team_df, new_ids = parse_new_files(BBB_DIR, seen_ids, registry_names)
    else:
        seen_ids = load_seen_ids()
        print(f"  Already processed: {len(seen_ids):,} matches")
        # ── Step 4: Parse new files ────────────────────────────────
        print("\n[4/6] Parsing Cricsheet JSONs ...")
        new_del_df, new_team_df, new_ids = parse_new_files(BBB_DIR, seen_ids, registry_names)

    # ── Merge delivery and team data ───────────────────────────────
    if new_ids:
        if os.path.exists(BBB_BASE_PATH) and not full_rebuild:
            print("  Loading existing bbb_base.parquet ...")
            base_df = pd.read_parquet(BBB_BASE_PATH)
            del_df  = pd.concat([base_df, new_del_df], ignore_index=True)
            print(f"  Combined: {len(del_df):,} delivery rows")
        else:
            del_df = new_del_df

        del_df.to_parquet(BBB_BASE_PATH, index=False)
        print(f"  ✓ bbb_base.parquet saved ({len(del_df):,} rows)")

        if os.path.exists(TEAM_RECORDS_PATH) and not full_rebuild:
            existing_teams = pd.read_parquet(TEAM_RECORDS_PATH)
            team_df = pd.concat([existing_teams, new_team_df], ignore_index=True)
        else:
            team_df = new_team_df

        team_df.to_parquet(TEAM_RECORDS_PATH, index=False)
        print(f"  ✓ team_match_records.parquet saved ({len(team_df):,} rows)")

    elif not players_only:
        # No new files, not players-only — load existing base for downstream steps
        if not teams_only and os.path.exists(BBB_BASE_PATH):
            del_df = pd.read_parquet(BBB_BASE_PATH)
            print(f"  No new matches. Loaded existing bbb_base: {len(del_df):,} rows.")
        else:
            del_df = pd.DataFrame()
    else:
        # players_only: load existing bbb_base
        if os.path.exists(BBB_BASE_PATH):
            del_df = pd.read_parquet(BBB_BASE_PATH)
            print(f"  Loaded bbb_base.parquet: {len(del_df):,} rows")
        else:
            print("  ERROR: bbb_base.parquet not found. Run without --players-only first.")
            return

    # ── Step 5: Build player aggregates ───────────────────────────
    if not teams_only:
        print("\n[5/6] Computing player aggregates ...")
        if not del_df.empty:
            players_df = compute_player_agg(del_df, registry)
            if not players_df.empty:
                players_df.to_parquet(PLAYERS_PATH, index=False)
                print(f"  ✓ players.parquet saved ({len(players_df):,} rows)")

        # ── Step 6: Build matchup files ────────────────────────────
        print("\n[6/6] Computing matchup aggregates ...")
        if not del_df.empty:
            compute_matchups(del_df, registry)
    else:
        print("\n[5/6] Skipping player aggregates (--teams-only mode)")
        print("\n[6/6] Skipping matchup aggregates (--teams-only mode)")

    # ── Write player_index.json ─────────────────────────────────────
    # FIX 6: Always write on any run that touches the registry
    print("\n  Writing entity resolution index ...")
    write_player_index(registry, PLAYER_INDEX_PATH)

    # ── Update seen_ids ────────────────────────────────────────────
    if new_ids:
        seen_ids.update(new_ids)
        save_seen_ids(seen_ids)
        save_delta_meta(len(new_ids), len(seen_ids))
        print(f"\n  seen_match_ids.json updated: {len(seen_ids):,} total matches")

    # ── Summary ────────────────────────────────────────────────────
    print(f"\n✓ Done — AskAI data layer at: {OUTPUT_DIR}")
    print("  Files produced:")
    for path in [PLAYERS_PATH, TEAM_RECORDS_PATH, MATCHUP_SUMMARY_PATH,
                 REGISTRY_PATH, PLAYER_INDEX_PATH]:
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / 1024 / 1024
            print(f"    {os.path.basename(path):<40} {size_mb:.2f} MB")
    by_batter_count = len(glob.glob(os.path.join(MATCHUP_BY_BATTER, "*.parquet")))
    if by_batter_count:
        print(f"    matchup/by_batter/                       {by_batter_count:,} files")


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AskAI Data Layer — Cricsheet BBB Pipeline"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Full rebuild from scratch (clears existing parquet + registry cache)"
    )
    parser.add_argument(
        "--teams-only", action="store_true",
        help="Only rebuild team_match_records (skip player/matchup aggregates)"
    )
    parser.add_argument(
        "--players-only", action="store_true",              # FIX 7
        help="Recompute player/matchup aggregates from existing bbb_base "
             "(no JSON parsing — fast if only aggregate logic changed)"
    )
    args = parser.parse_args()

    if args.full and (args.teams_only or args.players_only):
        parser.error("--full cannot be combined with --teams-only or --players-only")
    if args.teams_only and args.players_only:
        parser.error("--teams-only and --players-only are mutually exclusive")

    import time
    t_start = time.time()
    main(
        full_rebuild=args.full,
        teams_only=args.teams_only,
        players_only=args.players_only,
    )
    elapsed = time.time() - t_start
    mins, secs = divmod(int(elapsed), 60)
    print(f"\n⏱  Total runtime: {mins}m {secs}s")
