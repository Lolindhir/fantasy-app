#!/usr/bin/env node
"use strict";
// Research only. Historical as-of all-roster potential, not legal live lineup advice.
const {execFileSync}=require("node:child_process"),path=require("node:path");
const {SNAPS,TRUTH,historicalScores}=require("./backtest_asof_lineup_ensemble.cjs");
const POS=["QB","RB","WR","TE","K"],COUNTS={QB:2,RB:2,WR:2,TE:2,K:1,FLEX:4},Z=1.6448536269514722;
const assert=(x,m)=>{if(!x)throw Error(m)},sum=a=>a.reduce((x,y)=>x+y,0),mean=a=>a.length?sum(a)/a.length:null;
function best(c,k){
 let total=0,left=[];
 for(const pos of POS){const a=c.filter(x=>x.pos===pos&&x[k]>0).map(x=>x[k]).sort((a,b)=>b-a);total+=sum(a.slice(0,COUNTS[pos]));if(["RB","WR","TE"].includes(pos))left.push(...a.slice(COUNTS[pos]));}
 return total+sum(left.sort((a,b)=>b-a).slice(0,COUNTS.FLEX));
}
function forecast(d,p,w,dt){
 assert(Number(d.Season)===2026&&d.LineupWeek===w&&p.Season===2026&&p.Week===w&&dt<d.DecisionWindows.map(x=>x.StartsAtUtc).sort()[0],"invalid as-of");
 assert(p.Records.every(x=>x.Actual.State==="unavailable"&&x.Actual.Points===null),"target outcome present");
 const slots=d.FantasyRelevance.SlotDefinitions.map(x=>x.SlotType),counts=Object.fromEntries([...POS,"FLEX"].map(k=>[k,slots.filter(x=>x===k).length]));
 assert(slots.length===13&&JSON.stringify(counts)===JSON.stringify(COUNTS),"unsupported slots");
 const records=p.Records.filter(x=>x.PlayerID!=null),index=new Map(records.map(x=>[String(x.PlayerID),x]));
 assert(index.size===records.length&&d.FantasyRelevance.Teams.length===6,"duplicate player or team count");
 const rows=[];
 for(const t of d.FantasyRelevance.Teams){
 const id=String(t.FantasyTeamID),roster=t.Players.map(x=>({id:String(x.PlayerID),pos:x.Position,state:x.GameState,placement:x.Placement})),c=[];
 assert(new Set(roster.map(x=>x.id)).size===roster.length,"duplicate roster member");
 for(const pl of roster){const q=index.get(pl.id)?.Projection;if(pl.state!=="unlocked"||!POS.includes(pl.pos)||q?.Status!=="available")continue;assert(q.ParticipationCondition==="conditional-on-participation"&&!q.AvailabilityAdjustmentApplied&&q.PredictionRange.Level===.9&&[q.Points,q.PredictionRange.Lower,q.PredictionRange.Upper].every(Number.isFinite)&&q.PredictionRange.Upper>=q.PredictionRange.Lower,"invalid projection");c.push({...pl,mu:q.Points,sd:(q.PredictionRange.Upper-q.PredictionRange.Lower)/(2*Z)});}
 let state=(20261126+100*w+Number(id))>>>0;const u=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return (state+.5)/4294967296};const n=()=>Math.sqrt(-2*Math.log(u()))*Math.cos(2*Math.PI*u());const samples=[];
 for(let i=0;i<1200;i++){for(const x of c)x.draw=x.mu+x.sd*n();samples.push(best(c,"draw"));}
 const mc=mean(samples);rows.push({w,id,roster,candidates:c.length,det:best(c,"mu"),mc,sd:Math.sqrt(mean(samples.map(x=>(x-mc)**2)))});
 }
 return rows;
}
function evaluate(rows,m,t){
 assert(t.Season===2026&&t.Week===rows[0].w&&typeof t.FinalityEvidence==="string"&&m.length===6&&t.Teams.length===6,"invalid truth");
 const sid=x=>String(x.ProviderMappings.find(y=>y.Provider==="Sleeper")?.ProviderPlayerID),res=[];
 for(const r of rows){
 const row=m.find(x=>String(x.ProviderMappings.find(y=>y.Provider==="Sleeper")?.ProviderRosterID)===r.id),truth=t.Teams.find(x=>x.CanonicalLeagueRosterID===row?.CanonicalLeagueRosterID);assert(row&&truth&&row.Week===r.w,"missing final identity");
 const pts=new Map(row.PlayerPoints.map(x=>[sid(x.Player),x.Points])),finalIds=new Set(row.Players.map(sid));assert(pts.size===finalIds.size&&[...finalIds].every(id=>pts.has(id)&&Number.isFinite(pts.get(id))),"missing truth points");
 const same=finalIds.size===r.roster.length&&r.roster.every(x=>finalIds.has(x.id));
 const realized=best(r.roster.filter(x=>pts.has(x.id)).map(x=>({...x,score:pts.get(x.id)})),"score");
 assert([truth.PotentialPoints,truth.ActualStarterPoints,truth.OfficialMatchupPoints].every(Number.isFinite)&&truth.PotentialPoints>0,"invalid score");
 const aligned=same&&Math.abs(realized-truth.PotentialPoints)<.05;
 res.push({w:r.w,id:r.id,match:row.CanonicalLeagueMatchupID,det:r.det,mc:r.mc,sd:r.sd,bb:truth.PotentialPoints,actual:truth.ActualStarterPoints,official:truth.OfficialMatchupPoints,aligned,same,realized,candidates:r.candidates,roster:r.roster.length});
 }return res;
}
function walk(rows){
 // Warm up on W5–6, use only prior accepted aligned weeks, no target-dependent forecast.
 // 4 pseudo-observations on zero BB bias; 4 on prior league efficiency for own team.
 const results=[];
 for(const r of rows.filter(x=>x.w>=7)){
  const h=rows.filter(x=>x.w<r.w&&x.aligned),own=h.filter(x=>x.id===r.id);if(!h.length)continue;
  const eff=mean(h.map(x=>x.actual/x.bb));
  const e=(sum(own.map(x=>x.actual/x.bb))+4*eff)/(own.length+4);
  const missed=(sum(own.map(x=>x.bb-x.actual))+4*mean(h.map(x=>x.bb-x.actual)))/(own.length+4);
  const weighted=h.map(x=>({x,weight:.8**(r.w-1-x.w)})),W=sum(weighted.map(x=>x.weight));
  const bias=sum(h.map(x=>x.bb-x.mc))/(h.length+4),recentBias=sum(weighted.map(({x,weight})=>weight*(x.bb-x.mc)))/(W+4);
  const detBias=sum(h.map(x=>x.bb-x.det))/(h.length+4);
  const teamBias=sum(h.map(x=>x.actual-x.mc*eff))/(h.length+4); // comparator only: pooled current league eff on past data, not historic forecast residuals.
  const bb={rawMC:r.mc,calMC:Math.max(0,r.mc+bias),recentMC:Math.max(0,r.mc+recentBias),rawDet:r.det,calDet:Math.max(0,r.det+detBias)};
  const team={rawMC:bb.rawMC*e,calMC:bb.calMC*e,recentMC:bb.recentMC*e,rawDet:bb.rawDet*e,calDet:bb.calDet*e,calMissed:bb.calMC-missed,pooledTeamCorrection:r.mc*eff+teamBias};
  // Oracle is evaluation only; never passed to forecast or downstream.
  const oracle=r.bb*e;
  results.push({...r,bbPred:bb,teamPred:team,effPred:e,leagueEff:eff,n:h.length,ownN:own.length,oracle,
    decomposition:{potential:(bb.calMC-r.bb)*e,efficiency:r.bb*e-r.actual}});
 }
 return results;
}
function summarize(rows){
 const mk=(rs,field,target)=>Object.fromEntries(Object.keys(rs[0]?.[field]||{}).map(k=>{const err=rs.map(r=>r[field][k]-r[target]);return [k,{mae:mean(err.map(Math.abs)),bias:mean(err)}]}));
 const groups=new Map();for(const r of rows){const k=r.w+":"+r.match;const g=groups.get(k)||[];g.push(r);groups.set(k,g);}
 const pairs=[...groups.values()].filter(g=>g.length===2);
 const err=rows.map(r=>r.oracle-r.actual);
 return {n:rows.length,matches:pairs.length,bb:mk(rows,"bbPred","bb"),team:mk(rows,"teamPred","actual"),oracleMAE:mean(err.map(Math.abs)),effMAE:mean(rows.map(r=>Math.abs(r.effPred-r.actual/r.bb))),decomposition:{potentialMAE:mean(rows.map(r=>Math.abs(r.decomposition.potential))),efficiencyMAE:mean(rows.map(r=>Math.abs(r.decomposition.efficiency))),potentialBias:mean(rows.map(r=>r.decomposition.potential)),efficiencyBias:mean(rows.map(r=>r.decomposition.efficiency))}};
}
function validate(rows){
 const out=walk(rows);for(const r of out)assert(Math.abs(r.decomposition.potential+r.decomposition.efficiency-(r.teamPred.calMC-r.actual))<1e-8,"decomposition identity");
 for(const w of [...new Set(rows.map(x=>x.w))]){
  const changed=rows.map(x=>x.w>=w?{...x,actual:999999,bb:888888,official:999999,aligned:!x.aligned}:x);
  const pick=a=>a.filter(r=>r.w===w).map(r=>[r.id,r.bbPred,r.teamPred,r.effPred]);assert(JSON.stringify(pick(out))===JSON.stringify(pick(walk(changed))),"future outcome leakage");
 }
 return out;
}
function verifyPriorOfficial(rows,history,w){
 const h=new Map(history.Teams.map(t=>[String(t.TeamID),new Map(t.GameLog.map(g=>[g.Week,g.Points]))]));
 for(const r of rows.filter(x=>x.w<w))assert(h.get(r.id)?.get(r.w)===r.official,"prior official score mismatch at W"+w+" for W"+r.w+"/"+r.id);
 return true;
}
function main(){
 const root=path.resolve(__dirname,"../../.."),get=(ref,p)=>JSON.parse(execFileSync("git",["show",ref+":"+p],{cwd:root,encoding:"utf8",maxBuffer:32*1024*1024}));const rows=[];
 for(const [w,ref,dt] of SNAPS){const d=get(ref,"public/data/DecisionWindows.json"),p=get(ref,"public/data/PlayerWeekFantasy.json");const preds=forecast(d,p,w,dt);verifyPriorOfficial(rows,historicalScores(get(ref,"public/data/Matchups.json"),w),w);
 const m=get(TRUTH,"data-source/leagues/nfl-reise/seasons/2026/matchups/week-"+w+".json"),t=get(TRUTH,"data-derived/team-week-performance/nfl-reise/2026/"+String(w).padStart(2,"0")+".json");
 rows.push(...evaluate(preds,m,t));}
 const result=validate(rows);
 console.log(JSON.stringify({researchOnly:true,rows,all:summarize(result),aligned:summarize(result.filter(r=>r.aligned)),leakage:"PASS"},null,2));
}
if(require.main===module)main();
module.exports={forecast,evaluate,walk,summarize,validate,best,verifyPriorOfficial,SNAPS,TRUTH};
