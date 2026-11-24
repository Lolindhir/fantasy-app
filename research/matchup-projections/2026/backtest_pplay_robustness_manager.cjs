#!/usr/bin/env node
"use strict";
// CP3k: retrospective full-roster research only. No writer or production switch.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const cp = require("./backtest_product_pplay_best_ball.cjs");
const {optimize, randomNormal} = require("./simulate_best_ball_ranges.cjs");
const {slots} = require("./ablate_best_ball_oracle_availability.cjs");
const ARMS = ["raw","priorStatus","laggedHistory"];
const SEEDS = [20261123,17,991], DISTS = ["normal","splitCentered"];
const POS = ["QB","RB","WR","TE","K"], Z = 1.6448536269514722;
const mean = a => a.length ? a.reduce((x,y)=>x+y,0)/a.length : null;
function index(a,k) {
  const m = new Map(a.map(x=>[x[k],x]));
  assert.ok(m.size===a.length && a.every(x=>typeof x[k]==="string"&&x[k]));
  return m;
}
function seed(s,w,id) {
  let x=(s^Math.imul(w,2246822519))>>>0;
  for(const ch of id)x=Math.imul(x^ch.charCodeAt(0),16777619)>>>0;
  return x;
}
function uniform(s) {
  let st=s>>>0;
  return()=>{st=(Math.imul(st,1664525)+1013904223)>>>0;return(st+.5)/4294967296};
}
// Exact for fixed single-position slots + unrestricted RB/WR/TE FLEX only.
// Positive scores fill dedicated slots first; virtual zero slots remain allowed.
function best(c,counts) {
  let total=0,left=[];
  for(const p of POS){
    const a=c.filter(x=>x.pos===p&&x.draw>0).map(x=>x.draw).sort((a,b)=>b-a);
    total+=a.slice(0,counts[p]).reduce((s,x)=>s+x,0);
    if(["RB","WR","TE"].includes(p))left.push(...a.slice(counts[p]));
  }
  return total+left.sort((a,b)=>b-a).slice(0,counts.FLEX).reduce((s,x)=>s+x,0);
}
function runWeek({year,week,availability,league,pwf,roster,matchups,twp,prior,model,draws=1200}){
  assert.ok(twp.Season===year&&twp.Week===week&&twp.FinalityEvidence);
  assert.ok(pwf.Season===year&&pwf.Week===week&&pwf.Materialization.ActualScoringEvidenceFinalized);
  assert.ok(roster.Season===year&&roster.Week===week&&matchups.length===6&&league.Season===year);
  assert.ok(prior.length===week-1&&prior.every((t,i)=>t.Season===year&&t.Week===i+1&&t.FinalityEvidence));
  const formation=slots(league);
  const counts=Object.fromEntries([...POS,"FLEX"].map(p=>[p,formation.filter(x=>x===p).length]));
  assert.equal(Object.values(counts).reduce((a,b)=>a+b,0),formation.length,"unsupported formation");
  const pp=index(pwf.Records,"CanonicalPlayerID"),pos=index(roster.Records,"CanonicalPlayerID"),targets=index(twp.Teams,"CanonicalLeagueRosterID");
  const rows=[],skips=[];let equivalence=0;
  for(const team of matchups){
    const id=team.CanonicalLeagueRosterID,target=targets.get(id),c=[],missing=[],seen=new Set();
    const h=prior.map(t=>t.Teams.find(x=>x.CanonicalLeagueRosterID===id))
      .filter(t=>t&&Number.isFinite(t.EfficiencyPercent)&&t.PotentialPoints>0).map(t=>t.EfficiencyPercent/100);
    for(const pl of team.Players){
      const pid=pl.CanonicalPlayerID;assert.ok(typeof pid==="string"&&pid&&!seen.has(pid));seen.add(pid);
      const p=pp.get(pid),position=pos.get(pid)?.Position;
      if(!POS.includes(position)||p?.Projection?.Status!=="available")continue;
      const q=p.Projection;assert.ok(q.ParticipationCondition==="conditional-on-participation"&&!q.AvailabilityAdjustmentApplied&&q.PredictionRange.Level===.9&&p.Actual.State==="final");
      const pr=cp.participantProbabilities(availability,week,pid,model.trained,model.selected);
      if(!pr){missing.push(pid);continue}
      const lo=q.PredictionRange.Lower,hi=q.PredictionRange.Upper,m=q.Points;
      assert.ok([lo,hi,m,p.Actual.Points].every(Number.isFinite)&&hi>=lo);
      c.push({pos:position,mean:m,lo,hi,sigma:(hi-lo)/(2*Z),actual:p.Actual.Points,...pr,draw:m});
    }
    const projected=optimize(formation,c,"mean"),realized=optimize(formation,c,"actual");
    assert.ok([target.PotentialPoints,target.ActualStarterPoints,target.OfficialMatchupPoints].every(Number.isFinite));
    const aligned=realized.unfilled===0&&Math.abs(realized.points-target.PotentialPoints)<=.05;
    if(missing.length||projected.unfilled||!aligned||h.length<4){
      skips.push({year,week,id,missing,unfilled:projected.unfilled,aligned,priorWeeks:h.length});continue;
    }
    assert.ok(Math.abs(best(c,counts)-projected.points)<1e-7);equivalence++;
    const efficiency=mean(h),r={year,week,id,match:team.CanonicalLeagueMatchupID,target:target.PotentialPoints,actual:target.ActualStarterPoints,official:target.OfficialMatchupPoints,efficiency,rawProjected:projected.points,results:{}};
    for(const distribution of DISTS)for(const s of SEEDS){
      const z=randomNormal(seed(s,week,id)),u=uniform(seed(s^0x9e3779b9,week,id)),scores=Object.fromEntries(ARMS.map(a=>[a,[]]));
      for(let d=0;d<draws;d++){
        for(const p of c){
          const n=z(),left=Math.max(0,p.mean-p.lo)/Z,right=Math.max(0,p.hi-p.mean)/Z;
          // Mean-centered split-normal sensitivity, not a fitted PI1 distribution.
          p.draw=p.mean+(distribution==="normal"?p.sigma*n:(n<0?left:right)*n-(right-left)/Math.sqrt(2*Math.PI));p.u=u();
        }
        for(const a of ARMS){
          const pool=a==="raw"?c:c.filter(p=>p.u<p[a]);const v=best(pool,counts);
          if(d===0){assert.ok(Math.abs(v-optimize(formation,pool,"draw").points)<1e-7,"fast optimizer mismatch");equivalence++}
          scores[a].push(v);
        }
      }
      r.results[distribution+":"+s]=scores;
    }
    rows.push(r);
  }
  return {rows,skips,equivalence};
}
function summarize(rows,key,arm){
  const e=rows.map(r=>{
    const sc=r.results[key][arm],m=mean(sc),sort=[...sc].sort((a,b)=>a-b);
    return {bb:m-r.target,manager:m*r.efficiency-r.actual,cover:r.target>=sort[Math.floor((sc.length-1)*.1)]&&r.target<=sort[Math.floor((sc.length-1)*.9)]};
  });
  const groups=new Map();
  for(const r of rows){const k=r.year+":"+r.week+":"+r.match;const g=groups.get(k)||[];g.push(r);groups.set(k,g)}
  let brier=[],correct=[];
  for(const g of groups.values()){
    assert.ok(g.length<=2);
    if(g.length!==2)continue;
    const [a,b]=g,sa=a.results[key][arm],sb=b.results[key][arm];let p=0;
    assert.equal(sa.length,sb.length);
    for(let d=0;d<sa.length;d++){
      const x=sa[d]*a.efficiency,y=sb[d]*b.efficiency;p+=x>y?1:x===y?.5:0;
    }
    p/=sa.length;const y=a.official>b.official?1:a.official===b.official?.5:0;
    brier.push((p-y)**2);correct.push(Number((p>.5)===(y>.5)));
  }
  return {n:rows.length,bbMAE:mean(e.map(x=>Math.abs(x.bb))),bbBias:mean(e.map(x=>x.bb)),coverage:mean(e.map(x=>+x.cover)),managerMAE:mean(e.map(x=>Math.abs(x.manager))),managerBias:mean(e.map(x=>x.manager)),matches:brier.length,brier:mean(brier),accuracy:mean(correct)};
}
function report(rows){
  return {deterministicManagerMAE:mean(rows.map(r=>Math.abs(r.rawProjected*r.efficiency-r.actual))),
    stats:Object.fromEntries(DISTS.flatMap(d=>SEEDS.map(s=>{const k=d+":"+s;return[k,Object.fromEntries(ARMS.map(a=>[a,summarize(rows,k,a)]))]})))};
}
function main(){
  const root=path.resolve(__dirname,"../../.."),load=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
  if(process.argv.includes("--self-test")){
    cp.selfTest();
    const c=[{pos:"RB",draw:4},{pos:"RB",draw:3},{pos:"WR",draw:7},{pos:"TE",draw:-2}];
    assert.equal(best(c,{QB:0,RB:1,WR:1,TE:0,K:0,FLEX:1}),14);
    console.log("CP3k self-test OK");return;
  }
  const docs=new Map();for(let y=2016;y<=2024;y++)docs.set(y,load("data-derived/nfl-player-availability/"+y+".json"));
  const model=cp.fitFrozenModel(docs),all=[],skips=[];let equivalence=0;
  for(const year of [2025,2026]){
    const availability=cp.availabilityWeeks(load("data-derived/nfl-player-availability/"+year+".json"));
    const league=load("data-source/leagues/nfl-reise/seasons/"+year+"/league.json"),prior=[];
    for(let week=1;week<=10;week++){
      const w=String(week).padStart(2,"0"),twp=load("data-derived/team-week-performance/nfl-reise/"+year+"/"+w+".json");
      if(week>=5){
        const r=runWeek({year,week,availability,league,twp,prior,model,
          pwf:load("data-derived/player-week-fantasy/nfl-reise/"+year+"/"+w+".json"),
          roster:load("data-source/nfl/weekly-rosters/"+year+"/"+w+".json"),
          matchups:load("data-source/leagues/nfl-reise/seasons/"+year+"/matchups/week-"+week+".json")});
        all.push(...r.rows);skips.push(...r.skips);equivalence+=r.equivalence;
      }
      prior.push(twp);
    }
  }
  console.log(JSON.stringify({researchOnly:true,draws:1200,seeds:SEEDS,distributions:DISTS,equivalence,skips,bySeason:Object.fromEntries([2025,2026].map(y=>[y,report(all.filter(r=>r.year===y))])),aggregate:report(all)},null,2));
}
if(require.main===module)main();
module.exports={runWeek,report,summarize,best};
