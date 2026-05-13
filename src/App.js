import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import logo from "./assets/logo.png";
import { useNavigate } from "react-router-dom";
import { Routes, Route } from "react-router-dom";
import ProfilePage from "./ProfilePage";
import AskSF360 from "./AskSF360";

// ── API URL ────────────────────────────────────────────────────────────────────
const API_URL = "https://askai-1flm.onrender.com";

function App() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // ── Search ──────────────────────────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  // ── Search data (players from live API on mount) ────────────────────────────
  const [playerList, setPlayerList] = useState([
    "Virat Kohli", "Rohit Sharma", "MS Dhoni", "KL Rahul",
    "Hardik Pandya", "Jasprit Bumrah", "Shubman Gill", "Rashid Khan",
    "Yuzvendra Chahal", "Ruturaj Gaikwad"
  ]);
  const teams = ["MI", "CSK", "RCB", "KKR", "SRH", "DC", "RR", "GT", "LSG", "PBKS"];

  // ── Load player list from API ───────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API_URL}/player-list`)
      .then(res => res.json())
      .then(data => { if (data.players?.length) setPlayerList(data.players); })
      .catch(() => {});
  }, []);

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
                    placeholder="Search players or teams..."
                    onChange={(e) => handleSearchChange(e.target.value)}
                    onFocus={() => setShowDropdown(true)}
                    onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
                  />
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

          {/* ASK SF360 — full app */}
          <AskSF360 API_URL={API_URL} />

        </div>
      } />

      <Route path="/profile/:type/:name" element={<ProfilePage />} />

    </Routes>
  );
}

export default App;
