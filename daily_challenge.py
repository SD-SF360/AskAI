from flask import Blueprint, request, jsonify
import random

daily_challenge = Blueprint("daily_challenge", __name__)


@daily_challenge.route("/daily-challenge")
def get_daily_challenge():

    match_id = request.args.get("matchId", "default")

    # 🔥 Extract teams from matchId if available
    try:
        if "-" in match_id:
            parts = match_id.split("-")
            team1 = parts[0]
            team2 = parts[1]
        else:
            team1 = "MI"
            team2 = "CSK"
    except:
        team1 = "MI"
        team2 = "CSK"

    # 🔥 PLAYER POOLS (can later connect to DB/API)
    batsmen_pool = [
        "Rohit Sharma", "Suryakumar Yadav", "MS Dhoni",
        "Ruturaj Gaikwad", "Virat Kohli", "Faf du Plessis",
        "KL Rahul", "Shubman Gill"
    ]

    bowlers_pool = [
        "Bumrah", "Jadeja", "Pathirana",
        "Chahar", "Siraj", "Rashid Khan",
        "Kuldeep Yadav"
    ]

    # 🔥 Randomize players daily (makes it fun)
    batsmen = random.sample(batsmen_pool, 4)
    bowlers = random.sample(bowlers_pool, 4)

    # 🔥 Shuffle team options for unpredictability
    teams = [team1, team2]
    random.shuffle(teams)

    data = {
        "matchId": match_id,
        "questions": [
            {
                "id": "winner",
                "question": "🏆 Who will win?",
                "options": teams
            },
            {
                "id": "top_batsman",
                "question": "🔥 Top Batsman?",
                "options": batsmen
            },
            {
                "id": "top_bowler",
                "question": "🎯 Top Bowler?",
                "options": bowlers
            },
            {
                "id": "total_runs",
                "question": "💥 Total Runs?",
                "options": ["<150", "150-170", "170-190", "190+"]
            },
            {
                "id": "toss",
                "question": "⚡ Toss Winner?",
                "options": teams
            },
            {
                "id": "powerplay",
                "question": "🎯 Powerplay Score?",
                "options": ["<40", "40-60", "60-80", "80+"]
            }
        ]
    }

    return jsonify(data)