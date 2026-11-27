#!/usr/bin/env node
"use strict";
// Research only, #1451 AC1–AC5; read-only evidence from a pinned Git commit.
// Usage: node research/matchup-projections/2026/audit_projection_architecture.cjs --ref f417fbc4a735b9baf38bc5b948963940f7210cce --league nfl-reise --season 2026 --references
// Declared checked calculation edges, not an exhaustive inferred import graph. Optional PWF parity is not a TWP readiness dependency.
const EDGES = [
  [
    "CanonicalFacts",
    "PlayerWeekFantasy"
  ],
  [
    "CanonicalFacts",
    "AvailabilityFacts"
  ],
  [
    "CanonicalFacts",
    "TeamWeekPerformance"
  ],
  [
    "CanonicalFacts",
    "DecisionWindows"
  ],
  [
    "PlayerWeekFantasy",
    "HistoricalPregameAdapter"
  ],
  [
    "CanonicalFacts",
    "HistoricalPregameAdapter"
  ],
  [
    "HistoricalPregameAdapter",
    "SeasonStatistics"
  ],
  [
    "TeamWeekPerformance",
    "SeasonStatistics"
  ],
  [
    "SeasonStatistics",
    "Standings"
  ],
  [
    "Standings",
    "MatchupContext"
  ],
  [
    "Standings",
    "WeeklyRecaps"
  ],
  [
    "HistoricalPregameAdapter",
    "WeeklyRecaps"
  ],
  [
    "TeamWeekPerformance",
    "WeeklyRecaps"
  ],
  [
    "DecisionWindows",
    "MatchupContext"
  ],
  [
    "PlayerWeekFantasy",
    "MatchupContext"
  ],
  [
    "SeasonStatistics",
    "MatchupContext"
  ],
  [
    "SeasonStatistics",
    "ScheduleOutlook"
  ],
  [
    "CanonicalFacts",
    "ScheduleOutlook"
  ],
  [
    "AvailabilityFacts",
    "TeamInjuryImpact"
  ],
  [
    "PlayerWeekFantasy",
    "TeamInjuryImpact"
  ],
  [
    "CanonicalFacts",
    "TeamInjuryImpact"
  ]
];
// Candidate text references must be reviewed semantically; dynamic reads may not be caught.
const PATTERN = "PlayerWeekFantasy|player[-_ ]week[-_ ]fantasy|MatchupProjections|matchup[-_ ](projection|context)|ProjectedFinalScore|HybridExpected|BestBall|best[-_ ]ball|LineupEfficiency|EfficiencyPercent|PregameWinProbability|WinProbability|win[-_ ]prob|RelativeScoringStrength|ScheduleOutlook|schedule[-_ ]outlook|SeasonStatistics|season[-_ ]statistics|WeeklyRecaps|weekly[-_ ]recaps|team[-_ ]week[-_ ]performance|DecisionWindows|decision[-_ ]windows|nfl[-_ ]player[-_ ]availability|team[-_ ]injury[-_ ]impact|InjuryImpact|ExpectedPoints|PredictionRange|PlayerInjuryHistory|projection_view|league_scoring_projection";
const PATHS = ["tools","src/app","public/requests","fantasy-management/_ai","fantasy-management/automation/workflows","fantasy-management/analyses",".ai-context/manual",".github/workflows"];
function ensure(ok,message){if(!ok)throw Error(message)}
function canonical(v){if(Array.isArray(v))return v.map(canonical);if(v!==null&&typeof v==="object")return Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])]));return v}
function same(a,b){return JSON.stringify(canonical(a))===JSON.stringify(canonical(b))}
function topological(edges){const names=new Set(edges.flat()),todo=new Map([...names].map(n=>[n,new Set()])),levels=[];for(const [a,b] of edges)todo.get(b).add(a);while(todo.size){const ready=[...todo].filter(([,parents])=>parents.size===0).map(([k])=>k).sort();ensure(ready.length,"cycle: "+[...todo.keys()].join(", "));levels.push(ready);for(const n of ready)todo.delete(n);for(const p of todo.values())for(const n of ready)p.delete(n)}return levels}
function comparePregame(stats,recaps){const rows=new Map(),seen=new Set();for(const t of stats.Teams)for(const g of t.GameLog){const key=g.Week+":"+t.TeamID;ensure(!rows.has(key),"duplicate stats row "+key);rows.set(key,g)}const c={regularTeamWeeks:0,bothKnown:0,bothUnknown:0,onlyOne:0,diffAboveRounding:0,nearBoundary:0},differences=[];for(const w of recaps.Weeks)for(const m of w.WinProbabilities??[])for(const t of m.Teams??[]){const key=w.Week+":"+t.FantasyTeamID;if(!rows.has(key))continue;ensure(!seen.has(key),"duplicate recap row "+key);seen.add(key);const x=rows.get(key).PregameWinProbability,y=t.PregameWinProbability;c.regularTeamWeeks++;if(x==null&&y==null)c.bothUnknown++;else if(x==null||y==null){c.onlyOne++;differences.push({key,stats:x,recap:y})}else{ensure(Number.isFinite(x)&&x>=0&&x<=1&&Number.isInteger(y)&&y>=0&&y<=100,"bad probability "+key);c.bothKnown++;if(Math.abs(x*100-y)>.5050000001){c.diffAboveRounding++;differences.push({key,stats:x,recap:y})}if(Math.abs((x*100)%1-.5)<.005)c.nearBoundary++}}return {...c,statisticsTeamWeeks:rows.size,unmatchedStatisticsTeamWeeks:rows.size-seen.size,differences}}
async function audit(read,{league,season}){const receipts={};async function get(path){const r=await read(path);ensure(r&&r.sha&&r.value&&typeof r.value==="object","missing "+path);receipts[path]=r.sha;return r.value}const meta=await get("data-meta/"+league+"/metadata.json"),years=Object.keys(meta.Seasons).map(Number).filter(x=>x<=season).sort((a,b)=>a-b),root="data-derived/",historical=[];for(const year of years){const stats=await get(root+"season-statistics/"+league+"/"+year+".json"),recap=await get(root+"weekly-recaps/"+league+"/"+year+".json");ensure(stats.Season===year&&Number(recap.Season)===year&&stats.CanonicalLeagueID===league,"season identity mismatch");historical.push({season:year,statsWeeks:stats.Weeks.length,recapWeeks:recap.Weeks.length,...comparePregame(stats,recap),efficiency:stats.Teams.map(t=>({team:t.TeamID,meanWeekly:t.LineupEfficiencyActual,ratioTotals:recap.SeasonEfficiency.find(e=>e.FantasyTeamID===t.TeamID)?.EfficiencyPercent??null}))})}const context=await get(root+"matchup-context/"+league+"/"+season+"/current.json"),app=await get("public/data/MatchupProjections.json");ensure(app.CanonicalLeagueID===league&&app.Season===season&&app.Week===context.Week,"current matchup identity mismatch");const pwf=await get(root+"player-week-fantasy/"+league+"/"+season+"/"+String(app.Week).padStart(2,"0")+".json");ensure(pwf.CanonicalLeagueID===league&&pwf.Season===season&&pwf.Week===app.Week,"PWF identity mismatch");const outlookApp=await get("public/data/ScheduleOutlook.json");ensure(outlookApp.CanonicalLeagueID===league&&outlookApp.Season===season,"outlook identity mismatch");const outlook=await get(root+"league-schedule-outlook/"+league+"/"+season+"/after-week-"+String(outlookApp.AsOf.AfterWeek).padStart(2,"0")+".json"),available=pwf.Records.filter(r=>r.Projection?.Status==="available");return {league,season,selectedModels:meta.Seasons[String(season)].Models,player:{week:app.Week,records:pwf.Records.length,available:available.length,model:pwf.ProjectionModel,conditionalWithoutAdjustment:available.filter(r=>r.Projection.ParticipationCondition==="conditional-on-participation"&&r.Projection.AvailabilityAdjustmentApplied===false).length},current:{matchupProductEqualsApp:same(context.MatchupProjections,app),outlookProductEqualsApp:same(outlook,outlookApp),contextHasExactAsOf:typeof context.AsOfUtc==="string"||typeof context.FantasyGameContext?.AsOfUtc==="string",outlookAfterWeek:outlookApp.AsOf.AfterWeek,teams:app.Matchups.flatMap(m=>m.Teams.map(t=>({team:t.FantasyTeamID,starter:t.ProjectedFinalScore,display:t.DisplayProjectedScore,hybrid:t.HybridExpected?.ExpectedPoints??null,efficiencyThroughWeek:t.HybridExpected?.SourceThroughWeek??null})))},historical,declaredGraphLevels:topological(EDGES),receipts}}
async function cli(){const {execFileSync}=require("node:child_process"),args=process.argv.slice(2),options={};for(let i=0;i<args.length;i++){if(args[i]==="--references")options.references=true;else if(["--ref","--league","--season"].includes(args[i])){const key=args[i].slice(2);ensure(i+1<args.length&&!args[i+1].startsWith("--"),"missing "+key);options[key]=args[++i]}else throw Error("unknown argument "+args[i])}ensure(options.ref&&/^[a-f0-9]{40}$/.test(options.ref),"explicit 40-character commit --ref required");ensure(options.league&&/^[a-z0-9-]+$/.test(options.league),"--league required");ensure(/^\d{4}$/.test(options.season??""),"--season required");function git(args){return execFileSync("git",args,{encoding:"utf8",maxBuffer:128*1024*1024})}const pin=git(["rev-parse","--verify",options.ref+"^{commit}"]).trim(),read=path=>({sha:git(["rev-parse",pin+":"+path]).trim(),value:JSON.parse(git(["show",pin+":"+path]))}),result=await audit(read,{league:options.league,season:Number(options.season)});result.ref=pin;if(options.references){try{result.referenceCandidates=git(["grep","-I","-n","-E","-i",PATTERN,pin,"--",...PATHS]).trim().split("\n").filter(Boolean)}catch(e){if(e.status===1)result.referenceCandidates=[];else throw e}}process.stdout.write(JSON.stringify(result,null,2)+"\n")}
module.exports={audit,comparePregame,topological,EDGES,PATTERN,PATHS};
if(require.main===module) cli().catch(e=>{console.error(e);process.exitCode=1;});
