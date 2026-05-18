import os
import random

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

# ── Local modules ──────────────────────────────────────────────────────────────
import data_loader as dl
from intent_router import detect_intent
from memory_store import save_context, get_context
from feed_engine import get_feed
from teams_engine import get_teams
from players_engine import get_players
from matches_engine import get_matches
from live_matches import get_live_matches

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DATA_NOTE     = "\n\n📊 Stats sourced from Cricsheet — IPL 2008 to 2026, all T20 formats."
DATA_NOTE_IPL = "\n\n📊 IPL career stats, 2008–2026 (all seasons)."
DATA_NOTE_26  = "\n\n📊 IPL 2026 season stats only."
DATA_NOTE_T20 = "\n\n📊 All T20 Internationals (career)."

# Load data at startup
try:
    dl.load()
except Exception as e:
    print("Data layer load failed at startup:", e)


# ── Groq helper (open-ended knowledge questions only) ─────────────────────────

def _groq_answer(question: str) -> str:
    """
    Call Groq only for open-ended questions where we have no structured data.
    Strict system prompt prevents fabricating statistics.
    """
    context_turns = get_context()
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": t["question"] if i % 2 == 0 else t["answer"]}
        for i, t in enumerate(context_turns)
    ]

    system = (
        "You are AskSportsFan360, a cricket analyst assistant. "
        "Answer questions about IPL cricket: history, rules, format, team culture, player careers, tournament trivia. "
        "STRICT RULES: "
        "1. Never invent or estimate statistics — if you don't know a number say so. "
        "2. Keep answers concise (3–5 sentences max). "
        "3. Do not discuss non-cricket topics. "
        "4. If asked for stats like runs, wickets, averages — say the data system will provide those, do not guess."
    )

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": question}]

    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=300,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("Groq error:", e)
        return "Sorry, I'm unable to answer that right now. Please try again."


# ── Formatters ─────────────────────────────────────────────────────────────────

def _fmt_num(val, decimals=1):
    if val is None:
        return "N/A"
    try:
        return f"{val:.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def _leaderboard_text(rows: list, stat_key: str, stat_label: str) -> str:
    lines = []
    for r in rows:
        val = r.get(stat_key)
        val_str = str(int(val)) if val is not None and val == int(val) else _fmt_num(val)
        lines.append(f"{r['rank']}. {r['player']} ({r['team']}) — {val_str} {stat_label}")
    return "\n".join(lines)


def _player_summary(s: dict, context_label: str = "IPL career") -> str:
    nation = s.get("nation") or ""
    header = f"{s['name']} ({nation})" if nation else s["name"]
    parts  = [header]

    bat_parts = []
    if s.get("runs") is not None:
        bat_parts.append(f"{int(s['runs'])} runs")
    if s.get("avg") is not None:
        bat_parts.append(f"avg {_fmt_num(s['avg'])}")
    if s.get("sr") is not None:
        bat_parts.append(f"SR {_fmt_num(s['sr'])}")
    if s.get("sixes") is not None:
        bat_parts.append(f"{int(s['sixes'])} sixes")
    if s.get("fours") is not None:
        bat_parts.append(f"{int(s['fours'])} fours")
    if bat_parts:
        parts.append(f"Batting ({context_label}): {', '.join(bat_parts)}")

    bowl_parts = []
    if s.get("wickets") is not None and s["wickets"] > 0:
        bowl_parts.append(f"{int(s['wickets'])} wickets")
    if s.get("bowl_avg") is not None:
        bowl_parts.append(f"avg {_fmt_num(s['bowl_avg'])}")
    if s.get("economy") is not None:
        bowl_parts.append(f"econ {_fmt_num(s['economy'])}")
    if bowl_parts:
        parts.append(f"Bowling ({context_label}): {', '.join(bowl_parts)}")

    return " | ".join(parts)


