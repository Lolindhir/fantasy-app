#!/usr/bin/env node
"use strict";
// Research-only source-read witness audit. Does not execute materializers, prove complete DAG, or classify dynamic reads.
// CLI: node research/matchup-projections/2026/audit_projection_review_resolution.cjs --ref 46de0b7cc9026039b668361acca4055f0210253c --league nfl-reise --years 2024,2025,2026 --references
const WITNESSES = [
  [
    "player-week-fantasy",
    "season-statistics",
    "optional-projection",
    "tools/derived_data_lib/season_statistics.py",
    "_pwf_projections(repo_root, league_id, season, week)"
  ],
  [
    "team-week-performance",
    "season-statistics",
    "optional-efficiency",
    "tools/derived_data_lib/season_statistics.py",
    "DATA_DERIVED_ROOT / \"team-week-performance\""
  ],
  [
    "player-week-fantasy",
    "weekly-recaps",
    "optional-projection",
    "tools/derived_data_lib/weekly_recaps.py",
    "DATA_DERIVED_ROOT / \"player-week-fantasy\""
  ],
  [
    "team-week-performance",
    "weekly-recaps",
    "optional-efficiency",
    "tools/derived_data_lib/weekly_recaps.py",
    "DATA_DERIVED_ROOT / \"team-week-performance\""
  ],
  [
    "season-statistics",
    "league-standings",
    "optional-awards",
    "tools/derived_data.py",
    "read_season_statistics(data_derived_dir(repo_root), league_id, season)"
  ],
  [
    "league-standings",
    "matchup-context",
    "required-order",
    "tools/derived_data_lib/matchup_context.py",
    "participant_order_from_standings(standings_product(repo_root, league_id, season))"
  ],
  [
    "league-standings",
    "weekly-recaps",
    "required-order",
    "tools/derived_data_lib/weekly_recaps.py",
    "participant_order_from_standings(standings_product(repo_root, league_id, season))"
  ],
  [
    "player-week-fantasy",
    "matchup-context",
    "optional-projection-adapter",
    "tools/matchup_context_materialize.py",
    "load_sleeper_keyed_view(repo_root, league_id, season, int(context[\"Week\"]))"
  ],
  [
    "player-week-fantasy",
    "matchup-context",
    "adapter-read-path",
    "tools/derived_data_lib/player_week_fantasy_view.py",
    " / \"player-week-fantasy\""
  ],
  [
    "season-statistics",
    "matchup-context",
    "optional-fallback-preview",
    "tools/derived_data_lib/matchup_projection.py",
    "DATA_DERIVED_ROOT / \"season-statistics\""
  ],
  [
    "season-statistics",
    "league-schedule-outlook",
    "current-cutoff-strength",
    "tools/league_schedule_outlook_preview.py",
    "data_derived_dir(self.repo_root) / \"season-statistics\" / self.league_id / f\"{self.season}.json\""
  ],
  [
    "season-statistics",
    "league-schedule-outlook",
    "prior-season-strength",
    "tools/league_schedule_outlook_preview.py",
    "data_derived_dir(self.repo_root) / \"season-statistics\" / self.league_id / f\"{self.season - 1}.json\""
  ],
  [
    "nfl-player-availability",
    "team-injury-impact",
    "historical-evidence",
    "tools/derived_data_lib/team_injury_impact.py",
    "DATA_DERIVED_ROOT / \"nfl-player-availability\""
  ],
  [
    "player-week-fantasy",
    "team-injury-impact",
    "conditional-points",
    "tools/derived_data_lib/team_injury_impact.py",
    "DATA_DERIVED_ROOT / \"player-week-fantasy\""
  ],
  [
    "season-statistics",
    "league-records",
    "required-season-input",
    "tools/league_records_materialize.py",
    "out_root / \"season-statistics\""
  ],
  [
    "league-records",
    "app-season-statistics",
    "consumer-delivery",
    "tools/season_statistics_app_publish.py",
    "legacy_biggest_upset(read_persisted(out_root, league_id))"
  ],
  [
    "player-week-fantasy",
    "team-week-performance",
    "optional-parity-not-readiness",
    "tools/team_week_performance_materialize.py",
    "repo_root, model, inputs[\"matchup_rows\"], require_pwf=require_pwf,"
  ]
];
const FM_PATTERN = "PlayerWeekFantasy|player[-_ ]week[-_ ]fantasy|MatchupProjections|matchup[-_ ](projection|context)|ProjectedFinalScore|HybridExpected|LineupEfficiency|EfficiencyPercent|PregameWinProbability|RelativeScoringStrength|ScheduleOutlook|schedule[-_ ]outlook|SeasonStatistics|season[-_ ]statistics|WeeklyRecaps|weekly[-_ ]recaps|team[-_ ]week[-_ ]performance|DecisionWindows|decision[-_ ]windows|nfl[-_ ]player[-_ ]availability|team[-_ ]injury[-_ ]impact|PlayerInjuryHistory|projection_view|league_scoring_projection";
function assert(ok,msg){if(!ok)throw Error(msg)}
function levels(edges){const nodes=new Map();for(const [a,b] of edges){if(!nodes.has(a))nodes.set(a,new Set());if(!nodes.has(b))nodes.set(b,new Set());nodes.get(b).add(a)}const layers=[];while(nodes.size){const ready=[...nodes].filter(([,parents])=>!parents.size).map(([k])=>k).sort();assert(ready.length,"cycle in witnessed edge subset");layers.push(ready);for(const n of ready)nodes.delete(n);for(const p of nodes.values())for(const n of ready)p.delete(n)}return layers}
function compareEfficiency(stats,recaps){const rows=[];for(const t of stats.Teams){const index=new Map(t.GameLog.map(g=>[g.Week,g]));const w=recaps.Weeks.flatMap(w=>(w.TeamPerformance??[]).filter(e=>String(e.FantasyTeamID)===String(t.TeamID)&&Number.isFinite(index.get(w.Week)?.LineupEfficiencyActual)&&Number.isFinite(e.EfficiencyPercent)&&e.PotentialPoints>0).map(e=>({week:w.Week,stats:index.get(w.Week).LineupEfficiencyActual,recap:e.EfficiencyPercent,actual:e.ActualStarterPoints,potential:e.PotentialPoints})));const n=w.length,mean=x=>n?w.reduce((a,b)=>a+b[x],0)/n:null;rows.push({team:t.TeamID,scope:"common regular-season team-weeks with valid positive potential",weeks:w.map(e=>e.week),n,meanStats:mean("stats"),meanRecap:mean("recap"),ratioTotals:n?w.reduce((a,b)=>a+b.actual,0)/w.reduce((a,b)=>a+b.potential,0)*100:null,largestWeeklyDiff:n?Math.max(...w.map(x=>Math.abs(x.stats-x.recap))):null,statsOnlyWeeks:t.GameLog.filter(g=>!w.some(e=>e.week===g.Week)).map(g=>g.Week)})}return rows}
async function inspect(read,{league,years}){const files=new Map(),evidence=[];for(const [upstream,consumer,kind,path,anchor] of WITNESSES){if(!files.has(path))files.set(path,await read(path));const r=files.get(path);assert(r.sha&&r.content,"missing source: "+path);const lines=r.content.split("\n").map((text,i)=>({line:i+1,text:text.trim()})).filter(x=>x.text.includes(anchor.trim()));assert(lines.length,"unresolved witness: "+path+" "+anchor);evidence.push({upstream,consumer,kind,path,blob:r.sha,matches:lines})}const efficiency=[];for(const year of years){let a=await read("data-derived/season-statistics/"+league+"/"+year+".json"),b=await read("data-derived/weekly-recaps/"+league+"/"+year+".json");let s=JSON.parse(a.content),r=JSON.parse(b.content);efficiency.push({year,statsBlob:a.sha,recapBlob:b.sha,statsWeeks:s.Weeks.map(x=>x.Week),recapWeeks:r.Weeks.map(x=>x.Week),rows:compareEfficiency(s,r)})}return {witnesses:evidence,observedEdgeLevels:levels(evidence.map(x=>[x.upstream,x.consumer])),efficiency,limitations:["Witnessed source read sites, not an automatically complete dependency graph. Semantic labels reviewed by author; dynamic execution trace and exhaustive cross-language reference classification still required.","TWP optional PWF parity is not a production readiness requirement. App delivery is downstream. Source facts, imports, ordering and other products are not exhausted by this projection-specific subset."]}}
function classifyCandidate(path,line){if(path.startsWith("research/")||path.includes("/tests/")||path.includes(".spec.")||/\/test_/.test(path))return "research-or-test";if(path.startsWith("fantasy-management/analyses/"))return "historical-management-evidence";if(path.startsWith("fantasy-management/_ai/scripts/"))return "fm-executable-candidate";if(path.startsWith("fantasy-management/"))return "fm-doc-or-workflow-candidate";if(path.startsWith("src/app/"))return "app-candidate";if(path.startsWith(".github/workflows/"))return "orchestration-candidate";if(path.startsWith(".ai-context/"))return "canonical-doc-candidate";if(path.startsWith("tools/")||path.startsWith("public/requests/"))return "producer-or-adapter-candidate";return "unclassified"}
async function cli(){const {execFileSync}=require("node:child_process");const args=process.argv.slice(2),opt={};for(let i=0;i<args.length;i++){if(args[i]==="--references")opt.references=true;else if(["--ref","--league","--years"].includes(args[i]))opt[args[i].slice(2)]=args[++i];else throw Error("unknown argument "+args[i])}assert(/^[a-f0-9]{40}$/.test(opt.ref??""),"explicit commit --ref required");assert(/^[a-z0-9-]+$/.test(opt.league??""),"--league required");assert(/^\d{4}(,\d{4})*$/.test(opt.years??""),"--years required");function git(a){return execFileSync("git",a,{encoding:"utf8",maxBuffer:128*1024*1024})}const pin=git(["rev-parse","--verify",opt.ref+"^{commit}"]).trim(),read=path=>({sha:git(["rev-parse",pin+":"+path]).trim(),content:git(["show",pin+":"+path])});const report=await inspect(read,{league:opt.league,years:opt.years.split(",").map(Number)});report.ref=pin;if(opt.references){const paths=["tools","src/app","public/requests","fantasy-management","research",".github/workflows",".ai-context/manual"];let out;try{out=git(["grep","-I","-n","-E","-i",FM_PATTERN,pin,"--",...paths])}catch(e){if(e.status===1)out="";else throw e}report.referenceCandidates=out.trim().split("\n").filter(Boolean).map(s=>{let m=s.match(/^[^:]+:(.*?):(\d+):(.*)$/);return m?{path:m[1],line:Number(m[2]),category:classifyCandidate(m[1],m[3]),text:m[3]}:{category:"unparsed",text:s}});report.referenceCandidateCounts=report.referenceCandidates.reduce((a,x)=>(a[x.category]=(a[x.category]??0)+1,a),{});report.fmPythonFiles=git(["ls-tree","-r","--name-only",pin,"--","fantasy-management/_ai/scripts"]).trim().split("\n").filter(p=>p.endsWith(".py")&&!p.includes("/tests/"));}process.stdout.write(JSON.stringify(report,null,2)+"\n")}
module.exports={inspect,compareEfficiency,levels,WITNESSES,FM_PATTERN,classifyCandidate};
if(require.main===module) cli().catch(e=>{console.error(e);process.exitCode=1;});
