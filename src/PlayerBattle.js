import React,{useState,useEffect,useMemo,useRef} from "react";
import {
Radar,
RadarChart,
PolarGrid,
PolarAngleAxis,
PolarRadiusAxis,
ResponsiveContainer,
PieChart,
Pie,
Cell,
Tooltip,
Legend
} from "recharts";

function PlayerBattle({API_URL}){

const [players,setPlayers]=useState([]);
const [loadingPlayers,setLoadingPlayers]=useState(true);

const [search1,setSearch1]=useState("");
const [search2,setSearch2]=useState("");

const [p1,setP1]=useState("");
const [p2,setP2]=useState("");

const [show1,setShow1]=useState(false);
const [show2,setShow2]=useState(false);

const [result,setResult]=useState(null);
const [shot1,setShot1]=useState({off:0,leg:0,straight:0});
const [shot2,setShot2]=useState({off:0,leg:0,straight:0});

const [loading,setLoading]=useState(false);

const ref1=useRef();
const ref2=useRef();

/* LOAD PLAYERS */
useEffect(()=>{
setLoadingPlayers(true);

fetch(`${API_URL}/player-list`)
.then(r=>r.json())
.then(d=>{
let list=d?.players||[];
list=list.sort((a,b)=>a.localeCompare(b));
setPlayers(list);
setLoadingPlayers(false);
})
.catch(()=>{
setPlayers([]);
setLoadingPlayers(false);
});
},[API_URL]);

/* CLOSE DROPDOWN */
useEffect(()=>{
const handler=(e)=>{
if(ref1.current && !ref1.current.contains(e.target)) setShow1(false);
if(ref2.current && !ref2.current.contains(e.target)) setShow2(false);
};
document.addEventListener("click",handler);
return ()=>document.removeEventListener("click",handler);
},[]);

/* FILTER */
const filtered1=useMemo(()=>{
if(!search1) return [];
return players.filter(p=>p.toLowerCase().includes(search1.toLowerCase())).slice(0,15);
},[search1,players]);

const filtered2=useMemo(()=>{
if(!search2) return [];
return players.filter(p=>p.toLowerCase().includes(search2.toLowerCase())).slice(0,15);
},[search2,players]);

/* FETCH */
const startBattle=async()=>{

if(!p1 || !p2 || p1===p2){
alert("Select 2 different players");
return;
}

setLoading(true);

try{

const battle=await fetch(`${API_URL}/player-battle?p1=${encodeURIComponent(p1)}&p2=${encodeURIComponent(p2)}`).then(r=>r.json());

const s1=await fetch(`${API_URL}/player-shotmap?player=${encodeURIComponent(p1)}`).then(r=>r.json());
const s2=await fetch(`${API_URL}/player-shotmap?player=${encodeURIComponent(p2)}`).then(r=>r.json());

setResult(battle);
setShot1(s1?.data || {off:0,leg:0,straight:0});
setShot2(s2?.data || {off:0,leg:0,straight:0});

}catch(e){
console.error(e);
}

setLoading(false);
};

const safe=(v)=> (v===undefined || v===null ? 0 : v);

/* RADAR */
const radarData = result ? [
{stat:"Runs",p1:safe(result.stats1.runs),p2:safe(result.stats2.runs)},
{stat:"Wickets",p1:safe(result.stats1.wickets),p2:safe(result.stats2.wickets)},
{stat:"Sixes",p1:safe(result.stats1.sixes),p2:safe(result.stats2.sixes)},
{stat:"Strike Rate",p1:safe(result.stats1.strike_rate),p2:safe(result.stats2.strike_rate)},
{stat:"Average",p1:safe(result.stats1.average),p2:safe(result.stats2.average)}
] : [];

const pie1=[
{name:"Off Side",value:shot1.off},
{name:"Leg Side",value:shot1.leg},
{name:"Straight",value:shot1.straight}
];

const pie2=[
{name:"Off Side",value:shot2.off},
{name:"Leg Side",value:shot2.leg},
{name:"Straight",value:shot2.straight}
];

const getClass=(v1,v2)=>{
if(v1>v2) return "statBox win";
if(v1<v2) return "statBox lose";
return "statBox";
};

return(

<div className="battleContainer">

<div className="battleHeader">
<h2>⚔️ Player Intelligence Battle</h2>
<p>Compare full IPL performance across seasons</p>
</div>

{loadingPlayers && <p className="loadingText">Loading IPL player database...</p>}

{/* SELECTORS */}
<div className="battleSelectors">

<div className="dropdown" ref={ref1}>
<input
className="battleInput"
value={search1}
placeholder="Search Player 1"
onFocus={()=>setShow1(true)}
onChange={(e)=>{setSearch1(e.target.value);setP1("");}}
/>

{show1 && filtered1.length>0 && (
<div className="dropdownList">
{filtered1.map((p,i)=>(
<div key={i} className="dropdownItem" onClick={()=>{setP1(p);setSearch1(p);setShow1(false);}}>
{p}
</div>
))}
</div>
)}
</div>

<div className="vs">VS</div>

<div className={`dropdown ${!p1?"disabled":""}`} ref={ref2}>
<input
className="battleInput"
value={search2}
placeholder="Search Player 2"
disabled={!p1}
onFocus={()=>p1 && setShow2(true)}
onChange={(e)=>{setSearch2(e.target.value);setP2("");}}
/>

{show2 && filtered2.length>0 && (
<div className="dropdownList">
{filtered2.map((p,i)=>(
<div key={i} className="dropdownItem" onClick={()=>{setP2(p);setSearch2(p);setShow2(false);}}>
{p}
</div>
))}
</div>
)}
</div>

</div>

<div style={{textAlign:"center"}}>
<button className="compareBtn" onClick={startBattle}>Compare Players</button>
</div>

{loading && <p className="loadingText">Analyzing performance...</p>}


{result && (

<div className="resultCard">

<div className="playersRow">
<div className="playerName">{result.player1}</div>
<div className="vsBig">VS</div>
<div className="playerName">{result.player2}</div>
</div>

{/* STATS */}
<div className="statsGrid">
{["runs","wickets","sixes","fours","strike_rate","average","matches"].map((k,i)=>(
<div key={i} className={getClass(safe(result.stats1[k]),safe(result.stats2[k]))}>
<div className="statTitle">{k.toUpperCase()}</div>
<div className="statValueBig">{safe(result.stats1[k])} | {safe(result.stats2[k])}</div>
</div>
))}
</div>

{/* RADAR */}
<h3>📊 Performance Radar</h3>
<p className="chartInfo">Compares overall performance across multiple dimensions.</p>

<ResponsiveContainer width="100%" height={320}>
<RadarChart data={radarData}>
<PolarGrid/>
<PolarAngleAxis dataKey="stat"/>
<PolarRadiusAxis/>
<Radar name={result.player1} dataKey="p1" stroke="#FE2165" fill="#FE2165" fillOpacity={0.4}/>
<Radar name={result.player2} dataKey="p2" stroke="#4da6ff" fill="#4da6ff" fillOpacity={0.4}/>
<Legend/>
<Tooltip/>
</RadarChart>
</ResponsiveContainer>

{/* PIE */}
<h3>🥧 Shot Distribution</h3>
<p className="chartInfo">Shows scoring areas across the field.</p>

<div className="pieContainer">

<PieChart width={220} height={220}>
<Pie data={pie1} dataKey="value">
<Cell fill="#FE2165"/><Cell fill="#FD6E0C"/><Cell fill="#22c55e"/>
</Pie>
<Tooltip/><Legend/>
</PieChart>

<PieChart width={220} height={220}>
<Pie data={pie2} dataKey="value">
<Cell fill="#4da6ff"/><Cell fill="#60a5fa"/><Cell fill="#22c55e"/>
</Pie>
<Tooltip/><Legend/>
</PieChart>

</div>

{/* WAGON */}
<h3>🏏 Wagon Wheel</h3>
<p className="chartInfo">Directional shot intensity from batter.</p>

<div className="wagonContainer">
<div className="wagonLine red" style={{height:shot1.off,transform:"rotate(20deg)"}}/>
<div className="wagonLine red" style={{height:shot1.leg,transform:"rotate(-40deg)"}}/>
<div className="wagonLine red" style={{height:shot1.straight,transform:"rotate(90deg)"}}/>
</div>

{/* PITCH */}
<h3>📍 Pitch Map</h3>
<p className="chartInfo">Ball landing zones across pitch length.</p>

<div className="pitchMap">
{Array.from({length:20}).map((_,i)=>(
<div key={i} className="pitchDot" style={{top:Math.random()*200,left:Math.random()*300}}/>
))}
</div>

{/* WINNER */}
<div style={{textAlign:"center",marginTop:"20px"}}>
<div className="winnerBox glow">
🏆 Winner: {result.winner}
</div>
</div>

</div>

)}

</div>
);
}

export default PlayerBattle;