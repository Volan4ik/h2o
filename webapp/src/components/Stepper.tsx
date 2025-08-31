import React, { useRef } from "react";

export default function Stepper({value, onChange, min=0, max=10000, step=50}:{value:number; onChange:(v:number)=>void; min?:number; max?:number; step?:number;}){
  const timer = useRef<any>(null);
  function clamp(v:number){ return Math.max(min, Math.min(max, v)); }
  function bump(delta:number){ onChange(clamp(value + delta)); }
  function hold(delta:number){
    clearInterval(timer.current);
    bump(delta);
    timer.current = setInterval(()=>bump(delta), 150);
  }
  function release(){ clearInterval(timer.current); }
  return (
    <div style={{display:"inline-flex", alignItems:"center", borderRadius:12, overflow:"hidden", border:"1px solid var(--tg-theme-hint-color,#444)"}}>
      <button onMouseDown={()=>hold(-step)} onMouseUp={release} onMouseLeave={release} onClick={()=>bump(-step)} style={{padding:"10px 14px", border:"none"}}>-</button>
      <input value={value} onChange={e=>onChange(clamp(parseInt(e.target.value||"0")||0))} style={{width:90, textAlign:"center", border:"none", outline:"none", padding:"10px 0"}} />
      <span style={{paddingRight:8, opacity:.8}}>мл</span>
      <button onMouseDown={()=>hold(step)} onMouseUp={release} onMouseLeave={release} onClick={()=>bump(step)} style={{padding:"10px 14px", border:"none"}}>+</button>
    </div>
  );
}