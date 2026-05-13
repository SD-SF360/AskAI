import React,{useState,useRef,useEffect} from "react";
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


const statsPool=[

{label:"Most IPL Runs",value:"Virat Kohli",num:"8671"},
{label:"Most IPL Wickets",value:"YS Chahal",num:"229"},
{label:"Most IPL Titles",value:"Mumbai Indians",num:"5"},
{label:"Most IPL Sixes",value:"Chris Gayle",num:"357"},
{label:"Highest IPL Score",value:"Chris Gayle",num:"175"},

{label:"Most IPL Hundreds",value:"Virat Kohli",num:"7"},
{label:"Most IPL Matches",value:"MS Dhoni",num:"250+"},
{label:"Best Bowling Figures",value:"Alzarri Joseph",num:"6/12"},
{label:"Fastest IPL Fifty",value:"KL Rahul",num:"14 balls"},
{label:"Fastest IPL Century",value:"Chris Gayle",num:"30 balls"},

{label:"Most Dot Balls",value:"Bhuvneshwar Kumar",num:"1500+"},
{label:"Most Hat-tricks",value:"Amit Mishra",num:"3"},
{label:"Most Catches",value:"Suresh Raina",num:"109"},
{label:"Highest Team Total",value:"RCB",num:"263"},
{label:"Lowest Team Total",value:"RCB",num:"49"},

{label:"Most Fours", value:"Shikhar Dhawan", num:"750+"},
{label:"Most Runs in a Season", value:"Virat Kohli", num:"973"},
{label:"Most Wickets in a Season", value:"Dwayne Bravo", num:"32"},
{label:"Most Consecutive Wins", value:"KKR", num:"10"},
{label:"Most Player of Match Awards", value:"AB de Villiers", num:"25+"},

{label:"Most Runs in Powerplay", value:"David Warner", num:"3000+"},
{label:"Most Sixes in a Season", value:"Chris Gayle", num:"59"},
{label:"Best Strike Rate (min 1000 runs)", value:"Andre Russell", num:"170+"},
{label:"Most Runs Against One Team", value:"Virat Kohli vs CSK", num:"1000+"},
{label:"Most Finals Played", value:"MS Dhoni", num:"10+"},

{label:"Most Runs in Death Overs", value:"MS Dhoni", num:"2500+"},
{label:"Best Economy (min 500 overs)", value:"Rashid Khan", num:"6.5"},
{label:"Most Runs in Chases", value:"Virat Kohli", num:"4000+"},
{label:"Most Super Over Appearances", value:"MI", num:"10+"},
{label:"Most Wins as Captain", value:"MS Dhoni", num:"130+"},

{label:"Most Runs by Overseas Player", value:"David Warner", num:"6500+"},
{label:"Most Wickets by Spinner", value:"Amit Mishra", num:"170+"},
{label:"Most Wickets by Pacer", value:"Lasith Malinga", num:"170+"},
{label:"Most Ducks", value:"Rohit Sharma", num:"15+"},
{label:"Most Man of Series Awards", value:"Sunil Narine", num:"3"},
]

