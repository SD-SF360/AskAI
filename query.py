import pandas as pd

p = pd.read_parquet(r"C:\SD\SF360\sportsfan360-ai-agent-main\AskAI_Data\players.parquet")

print("=== TOP 10 IPL RUN GETTERS ===")
print(p[["display_name","Runs_IPL","Innings_IPL","Batting_Avg_IPL","Batting_SR_IPL"]]
      .sort_values("Runs_IPL", ascending=False).head(10).to_string(index=False))

print("\n=== TOP 10 T20I RUN GETTERS ===")
print(p[["display_name","Runs_T20I","Innings_T20I","Batting_Avg_T20I","Batting_SR_T20I"]]
      .sort_values("Runs_T20I", ascending=False).head(10).to_string(index=False))

print("\n=== TOP 10 IPL WICKET TAKERS ===")
print(p[["display_name","Wickets_IPL","Bowl_Innings_IPL","Econ_IPL","Bowling_Avg_IPL"]]
      .sort_values("Wickets_IPL", ascending=False).head(10).to_string(index=False))

print("\n=== TOP 10 T20I WICKET TAKERS ===")
print(p[["display_name","Wickets_T20I","Bowl_Innings_T20I","Econ_T20I","Bowling_Avg_T20I"]]
      .sort_values("Wickets_T20I", ascending=False).head(10).to_string(index=False))

# Spot check the specific players we fixed
print("\n=== SPOT CHECKS ===")
spot = ["SK Raina", "JJ Bumrah", "R Ashwin", "V Kohli", "RG Sharma"]
for name in spot:
    row = p[p["display_name"] == name]
    if not row.empty:
        print(f"{name}: Runs_IPL={row['Runs_IPL'].values[0]}, Wickets_IPL={row['Wickets_IPL'].values[0]}")