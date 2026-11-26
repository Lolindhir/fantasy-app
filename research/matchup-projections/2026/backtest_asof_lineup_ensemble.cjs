#!/usr/bin/env node
"use strict";
// Research only: replay frozen published snapshots; never a production input or writer.
const {execFileSync}=require("node:child_process");
const path=require("node:path");
const SNAPS=[[5,"a6e44e497cef4b1e05e665b0d16ce9dcc79f668c","2026-10-08T21:35:20Z"],[6,"47b93807dba5aacdbb9bd9904fd8df2f00e86e17","2026-10-15T21:13:28Z"],[7,"b772191c64cfe0434e5eeec45dee74a0a812f3f7","2026-10-22T23:13:28Z"],[8,"3b1bd8f163a631cee81ec708d550f5c8195201e5","2026-10-29T22:58:14Z"],[9,"ecdc08690342b6f55b9cf6e08ff3c04ea6a2edfd","2026-11-05T23:56:20Z"],[10,"1166a6d6f32b6dc517fe7b226ce15802b705023a","2026-11-13T00:43:03Z"],[11,"23a4b5f896543096e3b4e3c33fafac6aece36eda","2026-11-19T11:33:24Z"]];
const TRUTH="9ff07162a701ea3545de23020fa9f022bf7aac02";
function forecast(d,p,s,b,w){
 const assert=(v,m)=>{if(!v)throw Error(m)}, avg=a=>a.reduce((x,y)=>x+y,0)/a.length;
 assert(d.LineupWeek===w&&Number(d.Season)===2026&&p.Week===w&&p.Season===2026&&s.Season===2026&&s.AsOf.CompletedWeeks===w-1&&b.Season===2026&&b.Week===w,"snapshot mismatch");
 assert(p.Records.every(x=>x.Actual?.State==="unavailable"&&x.Actual.Points===null),"target actual in pregame input");
 const form=d.FantasyRelevance.SlotDefinitions.map(x=>x.SlotType),pos=["QB","RB","WR","TE","K"],counts=Object.fromEntries([...pos,"FLEX"].map(x=>[x,form.filter(y=>y===x).length]));
 assert(form.length===13&&Object.values(counts).reduce((a,b)=>a+b,0)===form.length,"unsupported formation");
 const records=p.Records.filter(x=>x.PlayerID!=null),pi=new Map(records.map(x=>[String(x.PlayerID),x.Projection]));assert(pi.size===records.length,"duplicate PWF identity");
 const si=new Map(s.Teams.map(x=>[String(x.TeamID),x])),bi=new Map(b.Matchups.flatMap(g=>g.Teams.map(x=>[String(x.FantasyTeamID),x])));
 assert(si.size===6&&bi.size===6&&d.FantasyRelevance.Teams.length===6,"team count mismatch");
 const all=s.Teams.flatMap(x=>x.GameLog);
 assert(s.Teams.every(x=>x.GameLog.length===w-1&&x.GameLog.every((r,i)=>r.Week===i+1&&Number.isFinite(r.Points))),"past log incomplete");
 const league=avg(all.map(x=>x.Points)), result=[];
 function solve(c,kind){
   const utility=x=>x.m+(kind==="inertia3"&&x.starter?3:0)-(kind==="risk25"?.25*x.sd:0);
   const sort=a=>[...a].sort((a,b)=>utility(b)-utility(a)||a.id.localeCompare(b.id));let picked=[],extra=[];
   for(const p of pos){const a=sort(c.filter(x=>x.pos===p));if(a.length<counts[p])return null;picked.push(...a.slice(0,counts[p]));if(["RB","WR","TE"].includes(p))extra.push(...a.slice(counts[p]));}
   if(extra.length<counts.FLEX)return null;picked.push(...sort(extra).slice(0,counts.FLEX));
   assert(picked.length===form.length&&new Set(picked.map(x=>x.id)).size===form.length,"invalid lineup");
   return {mu:picked.reduce((a,x)=>a+x.m,0),sd:Math.sqrt(picked.reduce((a,x)=>a+x.sd*x.sd,0)),ids:picked.map(x=>x.id)};
 }
 for(const t of d.FantasyRelevance.Teams){
   const id=String(t.FantasyTeamID),hist=si.get(id),base=bi.get(id);assert(hist&&base&&base.FinalStarterCount===0,"missing or postkickoff team");
   const c=[],seen=new Set();
   for(const pl of t.Players){const id=String(pl.PlayerID);assert(!seen.has(id),"duplicate candidate");seen.add(id);
      if(!["starter","bench"].includes(pl.Placement)||pl.GameState!=="unlocked"||pl.ScoringAvailability?.State==="out"||!pos.includes(pl.Position))continue;
      const q=pi.get(id);if(q?.Status!=="available")continue;
      assert(q.ParticipationCondition==="conditional-on-participation"&&!q.AvailabilityAdjustmentApplied&&q.PredictionRange.Level===.9&&[q.Points,q.PredictionRange.Lower,q.PredictionRange.Upper].every(Number.isFinite)&&q.PredictionRange.Upper>=q.PredictionRange.Lower,"invalid PWF");
      c.push({id,pos:pl.Position,m:q.Points,sd:(q.PredictionRange.Upper-q.PredictionRange.Lower)/(2*1.6448536269514722),starter:pl.Placement==="starter"});
   }
   const h=hist.GameLog.map(x=>x.Points),weight=h.map((_,i)=>.8**(h.length-1-i)),ewma=h.reduce((a,x,i)=>a+x*weight[i],0)/weight.reduce((a,b)=>a+b,0);
   const histSD=Math.max(10,Math.sqrt(h.reduce((a,x)=>a+(x-avg(h))**2,0)/(h.length-1)));
   const model={base:Number.isFinite(base.ProjectedFinalScore)&&Number.isFinite(base.StandardDeviation)?{mu:base.ProjectedFinalScore,sd:base.StandardDeviation}:null,direct:solve(c,"direct"),inertia3:solve(c,"inertia3"),risk25:solve(c,"risk25"),ewma:{mu:ewma,sd:histSD},shrink4:{mu:(h.length*avg(h)+4*league)/(h.length+4),sd:histSD}};
   // Efficiency estimated on past weeks only; direct lineup (not hindsight best ball) is not multiplied by actual efficiency.
   model.bbActualEff=model.direct&&Number.isFinite(hist.LineupEfficiencyActual)?{mu:model.direct.mu*hist.LineupEfficiencyActual/100,sd:model.direct.sd*hist.LineupEfficiencyActual/100}:null;
   model.bbProjectedEff=model.direct&&Number.isFinite(hist.LineupEfficiencyProjected)?{mu:model.direct.mu*hist.LineupEfficiencyProjected/100,sd:model.direct.sd*hist.LineupEfficiencyProjected/100}:null;
   for(const [key,x] of [["baseEWMA",model.base],["directEWMA",model.direct],["inertiaEWMA",model.inertia3]]){
      // linear blend of estimates, not variance of independent predictions: use average SD.
      model[key]=x?{mu:(x.mu+ewma)/2,sd:(x.sd+histSD)/2}:null;
   }
   result.push({id,model,candidates:c.length,archiveHybrid:base.HybridExpected?.ExpectedPoints??null});
 }
 return result;
}
function evaluate(rows,b,m,t,w){
 const assert=(v,msg)=>{if(!v)throw Error(msg)};
 assert(t.Season===2026&&t.Week===w&&t.FinalityEvidence&&m.length===6&&t.Teams.length===6,"truth invalid");
 const target=new Map(t.Teams.map(x=>[x.CanonicalLeagueRosterID,x])),mi=new Map(m.map(x=>[String(x.ProviderMappings.find(y=>y.Provider==="Sleeper").ProviderRosterID),x]));
 const joined=rows.map(r=>{const src=mi.get(r.id),tr=target.get(src?.CanonicalLeagueRosterID);assert(src&&src.Week===w&&tr&&Number.isFinite(tr.ActualStarterPoints)&&Number.isFinite(tr.OfficialMatchupPoints),"truth identity");const starters=new Set(src.Starters.flatMap(x=>x?.ProviderMappings?.filter(y=>y.Provider==="Sleeper").map(y=>String(y.ProviderPlayerID))??[]));return {...r,w,match:src.CanonicalLeagueMatchupID,actual:tr.ActualStarterPoints,official:tr.OfficialMatchupPoints,overlap:Object.fromEntries(Object.entries(r.model).filter(([k,v])=>v?.ids).map(([k,v])=>[k,v.ids.filter(x=>starters.has(x)).length]))}});
 const map=new Map(joined.map(r=>[r.id,r]));for(const g of b.Matchups){const [a,c]=g.Teams.map(x=>map.get(String(x.FantasyTeamID)));assert(a&&c&&a.match===c.match,"match mismatch");}
 return joined;
}
function summarize(rows){
 const keys=Object.keys(rows[0].model),avg=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
 const norm=x=>{if(x===0)return .5;const t=1/(1+.2316419*Math.abs(x)),z=1-Math.exp(-x*x/2)/Math.sqrt(2*Math.PI)*t*(.31938153+t*(-.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))));return x<0?1-z:z};
 const groups={};for(const r of rows)(groups[r.w+":"+r.match]??=[]).push(r);
 const pairs=Object.values(groups);if(pairs.some(g=>g.length!==2))throw Error("invalid pair");
 function metrics(rs,ps,k){const a=rs.filter(r=>r.model[k]),b=ps.filter(g=>g.every(r=>r.model[k]));const errors=a.map(r=>r.model[k].mu-r.actual),loss=b.map(([r,s])=>{const x=r.model[k],z=s.model[k],y=r.official===s.official?.5:+(r.official>s.official),sd=Math.hypot(x.sd,z.sd),p=sd?norm((x.mu-z.mu)/sd):x.mu===z.mu?.5:+(x.mu>z.mu);return {raw:(p-y)**2,half:(.5+.5*(p-.5)-y)**2,coin:(.5-y)**2}});
 return {n:a.length,matches:b.length,mae:avg(errors.map(Math.abs)),bias:avg(errors),brier:avg(loss.map(x=>x.raw)),halfBrier:avg(loss.map(x=>x.half)),coin:avg(loss.map(x=>x.coin)),overlap:avg(a.filter(x=>Number.isFinite(x.overlap[k])).map(x=>x.overlap[k]))};}
 const common=rows.filter(r=>keys.every(k=>r.model[k])),cp=pairs.filter(g=>g.every(r=>keys.every(k=>r.model[k])));
 return {full:Object.fromEntries(keys.map(k=>[k,metrics(rows,pairs,k)])),common:Object.fromEntries(keys.map(k=>[k,metrics(common,cp,k)]))};
}
function main(){const root=path.resolve(__dirname,"../../.."),get=(ref,p)=>JSON.parse(execFileSync("git",["show",ref+":"+p],{cwd:root,encoding:"utf8",maxBuffer:32*1024*1024}));const rows=[],skips=[];for(const [w,ref,dt] of SNAPS){try{const d=get(ref,"public/data/DecisionWindows.json"),p=get(ref,"public/data/PlayerWeekFantasy.json"),s=get(ref,"data-derived/season-statistics/nfl-reise/2026.json"),b=get(ref,"public/data/MatchupProjections.json");if(!(dt<d.DecisionWindows.map(x=>x.StartsAtUtc).sort()[0]))throw Error("not pregame");const pred=forecast(d,p,s,b,w);const m=get(TRUTH,"data-source/leagues/nfl-reise/seasons/2026/matchups/week-"+w+".json"),t=get(TRUTH,"data-derived/team-week-performance/nfl-reise/2026/"+String(w).padStart(2,"0")+".json");rows.push(...evaluate(pred,b,m,t,w));}catch(e){skips.push({w,error:String(e)});}}if(!rows.length)throw Error("no accepted weeks");console.log(JSON.stringify({skips,overall:summarize(rows),byWeek:Object.fromEntries([...new Set(rows.map(x=>x.w))].map(w=>[w,summarize(rows.filter(x=>x.w===w))])),rows},null,2));}
if(require.main===module)main();
module.exports={forecast,evaluate,summarize,SNAPS,TRUTH};
