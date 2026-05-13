import requests

API_KEY = "830cd356-c66b-4f9a-9fcb-40ed04fae5b5"

def get_live_matches():

    try:
        current_url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"
        matches_url = f"https://api.cricapi.com/v1/matches?apikey={API_KEY}&offset=0"
        score_url = f"https://api.cricapi.com/v1/cricScore?apikey={API_KEY}"

        current_data = requests.get(current_url, timeout=10).json().get("data", [])
        all_matches_data = requests.get(matches_url, timeout=10).json().get("data", [])
        score_data = requests.get(score_url, timeout=10).json().get("data", [])

        matches = []

        def extract_teams(m):
            team_info = m.get("teamInfo", [])
            if len(team_info) >= 2:
                return team_info[0].get("name", "TBD"), team_info[1].get("name", "TBD")
            return None, None

        def get_score(team1, team2):
            for s in score_data:
                t1 = s.get("t1", "").lower()
                t2 = s.get("t2", "").lower()
                if team1.lower() in t1 or team2.lower() in t2:
                    return s.get("score", "")
            return ""

        def is_live(status):
            status = (status or "").lower()
            return any(x in status for x in ["live", "progress", "innings", "stumps"])

        # 🔥 1. CURRENT MATCHES
        for m in current_data:
            team1, team2 = extract_teams(m)
            if not team1 or not team2:
                continue

            status = m.get("status", "")
            score = get_score(team1, team2)

            matches.append({
                "id": m.get("id"),
                "team1": team1,
                "team2": team2,
                "status": "Live" if is_live(status) else status,
                "venue": m.get("venue", "Unknown"),
                "date": m.get("date", ""),
                "score": score if score else "Match ongoing"
            })

        # 🔥 2. UPCOMING MATCHES
        for m in all_matches_data:

            if len(matches) >= 10:
                break

            team1, team2 = extract_teams(m)
            if not team1 or not team2:
                continue

            if any(x["team1"] == team1 and x["team2"] == team2 for x in matches):
                continue

            matches.append({
                "id": m.get("id"),
                "team1": team1,
                "team2": team2,
                "status": "Upcoming",
                "venue": m.get("venue", "Unknown"),
                "date": m.get("date", ""),
                "score": "Starts soon"
            })

        # 🔥 SORT LIVE FIRST
        matches = sorted(matches, key=lambda x: (
            not is_live(x["status"])
        ))

        return matches[:10]

    except Exception as e:
        print("Match Error:", e)
        return []