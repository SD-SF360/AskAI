def get_players(team=None):

    players = [

    {"name":"Virat Kohli","team":"RCB","role":"Batsman"},
    {"name":"Faf du Plessis","team":"RCB","role":"Batsman"},
    {"name":"Glenn Maxwell","team":"RCB","role":"All-rounder"},
    {"name":"Jasprit Bumrah","team":"MI","role":"Bowler"},
    {"name":"Rohit Sharma","team":"MI","role":"Batsman"},
    {"name":"MS Dhoni","team":"CSK","role":"Wicketkeeper"},
    {"name":"Ravindra Jadeja","team":"CSK","role":"All-rounder"},
    {"name":"Shubman Gill","team":"GT","role":"Batsman"},
    {"name":"KL Rahul","team":"LSG","role":"Batsman"},
    {"name":"Sanju Samson","team":"RR","role":"Wicketkeeper"}

    ]

    if team:
        players = [p for p in players if p["team"]==team]

    return {"players":players}