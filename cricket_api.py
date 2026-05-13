import requests
import os

API_KEY=os.getenv("CRICKET_API_KEY")

def get_live_matches():

    url=f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"

    try:

        r=requests.get(url,timeout=20)

        data=r.json()

        matches=[]

        for m in data.get("data",[])[:5]:

            matches.append({
            "teams":m.get("teams"),
            "status":m.get("status")
            })

        return matches

    except:

        return []