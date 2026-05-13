import React, { useState } from "react";
import "./App.css";
import logo from "./assets/logo.png";

import RunsChart from "./components/RunsChart";
import WicketsChart from "./components/WicketsChart";

function App() {

  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [showJSON, setShowJSON] = useState(false);
  const [chartType, setChartType] = useState("runs");

  const askAI = async () => {

    if (!question) return;

    const response = await fetch(
      /*`http://127.0.0.1:8000/ask?question=${question}*/
	  fetch("https://sportsfan360-ai-agent-1.onrender.com/ask?question=" + question)
    );

    const data = await response.json();

    setResult(data);

    // decide chart type automatically
    if (data.chart_title) {

      if (data.chart_title.toLowerCase().includes("wicket")) {
        setChartType("wickets");
      } else {
        setChartType("runs");
      }

    }

  };

  // CLEAR BUTTON FUNCTION
  const clearSearch = () => {
    setQuestion("");
    setResult(null);
    setShowJSON(false);
  };


  const renderResult = () => {

    if (!result) return null;

    if (result.winner) {
      return (
        <div className="card">
          <h3>🏆 IPL {result.season} Winner</h3>
          <p className="big">{result.winner}</p>
        </div>
      );
    }

    if (result.answer) {
      return (
        <div className="card">
          <h3>{result.chart_title}</h3>
          <p>{result.answer}</p>
        </div>
      );
    }

    // Handle chart responses from backend
    if (result.chart_data) {
      return (
        <div className="card">
          <h3>{result.chart_title}</h3>
          <p>{result.answer}</p>
        </div>
      );
    }

    // OLD API support

    if (result.top_run_scorers) {
      return (
        <div className="card">
          <h3>🔥 Top Run Scorers</h3>

          {result.top_run_scorers.map((p, i) => (
            <p key={i}>
              {i + 1}. {p.player} — {p.value} runs
            </p>
          ))}

        </div>
      );
    }

    if (result.top_wicket_takers) {
      return (
        <div className="card">
          <h3>🎯 Top Wicket Takers</h3>

          {result.top_wicket_takers.map((p, i) => (
            <p key={i}>
              {i + 1}. {p.player} — {p.value} wickets
            </p>
          ))}

        </div>
      );
    }

    return <p>No result</p>;
  };


  // Chart data normalization
  const chartData =
    result?.chart_data ||
    result?.top_run_scorers ||
    result?.top_wicket_takers ||
    [];


  return (

    <div className="app">

      <header className="header">

        <img src={logo} className="logo" alt="logo" />

        <div className="title">
          <h1>SportsFan360</h1>
          <p>AI IPL Analytics Dashboard</p>
        </div>

      </header>


      <div className="search">

        <input
          placeholder="Ask anything about IPL..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") askAI();
          }}
        />

        <button onClick={askAI}>
          Ask
        </button>

        <button onClick={clearSearch} className="clearBtn">
          Clear
        </button>

      </div>


      {result && (

        <div className="result">

          <h2>Result</h2>

          {renderResult()}

          {result.insight && (
            <p className="insight">💡 {result.insight}</p>
          )}

          <div className="jsonToggle">

            <button onClick={() => setShowJSON(!showJSON)}>
              {showJSON ? "Hide JSON" : "Show JSON"}
            </button>

            {showJSON && (
              <pre>
                {JSON.stringify(result, null, 2)}
              </pre>
            )}

          </div>

        </div>

      )}


      <div className="examples">

        <p>Try asking:</p>

        <ul>
          <li>Who won IPL 2022</li>
          <li>Top run scorers</li>
          <li>Most wickets</li>
          <li>Highest score</li>
        </ul>

      </div>


      {/* DYNAMIC CHART AREA */}

      {result && chartData.length > 0 && (

        <div className="analytics">

          <h2>{result.chart_title || "Match Analytics"}</h2>

          <div className="chartBox">

            {chartType === "runs" && (
              <RunsChart data={chartData} />
            )}

            {chartType === "wickets" && (
              <WicketsChart data={chartData} />
            )}

          </div>

        </div>

      )}

    </div>

  );

}

export default App;