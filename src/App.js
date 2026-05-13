import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import logo from "./assets/logo.png";
import Trivia from "./Trivia";
import PlayerBattle from "./PlayerBattle";
import DailyChallenge from "./DailyChallenge";
import Leaderboard from "./Leaderboard";
import { useNavigate } from "react-router-dom";
import { Routes, Route } from "react-router-dom";
import ProfilePage from "./ProfilePage";
import DataPage from "./DataPage";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import AskSF360 from "./AskSF360";

// ── API URL ────────────────────────────────────────────────────────────────────
// Change to https://sportsfan360-ai-agent-1.onrender.com when deploying
const API_URL = "https://askai-1flm.onrender.com";

// ── Quick stats pulled from your live dashboard ────────────────────────────────
// These are fetched dynamically on load; fallback values shown until fetch completes
const statsFallback = [
  { label: "IPL 2026 leader (runs)", value: "Loading...", num: "" },
  { label: "IPL 2026 leader (wickets)", value: "Loading...", num: "" },
  { label: "Most IPL Titles", value: "MI & CSK", num: "5" },
];

function App() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // ── Search ──────────────────────────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  // ── Tabs & feed ─────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState("home");
  const [feed, setFeed] = useState(null);
  const [matches, setMatches] = useState([]);
  const [stats, setStats] = useState(statsFallback);
  const [challengeTab, setChallengeTab] = useState("challenge");

  // ── Ask AI ──────────────────────────────────────────────────────────────────
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);

  const chatEndRef = useRef();

  // ── Search data (players from live API on mount) ────────────────────────────
  const [playerList, setPlayerList] = useState([
    "Virat Kohli", "Rohit Sharma", "MS Dhoni", "KL Rahul",
    "Hardik Pandya", "Jasprit Bumrah", "Shubman Gill", "Rashid Khan",
    "Yuzvendra Chahal", "Ruturaj Gaikwad"
  ]);
  const teams = ["MI", "CSK", "RCB", "KKR", "SRH", "DC", "RR", "GT", "LSG", "PBKS"];

  // ── Predefined questions ────────────────────────────────────────────────────
  const suggestionList = [
    "Most IPL runs",
    "Most IPL wickets",
    "Most IPL sixes",
    "Which team has most IPL titles",
    "Highest IPL score",
    "Compare Kohli vs Rohit",
    "Why is IPL popular",
  ];

  // ── Load player list from API ───────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API_URL}/player-list`)
      .then(res => res.json())
      .then(data => { if (data.players?.length) setPlayerList(data.players); })
      .catch(() => {});
  }, []);

  // ── Load home data ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== "home") return;

    fetch(`${API_URL}/matches`)
      .then(res => res.json())
      .then(data => setMatches(data))
      .catch(() => setMatches([]));

    fetch(`${API_URL}/feed`)
      .then(res => res.json())
      .then(data => setFeed(data))
      .catch(() => setFeed(null));

    // Live quick stats from your dashboard
    Promise.all([
      fetch(`${API_URL}/ask?question=Most IPL runs`).then(r => r.json()),
      fetch(`${API_URL}/ask?question=Most IPL wickets`).then(r => r.json()),
    ]).then(([runsData, wicketsData]) => {
      const topRun = runsData?.chart_data?.[0];
      const topWkt = wicketsData?.chart_data?.[0];
      setStats([
        topRun
          ? { label: "Most IPL Runs (2021+)", value: topRun.player, num: topRun.value.toLocaleString() }
          : statsFallback[0],
        topWkt
          ? { label: "Most IPL Wickets (2021+)", value: topWkt.player, num: topWkt.value }
          : statsFallback[1],
        { label: "Most IPL Titles", value: "MI & CSK", num: "5" },
      ]);
    }).catch(() => {});
  }, [activeTab]);

  // ── Auto-scroll chat ────────────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Search handlers ─────────────────────────────────────────────────────────
  const handleSearchChange = (value) => {
    setSearch(value);
    if (!value) { setSuggestions([]); setShowDropdown(false); return; }
    const q = value.toLowerCase();
    const combined = [
      ...playerList.filter(p => p.toLowerCase().includes(q)).slice(0, 4).map(p => ({ type: "player", name: p })),
      ...teams.filter(t => t.toLowerCase().includes(q)).map(t => ({ type: "team", name: t })),
    ];
    setSuggestions(combined.slice(0, 5));
    setShowDropdown(true);
  };

  const handleSelect = (item) => {
    setSearch(item.name);
    setShowDropdown(false);
    navigate(`/profile/${item.type}/${item.name.toLowerCase()}`);
  };

  const handleSearch = () => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    const jerseyMap = { "45": "rohit sharma", "18": "virat kohli", "7": "ms dhoni" };
    if (/^\d+$/.test(q) && jerseyMap[q]) { navigate(`/profile/player/${jerseyMap[q]}`); return; }
    if (teams.map(t => t.toLowerCase()).includes(q)) { navigate(`/profile/team/${q}`); return; }
    navigate(`/profile/player/${q}`);
  };

  // ── Ask AI ──────────────────────────────────────────────────────────────────
  const askAI = async (q = question) => {
    if (!q.trim()) return;
    setLoading(true);

    const newMessages = [...messages, { role: "user", text: q }];
    setMessages(newMessages);
    setQuestion("");

    try {
      const res = await fetch(`${API_URL}/ask?question=${encodeURIComponent(q)}`);
      const data = await res.json();

      const answer = data?.answer || "No response";
      const chartData = data?.chart_data || [];
      const chartTitle = data?.chart_title || "";

      setMessages([...newMessages, {
        role: "ai",
        text: answer,
        chartData: chartData.length > 0 ? chartData : null,
        chartTitle,
      }]);

      speakText(answer);

    } catch {
      setMessages([...newMessages, { role: "ai", text: "Server error — please try again." }]);
    }

    setLoading(false);
  };

  // ── Voice ───────────────────────────────────────────────────────────────────
  const isVoiceSupported = typeof window !== "undefined" && "webkitSpeechRecognition" in window;
  const isSpeechOutputSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  const speakText = (text) => {
    if (!isSpeechOutputSupported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/📊.*/, ""));
    utterance.lang = "en-IN";
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const clearChat = () => setMessages([]);

  const startVoice = () => {
    if (!isVoiceSupported) return;
    const SpeechRecognition = window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = true;
    recognition.interimResults = true;
    let finalTranscript = "";
    recognition.onstart = () => setListening(true);
    recognition.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        e.results[i].isFinal ? (finalTranscript += t) : (interim += t);
      }
      setQuestion(finalTranscript + interim);
    };
    recognition.onend = () => { setListening(false); if (finalTranscript.trim()) askAI(finalTranscript); };
    recognition.onerror = () => setListening(false);
    recognition.start();
    setTimeout(() => recognition.stop(), 6000);
  };

  // ── Message renderer ────────────────────────────────────────────────────────
  const renderMessage = (m, i) => {
    // Split answer on \n, render each line; note lines get muted style
    const lines = m.text.split("\n").filter(l => l.trim() !== "");

    return (
      <div key={i} className={`bubbleRow ${m.role}`}>
        <div className={`bubble ${m.role}`}>

          {lines.map((line, j) => {
            const isNote = line.startsWith("📊");
            const isNumbered = /^\d+\./.test(line);
            return (
              <p key={j} style={{
                margin: "2px 0",
                fontSize: isNote ? "11px" : isNumbered ? "13px" : "14px",
                opacity: isNote ? 0.6 : 1,
                fontFamily: isNumbered ? "monospace" : "inherit",
              }}>
                {line}
              </p>
            );
          })}

          {/* Chart — rendered inside the bubble when chart_data present */}
          {m.chartData && m.chartData.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              {m.chartTitle && (
                <p style={{ fontSize: "12px", opacity: 0.7, marginBottom: "6px" }}>
                  {m.chartTitle}
                </p>
              )}
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={m.chartData.map(d => ({ name: d.player, value: d.value }))}
                  margin={{ top: 4, right: 8, left: 0, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: "#ccc" }}
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 10, fill: "#ccc" }} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "none", borderRadius: "8px", fontSize: "12px" }}
                    labelStyle={{ color: "#fff" }}
                    itemStyle={{ color: "#38bdf8" }}
                  />
                  <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

        </div>
      </div>
    );
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <Routes>
      <Route path="/" element={
        <div className="app">

          {/* HEADER */}
          <header className="header">
            <div className="brand">
              <img src={logo} className="logo" alt="logo" />
              <div className="title">
                <h1>SportsFan360</h1>
                <p>AI Cricket Analyst</p>
              </div>
            </div>

            <div className="headerSearch">
              <div className="searchWrapper">
                <div className="searchInputWrapper">
                  <svg className="searchIcon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  <input
                    value={search}
                    placeholder="Search..."
                    onChange={(e) => handleSearchChange(e.target.value)}
                    onFocus={() => setShowDropdown(true)}
                    onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
                  />
                  <button
                    className="askSF360Btn"
                    onClick={() => { setActiveTab("ask"); setShowDropdown(false); }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    Ask SF360
                  </button>
                </div>
                {showDropdown && suggestions.length > 0 && (
                  <div className="searchDropdown">
                    {suggestions.map((item, i) => (
                      <div key={i} className="dropdownItem" onClick={() => handleSelect(item)}>
                        <span className="type">{item.type === "player" ? "🏏" : "🏆"}</span>
                        {item.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="headerRight">
              <div className="avatar" onClick={() => setOpen(!open)}>T</div>
              {open && (
                <div className="userDropdown">
                  <div className="userInfo">
                    <div className="userAvatar">T</div>
                    <div>
                      <div className="userName">Tushar</div>
                      <div className="userEmail">tushar@email.com</div>
                    </div>
                  </div>
                  <div className="dropdownDivider"></div>
                  <div className="dropdownItem">Profile</div>
                  <div className="dropdownItem">Settings</div>
                  <div className="dropdownDivider"></div>
                  <div className="dropdownItem logout">Logout</div>
                </div>
              )}
            </div>
          </header>

          {/* NAV */}
          <div className="tabs">
            <button className={activeTab === "home" ? "tab active" : "tab"} onClick={() => setActiveTab("home")}>🏠 Home</button>
            <button className={activeTab === "ask" ? "tab active" : "tab"} onClick={() => setActiveTab("ask")}>🤖 AskSportsFan360</button>
            <button className={activeTab === "trivia" ? "tab active" : "tab"} onClick={() => setActiveTab("trivia")}>🏏 IPL Trivia</button>
            <button className={activeTab === "battle" ? "tab active" : "tab"} onClick={() => setActiveTab("battle")}>⚔️ Player Battle</button>
          </div>

          {/* HOME */}
          {activeTab === "home" && (
            <div className="home">

              <div className="hero">
                <h2>Cricket Intelligence Hub</h2>
                <p>Player insights, stats, AI powered cricket knowledge.</p>
              </div>

              <div className="sectionTitle">🔥 IPL Quick Stats</div>
              <div className="quickStats">
                {stats.map((s, i) => (
                  <div key={i} className="statCard">
                    <span className="statLabel">{s.label}</span>
                    <div className="statRow">
                      <strong>{s.value}</strong>
                      <span className="statNum">{s.num}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="sectionTitle">🏏 Live & Upcoming Matches</div>
              {(() => {
                const matchList = Array.isArray(matches) ? matches : (matches?.matches || []);
                if (matchList.length === 0) return <div className="noMatches">No live or upcoming matches available</div>;
                return (
                  <div className="matchCards">
                    {matchList.map((m, i) => (
                      <div key={i} className="matchCard">
                        <div className={`matchBadge ${(m.status || "").toLowerCase().includes("live") ? "live" : "upcoming"}`}>
                          {m.status || "Upcoming"}
                        </div>
                        <div className="matchTeams">
                          <div className="team">{m.team1 || "TBD"}</div>
                          <div className="vs">vs</div>
                          <div className="team">{m.team2 || "TBD"}</div>
                        </div>
                        <div className="matchScore">{m.score && m.score !== "" ? m.score : "No score available"}</div>
                        <div className="matchMeta">
                          <span>{m.venue || "Unknown venue"}</span>
                          <span>{m.date || ""}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()}

              <div className="challengeTabsWrapper">
                <h2>🔥 | 🏆 Daily Predictions</h2>
                <div className="challengeTabs">
                  <button className={challengeTab === "challenge" ? "active" : ""} onClick={() => setChallengeTab("challenge")}>🔥 Daily Predictions</button>
                  <button className={challengeTab === "leaderboard" ? "active" : ""} onClick={() => setChallengeTab("leaderboard")}>🏆 Leaderboard</button>
                </div>
                <div className="challengeContent">
                  {(() => {
                    const matchList = Array.isArray(matches) ? matches : (matches?.matches || []);
                    if (challengeTab === "challenge") {
                      if (matchList.length === 0) return <div className="noMatches">No matches available</div>;
                      return <DailyChallenge match={matchList[0]} API_URL={API_URL} />;
                    }
                    if (challengeTab === "leaderboard") return <Leaderboard />;
                    return null;
                  })()}
                </div>
              </div>

              <div className="sectionTitle">📰 Latest Cricket News</div>
              {feed && (
                <div className="feedCards">
                  {feed.cards.map((c, i) => (
                    <a key={i} href={c.link} target="_blank" rel="noreferrer" className="feedCard">
                      {c.image && <img src={c.image} className="feedImage" alt="news" />}
                      <div className="feedContent">
                        <h3>{c.title}</h3>
                        <p>{c.text}</p>
                      </div>
                    </a>
                  ))}
                </div>
              )}

            </div>
          )}

          {/* ASK */}
          {activeTab === "ask" && <AskSF360 API_URL={API_URL} />}

          {activeTab === "trivia" && <Trivia />}
          {activeTab === "battle" && <PlayerBattle API_URL={API_URL} />}

        </div>
      } />

      <Route path="/profile/:type/:name" element={<ProfilePage />} />
      <Route path="/data" element={<DataPage />} />

    </Routes>
  );
}

export default App;
