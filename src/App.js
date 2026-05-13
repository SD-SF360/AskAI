import React from "react";
import "./App.css";
import { Routes, Route } from "react-router-dom";
import ProfilePage from "./ProfilePage";
import AskSF360 from "./AskSF360";

// ── API URL ────────────────────────────────────────────────────────────────────
const API_URL = "https://askai-1flm.onrender.com";

function App() {
  return (
    <Routes>
      <Route path="/" element={<AskSF360 API_URL={API_URL} />} />
      <Route path="/profile/:type/:name" element={<ProfilePage />} />
    </Routes>
  );
}

export default App;
