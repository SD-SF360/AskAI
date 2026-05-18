# query_matchup.py
# ══════════════════════════════════════════════════════════════════════
# Ad-hoc matchup query against AskAI parquet files
# Usage:
#   python query_matchup.py                          # default: Samson vs Cummins
#   python query_matchup.py "V Kohli" "JJ Bumrah"   # any batter vs bowler
#
# Batter and bowler names must match Cricsheet unique_name format.
# If unsure of the exact name, use --search to look up.
#   python query_matchup.py --search "samson"
# ══════════════════════════════════════════════════════════════════════

import os
import sys
import json
import argparse
import pandas as pd

# ── Paths — adjust if your AskAI_Data folder is elsewhere ──────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
ASKAI_DATA_DIR   = os.path.join(BASE_DIR, "AskAI_Data")
BBB_BASE_PATH    = os.path.join(ASKAI_DATA_DIR, "bbb_base.parquet")
PLAYERS_PATH     = os.path.join(ASKAI_DATA_DIR, "players.parquet")
PLAYER_INDEX     = os.path.join(ASKAI_DATA_DIR, "player_index.json")
REGISTRY_PATH    = os.path.join(ASKAI_DATA_DIR, "player_registry.parquet")


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def safe_div(num, denom, decimals=2):
    if not denom:
        return None
    return round(num / denom, decimals)


def load_registry_lookup():
    """
    Returns dict: lowercase name/alias → unique_name (Cricsheet form).
    Uses player_index.json (cricinfo_id values) cross-referenced with
    player_registry for the unique_name ↔ display_name mapping.
    """
    if not os.path.exists(REGISTRY_PATH):
        return {}
    reg = pd.read_parquet(REGISTRY_PATH)
    # Build: display_name.lower() → unique_name
    #        unique_name.lower()  → unique_name
    lookup = {}
    for _, row in reg.iterrows():
        un = row["unique_name"]
        dn = str(row.get("display_name", "")).strip()
        lookup[un.lower()] = un
        if dn:
            lookup[dn.lower()] = un
        # last name shortcut
        parts = dn.split()
        if parts:
            last = parts[-1].lower()
            if last not in lookup:
                lookup[last] = un
    return lookup


def resolve_name(raw_name, lookup):
    """
    Resolve a loose player name to a Cricsheet unique_name.
    Tries exact, lowercase, and partial match in that order.
    """
    # exact
    if raw_name in lookup:
        return lookup[raw_name]
    # lowercase
    key = raw_name.lower().strip()
    if key in lookup:
        return lookup[key]
    # partial — find all keys containing the search term
    matches = {v for k, v in lookup.items() if key in k}
    if len(matches) == 1:
        return matches.pop()
    if len(matches) > 1:
        print(f"  Ambiguous name '{raw_name}' — matches: {sorted(matches)}")
        print("  Use the exact unique_name shown above.")
        return None
    return None


def search_players(term):
    """Print all registry players whose name contains `term`."""
    if not os.path.exists(REGISTRY_PATH):
        print("player_registry.parquet not found. Run askai_data_prep.py first.")
        return
    reg = pd.read_parquet(REGISTRY_PATH)
    term_lower = term.lower()
    hits = reg[
        reg["unique_name"].str.lower().str.contains(term_lower, na=False) |
        reg["display_name"].str.lower().str.contains(term_lower, na=False)
    ][["unique_name", "display_name", "cricinfo_id", "nation", "ipl_ever", "t20i_ever"]]
    if hits.empty:
        print(f"No players found matching '{term}'")
    else:
        print(f"\n  Players matching '{term}':")
        print(hits.to_string(index=False))


# ══════════════════════════════════════════════════════════════════════
# CORE QUERY
# ══════════════════════════════════════════════════════════════════════

