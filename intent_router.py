import re


# Ordered most-specific → least-specific.
# Each entry: (intent_key, list_of_patterns_any_must_match)
# Patterns are matched against the lowercased question.

_RULES = [

    # ── Compare (must come before runs/wickets to catch "compare runs") ────────
    ("compare", [
        r"\bcompare\b",
        r"\bvs\b",
        r"\bversus\b",
        r"\bwho is better\b",
        r"\bbetter (batsman|bowler|player|cricketer)\b",
        r"\b(battle|head.?to.?head)\b",
    ]),

    # ── Points table / standings ───────────────────────────────────────────────
    ("points_table", [
        r"\bpoints table\b",
        r"\bstandings\b",
        r"\bleague table\b",
        r"\bwho (is|are) (on )?top\b",
        r"\btable (leader|topper)\b",
        r"\bwhich team (is|are) (leading|top|first|ahead)\b",
    ]),

    # ── Live / today's matches ─────────────────────────────────────────────────
    ("live_matches", [
        r"\blive (match|game|score)\b",
        r"\btoday.?s? (match|game)\b",
        r"\bcurrent(ly)? (playing|live)\b",
        r"\bwhat.?s (happening|on) (today|now|live)\b",
    ]),

    # ── Titles / championships ────────────────────────────────────────────────
    ("titles", [
        r"\b(most|how many) (ipl )?titles\b",
        r"\b(won|win).*(championship|title|trophy)\b",
        r"\bmost (successful|dominant) team\b",
        r"\bwhich team has won (the most|more)\b",
        r"\bipl champion\b",
    ]),

    # ── Highest individual score ───────────────────────────────────────────────
    ("highest_score", [
        r"\bhighest (individual |ipl )?score\b",
        r"\bbiggest (ipl )?innings\b",
        r"\bmost runs in (a|an|one|single) (match|innings|game)\b",
        r"\brecord (ipl )?score\b",
    ]),

    # ── Most runs (career leaderboard) ────────────────────────────────────────
    ("runs", [
        r"\bmost (ipl )?runs\b",
        r"\bhighest (ipl )?run scorer\b",
        r"\bwho (has )?scored (the )?most\b",
        r"\btop (run |ipl )?scorer\b",
        r"\brun (king|leader|chart)\b",
    ]),

    # ── Most wickets ──────────────────────────────────────────────────────────
    ("wickets", [
        r"\bmost (ipl )?wickets\b",
        r"\btop (ipl )?wicket.taker\b",
        r"\bwho (has )?taken (the )?most wickets\b",
        r"\bwicket (king|leader|chart)\b",
        r"\bbest bowler (in ipl|of ipl|all time)\b",
    ]),

    # ── Most sixes ────────────────────────────────────────────────────────────
    ("sixes", [
        r"\bmost (ipl )?sixes\b",
        r"\bbiggest (ipl )?six.?hitter\b",
        r"\bwho (has )?hit (the )?most six\b",
        r"\bsix (king|machine|leader)\b",
    ]),

    # ── Player profile / info ─────────────────────────────────────────────────
    ("player_info", [
        r"\bwho is\b",
        r"\btell me about\b",
        r"\binfo (on|about)\b",
        r"\bplayer (profile|stats|info)\b",
    ]),

    # ── Catch-all: open knowledge question ───────────────────────────────────
    ("knowledge", []),   # always matches — keep last
]


def detect_intent(question: str) -> str:
    q = question.lower()
    for intent, patterns in _RULES:
        if not patterns:        # "knowledge" catch-all
            return intent
        for pat in patterns:
            if re.search(pat, q):
                return intent
    return "knowledge"
