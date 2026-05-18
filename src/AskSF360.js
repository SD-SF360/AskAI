import React, { useState, useRef, useEffect } from "react";
import "./AskSF360.css";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const SUGGESTIONS = [
  "Who won the first IPL?",
  "Which player has won the most Orange Cap awards in IPL history?",
  "Which team has won the highest number of IPL titles (tied at 5 each)?",
  "Most IPL runs",
  "Most IPL wickets",
  "Most IPL sixes",
  "Compare Kohli vs Rohit",
];

// Pick 3 random suggestions
const pickSuggestions = () => {
  const shuffled = [...SUGGESTIONS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
};

function AskSF360({ API_URL }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [suggestions, setSuggestions] = useState(pickSuggestions());
  const [audioEnabled, setAudioEnabled] = useState(false);

  const chatEndRef = useRef();
  const inputRef = useRef();

  const isVoiceSupported = typeof window !== "undefined" && "webkitSpeechRecognition" in window;
  const isSpeechOutputSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  const hasMessages = messages.length > 0;

  // Auto scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Shuffle suggestions
  const shuffleSuggestions = () => setSuggestions(pickSuggestions());

  // Speak
  const speakText = (text) => {
    if (!isSpeechOutputSupported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/📊.*/, ""));
    utterance.lang = "en-IN";
    window.speechSynthesis.speak(utterance);
  };

  // Ask
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
        chartData: chartData.filter(d => d.value > 0).length > 0 ? chartData.filter(d => d.value > 0) : null,
        chartTitle,
      }]);

      if (audioEnabled) speakText(answer);

    } catch {
      setMessages([...newMessages, { role: "ai", text: "Server error — please try again." }]);
    }

    setLoading(false);
  };

  // Voice
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
    recognition.onend = () => {
      setListening(false);
      if (finalTranscript.trim()) askAI(finalTranscript);
    };
    recognition.onerror = () => setListening(false);
    recognition.start();
    setTimeout(() => recognition.stop(), 6000);
  };

  // Render message lines
  const renderMessage = (m, i) => {
    const lines = m.text.split("\n").filter(l => l.trim() !== "");

    // Parse **bold** markers
    const parseBold = (text) => {
      const parts = text.split(/\*\*(.*?)\*\*/g);
      return parts.map((part, idx) =>
        idx % 2 === 1 ? <strong key={idx}>{part}</strong> : part
      );
    };

    return (
      <div key={i} className={`ask-bubble-row ${m.role}`}>
        {m.role === "ai" && (
          <div className="ask-ai-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="url(#grad)" />
              <text x="12" y="16" textAnchor="middle" fontSize="10" fill="white">AI</text>
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#f97316" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        )}
        <div className={`ask-bubble ${m.role}`}>
          {lines.map((line, j) => {
            const isNote = line.startsWith("📊");
            const isNumbered = /^\d+\./.test(line);
            return (
              <p key={j} style={{
                margin: "3px 0",
                fontSize: isNote ? "11px" : isNumbered ? "13px" : "14px",
                opacity: isNote ? 0.5 : 1,
                fontFamily: isNumbered ? "'Courier New', monospace" : "inherit",
                lineHeight: 1.6,
              }}>
                {parseBold(line)}
              </p>
            );
          })}

          {m.chartData && (
            <div style={{ marginTop: "14px" }}>
              {m.chartTitle && (
                <p style={{ fontSize: "11px", opacity: 0.5, marginBottom: "8px", margin: "0 0 8px" }}>
                  {m.chartTitle}
                </p>
              )}
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={m.chartData.map(d => ({ name: d.player || d.team, value: d.value }))}
                  margin={{ top: 4, right: 8, left: 0, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: "rgba(255,255,255,0.5)" }}
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 10, fill: "rgba(255,255,255,0.5)" }} />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a1a",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                      fontSize: "12px"
                    }}
                    labelStyle={{ color: "#fff" }}
                    itemStyle={{ color: "#f97316" }}
                  />
                  <Bar dataKey="value" fill="#f97316" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="ask-page">

      {/* ── Landing state: centered hero + input ── */}
      {!hasMessages && (
        <div className="ask-landing">
          <h1 className="ask-hero-title">Your AI companion for everything cricket</h1>
        </div>
      )}

      {/* ── Conversation area ── */}
      {hasMessages && (
        <div className="ask-messages">
          {[...messages].reverse().map((m, i) => renderMessage(m, messages.length - 1 - i))}
          {loading && (
            <div className="ask-bubble-row ai">
              <div className="ask-ai-avatar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" fill="url(#grad2)" />
                  <text x="12" y="16" textAnchor="middle" fontSize="10" fill="white">AI</text>
                  <defs>
                    <linearGradient id="grad2" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#f97316" />
                      <stop offset="100%" stopColor="#ec4899" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div className="ask-bubble ai ask-thinking">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      )}

      {/* ── Input area — inline on landing, fixed when chatting ── */}
      <div className="ask-input-area">
        <div className="ask-input-inner">

          {/* Input bar */}
          <div className="ask-input-bar">
            <input
              ref={inputRef}
              className="ask-input"
              value={question}
              placeholder={listening ? "Listening..." : "Ask anything"}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") askAI(); }}
            />
            <button
              className={`ask-mic-btn ${audioEnabled ? "listening" : ""}`}
              onClick={() => {
                setAudioEnabled(v => !v);
                if (audioEnabled) window.speechSynthesis?.cancel();
              }}
              title={audioEnabled ? "Audio on — click to mute" : "Audio off — click to enable"}
            >
              {audioEnabled ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                  <line x1="23" y1="9" x2="17" y2="15"/>
                  <line x1="17" y1="9" x2="23" y2="15"/>
                </svg>
              )}
            </button>
            <button
              className={`ask-mic-btn ${listening ? "listening" : ""}`}
              onClick={startVoice}
              title="Voice input"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
            </button>
            <button className="ask-send-btn" onClick={() => askAI()} title="Send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12 5 19 12 12 19"/>
              </svg>
            </button>
          </div>

          {/* Suggestions */}
          <div className="ask-suggestions">
            {suggestions.map((s, i) => (
              <button key={i} className="ask-suggestion" onClick={() => askAI(s)}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, opacity: 0.45 }}>
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                {s}
              </button>
            ))}
            <button className="ask-suggestion-refresh" onClick={shuffleSuggestions} title="Refresh">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </button>
          </div>

          {/* Clear chat */}
          {hasMessages && (
            <button className="ask-clear" onClick={() => setMessages([])}>
              Clear chat
            </button>
          )}

        </div>
      </div>

    </div>
  );
}

export default AskSF360;