def _compare_text(result: dict) -> str:
    s1 = result["player1"]
    s2 = result["player2"]
    edges = result["edges"]

    lines = [f"**{s1['name']}** vs **{s2['name']}** — IPL career comparison\n"]

    def bat_row(s):
        r   = s.get("runs")
        avg = s.get("avg")
        sr  = s.get("sr")
        sx  = s.get("sixes")
        return (
            f"  Runs: {int(r) if r else 'N/A'}  |  "
            f"Avg: {_fmt_num(avg)}  |  "
            f"SR: {_fmt_num(sr)}  |  "
            f"Sixes: {int(sx) if sx else 'N/A'}"
        )

    lines.append(f"{s1['name']}\n{bat_row(s1)}")
    lines.append(f"{s2['name']}\n{bat_row(s2)}")

    edge_summary = []
    if edges.get("more_runs") not in (None, "n/a"):
        edge_summary.append(f"More runs: {edges['more_runs']}")
    if edges.get("better_avg") not in (None, "n/a"):
        edge_summary.append(f"Better avg: {edges['better_avg']}")
    if edges.get("better_sr") not in (None, "n/a"):
        edge_summary.append(f"Better SR: {edges['better_sr']}")
    if edge_summary:
        lines.append("\nEdge: " + "  |  ".join(edge_summary))

    return "\n".join(lines)


# ── Main /ask route ────────────────────────────────────────────────────────────

