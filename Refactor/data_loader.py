import pandas as pd
import numpy as np
import os
import re

# ── Path to your dashboard Excel ──────────────────────────────────────────────
_EXCEL_PATH = os.path.join(os.path.dirname(__file__), "IPL2026_Dashboard.xlsx")

# ── Module-level state ─────────────────────────────────────────────────────────
_loaded = False

players_df      = None   # Collated_Data (250 players)
standings_df    = None   # IPL26_Standings
vs_team_df      = None   # VsTeam_Data
venue_df        = None   # Venue_Data

# Name resolution maps built at load time
_name_map       = {}     # lowercase variant → canonical Player name
_player_names   = []     # sorted list for fuzzy search

# ── IPL titles (stable history, hardcoded) ─────────────────────────────────────
IPL_TITLES = {
    "Mumbai Indians":              5,
    "Chennai Super Kings":         5,
    "Kolkata Knight Riders":       3,
    "Rajasthan Royals":            1,
    "Sunrisers Hyderabad":         1,   # 2016 only — 2009 belongs to defunct Deccan Chargers (separate franchise)
    "Gujarat Titans":              1,
    "Royal Challengers Bengaluru": 1,
    "Delhi Capitals":              0,
    "Punjab Kings":                0,
    "Lucknow Super Giants":        0,
}


def _safe(val):
    """Return None for NaN/missing, else the value."""
    if val is None:
        return None
    try:
        if np.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _build_name_map(df):
    """Build every reasonable lowercase variant that a user might type."""
    name_map = {}
    for _, row in df.iterrows():
        canonical = row["Player"]
        candidates = [
            canonical,
            row.get("Cricsheet Name", ""),
            row.get("Full Name", ""),
        ]
        for raw in candidates:
            if not raw or (isinstance(raw, float) and np.isnan(raw)):
                continue
            raw = str(raw)
            key = raw.lower().strip()
            name_map[key] = canonical
            # last name only
            parts = key.split()
            if len(parts) >= 2:
                name_map[parts[-1]] = canonical
                name_map[parts[0] + " " + parts[-1]] = canonical
            # initials-style: "v kohli" → "virat kohli"
            if len(parts) >= 2 and len(parts[0]) <= 2:
                name_map[" ".join(parts[1:])] = canonical
    return name_map


def load():
    """Load all sheets once. Safe to call multiple times."""
    global _loaded, players_df, standings_df, vs_team_df, venue_df
    global _name_map, _player_names

    if _loaded:
        return

    xl = pd.read_excel(_EXCEL_PATH, sheet_name=None)

    players_df   = xl["Collated_Data"]
    standings_df = xl["IPL26_Standings"]
    vs_team_df   = xl["VsTeam_Data"]
    venue_df     = xl["Venue_Data"]

    _name_map    = _build_name_map(players_df)
    _player_names = sorted(players_df["Player"].tolist())

    _loaded = True
    print("IPL dashboard loaded —", len(players_df), "players")


# ── Name resolution ────────────────────────────────────────────────────────────

def resolve_player(name: str):
    """
    Return the canonical Player name from the dashboard, or None if not found.
    Handles full names, last names, Cricsheet short names, initials variants.
    """
    load()
    key = name.lower().strip()
    if key in _name_map:
        return _name_map[key]
    # partial substring match as last resort
    for pname in _player_names:
        if key in pname.lower():
            return pname
    return None


def all_player_names():
    load()
    return _player_names


# ── Stat helpers ───────────────────────────────────────────────────────────────

def _row(player_name: str):
    """Return the DataFrame row for a resolved player name."""
    load()
    rows = players_df[players_df["Player"] == player_name]
    if rows.empty:
        return None
    return rows.iloc[0]


def get_player_stats(player_name: str, context: str = "IPL") -> dict | None:
    """
    Return a clean stats dict for a player.
    context = "IPL" | "IPL26" | "2025" | "Overall"
    """
    load()
    canonical = resolve_player(player_name)
    if not canonical:
        return None
    row = _row(canonical)
    if row is None:
        return None

    suffix = f"_{context}" if not context.startswith("_") else context

    def g(col):
        return _safe(row.get(col))

    return {
        "name":          canonical,
        "team":          row.get("Team"),
        "role":          row.get("Role"),
        "bat_hand":      row.get("Bat Hand"),
        "bowling_type":  row.get("Bowling Type"),

        # batting
        "innings":       g(f"Innings{suffix}"),
        "runs":          g(f"Runs{suffix}"),
        "avg":           g(f"Batting Avg{suffix}"),
        "sr":            g(f"Batting SR{suffix}"),
        "hs":            g(f"HS{suffix}"),
        "fours":         g(f"_raw_bat_fours{suffix}"),
        "sixes":         g(f"_raw_bat_sixes{suffix}"),
        "fifties_tons":  g(f"50s_100s{suffix}"),

        # bowling
        "wickets":       g(f"Wickets{suffix}"),
        "bowl_avg":      g(f"Bowling Avg{suffix}"),
        "bowl_sr":       g(f"Bowling SR{suffix}"),
        "economy":       g(f"Econ{suffix}"),
        "best_bowling":  g(f"BB{suffix}"),

        # percentiles (IPL career only, most complete)
        "pct_bat_avg_ipl":        g("Batting_Avg_Pct_IPL"),
        "pct_bat_sr_ipl":         g("Batting_SR_Pct_IPL"),
        "pct_bowl_avg_ipl":       g("Bowling_Avg_Pct_IPL"),
        "pct_bowl_econ_ipl":      g("Bowling_Econ_Pct_IPL"),
        "pct_bat_pp_sr_ipl":      g("Bat_PP_SR_Pct_IPL"),
        "pct_bat_mid_sr_ipl":     g("Bat_Mid_SR_Pct_IPL"),
        "pct_bat_death_sr_ipl":   g("Bat_Death_SR_Pct_IPL"),
        "pct_bowl_death_econ_ipl":g("Bowl_Death_Econ_Pct_IPL"),
    }


