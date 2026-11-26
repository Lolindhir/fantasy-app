#!/usr/bin/env node
"use strict";
// Research only. No production writer. CP3n as-of inputs and lagged, archived results.
const {execFileSync}=require("node:child_process"),path=require("node:path");
const {forecast,evaluate,historicalScores,SNAPS,TRUTH}=require("./backtest_asof_lineup_ensemble.cjs");
function calibrate(prior,history,r,key){
 const original=r.model[key];if(!original)return null;
 const e=prior.filter(x=>x.model[key]).map(x=>{const y=history.get(x.id)?.get(x.w);if(!Number.isFinite(y)||x.w>=r.w)throw Error("missing prior final score");return y-x.model[key].mu;});
 const k=12,bias=e.reduce((s,x)=>s+x,0)/(k+e.length);
 return {mu:original.mu+bias,sd:Math.max(10,Math.sqrt((k*original.sd**2+e.reduce((s,x)=>s+(x-bias)**2,0))/(k+e.length))),n:e.length,bias};
}
function experiment(rows,histories){
 const keys=["base","inertia3","shrink4","inertiaEWMA"];const sorted=[...rows].sort((a,b)=>a.w-b.w);
 return sorted.map(r=>{
 const prior=sorted.filter(x=>x.w<r.w),h=histories.get(r.w);if(!h)throw Error("missing historical snapshot");
 const model=Object.fromEntries(keys.map(k=>[k,r.model[k]]));
 for(const k of keys)model[k+"Cal"]=calibrate(prior,h,r,k);
 model.inertiaFallback=model.inertia3??model.shrink4;
 model.ensembleFallback=model.inertiaEWMA??model.shrink4;
 model.ensembleCalFallback=model.inertiaEWMACal??model.shrink4Cal;
 return {...r,model};
 });
}
function stats(rows){
 const keys=Object.keys(rows[0].model),avg=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
 const norm=x=>{if(x===0)return .5;const t=1/(1+.2316419*Math.abs(x)),z=1-Math.exp(-x*x/2)/Math.sqrt(2*Math.PI)*t*(.31938153+t*(-.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));return x<0?1-z:z};
 const groups={};for(const r of rows)(groups[r.w+":"+r.match]??=[]).push(r);
 const pairs=Object.values(groups);if(pairs.some(g=>g.length!==2))throw Error("invalid pair");
 const common=rows.filter(r=>r.model.base&&r.model.inertia3),commonP=pairs.filter(g=>g.every(r=>r.model.base&&r.model.inertia3));
 function metrics(rs,ps,k){const a=rs.filter(r=>r.model[k]),b=ps.filter(g=>g.every(r=>r.model[k]));const err=a.map(r=>r.model[k].mu-r.actual),loss=b.map(([r,s])=>{const x=r.model[k],z=s.model[k],y=r.official===s.official?.5:+(r.official>s.official),sd=Math.hypot(x.sd,z.sd),p=sd?norm((x.mu-z.mu)/sd):x.mu===z.mu?.5:+(x.mu>z.mu);return {raw:(p-y)**2,half:(.5+.5*(p-.5)-y)**2}});
 return {n:a.length,m:b.length,mae:avg(err.map(Math.abs)),bias:avg(err),brier:avg(loss.map(x=>x.raw)),half:avg(loss.map(x=>x.half))};}
 const baseP=pairs.filter(g=>g.every(r=>r.model.base)),baseR=rows.filter(r=>r.model.base);
 return {common:Object.fromEntries(keys.map(k=>[k,metrics(common,commonP,k)])),baseCoverage:Object.fromEntries(keys.filter(k=>["base","baseCal","inertiaFallback","ensembleFallback","ensembleCalFallback","shrink4","shrink4Cal"].includes(k)).map(k=>[k,metrics(baseR,baseP,k)])),full:Object.fromEntries(keys.filter(k=>k.endsWith("Fallback")||k==="shrink4").map(k=>[k,metrics(rows,pairs,k)])),loo:[...new Set(commonP.map(g=>g[0].w))].map(w=>({w,base:metrics(common.filter(r=>r.w!==w),commonP.filter(g=>g[0].w!==w),"base").brier,ensemble:metrics(common.filter(r=>r.w!==w),commonP.filter(g=>g[0].w!==w),"ensembleFallback").half}))};
}
function main(){
 const root=path.resolve(__dirname,"../../.."),get=(ref,p)=>JSON.parse(execFileSync("git",["show",ref+":"+p],{cwd:root,encoding:"utf8",maxBuffer:32*1024*1024}));
 const rows=[],histories=new Map();
 for(const [w,ref,dt] of SNAPS){
 const d=get(ref,"public/data/DecisionWindows.json"),p=get(ref,"public/data/PlayerWeekFantasy.json"),h=historicalScores(get(ref,"public/data/Matchups.json"),w),b=get(ref,"public/data/MatchupProjections.json");
 if(!(dt<d.DecisionWindows.map(x=>x.StartsAtUtc).sort()[0]))throw Error("not pregame");
 histories.set(w,new Map(h.Teams.map(t=>[String(t.TeamID),new Map(t.GameLog.map(g=>[g.Week,g.Points]))])));
 const preds=forecast(d,p,h,b,w);
 const m=get(TRUTH,"data-source/leagues/nfl-reise/seasons/2026/matchups/week-"+w+".json"),t=get(TRUTH,"data-derived/team-week-performance/nfl-reise/2026/"+String(w).padStart(2,"0")+".json");
 rows.push(...evaluate(preds,b,m,t,w));
 }
 const out=experiment(rows,histories);
 const changed=rows.map(r=>r.w===11?{...r,actual:999999,official:999999}:r);
 if(JSON.stringify(experiment(changed,histories).map(r=>r.model))!==JSON.stringify(out.map(r=>r.model)))throw Error("leakage");
 console.log(JSON.stringify({targetPerturbation:"PASS",all:stats(out),v1:stats(out.filter(r=>r.w>=10))},null,2));
}
if(require.main===module)main();
module.exports={calibrate,experiment,stats};
