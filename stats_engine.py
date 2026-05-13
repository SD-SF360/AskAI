runs_cache={}
wickets_cache={}
titles_cache={}
highest_score_cache={}
sixes_cache={}

def set_caches(r,w,t,h,s):
    global runs_cache,wickets_cache,titles_cache,highest_score_cache,sixes_cache
    runs_cache=r
    wickets_cache=w
    titles_cache=t
    highest_score_cache=h
    sixes_cache=s


def top_runs():

    top=sorted(runs_cache.items(),key=lambda x:x[1],reverse=True)[:5]

    chart=[{"player":p,"value":v} for p,v in top]

    answer=f"{top[0][0]} has the most IPL runs with {top[0][1]} runs."

    return {
    "chart_title":"Top IPL Run Scorers",
    "chart_data":chart,
    "answer":answer
    }


def top_wickets():

    top=sorted(wickets_cache.items(),key=lambda x:x[1],reverse=True)[:5]

    chart=[{"player":p,"value":v} for p,v in top]

    answer=f"{top[0][0]} has taken the most IPL wickets with {top[0][1]}."

    return {
    "chart_title":"Top IPL Wicket Takers",
    "chart_data":chart,
    "answer":answer
    }


def top_sixes():

    top=sorted(sixes_cache.items(),key=lambda x:x[1],reverse=True)[:5]

    chart=[{"player":p,"value":v} for p,v in top]

    answer=f"{top[0][0]} has hit the most IPL sixes with {top[0][1]}."

    return {
    "chart_title":"Most IPL Sixes",
    "chart_data":chart,
    "answer":answer
    }


def team_titles():

    top=sorted(titles_cache.items(),key=lambda x:x[1],reverse=True)

    chart=[{"player":t,"value":v} for t,v in top]

    answer=f"{top[0][0]} has won the most IPL titles with {top[0][1]} championships."

    return {
    "chart_title":"IPL Titles by Team",
    "chart_data":chart,
    "answer":answer
    }


def highest_score():

    p=highest_score_cache["player"]
    r=highest_score_cache["runs"]
    m=highest_score_cache["match"]

    return {
    "chart_title":"",
    "chart_data":[],
    "answer":f"Highest IPL score is {r} by {p} in {m}."
    }