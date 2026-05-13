import React, { useEffect, useState } from "react";

function Leaderboard() {

  const [leaders, setLeaders] = useState([]);

  useEffect(() => {

    const data = localStorage.getItem("ipl_leaderboard");

    if (data) {
      setLeaders(JSON.parse(data));
    } else {
      const demo = [
        { name: "You", score: 50 },
        { name: "Player123", score: 40 },
        { name: "CricketFan", score: 30 }
      ];
      localStorage.setItem("ipl_leaderboard", JSON.stringify(demo));
      setLeaders(demo);
    }

  }, []);

  return (
    <div className="leaderboardCard fadeSlide">

      <div className="leaderHeader">
        <h3>🏆 Top Fans</h3>
        <p className="leaderHint">Climb the leaderboard with accurate predictions 🔥</p>
      </div>

      <div className="leaderList">

        {leaders.map((l, i) => {

          const isYou = l.name === "You";

          return (
            <div
              key={i}
              className={`leaderItem rank-${i + 1} ${isYou ? "youCard" : ""}`}
            >

              <div className="leaderLeft">
                <span className="rankBadge">#{i + 1}</span>
                <span className="leaderName">{l.name}</span>
              </div>

              <div className="leaderRight">
                {i === 0 && <span className="medal">🥇</span>}
                {i === 1 && <span className="medal">🥈</span>}
                {i === 2 && <span className="medal">🥉</span>}
                <span className="leaderScore">{l.score} pts</span>
              </div>

            </div>
          );
        })}

      </div>

    </div>
  );
}

export default Leaderboard;