function App(){
const [open, setOpen] = useState(false);
const API_URL="https://sportsfan360-ai-agent-1.onrender.com"

const navigate = useNavigate();

// ✅ STATES (ONLY ONCE)
const [search,setSearch]=useState("");
const [suggestions,setSuggestions]=useState([]);
const [showDropdown,setShowDropdown]=useState(false);

const [activeTab,setActiveTab]=useState("home")
const [feed,setFeed]=useState(null)

const [question,setQuestion]=useState("")
const [messages,setMessages]=useState([])
const [loading,setLoading]=useState(false)

const chatEndRef=useRef()
const [stats,setStats]=useState(statsPool.slice(0,3))

const [speaking,setSpeaking]=useState(false)
const [listening,setListening]=useState(false)
const [challengeTab, setChallengeTab] = useState("challenge");

const [matches,setMatches]=useState([])

// 🔍 SEARCH DATA
const players = [
  "Virat Kohli","Rohit Sharma","MS Dhoni","AB de Villiers",
  "Chris Gayle","KL Rahul","Hardik Pandya","Jasprit Bumrah",
  "Ravindra Jadeja","Suresh Raina"
];

const teams = ["MI","CSK","RCB","KKR","SRH","DC","RR","GT","LSG","PBKS"];

// 🔍 LIVE SEARCH
const handleSearchChange = (value) => {
  setSearch(value);

  if(!value){
    setSuggestions([]);
    setShowDropdown(false);
    return;
  }

  const q = value.toLowerCase();

  const playerMatches = players.filter(p => p.toLowerCase().includes(q));
  const teamMatches = teams.filter(t => t.toLowerCase().includes(q));

  const combined = [
    ...playerMatches.map(p => ({type:"player", name:p})),
    ...teamMatches.map(t => ({type:"team", name:t}))
  ];

  setSuggestions(combined.slice(0,5));
  setShowDropdown(true);
};

const handleSelect = (item) => {
  setSearch(item.name);
  setShowDropdown(false);

  if(item.type==="team"){
    navigate(`/profile/team/${item.name.toLowerCase()}`);
  }else{
    navigate(`/profile/player/${item.name.toLowerCase()}`);
  }
};

// 🔍 SEARCH BUTTON
const handleSearch = () => {
  const q = search.trim().toLowerCase();
  if(!q) return;

  const jerseyMap = {
    "45": "rohit sharma",
    "18": "virat kohli",
    "7": "ms dhoni"
  };

  const teamList = ["mi","csk","rcb","kkr","srh","dc","rr","gt","lsg","pbks"];

  if(/^\d+$/.test(q)){
    const player = jerseyMap[q];
    if(player){
      navigate(`/profile/player/${player}`);
      return;
    }
  }

  if(teamList.includes(q)){
    navigate(`/profile/team/${q}`);
    return;
  }

  navigate(`/profile/player/${q}`);
};

// ⚠️ RENAMED (IMPORTANT)
const suggestionList=[
"Most IPL runs",
"Most IPL wickets",
"Most IPL sixes",
"Which team has most IPL titles",
"Highest IPL score",
"Compare Kohli vs Rohit",
"Why is IPL popular"
];

/* ASK */
const askAI=async(q=question)=>{
if(!q.trim()) return

setLoading(true)

const newMessages=[...messages,{role:"user",text:q}]
setMessages(newMessages)
setQuestion("")

try{
const res=await fetch(`${API_URL}/ask?question=${encodeURIComponent(q)}`)
const data=await res.json()

const answer=data?.answer || "No response"

setMessages([...newMessages,{role:"ai",text:answer}])
speakText(answer)

}catch{
const errorMsg="Server error"
setMessages([...newMessages,{role:"ai",text:errorMsg}])
speakText(errorMsg)
}

setLoading(false)
}

/* VOICE SUPPORT */
const isVoiceSupported =
  typeof window !== "undefined" && "webkitSpeechRecognition" in window;

const isSpeechOutputSupported =
  typeof window !== "undefined" && "speechSynthesis" in window;

/* SPEAK */
const speakText = (text) => {
  if (!isSpeechOutputSupported) return;

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";

  utterance.onstart = () => setSpeaking(true);
  utterance.onend = () => setSpeaking(false);

  window.speechSynthesis.speak(utterance);
};

/* CLEAR CHAT */
const clearChat = () => setMessages([]);

/* VOICE INPUT */
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
      let transcript = e.results[i][0].transcript;

      if (e.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interim += transcript;
      }
    }

    setQuestion(finalTranscript + interim);
  };

  recognition.onend = () => {
    setListening(false);

    if (finalTranscript.trim()) {
      askAI(finalTranscript);
    }
  };

  recognition.onerror = () => setListening(false);

  recognition.start();

  setTimeout(() => recognition.stop(), 6000);
};