def query_matchup(batter_raw, bowler_raw, min_balls=1):
    """
    Pull all deliveries for batter vs bowler from bbb_base.parquet,
    aggregate by competition × phase, and print a formatted card.
    """
    if not os.path.exists(BBB_BASE_PATH):
        print(f"\n  ERROR: bbb_base.parquet not found at {BBB_BASE_PATH}")
        print("  Run askai_data_prep.py --full first.")
        return

    # ── Resolve names ──────────────────────────────────────────────
    lookup = load_registry_lookup()
    batter = resolve_name(batter_raw, lookup)
    bowler = resolve_name(bowler_raw, lookup)

    if not batter:
        print(f"\n  Could not resolve batter name: '{batter_raw}'")
        print("  Try: python query_matchup.py --search \"samson\"")
        return
    if not bowler:
        print(f"\n  Could not resolve bowler name: '{bowler_raw}'")
        print("  Try: python query_matchup.py --search \"cummins\"")
        return

    print(f"\n{'='*58}")
    print(f"  MATCHUP: {batter}  vs  {bowler}")
    print(f"{'='*58}")

    # ── Load and filter bbb_base ───────────────────────────────────
    print("  Loading bbb_base.parquet ...")
    df = pd.read_parquet(
        BBB_BASE_PATH,
        filters=[
            ("batter", "==", batter),
            ("bowler", "==", bowler),
        ]
    )

    # Exclude super overs (matches official stats convention)
    df = df[~df["is_super_over"]]

    if df.empty:
        print(f"\n  No deliveries found for {batter} vs {bowler}.")
        print("  Check name spelling or use --search to find exact unique_name.")
        return

    print(f"  {len(df):,} deliveries found across all competitions.\n")

    # ── Aggregate function ─────────────────────────────────────────
    def agg(grp):
        balls     = int((grp["is_legal"] | grp["is_noball"]).sum())
        runs      = int(grp["runs_batter"].sum())
        dots      = int(grp["is_dot"].sum())
        fours     = int(grp["is_four"].sum())
        sixes     = int(grp["is_six"].sum())
        dismissed = int(grp["bowl_wicket"].sum())
        sr        = safe_div(runs * 100, balls, 1)
        dot_pct   = safe_div(dots * 100, balls, 1)
        return {
            "Balls": balls, "Runs": runs, "Dismissed": dismissed,
            "SR": sr, "Dots": dots, "Dot%": dot_pct,
            "4s": fours, "6s": sixes,
        }

    # ── Section 1: Career summary (all competitions, all phases) ──
    career = agg(df)
    print(f"  ── CAREER (all competitions) {'─'*27}")
    print(f"  Balls  Runs  Dismissed  SR      Dots  Dot%   4s  6s")
    print(f"  {career['Balls']:<6} {career['Runs']:<5} {career['Dismissed']:<10} "
          f"{str(career['SR']):<7} {career['Dots']:<5} {str(career['Dot%']):<6} "
          f"{career['4s']:<3} {career['6s']}")

    # ── Section 2: By competition ──────────────────────────────────
    print(f"\n  ── BY COMPETITION {'─'*38}")
    header = f"  {'Competition':<22} {'Balls':<6} {'Runs':<6} {'Dis':<5} {'SR':<8} {'Dot%'}"
    print(header)
    print("  " + "─" * 54)

    comp_order = ["IPL", "T20I", "BBL", "PSL", "SA20", "CPL",
                  "T20 Blast", "ILT20", "The Hundred", "LPL",
                  "CSA T20 Challenge", "Super Smash", "MSL", "MLC", "BPL"]

    comps_in_data = df["competition"].unique().tolist()
    # Show in preferred order, then any remaining
    ordered = [c for c in comp_order if c in comps_in_data]
    ordered += [c for c in comps_in_data if c not in ordered]

    for comp in ordered:
        grp = df[df["competition"] == comp]
        if grp.empty:
            continue
        s = agg(grp)
        if s["Balls"] < min_balls:
            continue
        print(f"  {comp:<22} {s['Balls']:<6} {s['Runs']:<6} {s['Dismissed']:<5} "
              f"{str(s['SR']):<8} {s['Dot%']}")

    # ── Section 3: By phase (career across all competitions) ───────
    print(f"\n  ── BY PHASE (career) {'─'*35}")
    phase_order = [("PP", "Powerplay  (ov 0-5)"),
                   ("MID", "Middle     (ov 6-14)"),
                   ("DEATH", "Death      (ov 15-19)")]
    header2 = f"  {'Phase':<22} {'Balls':<6} {'Runs':<6} {'Dis':<5} {'SR':<8} {'Dot%'}"
    print(header2)
    print("  " + "─" * 54)
    for phase_key, phase_label in phase_order:
        grp = df[df["phase"] == phase_key]
        if grp.empty:
            continue
        s = agg(grp)
        if s["Balls"] < min_balls:
            continue
        print(f"  {phase_label:<22} {s['Balls']:<6} {s['Runs']:<6} {s['Dismissed']:<5} "
              f"{str(s['SR']):<8} {s['Dot%']}")

    # ── Section 4: IPL phase breakdown (if IPL data exists) ────────
    ipl_df = df[df["is_ipl"] & (df["season"] >= 2008)]
    if not ipl_df.empty:
        print(f"\n  ── IPL PHASE BREAKDOWN {'─'*32}")
        print(header2)
        print("  " + "─" * 54)
        for phase_key, phase_label in phase_order:
            grp = ipl_df[ipl_df["phase"] == phase_key]
            if grp.empty:
                continue
            s = agg(grp)
            if s["Balls"] < min_balls:
                continue
            print(f"  {phase_label:<22} {s['Balls']:<6} {s['Runs']:<6} {s['Dismissed']:<5} "
                  f"{str(s['SR']):<8} {s['Dot%']}")

        # IPL season-by-season
        seasons = sorted(ipl_df["season"].unique())
        if len(seasons) > 1:
            print(f"\n  ── IPL SEASON BY SEASON {'─'*30}")
            hdr3 = f"  {'Season':<10} {'Balls':<6} {'Runs':<6} {'Dis':<5} {'SR':<8} {'Dot%'}"
            print(hdr3)
            print("  " + "─" * 44)
            for season in seasons:
                grp = ipl_df[ipl_df["season"] == season]
                s = agg(grp)
                if s["Balls"] < min_balls:
                    continue
                print(f"  IPL {season:<6} {s['Balls']:<6} {s['Runs']:<6} {s['Dismissed']:<5} "
                      f"{str(s['SR']):<8} {s['Dot%']}")

    # ── Section 5: T20I breakdown (if exists) ──────────────────────
    t20i_df = df[df["is_t20i"]]
    if not t20i_df.empty:
        print(f"\n  ── T20I PHASE BREAKDOWN {'─'*31}")
        print(header2)
        print("  " + "─" * 54)
        for phase_key, phase_label in phase_order:
            grp = t20i_df[t20i_df["phase"] == phase_key]
            if grp.empty:
                continue
            s = agg(grp)
            if s["Balls"] < min_balls:
                continue
            print(f"  {phase_label:<22} {s['Balls']:<6} {s['Runs']:<6} {s['Dismissed']:<5} "
                  f"{str(s['SR']):<8} {s['Dot%']}")

    # ── Section 6: Dismissal detail ────────────────────────────────
    dismissed_df = df[df["bowl_wicket"]]
    if not dismissed_df.empty:
        print(f"\n  ── DISMISSALS ({len(dismissed_df)}) {'─'*38}")
        for _, row in dismissed_df.iterrows():
            comp   = row["competition"]
            season = row["season"]
            phase  = row["phase"]
            over   = row["over"]
            print(f"  {comp} {season}  |  Over {over+1}  |  Phase: {phase}")

    print(f"\n{'='*58}\n")


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Query batter vs bowler matchup from AskAI parquet files"
    )
    parser.add_argument(
        "batter", nargs="?", default="SV Samson",
        help="Batter name (Cricsheet unique_name or display name)"
    )
    parser.add_argument(
        "bowler", nargs="?", default="PJ Cummins",
        help="Bowler name (Cricsheet unique_name or display name)"
    )
    parser.add_argument(
        "--search", metavar="TERM",
        help="Search registry for players matching TERM (to find exact names)"
    )
    parser.add_argument(
        "--min-balls", type=int, default=1,
        help="Minimum balls to show a phase/competition row (default: 1)"
    )
    parser.add_argument(
        "--data-dir", metavar="PATH",
        help="Override AskAI_Data directory path"
    )
    args = parser.parse_args()

    # Override data dir if provided
    if args.data_dir:
        ASKAI_DATA_DIR = args.data_dir
        BBB_BASE_PATH  = os.path.join(ASKAI_DATA_DIR, "bbb_base.parquet")
        PLAYERS_PATH   = os.path.join(ASKAI_DATA_DIR, "players.parquet")
        PLAYER_INDEX   = os.path.join(ASKAI_DATA_DIR, "player_index.json")
        REGISTRY_PATH  = os.path.join(ASKAI_DATA_DIR, "player_registry.parquet")

    if args.search:
        search_players(args.search)
    else:
        query_matchup(args.batter, args.bowler, min_balls=args.min_balls)