# ── Leaderboard queries ────────────────────────────────────────────────────────

def top_run_scorers(n: int = 5, context: str = "IPL") -> list[dict]:
    load()
    col = f"Runs_{context}"
    df = players_df.dropna(subset=[col]).sort_values(col, ascending=False).head(n)
    return [
        {
            "rank":    i + 1,
            "player":  r["Player"],
            "team":    r["Team"],
            "runs":    int(r[col]),
            "avg":     _safe(r.get(f"Batting Avg_{context}")),
            "sr":      _safe(r.get(f"Batting SR_{context}")),
            "innings": _safe(r.get(f"Innings_{context}")),
        }
        for i, (_, r) in enumerate(df.iterrows())
    ]


def top_wicket_takers(n: int = 5, context: str = "IPL") -> list[dict]:
    load()
    col = f"Wickets_{context}"
    df = players_df.dropna(subset=[col]).sort_values(col, ascending=False).head(n)
    return [
        {
            "rank":       i + 1,
            "player":     r["Player"],
            "team":       r["Team"],
            "wickets":    int(r[col]),
            "avg":        _safe(r.get(f"Bowling Avg_{context}")),
            "economy":    _safe(r.get(f"Econ_{context}")),
            "best":       r.get(f"BB_{context}"),
        }
        for i, (_, r) in enumerate(df.iterrows())
    ]


def top_six_hitters(n: int = 5, context: str = "IPL") -> list[dict]:
    load()
    col = f"_raw_bat_sixes_{context}"
    df = players_df.dropna(subset=[col]).sort_values(col, ascending=False).head(n)
    return [
        {
            "rank":   i + 1,
            "player": r["Player"],
            "team":   r["Team"],
            "sixes":  int(r[col]),
            "sr":     _safe(r.get(f"Batting SR_{context}")),
        }
        for i, (_, r) in enumerate(df.iterrows())
    ]


def highest_individual_score(context: str = "IPL") -> dict | None:
    load()
    col = f"HS_{context}"
    df = players_df.dropna(subset=[col]).sort_values(col, ascending=False)
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "player": row["Player"],
        "team":   row["Team"],
        "score":  _safe(row[col]),
    }


def ipl_titles_table() -> list[dict]:
    """Returns teams sorted by title count descending."""
    return sorted(
        [{"team": t, "titles": c} for t, c in IPL_TITLES.items()],
        key=lambda x: x["titles"],
        reverse=True,
    )


# ── Points table ───────────────────────────────────────────────────────────────

def get_standings() -> list[dict]:
    load()
    result = []
    for _, r in standings_df.iterrows():
        result.append({
            "position": int(r["Position"]),
            "team":     r["Team"],
            "played":   int(r["Mat"]),
            "won":      int(r["W"]),
            "lost":     int(r["L"]),
            "nr":       int(r["NR"]),
            "points":   int(r["Pts"]),
            "nrr":      float(r["NRR"]),
        })
    return result


# ── Compare two players ────────────────────────────────────────────────────────

def compare_players(name1: str, name2: str, context: str = "IPL") -> dict | None:
    load()
    s1 = get_player_stats(name1, context)
    s2 = get_player_stats(name2, context)
    if not s1 or not s2:
        missing = name1 if not s1 else name2
        return {"error": f"Could not find player: {missing}"}

    def verdict(a, b, higher_is_better=True):
        if a is None or b is None:
            return "n/a"
        return s1["name"] if (a > b) == higher_is_better else s2["name"]

    return {
        "player1": s1,
        "player2": s2,
        "edges": {
            "more_runs":     verdict(s1["runs"],    s2["runs"]),
            "better_avg":    verdict(s1["avg"],     s2["avg"]),
            "better_sr":     verdict(s1["sr"],      s2["sr"]),
            "more_wickets":  verdict(s1["wickets"], s2["wickets"]),
            "better_econ":   verdict(s1["economy"], s2["economy"], higher_is_better=False),
            "more_sixes":    verdict(s1["sixes"],   s2["sixes"]),
        },
    }


# ── Extract two player names from a compare question ──────────────────────────

def extract_compare_names(question: str):
    """
    Parse 'compare Kohli vs Rohit' or 'kohli and rohit sharma' style questions.
    Returns (name1, name2) canonical strings or (None, None).
    """
    load()
    q = question.lower()

    # Split on common separators
    for sep in [" vs ", " versus ", " and ", " with ", " against "]:
        if sep in q:
            # strip leading "compare", "who is better" etc.
            q_clean = re.sub(r"^(compare|who is better|battle|fight)\s*", "", q).strip()
            parts = q_clean.split(sep, 1)
            if len(parts) == 2:
                n1 = resolve_player(parts[0].strip())
                n2 = resolve_player(parts[1].strip())
                if n1 and n2:
                    return n1, n2

    # Fallback: find any two known player names mentioned
    found = []
    for pname in _player_names:
        if pname.lower() in q and pname not in found:
            found.append(pname)
        if len(found) == 2:
            break

    if len(found) == 2:
        return found[0], found[1]

    return None, None