@app.get("/ask")
def ask(question: str):
    if not dl._loaded:
        try:
            dl.load()
        except Exception as e:
            return {"answer": "Data is loading, please try again in a moment.", "chart_title": "", "chart_data": []}

    intent = detect_intent(question)
    answer = ""
    chart_title = ""
    chart_data = []

    # ── IPL career runs leaderboard ───────────────────────────────────────────
    if intent == "runs":
        rows = dl.top_run_scorers(n=5, prefix="IPL")
        chart_title = "Top 5 IPL run scorers (all-time)"
        chart_data = [{"player": r["player"], "value": r["runs"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads all IPL run scorers with **{rows[0]['runs']:,} runs** "
            f"(avg {_fmt_num(rows[0]['avg'])}, SR {_fmt_num(rows[0]['sr'])}).\n\n"
            + _leaderboard_text(rows, "runs", "runs")
            + DATA_NOTE_IPL
        )

    # ── IPL career wickets leaderboard ────────────────────────────────────────
    elif intent == "wickets":
        rows = dl.top_wicket_takers(n=5, prefix="IPL")
        chart_title = "Top 5 IPL wicket takers (all-time)"
        chart_data = [{"player": r["player"], "value": r["wickets"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads the IPL wicket charts with **{rows[0]['wickets']} wickets** "
            f"(avg {_fmt_num(rows[0]['avg'])}, econ {_fmt_num(rows[0]['economy'])}).\n\n"
            + _leaderboard_text(rows, "wickets", "wickets")
            + DATA_NOTE_IPL
        )

    # ── Sixes leaderboard ─────────────────────────────────────────────────────
    elif intent == "sixes":
        rows = dl.top_six_hitters(n=5, prefix="IPL")
        chart_title = "Top 5 IPL six hitters (all-time)"
        chart_data = [{"player": r["player"], "value": r["sixes"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** has hit the most sixes in IPL history — **{rows[0]['sixes']} sixes**.\n\n"
            + _leaderboard_text(rows, "sixes", "sixes")
            + DATA_NOTE_IPL
        )

    # ── Highest individual score ──────────────────────────────────────────────
    elif intent == "highest_score":
        answer = _groq_answer(question)

    # ── Titles ────────────────────────────────────────────────────────────────
    elif intent == "titles":
        table = dl.ipl_titles_table()
        winners = [t for t in table if t["titles"] > 0]
        chart_title = "IPL titles by team"
        chart_data = [{"player": t["team"], "value": t["titles"]} for t in winners]
        top = winners[0]
        lines = [f"{t['team']}: {t['titles']}" for t in winners]
        answer = (
            f"**{top['team']}** are joint-most successful with **{top['titles']} IPL titles**.\n\n"
            + "\n".join(lines)
        )

    # ── Points table ──────────────────────────────────────────────────────────
    elif intent == "points_table":
        rows = dl.get_standings()
        chart_title = "IPL 2026 points table"
        chart_data = [{"player": r["team"], "value": r["points"]} for r in rows]
        lines = [
            f"{r['position']}. **{r['team']}** — {r['points']} pts  (W{r['won']} L{r['lost']} NRR {r['nrr']:+.3f})"
            for r in rows
        ]
        leader = rows[0]
        answer = (
            f"**{leader['team']}** top the IPL 2026 standings with **{leader['points']} points**.\n\n"
            + "\n".join(lines)
        )

    # ── IPL 2026 season runs ──────────────────────────────────────────────────
    elif intent == "ipl26_runs":
        rows = dl.top_run_scorers_ipl26(n=5)
        chart_title = "Top 5 run scorers — IPL 2026"
        chart_data = [{"player": r["player"], "value": r["runs"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads the IPL 2026 run charts with **{rows[0]['runs']:,} runs** "
            f"(avg {_fmt_num(rows[0]['avg'])}, SR {_fmt_num(rows[0]['sr'])}).\n\n"
            + _leaderboard_text(rows, "runs", "runs")
            + DATA_NOTE_26
        )

    # ── IPL 2026 season wickets ───────────────────────────────────────────────
    elif intent == "ipl26_wickets":
        rows = dl.top_wicket_takers_ipl26(n=5)
        chart_title = "Top 5 wicket takers — IPL 2026"
        chart_data = [{"player": r["player"], "value": r["wickets"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads IPL 2026 wickets with **{rows[0]['wickets']} wickets** "
            f"(econ {_fmt_num(rows[0]['economy'])}).\n\n"
            + _leaderboard_text(rows, "wickets", "wickets")
            + DATA_NOTE_26
        )

    # ── Form window (2025) ────────────────────────────────────────────────────
    elif intent == "form_runs":
        rows = dl.top_form_batters(n=5)
        chart_title = "Top 5 in-form batters (2025)"
        chart_data = [{"player": r["player"], "value": r["runs"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** has been the standout batter in 2025 with **{rows[0]['runs']:,} runs** "
            f"(avg {_fmt_num(rows[0]['avg'])}, SR {_fmt_num(rows[0]['sr'])}).\n\n"
            + _leaderboard_text(rows, "runs", "runs")
            + "\n\n📊 Stats from Jan 2025 onwards, all T20 formats."
        )

    # ── T20I runs ─────────────────────────────────────────────────────────────
    elif intent == "t20i_runs":
        rows = dl.top_run_scorers(n=5, prefix="T20I")
        chart_title = "Top 5 T20I run scorers (all-time)"
        chart_data = [{"player": r["player"], "value": r["runs"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads all T20I run scorers with **{rows[0]['runs']:,} runs** "
            f"(avg {_fmt_num(rows[0]['avg'])}, SR {_fmt_num(rows[0]['sr'])}).\n\n"
            + _leaderboard_text(rows, "runs", "runs")
            + DATA_NOTE_T20
        )

    # ── T20I wickets ──────────────────────────────────────────────────────────
    elif intent == "t20i_wickets":
        rows = dl.top_wicket_takers(n=5, prefix="T20I")
        chart_title = "Top 5 T20I wicket takers (all-time)"
        chart_data = [{"player": r["player"], "value": r["wickets"]} for r in rows]
        answer = (
            f"**{rows[0]['player']}** leads all T20I wicket takers with **{rows[0]['wickets']} wickets** "
            f"(avg {_fmt_num(rows[0]['avg'])}, econ {_fmt_num(rows[0]['economy'])}).\n\n"
            + _leaderboard_text(rows, "wickets", "wickets")
            + DATA_NOTE_T20
        )

    # ── Matchup: batter vs bowler ─────────────────────────────────────────────
    elif intent == "matchup":
        n1, n2 = dl.extract_compare_names(question)
        if n1 and n2:
            # Determine who is batter / bowler by trying both orders
            result = dl.get_matchup(n1, n2, competition="IPL", phase="ALL")
            if not result:
                result = dl.get_matchup(n2, n1, competition="IPL", phase="ALL")
                if result:
                    n1, n2 = n2, n1  # swap so n1=batter, n2=bowler

            if result:
                chart_title = f"{result['batter']} vs {result['bowler']} — IPL matchup"
                chart_data = [
                    {"player": "Balls",        "value": result["balls"]},
                    {"player": "Runs",         "value": result["runs"]},
                    {"player": "Dismissals",   "value": result["dismissed"]},
                    {"player": "Fours",        "value": result["fours"]},
                    {"player": "Sixes",        "value": result["sixes"]},
                ]
                answer = (
                    f"**{result['batter']}** vs **{result['bowler']}** in IPL (all phases):\n\n"
                    f"Balls faced: {result['balls']}  |  Runs: {result['runs']}  |  "
                    f"Dismissals: {result['dismissed']}\n"
                    f"Strike rate: {_fmt_num(result['sr'])}  |  "
                    f"Dot ball %: {_fmt_num(result['dot_pct'])}%  |  "
                    f"Dismissal rate: {_fmt_num(result['dismiss_rate'])}%"
                    + DATA_NOTE_IPL
                )
            else:
                # Fall back to career
                result = dl.get_matchup(n1, n2, competition="Career", phase="ALL")
                if result:
                    answer = (
                        f"**{result['batter']}** vs **{result['bowler']}** (career, all T20s):\n\n"
                        f"Balls: {result['balls']}  |  Runs: {result['runs']}  |  "
                        f"Dismissals: {result['dismissed']}  |  SR: {_fmt_num(result['sr'])}"
                        + DATA_NOTE
                    )
                else:
                    answer = (
                        f"Not enough data found for that matchup. "
                        f"Try asking: 'How does Kohli bat against Bumrah?'"
                    )
        else:
            answer = (
                "I couldn't identify the two players. "
                "Try: 'How does Kohli bat against Bumrah?'"
            )

    # ── Compare two players ───────────────────────────────────────────────────
    elif intent == "compare":
        n1, n2 = dl.extract_compare_names(question)
        if n1 and n2:
            result = dl.compare_players(n1, n2, prefix="IPL")
            if "error" in result:
                answer = result["error"]
            else:
                s1, s2 = result["player1"], result["player2"]
                chart_title = f"{s1['name']} vs {s2['name']} — IPL stats"
                chart_data = [
                    {"player": s1["name"], "metric": "Runs",    "value": s1["runs"] or 0},
                    {"player": s2["name"], "metric": "Runs",    "value": s2["runs"] or 0},
                    {"player": s1["name"], "metric": "Wickets", "value": s1["wickets"] or 0},
                    {"player": s2["name"], "metric": "Wickets", "value": s2["wickets"] or 0},
                ]
                answer = _compare_text(result) + DATA_NOTE_IPL
        else:
            answer = (
                "I couldn't identify two players to compare. "
                "Try: 'Compare Virat Kohli vs Rohit Sharma'."
            )

    # ── Player info ───────────────────────────────────────────────────────────
    elif intent == "player_info":
        unique_name = None
        q_lower = question.lower()

        # Try multi-word names first (longest match wins)
        for pname in sorted(dl.all_player_names(), key=len, reverse=True):
            if pname.lower() in q_lower:
                unique_name = dl.resolve_player(pname)
                break

        # Fallback: word-by-word
        if not unique_name:
            for word in q_lower.split():
                unique_name = dl.resolve_player(word)
                if unique_name:
                    break

        if unique_name:
            stats = dl.get_player_stats(unique_name, prefix="IPL")
            if stats:
                answer = _player_summary(stats, context_label="IPL career") + DATA_NOTE_IPL
            else:
                answer = f"Found {dl.resolve_display(unique_name)} but couldn't load their stats."
        else:
            answer = _groq_answer(question)

    # ── Open knowledge → Groq ─────────────────────────────────────────────────
    else:
        answer = _groq_answer(question)

    # Save to memory
    save_context(question, answer)

    return {
        "answer": answer,
        "chart_title": chart_title,
        "chart_data": chart_data,
    }


# ── All other existing routes (unchanged) ─────────────────────────────────────

@app.get("/")
def home():
    return {"message": "SportsFan360 AI running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/feed")
def feed():
    return get_feed()


@app.get("/teams")
def teams():
    return get_teams()


@app.get("/players")
def players(team: str = None):
    return get_players(team)


@app.get("/matches")
def matches():
    from matches_engine import get_matches as _gm
    return _gm()


@app.get("/standings")
def standings():
    return {"standings": dl.get_standings()}


@app.get("/live-matches")
def live_matches_route():
    return get_live_matches()


@app.get("/player-list")
def player_list():
    return {"players": dl.all_player_names()}


@app.get("/player-battle")
def player_battle(p1: str, p2: str):
    result = dl.compare_players(p1, p2, context="IPL")
    if "error" in result:
        return {"error": result["error"]}

    s1 = result["player1"]
    s2 = result["player2"]
    impact1 = (s1["runs"] or 0) + (s1["wickets"] or 0) * 20 + (s1["sixes"] or 0) * 2
    impact2 = (s2["runs"] or 0) + (s2["wickets"] or 0) * 20 + (s2["sixes"] or 0) * 2

    return {
        "player1":  s1["name"],
        "player2":  s2["name"],
        "stats1":   s1,
        "stats2":   s2,
        "impact1":  impact1,
        "impact2":  impact2,
        "winner":   s1["name"] if impact1 >= impact2 else s2["name"],
    }


@app.get("/player-shotmap")
def player_shotmap(player: str):
    return {
        "data": {
            "off":      random.randint(10, 100),
            "leg":      random.randint(10, 100),
            "straight": random.randint(10, 100),
        }
    }


@app.get("/match-commentary")
def match_commentary(team1: str, team2: str, status: str):
    prompt = (
        f"Match: {team1} vs {team2}\nStatus: {status}\n"
        "Give a short live match commentary in 2-3 lines."
    )
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional cricket commentator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=150,
        )
        commentary = res.choices[0].message.content.strip()
    except Exception as e:
        print("Commentary error:", e)
        commentary = f"{team1} vs {team2} is in progress."

    return {"commentary": commentary}


@app.get("/daily-challenge")
def daily_challenge(matchId: str = "default"):
    try:
        if "-" in matchId:
            parts = matchId.split("-")
            team1, team2 = parts[0], parts[1]
        else:
            team1, team2 = "MI", "CSK"
    except Exception:
        team1, team2 = "MI", "CSK"

    # Pull actual squad batters and bowlers from the loaded data
    try:
        t1_batters = dl.players_df[
            (dl.players_df["Team"].str.contains(team1, case=False, na=False)) &
            (dl.players_df["Role"].isin(["Batter", "Allrounder"]))
        ]["Player"].tolist()
        t2_batters = dl.players_df[
            (dl.players_df["Team"].str.contains(team2, case=False, na=False)) &
            (dl.players_df["Role"].isin(["Batter", "Allrounder"]))
        ]["Player"].tolist()
        all_batters = list(set(t1_batters + t2_batters))

        t1_bowlers = dl.players_df[
            (dl.players_df["Team"].str.contains(team1, case=False, na=False)) &
            (dl.players_df["Role"].isin(["Bowler", "Allrounder"]))
        ]["Player"].tolist()
        t2_bowlers = dl.players_df[
            (dl.players_df["Team"].str.contains(team2, case=False, na=False)) &
            (dl.players_df["Role"].isin(["Bowler", "Allrounder"]))
        ]["Player"].tolist()
        all_bowlers = list(set(t1_bowlers + t2_bowlers))

        batsmen = random.sample(all_batters, min(4, len(all_batters)))
        bowlers = random.sample(all_bowlers, min(4, len(all_bowlers)))
    except Exception:
        batsmen = ["Virat Kohli", "Rohit Sharma", "KL Rahul", "Shubman Gill"]
        bowlers  = ["Jasprit Bumrah", "Rashid Khan", "Yuzvendra Chahal", "Mohammed Shami"]

    teams = [team1, team2]
    random.shuffle(teams)

    return {
        "matchId":   matchId,
        "questions": [
            {"id": "winner",      "question": "🏆 Who will win?",        "options": teams},
            {"id": "top_batsman", "question": "🔥 Top Batsman?",         "options": batsmen},
            {"id": "top_bowler",  "question": "🎯 Top Bowler?",          "options": bowlers},
            {"id": "total_runs",  "question": "💥 Total Runs?",          "options": ["<150", "150-170", "170-190", "190+"]},
            {"id": "toss",        "question": "⚡ Toss Winner?",         "options": teams},
            {"id": "powerplay",   "question": "🎯 Powerplay Score?",     "options": ["<40", "40-60", "60-80", "80+"]},
        ],
    }
