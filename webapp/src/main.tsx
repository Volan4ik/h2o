import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import Bottle from "./components/Bottle";
import Stepper from "./components/Stepper";

const tg = (window as any).Telegram?.WebApp;
const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

function useApi(){
  async function getToday(){
    const r = await fetch(`${API_BASE}/api/webapp/today`, { headers: { "X-Tg-Init-Data": tg?.initData || "" } });
    if(!r.ok) throw new Error("today failed");
    return r.json();
  }
  async function getStats(days=7){
    const r = await fetch(`${API_BASE}/api/webapp/stats/days?days=${days}`, { headers: { "X-Tg-Init-Data": tg?.initData || "" } });
    if(!r.ok) throw new Error("stats failed");
    return r.json();
  }
  async function add(amount:number){
    const r = await fetch(`${API_BASE}/api/webapp/log`, { method: "POST", headers: { "Content-Type": "application/json", "X-Tg-Init-Data": tg?.initData || "" }, body: JSON.stringify({ amount_ml: amount }) });
    if(!r.ok) throw new Error("log failed");
  }
  return { getToday, getStats, add };
}

function Bars({data, goal}:{data:{date:string, ml:number}[], goal:number}){
  const max = Math.max(goal, ...data.map(d=>d.ml));
  return (
    <div style={{display:"grid", gridTemplateColumns:`repeat(${data.length},1fr)`, gap:8, alignItems:"end", marginTop:16}}>
      {data.map((d,i)=>{
        const h = Math.round((d.ml/max)*100);
        return (
          <div key={i} title={`${d.date}: ${d.ml} мл`} style={{height:100, background:"var(--tg-theme-background-color,#222)", borderRadius:8, position:"relative"}}>
            <div style={{position:"absolute", bottom:0, left:0, right:0, height:`${h}%`, background:"var(--tg-theme-button-color,#37e)", borderRadius:8}}/>
          </div>
        );
      })}
    </div>
  );
}

function App(){
  const api = useApi();
  const [goal, setGoal] = useState(0);
  const [consumed, setConsumed] = useState(0);
  const [glass, setGlass] = useState(250);
  const [week, setWeek] = useState<{date:string, ml:number}[]>([]);
  const pct = useMemo(()=> Math.min(100, Math.round(consumed/Math.max(1,goal)*100)), [consumed, goal]);

  async function refresh(){
    const t = await api.getToday();
    setGoal(t.goal_ml); setConsumed(t.consumed_ml); setGlass(t.default_glass_ml);
    const s = await api.getStats(7);
    setWeek(s.days);
  }

  async function add(amount:number){
    await api.add(amount); await refresh();
  }

  useEffect(()=>{ tg?.ready(); tg?.expand(); refresh(); }, []);

  return (
    <div style={{padding:16}}>
      <Bottle percent={pct} animateBubbles={true}/>
      <div style={{textAlign:"center", marginTop:8}}>Цель: {goal} мл · Выпито: {consumed} мл</div>
      <div style={{display:"flex", justifyContent:"center", marginTop:12}}>
        <Stepper value={glass} min={50} max={1000} step={50} onChange={setGlass} />
      </div>
      <div style={{display:"flex", justifyContent:"center", gap:8, marginTop:12}}>
        <button onClick={()=>add(glass)} style={{padding:"12px 16px", borderRadius:12, border:"none", background:"var(--tg-theme-button-color,#37e)", color:"var(--tg-theme-button-text-color,#000)"}}>+{glass} мл</button>
        <button onClick={()=>add(250)} style={{padding:"12px 16px", borderRadius:12, border:"none"}}>+250</button>
        <button onClick={()=>add(500)} style={{padding:"12px 16px", borderRadius:12, border:"none"}}>+500</button>
      </div>
      <h3 style={{marginTop:24, marginBottom:8}}>Неделя</h3>
      <Bars data={week} goal={goal}/>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);