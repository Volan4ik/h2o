import React from "react";

// SVG бутылка с двумя волнами и пузырьками. Анимации лёгкие, уважают prefers-reduced-motion.
export default function Bottle({percent, animateBubbles=true}:{percent:number, animateBubbles?:boolean}){
  const clamped = Math.max(0, Math.min(100, percent));
  const waveY = 100 - clamped; // проценты снизу
  const bubbles = Array.from({length: 8}).map((_,i)=>({
    left: 10 + Math.random()*80,
    delay: `${Math.random()*4}s`,
    dur: `${3+Math.random()*3}s`,
    size: 4 + Math.random()*6
  }));
  return (
    <div style={{display:"flex", justifyContent:"center", marginTop:12}}>
      <svg width="160" height="300" viewBox="0 0 160 300" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <clipPath id="bottle-clip">
            <path d="M60 15 h40 v30 c0 10 20 20 20 30 v150 c0 40 -30 60 -60 60 s-60 -20 -60 -60 v-150 c0 -10 20 -20 20 -30 v-30 z"/>
          </clipPath>
          <linearGradient id="glass" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#ffffff11"/>
            <stop offset="100%" stopColor="#ffffff22"/>
          </linearGradient>
          <linearGradient id="water" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--tg-theme-button-color,#37e)"/>
            <stop offset="100%" stopColor="#4cf"/>
          </linearGradient>
        </defs>
        <path d="M60 15 h40 v30 c0 10 20 20 20 30 v150 c0 40 -30 60 -60 60 s-60 -20 -60 -60 v-150 c0 -10 20 -20 20 -30 v-30 z" fill="url(#glass)" stroke="currentColor" strokeOpacity="0.2"/>

        <g clipPath="url(#bottle-clip)">
          <rect x="0" y="0" width="160" height="300" fill="none"/>
          <g transform={`translate(0,${waveY*3})`}>
            <Wave speed={8} amplitude={6} />
            <Wave speed={12} amplitude={3} opacity={0.6} />
          </g>
          {animateBubbles && bubbles.map((b,i)=> (
            <circle key={i} cx={`${b.left}%`} cy="260" r={b.size} fill="#fff" fillOpacity="0.35" style={{animation: `rise ${b.dur} linear ${b.delay} infinite`, filter: "blur(0.2px)"}} />
          ))}
        </g>
        <style>{`
          @keyframes drift { from { transform: translateX(0); } to { transform: translateX(-160px); } }
          @keyframes rise { 0% { transform: translateY(0); opacity: .0; } 10%{opacity:.6;} 100% { transform: translateY(-220px); opacity: 0; } }
          @media (prefers-reduced-motion: reduce) { 
            circle, path.wave { animation: none !important; }
          }
        `}</style>
      </svg>
    </div>
  );
}

function Wave({speed=10, amplitude=5, opacity=1}:{speed?:number, amplitude?:number, opacity?:number}){
  return (
    <g style={{animation: `drift ${speed}s linear infinite`}}>
      <path className="wave" d={`M0 ${200} C 20 ${200-amplitude}, 40 ${200+amplitude}, 60 ${200-amplitude} S 100 ${200+amplitude}, 120 ${200-amplitude} S 160 ${200+amplitude}, 180 ${200-amplitude}`}
            fill="url(#water)" fillOpacity={opacity}/>
    </g>
  );
}