/* LOAD DATA */
useEffect(()=>{
if(activeTab==="home"){

// MATCHES
fetch(`${API_URL}/matches`)
.then(res=>res.json())
.then(data=>setMatches(data))
.catch(()=>setMatches([]))

// NEWS FEED
fetch(`${API_URL}/feed`)
.then(res=>res.json())
.then(data=>setFeed(data))
.catch(()=>setFeed(null))

}
},[activeTab])

return(

<Routes>

  {/* MAIN APP */}
  <Route path="/" element={

    <div className="app">

<header className="header">

  {/* LEFT: BRAND */}
  <div className="brand">
    <img src={logo} className="logo" alt="logo"/>
    <div className="title">
      <h1>SportsFan360</h1>
      <p>AI Cricket Analyst</p>
    </div>
  </div>

  {/* CENTER: SEARCH */}
  <div className="headerSearch">

    <div className="searchWrapper">

      <div className="searchInputWrapper">
        <span className="searchIcon">🔍</span>

        <input
          value={search}
          placeholder="Search players, teams..."
          onChange={(e)=>handleSearchChange(e.target.value)}
          onFocus={()=>setShowDropdown(true)}
        />

        <button className="searchBtn" onClick={handleSearch}>
          Go
        </button>
      </div>

      {/* 🔽 DROPDOWN */}
      {showDropdown && suggestions.length > 0 && (
        <div className="searchDropdown">
          {suggestions.map((item,i)=>(
            <div
              key={i}
              className="dropdownItem"
              onClick={()=>handleSelect(item)}
            >
              <span className="type">
                {item.type==="player" ? "🏏" : "🏆"}
              </span>
              {item.name}
            </div>
          ))}
        </div>
      )}

    </div>

  </div>

  {/* RIGHT: LOGIN */}
  <div className="headerRight">
    <div 
      className="avatar"
      onClick={() => setOpen(!open)}   /* ✅ ADDED */
    >
      T
    </div>

    {open && (   /* ✅ ADDED */
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
<button className={activeTab==="home"?"tab active":"tab"} onClick={()=>setActiveTab("home")}>🏠 Home</button>
<button className={activeTab==="ask"?"tab active":"tab"} onClick={()=>setActiveTab("ask")}>🤖 AskSportsFan360</button>
<button className={activeTab==="trivia"?"tab active":"tab"} onClick={()=>setActiveTab("trivia")}>🏏 IPL Trivia</button>
<button className={activeTab==="battle"?"tab active":"tab"} onClick={()=>setActiveTab("battle")}>⚔️ Player Battle</button>
</div>

{/* HOME */}
{activeTab==="home" && (
<div className="home">

  {/* 🎯 HERO */}
  <div className="hero">
    <h2>Cricket Intelligence Hub</h2>
    <p>Player insights, stats, AI powered cricket knowledge.</p>
  </div>

  {/* 🔥 IPL Quick Stats */}
  <div className="sectionTitle">🔥 IPL Quick Stats</div>

  <div className="quickStats">
    {stats.map((s,i)=>(
      <div key={i} className="statCard">
        <span className="statLabel">{s.label}</span>
        <div className="statRow">
          <strong>{s.value}</strong>
          <span className="statNum">{s.num}</span>
        </div>
      </div>
    ))}
  </div>

  {/* 🏏 MATCHES */}
  <div className="sectionTitle">🏏 Live & Upcoming Matches</div>

  {(() => {
    const matchList = Array.isArray(matches)
      ? matches
      : (matches?.matches || []);

    if(matchList.length === 0){
      return (
        <div className="noMatches">
          No live or upcoming matches available
        </div>
      );
    }

    return (
      <div className="matchCards">
        {matchList.map((m,i)=>(
          <div key={i} className="matchCard">

            <div className={`matchBadge ${
              (m.status || "").toLowerCase().includes("live") ? "live" : "upcoming"
            }`}>
              {m.status || "Upcoming"}
            </div>

            <div className="matchTeams">
              <div className="team">{m.team1 || "TBD"}</div>
              <div className="vs">vs</div>
              <div className="team">{m.team2 || "TBD"}</div>
            </div>

            <div className="matchScore">
              {m.score && m.score !== "" ? m.score : "No score available"}
            </div>

            <div className="matchMeta">
              <span>{m.venue || "Unknown venue"}</span>
              <span>{m.date || ""}</span>
            </div>

          </div>
        ))}
      </div>
    );
  })()}

  {/* 🔥 DAILY + LEADERBOARD */}
  <div className="challengeTabsWrapper">
    <h2>🔥 | 🏆 Daily Predications</h2>

    <div className="challengeTabs">
      <button
        className={challengeTab === "challenge" ? "active" : ""}
        onClick={() => setChallengeTab("challenge")}
      >
        🔥 Daily Predications
      </button>

      <button
        className={challengeTab === "leaderboard" ? "active" : ""}
        onClick={() => setChallengeTab("leaderboard")}
      >
        🏆 Leaderboard
      </button>
    </div>

    <div className="challengeContent">
      {(() => {
        const matchList = Array.isArray(matches)
          ? matches
          : (matches?.matches || []);

        if (challengeTab === "challenge") {
          if (matchList.length === 0) {
            return <div className="noMatches">No matches available</div>;
          }

          return (
            <DailyChallenge
              match={matchList[0]}
              API_URL={API_URL}
            />
          );
        }

        if (challengeTab === "leaderboard") {
          return <Leaderboard />;
        }

        return null;
      })()}
    </div>
  </div>

  {/* 📰 NEWS */}
  <div className="sectionTitle">📰 Latest Cricket News</div>

  {feed && (
    <div className="feedCards">
      {feed.cards.map((c,i)=>(
        <a key={i} href={c.link} target="_blank" rel="noreferrer" className="feedCard">
          {c.image && <img src={c.image} className="feedImage" alt="news"/>}
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
{activeTab==="ask" && (
<div className="askPage">

<div className="chatContainer">

<div className="chatHeader">
<button className="clearChat" onClick={clearChat}>Clear Chat</button>
</div>

<div className="chatMessages">

{messages.length===0 && (
<div className="welcome">
<h2>Ask anything about IPL</h2>
<p>Teams • Players • Records • Runs • Wickets • Comparisons</p>
</div>
)}

{messages.map((m,i)=>(
<div key={i} className={`bubbleRow ${m.role}`}>
<div className={`bubble ${m.role}`}>
{m.text}
</div>
</div>
))}

{loading && <div className="bubble ai">Analyzing...</div>}

<div ref={chatEndRef}></div>

</div>

<div className="chatBottom">

<div className="suggestions">
{suggestionList.map((s,i)=>(
<button key={i} onClick={()=>askAI(s)}>{s}</button>
))}
</div>

<div className="inputBox">

<input
value={question}
placeholder={listening ? "Listening..." : "Ask SportsFan360..."}
onChange={(e)=>setQuestion(e.target.value)}
onKeyDown={(e)=>{if(e.key==="Enter")askAI()}}
/>

{isVoiceSupported && (
<button className={`micBtn ${listening?"listening":""}`} onClick={startVoice}>
{listening ? "🔴 Listening..." : "🎤"}
</button>
)}

<button onClick={()=>askAI()}>Ask</button>

</div>

</div>

</div>

</div>
)}

{activeTab==="trivia" && <Trivia />}
{activeTab==="battle" && <PlayerBattle API_URL={API_URL}/>}

    </div>

  } />

  {/* PROFILE PAGE */}
  <Route path="/profile/:type/:name" element={<ProfilePage />} />
  <Route path="/data" element={<DataPage />} />

</Routes>

)

}

export default App;