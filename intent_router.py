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

    # ── Matchup: batter vs bowler head-to-head ────────────────────────────────
    ("matchup", [
        r"\b(how does|how do|how has|how have)\b.*(bat|bowl|face|perform|play).*(against|vs|versus)\b",
        r"\b(against|vs|versus)\b.*(how does|how do|how has|how have)\b",
        r"\bmatchup\b",
        r"\bhead.?to.?head\b",
        r"\b(batter|batsman).*(bowler|bowling)\b",
        r"\b(bowler|bowling).*(batter|batsman)\b",
        r"\bfaced\b.*\btimes\b",
        r"\brecord against\b",
        r"\bhow (does|has) \w+ (bat|play) (against|vs)\b",
        r"\bhow (does|has) \w+ (bowl|perform) (against|to|vs)\b",
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

    # ── IPL 2026 season stats ─────────────────────────────────────────────────
    ("ipl26_runs", [
        r"\b(ipl 2026|ipl26|this season).*(most runs|top scorer|run scorer|orange cap)\b",
        r"\b(most runs|top scorer|run scorer|orange cap).*(ipl 2026|ipl26|this season)\b",
        r"\b(2026 ipl|current season).*(run|scorer)\b",
    ]),

    ("ipl26_wickets", [
        r"\b(ipl 2026|ipl26|this season).*(most wickets|top wicket|purple cap)\b",
        r"\b(most wickets|top wicket|purple cap).*(ipl 2026|ipl26|this season)\b",
        r"\b(2026 ipl|current season).*(wicket)\b",
    ]),

    # ── Form / recent stats ───────────────────────────────────────────────────
    ("form_runs", [
        r"\b(form|recent|in form|current form|best form)\b.*(batsman|batter|scorer)\b",
        r"\b(best|top).*(batsman|batter).*(form|recent|2025)\b",
        r"\bwho (is|are) (in )?best form\b",
        r"\btop scorer.*(2025|recent|last (year|season))\b",
    ]),

    # ── Most runs (IPL career leaderboard) ────────────────────────────────────
    ("runs", [
        r"\bmost (ipl )?runs\b",
        r"\bhighest (ipl )?run scorer\b",
        r"\bwho (has )?scored (the )?most\b",
        r"\btop (run |ipl )?scorer\b",
        r"\brun (king|leader|chart)\b",
        r"\bmost runs (in ipl|in the ipl|all.?time)\b",
        r"\bipl run.?scorer\b",
    ]),

    # ── Most wickets ──────────────────────────────────────────────────────────
    ("wickets", [
        r"\bmost (ipl )?wickets\b",
        r"\btop (ipl )?wicket.taker\b",
        r"\bwho (has )?taken (the )?most wickets\b",
        r"\bwicket (king|leader|chart)\b",
        r"\bbest bowler (in ipl|of ipl|all time)\b",
        r"\bmost wickets (in ipl|in the ipl|all.?time)\b",
    ]),

    # ── Most sixes ────────────────────────────────────────────────────────────
    ("sixes", [
        r"\bmost (ipl )?sixes\b",
        r"\bbiggest (ipl )?six.?hitter\b",
        r"\bwho (has )?hit (the )?most six\b",
        r"\bsix (king|machine|leader)\b",
    ]),

    # ── T20I stats ────────────────────────────────────────────────────────────
    ("t20i_runs", [
        r"\bmost t20i runs\b",
        r"\btop t20i (run )?scorer\b",
        r"\bmost runs in t20(i| international)\b",
        r"\bt20 international.*(most runs|top scorer)\b",
    ]),

    ("t20i_wickets", [
        r"\bmost t20i wickets\b",
        r"\btop t20i wicket.taker\b",
        r"\bmost wickets in t20(i| international)\b",
        r"\bt20 international.*(most wickets|top wicket)\b",
    ]),

    # ── Player profile / info ─────────────────────────────────────────────────
    ("player_info", [
        r"\bwho is\b",
        r"\btell me about\b",
        r"\binfo (on|about)\b",
        r"\bplayer (profile|stats|info)\b",
        r"\bstats (of|for)\b",
        r"\bhow (many|much).*(run|wicket|six|average|economy)\b",
        r"\bcareer (stats|record|numbers)\b",
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
