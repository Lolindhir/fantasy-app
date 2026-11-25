#!/usr/bin/env node
"use strict";
// CP3l: research-only, strictly lagged team-score benchmark; no PWF or target-week features.
// Read pinned CP3k tree with git show; no writers, no generated file edits.
// Run: node research/matchup-projections/2026/backtest_lag_only_team_strength.cjs [--self-test]
const {execFileSync}=require("node:child_process");
const path=require("node:path");
const REF="5712ec20e6207c1b3afee0a64abd3cb8adcf75ae";
function run(year,docs,matchups,from=5,to=docs.length){
 const assert=(x,msg)=>{if(!x)throw Error(msg)};
 const names=["league","mean","last4","shrink4","potentialEfficiency","additiveMissed","ewma"],avg=a=>a.reduce((s,x)=>s+x,0)/a.length;
 const norm=x=>{if(x===0)return .5;const t=1/(1+.2316419*Math.abs(x)),z=1-Math.exp(-x*x/2)/Math.sqrt(2*Math.PI)*t*(.31938153+t*(-.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));return x<0?1-z:z};
 const rows=[],matches=[],errors=Object.fromEntries(names.map(n=>[n,[]]));
 assert(docs.every((t,i)=>t.FinalityEvidence&&t.Season===year&&t.Week===i+1&&t.Teams.length===6&&new Set(t.Teams.map(x=>x.CanonicalLeagueRosterID)).size===6&&t.Teams.every(x=>[x.ActualStarterPoints,x.OfficialMatchupPoints,x.PotentialPoints,x.EfficiencyPercent,x.MissedPoints].every(Number.isFinite))),"invalid input");
 for(let w=3;w<=to;w++){
  const target=docs[w-1],hist=docs.slice(0,w-1),lg=avg(hist.flatMap(t=>t.Teams.map(x=>x.ActualStarterPoints)));
  const wr=target.Teams.map(t=>{
   const h=hist.map(x=>x.Teams.find(k=>k.CanonicalLeagueRosterID===t.CanonicalLeagueRosterID));assert(h.every(Boolean),"missing prior team");
   const mean=avg(h.map(x=>x.ActualStarterPoints)),pot=avg(h.map(x=>x.PotentialPoints)),eff=avg(h.map(x=>x.EfficiencyPercent/100)),weight=h.map((x,i)=>.8**(h.length-1-i));
   const p={league:lg,mean,last4:avg(h.slice(-4).map(x=>x.ActualStarterPoints)),shrink4:(h.length*mean+4*lg)/(h.length+4),potentialEfficiency:pot*eff,additiveMissed:pot-avg(h.map(x=>x.MissedPoints)),ewma:h.reduce((s,x,i)=>s+x.ActualStarterPoints*weight[i],0)/weight.reduce((a,b)=>a+b,0)};
   return {w,id:t.CanonicalLeagueRosterID,actual:t.ActualStarterPoints,official:t.OfficialMatchupPoints,p,sd:Object.fromEntries(names.map(n=>[n,errors[n].length>=12?Math.max(10,Math.sqrt(avg(errors[n].map(x=>x*x)))):35]))}
  });
  if(w>=from){
   rows.push(...wr);const source=matchups[w];assert(Array.isArray(source)&&source.length===6&&new Set(source.map(x=>x.CanonicalLeagueRosterID)).size===6,"invalid matchup source");
   const groups={};for(const t of source){assert(t.Week===w&&typeof t.CanonicalLeagueMatchupID==="string"&&t.CanonicalLeagueMatchupID,"invalid matchup key");(groups[t.CanonicalLeagueMatchupID]??=[]).push(wr.find(r=>r.id===t.CanonicalLeagueRosterID))}
   for(const g of Object.values(groups)){assert(g.length===2&&g.every(Boolean),"invalid match");const[a,b]=g;matches.push({w,ids:g.map(r=>r.id),y:a.official===b.official?.5:+(a.official>b.official),p:Object.fromEntries(names.map(n=>[n,norm((a.p[n]-b.p[n])/Math.hypot(a.sd[n],b.sd[n]))]))})}
  }
  for(const r of wr)for(const n of names)errors[n].push(r.p[n]-r.actual)
 }
 const report=(rs,ms)=>({teams:rs.length,matchups:ms.length,metrics:Object.fromEntries(names.map(n=>[n,{mae:avg(rs.map(r=>Math.abs(r.p[n]-r.actual))),bias:avg(rs.map(r=>r.p[n]-r.actual)),brier:avg(ms.map(m=>(m.p[n]-m.y)**2))}]))});
 const skip=year===2025?[7,"clr-404c16cec9545e41bcfd6114ff4c755a"]:[10,"clr-dc35c0c936175f68a694e7b05bd6861d"];
 return {year,from,to,full:report(rows,matches),cp3kPaired:from===5&&to===10?report(rows.filter(r=>!(r.w===skip[0]&&r.id===skip[1])),matches.filter(m=>!(m.w===skip[0]&&m.ids.includes(skip[1])))):null,rows,matches};
}
function selfTest(){
 const doc=(w,shift=0)=>({Season:2025,Week:w,FinalityEvidence:"synthetic",Teams:Array.from({length:6},(_,i)=>{const p=100+i*10+shift;return {CanonicalLeagueRosterID:"r"+i,ActualStarterPoints:p,OfficialMatchupPoints:p,PotentialPoints:p+10,MissedPoints:10,EfficiencyPercent:100*p/(p+10)}})});
 const a=Array.from({length:5},(_,i)=>doc(i+1)),m={5:Array.from({length:6},(_,i)=>({Week:5,CanonicalLeagueRosterID:"r"+i,CanonicalLeagueMatchupID:"m"+Math.floor(i/2)}))};
 const b=run(2025,a,m,5,5),c=run(2025,[...a.slice(0,4),doc(5,1000)],m,5,5);
 if(b.full.teams!==6||b.full.matchups!==3||b.full.metrics.mean.mae!==0||b.full.metrics.league.brier!==.25||JSON.stringify(b.rows.map(r=>[r.p,r.sd]))!==JSON.stringify(c.rows.map(r=>[r.p,r.sd])))throw Error("self-test failed");
 return "PASS";
}
function main(){
 if(process.argv.includes("--self-test")){console.log(selfTest());return;}
 const root=path.resolve(__dirname,"../../.."),load=p=>JSON.parse(execFileSync("git",["show",REF+":"+p],{cwd:root,encoding:"utf8",maxBuffer:16*1024*1024}));
 for(const [year,end] of [[2025,14],[2026,10]]){
  const docs=Array.from({length:end},(_,i)=>load("data-derived/team-week-performance/nfl-reise/"+year+"/"+String(i+1).padStart(2,"0")+".json"));
  const matchups=Object.fromEntries(Array.from({length:end-4},(_,i)=>[i+5,load("data-source/leagues/nfl-reise/seasons/"+year+"/matchups/week-"+(i+5)+".json")]));
  for(const [from,to] of [[5,10],...(year===2025?[[11,14]]:[])]){
   const {rows,matches,...summary}=run(year,docs,matchups,from,to);
   console.log(JSON.stringify(summary,null,2));
  }
 }
}
if(require.main===module)main();
module.exports={run,selfTest};
