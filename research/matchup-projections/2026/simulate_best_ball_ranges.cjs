#!/usr/bin/env node
'use strict';
// CP3b, research-only. Read-only historical ex-post Best Ball from PWF PI1 ranges.
// This is NOT a Tuesday/as-of roster replay or a manager-score/win-prob model.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ROOT = path.resolve(__dirname, '../../..');
const Z90 = 1.6448536269514722;
const FLEX = {FLEX:['RB','WR','TE'], WRRB_FLEX:['WR','RB'], REC_FLEX:['WR','TE'], SUPER_FLEX:['QB','RB','WR','TE']};
const POS = new Set(['QB','RB','WR','TE','K']);
function load(file) { return JSON.parse(fs.readFileSync(path.join(ROOT, file), 'utf8')); }
function eligible(pos, slot) { return (FLEX[slot] || [slot]).includes(pos); }
function slots(league) {
  const result = league.RosterPositions.filter(x => x !== 'BN');
  for (const x of result) if (!POS.has(x) && !FLEX[x]) throw new Error('Unsupported slot ' + x);
  return result;
}
function index(rows, key) {
  const m = new Map();
  for (const r of rows) {
    const k = r[key];
    if (typeof k !== 'string' || !k || m.has(k)) throw new Error('Duplicate/empty ' + key);
    m.set(k,r);
  }
  return m;
}
// Global rectangular Hungarian matching with one zero-value empty candidate per slot.
// Same eligibility and virtual-empty convention as weekly_lineup_optimizer.py.
function optimize(slotTypes, players, prop) {
  const n=slotTypes.length, m=players.length+n;
  const penalty=players.reduce((s,p)=>s+Math.abs(p[prop]),0)+1000000;
  const costs=slotTypes.map(slot=>players.map(p=>eligible(p.pos,slot)?-p[prop]:penalty).concat(Array(n).fill(0)));
  const u=Array(n+1).fill(0),v=Array(m+1).fill(0),match=Array(m+1).fill(0),way=Array(m+1).fill(0);
  for(let i=1;i<=n;i++){
    match[0]=i;
    const best=Array(m+1).fill(Infinity),used=Array(m+1).fill(false);
    let j0=0;
    do{
      used[j0]=true;
      const i0=match[j0];
      let delta=Infinity,j1=0;
      for(let j=1;j<=m;j++){
        if(used[j])continue;
        const candidate=costs[i0-1][j-1]-u[i0]-v[j];
        if(candidate<best[j]){best[j]=candidate;way[j]=j0;}
        if(best[j]<delta){delta=best[j];j1=j;}
      }
      for(let j=0;j<=m;j++){
        if(used[j]){u[match[j]]+=delta;v[j]-=delta;}
        else best[j]-=delta;
      }
      j0=j1;
    }while(match[j0]!==0);
    do{const j1=way[j0];match[j0]=match[j1];j0=j1;}while(j0!==0);
  }
  let points=0,unfilled=0;
  for(let j=1;j<=m;j++)if(match[j]){
    if(j>players.length)unfilled++;
    else{
      const p=players[j-1];
      assert(eligible(p.pos,slotTypes[match[j]-1]));
      points+=p[prop];
    }
  }
  return {points,unfilled};
}
function randomNormal(seed) {
  let state=seed>>>0;
  function uniform(){state=(Math.imul(state,1664525)+1013904223)>>>0;return(state+0.5)/4294967296;}
  return ()=>Math.sqrt(-2*Math.log(uniform()))*Math.cos(2*Math.PI*uniform());
}
const avg=rows=>rows.reduce((a,b)=>a+b,0)/rows.length;
function summary(rows) {
  const ok=rows.filter(r=>r.status==='ok');
  if(!ok.length)return {total:rows.length,valid:0};
  const metric=f=>avg(ok.map(f));
  return {total:rows.length,valid:ok.length,
    simulatedUpliftPct:100*(metric(r=>r.sim/r.projected)-1),
    realizedUpliftPct:100*(metric(r=>r.actual/r.projected)-1),
    simulatedBias:metric(r=>r.sim-r.actual),
    projectedBias:metric(r=>r.projected-r.actual),
    simulatedMAE:metric(r=>Math.abs(r.sim-r.actual)),
    projectedMAE:metric(r=>Math.abs(r.projected-r.actual)),
    interval80Coverage:metric(r=>+(r.actual>=r.q10&&r.actual<=r.q90)),
    optimalProjectionCovered:metric(r=>+r.optimalProjectionCovered),
    skips:rows.filter(r=>r.status!=='ok')};
}
function runYear(season,weeks,draws,seed,blockSize) {
  const base='data-source/leagues/nfl-reise/seasons/'+season;
  const league=load(base+'/league.json');
  assert.equal(league.Season,season);
  const formation=slots(league),rows=[];
  for(let offset=0;offset<weeks.length;offset+=blockSize){
    const normal=randomNormal(seed);
    for(const week of weeks.slice(offset,offset+blockSize)){
      const w=String(week).padStart(2,'0');
      const pwf=load('data-derived/player-week-fantasy/nfl-reise/'+season+'/'+w+'.json');
      const weeklyRoster=load('data-source/nfl/weekly-rosters/'+season+'/'+w+'.json');
      const matchups=load(base+'/matchups/week-'+week+'.json');
      const twp=load('data-derived/team-week-performance/nfl-reise/'+season+'/'+w+'.json');
      for(const doc of [pwf,weeklyRoster,twp]){assert.equal(doc.Season,season);assert.equal(doc.Week,week);}
      assert(twp.FinalityEvidence && twp.Teams.length===matchups.length);
      const pmap=index(pwf.Records,'CanonicalPlayerID');
      const pos=index(weeklyRoster.Records,'CanonicalPlayerID');
      const actuals=index(twp.Teams,'CanonicalLeagueRosterID');
      for(const team of matchups){
        const rosterID=team.CanonicalLeagueRosterID;
        const actual=actuals.get(rosterID);
        if(!actual)throw new Error('Missing TWP: '+rosterID);
        const candidates=[];
        let missingPositions=0,unavailable=0;
        const seen=new Set();
        for(const ref of team.Players){
          const id=ref.CanonicalPlayerID;
          if(!id||seen.has(id))throw new Error('Duplicate roster player '+id);
          seen.add(id);
          const position=pos.get(id)?.Position,projection=pmap.get(id)?.Projection;
          if(!position)missingPositions++;
          if(!POS.has(position)||projection?.Status!=='available'){unavailable++;continue;}
          const r=projection.PredictionRange;
          if(r?.Level!==0.9){unavailable++;continue;}
          const numbers=[projection.Points,r.Lower,r.Upper];
          if(!numbers.every(Number.isFinite)||r.Upper<r.Lower)throw new Error('Invalid PI1 interval '+id);
          candidates.push({pos:position,mean:projection.Points,sigma:(r.Upper-r.Lower)/(2*Z90),draw:0});
        }
        const projected=optimize(formation,candidates,'mean');
        if(projected.unfilled){
          rows.push({season,week,rosterID,status:'incomplete',unfilled:projected.unfilled,missingPositions,unavailable});
          continue;
        }
        const scores=[];
        for(let i=0;i<draws;i++){
          for(const p of candidates)p.draw=p.mean+p.sigma*normal();
          scores.push(optimize(formation,candidates,'draw').points);
        }
        scores.sort((a,b)=>a-b);
        rows.push({season,week,rosterID,status:'ok',
          projected:projected.points,sim:avg(scores),actual:actual.PotentialPoints,
          q10:scores[Math.floor(scores.length*.1)],q90:scores[Math.floor(scores.length*.9)],
          candidateCount:candidates.length,missingPositions,unavailable,
          optimalProjectionCovered:actual.OptimalLineup.every(p=>pmap.get(p.CanonicalPlayerID)?.Projection?.Status==='available')});
      }
    }
  }
  return {formation,rows,summary:summary(rows)};
}
function selfTest(){
  assert.deepEqual(optimize(['QB','FLEX'],[{pos:'QB',mean:10},{pos:'RB',mean:12}], 'mean'),{points:22,unfilled:0});
  assert.deepEqual(optimize(['QB','QB'],[{pos:'QB',mean:10},{pos:'QB',mean:-2}], 'mean'),{points:10,unfilled:1});
  assert.deepEqual(optimize(['REC_FLEX','WRRB_FLEX'],[{pos:'TE',mean:19},{pos:'RB',mean:20}], 'mean'),{points:39,unfilled:0});
  console.log('CP3b self-test OK');
}
function main(){
  const args=Object.fromEntries(process.argv.slice(2).map(x=>{const a=x.replace(/^--/,'').split('=');return[a[0],a[1]||true];}));
  if(args['self-test'])return selfTest();
  const seasons=String(args.seasons||'2024,2025,2026').split(',').map(Number);
  const range=/^(\d+)-(\d+)$/.exec(String(args.weeks||'5-10'));
  if(!range)throw new Error('Use --weeks=5-10');
  const weeks=Array.from({length:+range[2]- +range[1]+1},(_,i)=>+range[1]+i);
  const draws=+(args.draws||1200), seed=+(args.seed||20261119),block=+(args.block||3);
  if(!Number.isInteger(draws)||draws<10||draws>100000||!Number.isInteger(seed)||!Number.isInteger(block)||block<1)throw new Error('Invalid draw options');
  const bySeason={},all=[];
  for(const season of seasons){
    const n=season===2024&&args['draws-2024']?+args['draws-2024']:draws;
    const result=runYear(season,weeks,n,seed,block);
    bySeason[season]={formation:result.formation,draws:n,summary:result.summary};
    all.push(...result.rows);
  }
  const report={researchOnly:true,method:'independent-normal-PI1-90%-expost-bestball-v0',seed,weeks,
    caveat:'Historical full roster including IR/Taxi; conditional participation; no actual Tuesday locks, no correlation model',
    bySeason,aggregate:summary(all)};
  if(args.rows)report.rows=all;
  console.log(JSON.stringify(report,null,2));
}
if(require.main===module)main();
module.exports={optimize,eligible,randomNormal,summary};
