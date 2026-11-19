#!/usr/bin/env node
'use strict';
// CP3d research-only paired availability-oracle ablation. NEVER use oracle inputs in live forecasts.
// Reuses CP3b exact assignment and RNG, CP3c snap-evidence participation proxy.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {optimize, randomNormal} = require('./simulate_best_ball_ranges.cjs');
const {snapsByPlayer, playedFromSnap} = require('./audit_pwf_range_coverage.cjs');
const ROOT = path.resolve(__dirname, '../../..');
const Z90 = 1.6448536269514722;
const FLEX = {FLEX:['RB','WR','TE'],WRRB_FLEX:['WR','RB'],REC_FLEX:['WR','TE'],SUPER_FLEX:['QB','RB','WR','TE']};
const POS = new Set(['QB','RB','WR','TE','K']);
const load = relative => JSON.parse(fs.readFileSync(path.join(ROOT, relative), 'utf8'));
const mean = numbers => numbers.reduce((a,b)=>a+b,0)/numbers.length;
const round = x => Math.round(x*10000)/10000;
const percentile = (sorted,p) => sorted[Math.floor(sorted.length*p)];
function slots(league) {
  const list=league.RosterPositions.filter(x=>x!=='BN');
  for(const s of list)if(!POS.has(s)&&!FLEX[s])throw Error('Unsupported slot '+s);
  return list;
}
function index(rows,key){
  const m=new Map();
  for(const r of rows){
    if(typeof r[key]!=='string'||!r[key]||m.has(r[key]))throw Error('Invalid/duplicate '+key);
    m.set(r[key],r);
  }
  return m;
}
function checkFinite(value,context) {
  if(!Number.isFinite(value))throw Error('Non-finite '+context);
  return value;
}
function summary(rows) {
  const raw=rows.filter(r=>r.rawComplete);
  const pairs=rows.filter(r=>r.rawComplete && r.oracleComplete);
  const metric=(a,fn)=>a.length?round(mean(a.map(fn))):null;
  const diagnostics={
    total:rows.length,rawComplete:raw.length,oracleComplete:rows.filter(r=>r.oracleComplete).length,
    paired: pairs.length,oracleIncomplete:rows.filter(r=>!r.oracleComplete).length,
    oracleUnfilledByWeek:rows.filter(r=>r.rawComplete&&!r.oracleComplete)
      .map(r=>({season:r.season,week:r.week,rosterID:r.rosterID,unfilled:r.oracleUnfilled})),
    totalCandidateCount:rows.reduce((s,r)=>s+r.candidateCount,0),
    totalOracleCandidateCount:rows.reduce((s,r)=>s+r.oracleCandidateCount,0),
    totalMissingSnapEvidence:rows.reduce((s,r)=>s+r.missingSnapEvidence,0),
    positionDisagreements:rows.reduce((s,r)=>s+r.positionDisagreements,0),
    targetReproducedRaw:rows.filter(r=>r.rawActualMatchesTWP).length,
    targetReproducedOracle:rows.filter(r=>r.oracleActualMatchesTWP).length,
    twpUnfilled:rows.filter(r=>r.twpUnfilled>0).length,
    twpOptimalMissingProjection:rows.filter(r=>r.twpOptimalMissingProjection).length,
  };
  const rawAll={
    mae:metric(raw,r=>Math.abs(r.rawSim-r.target)),
    bias:metric(raw,r=>r.rawSim-r.target),
    meanSimUpliftPct:metric(raw,r=>100*(r.rawSim/r.rawProjected-1)),
    coverage80:metric(raw,r=>+(r.target>=r.rawP10 && r.target<=r.rawP90)),
  };
  const paired={
    rawMAE:metric(pairs,r=>Math.abs(r.rawSim-r.target)),
    oracleMAE:metric(pairs,r=>Math.abs(r.oracleSim-r.target)),
    rawBias:metric(pairs,r=>r.rawSim-r.target),
    oracleBias:metric(pairs,r=>r.oracleSim-r.target),
    rawCoverage80:metric(pairs,r=>+(r.target>=r.rawP10&&r.target<=r.rawP90)),
    oracleCoverage80:metric(pairs,r=>+(r.target>=r.oracleP10&&r.target<=r.oracleP90)),
    rawUpliftPct:metric(pairs,r=>100*(r.rawSim/r.rawProjected-1)),
    oracleUpliftPct:metric(pairs,r=>100*(r.oracleSim/r.oracleProjected-1)),
    oracleMinusRawSimPoints:metric(pairs,r=>r.oracleSim-r.rawSim),
    rawProjectedMinusOracleProjected:metric(pairs,r=>r.rawProjected-r.oracleProjected),
    rawActualMinusOracleActual:metric(pairs,r=>r.rawCandidateActual-r.oracleCandidateActual),
    meanTwpPotential:metric(pairs,r=>r.target),
    meanObservedFullPoolVsTWP:metric(pairs,r=>r.rawCandidateActual-r.target),
    meanObservedOraclePoolVsTWP:metric(pairs,r=>r.oracleCandidateActual-r.target),
  };
  // The two retrospective pools can have missing projections. This subset is the
  // strict like-for-like TWP benchmark; counts are disclosed rather than silently filtered.
  const aligned=pairs.filter(r=>r.rawActualMatchesTWP && r.oracleActualMatchesTWP && !r.twpUnfilled);
  const alignedMetrics={n:aligned.length,rawMAE:metric(aligned,r=>Math.abs(r.rawSim-r.target)),
    oracleMAE:metric(aligned,r=>Math.abs(r.oracleSim-r.target)),
    rawBias:metric(aligned,r=>r.rawSim-r.target),
    oracleBias:metric(aligned,r=>r.oracleSim-r.target)};
  return {diagnostics,rawAll,paired,aligned:alignedMetrics};
}
function runYear(season,weeks,draws,seed,block){
  const base='data-source/leagues/nfl-reise/seasons/'+season;
  const league=load(base+'/league.json');
  assert.equal(league.Season,season);
  const formation=slots(league),rows=[];
  for(let offset=0;offset<weeks.length;offset+=block){
    // Intentionally matches CP3b reset and candidate draw order (common random numbers).
    const normal=randomNormal(seed);
    for(const week of weeks.slice(offset,offset+block)){
      const w=String(week).padStart(2,'0');
      const [pwf,weekly,snaps,matchups,twp]=[
        load('data-derived/player-week-fantasy/nfl-reise/'+season+'/'+w+'.json'),
        load('data-source/nfl/weekly-rosters/'+season+'/'+w+'.json'),
        load('data-source/nfl/snap-counts/'+season+'/'+w+'.json'),
        load(base+'/matchups/week-'+week+'.json'),
        load('data-derived/team-week-performance/nfl-reise/'+season+'/'+w+'.json'),
      ];
      for(const doc of [pwf,weekly,snaps,twp]) {
        assert.equal(doc.Season,season);
        assert.equal(doc.Week,week);
      }
      assert.equal(pwf.Materialization?.ActualScoringEvidenceFinalized,true);
      assert(twp.FinalityEvidence&&Array.isArray(matchups)&&twp.Teams.length===matchups.length);
      const projections=index(pwf.Records,'CanonicalPlayerID');
      const positions=index(weekly.Records,'CanonicalPlayerID');
      const snapIndex=snapsByPlayer(snaps);
      const actualTeams=index(twp.Teams,'CanonicalLeagueRosterID');
      for(const team of matchups){
        const rosterID=team.CanonicalLeagueRosterID;
        const actualTeam=actualTeams.get(rosterID);
        if(!actualTeam)throw Error('Missing TWP '+rosterID);
        const target=checkFinite(actualTeam.PotentialPoints,'TWP potential');
        const players=[], seen=new Set();
        let missingSnapEvidence=0, positionDisagreements=0, excludedProjections=0;
        for(const ref of team.Players){
          const id=ref.CanonicalPlayerID;
          if(!id||seen.has(id))throw Error('Duplicate/empty roster player '+id);
          seen.add(id);
          const pos=positions.get(id)?.Position, projection=projections.get(id)?.Projection;
          if(!POS.has(pos)||projection?.Status!=='available'||projection?.PredictionRange?.Level!==0.9){
            excludedProjections++;continue;
          }
          if(projection.ParticipationCondition!=='conditional-on-participation'||
             projection.AvailabilityAdjustmentApplied!==false)throw Error('Unexpected participation model '+id);
          const lower=checkFinite(projection.PredictionRange.Lower,'range.lower');
          const upper=checkFinite(projection.PredictionRange.Upper,'range.upper');
          const mu=checkFinite(projection.Points,'projection.points');
          if(upper<lower)throw Error('Reversed PWF interval '+id);
          const pwfActual=projections.get(id)?.Actual;
          if(pwfActual?.State!=='final')throw Error('Missing finalized PWF actual for '+id);
          const realized=checkFinite(pwfActual.Points,'PWF actual');
          const snap=snapIndex.get(id);
          if(!snap)missingSnapEvidence++;
          if(snap && snap.position!==pos)positionDisagreements++;
          players.push({id,pos,mean:mu,draw:0,actual:realized,
            sigma:(upper-lower)/(2*Z90),oraclePlayed:playedFromSnap(snap)});
        }
        const oracle=players.filter(x=>x.oraclePlayed);
        const rawProjected=optimize(formation,players,'mean');
        const oracleProjected=optimize(formation,oracle,'mean');
        const rawCandidateActual=optimize(formation,players,'actual');
        const oracleCandidateActual=optimize(formation,oracle,'actual');
        if (oracleProjected.points > rawProjected.points + 1e-8) {
          throw Error('Oracle projected score exceeds full-pool optimum '+season+' W'+week+'/'+rosterID);
        }
        const rawComplete=rawProjected.unfilled===0;
        const oracleComplete=oracleProjected.unfilled===0;
        let rawSim=null,oracleSim=null,rawP10=null,rawP90=null,oracleP10=null,oracleP90=null;
        if(rawComplete){
          const rawScores=[],oracleScores=[];
          for(let i=0;i<draws;i++){
            for(const p of players)p.draw=p.mean+p.sigma*normal();
            const rawScore=optimize(formation,players,'draw').points;
            rawScores.push(rawScore);
            if(oracleComplete){
              const oracleScore=optimize(formation,oracle,'draw').points;
              if(oracleScore > rawScore + 1e-8) throw Error('Oracle draw exceeds raw draw');
              oracleScores.push(oracleScore);
            }
          }
          rawScores.sort((a,b)=>a-b);
          rawSim=mean(rawScores);
          rawP10=percentile(rawScores,0.1);rawP90=percentile(rawScores,0.9);
          if(oracleComplete){
            oracleScores.sort((a,b)=>a-b);
            oracleSim=mean(oracleScores);
            oracleP10=percentile(oracleScores,0.1);oracleP90=percentile(oracleScores,0.9);
          }
        }
        const optimal=actualTeam.OptimalLineup;
        if(!Array.isArray(optimal))throw Error('Missing TWP optimal lineup '+rosterID);
        rows.push({season,week,rosterID,draws,target,rawComplete,oracleComplete,
          rawUnfilled:rawProjected.unfilled,oracleUnfilled:oracleProjected.unfilled,
          twpUnfilled:actualTeam.UnfilledSlotIDs?.length ?? 0,
          twpOptimalMissingProjection:optimal.some(x=>!players.some(p=>p.id===x.CanonicalPlayerID)),
          candidateCount:players.length,oracleCandidateCount:oracle.length,
          missingSnapEvidence,positionDisagreements,excludedProjections,
          rawProjected:rawProjected.points,oracleProjected:oracleProjected.points,
          rawSim,oracleSim,rawP10,rawP90,oracleP10,oracleP90,
          rawCandidateActual:rawCandidateActual.points,oracleCandidateActual:oracleCandidateActual.points,
          rawActualMatchesTWP:rawCandidateActual.unfilled===0&&Math.abs(rawCandidateActual.points-target)<=0.05,
          oracleActualMatchesTWP:oracleCandidateActual.unfilled===0&&Math.abs(oracleCandidateActual.points-target)<=0.05});
      }
    }
  }
  return {formation,rows,summary:summary(rows)};
}
function selfTest(){
  assert.equal(playedFromSnap({position:'K',offense:0,special:2}),true);
  assert.equal(playedFromSnap({position:'WR',offense:0,special:2}),false);
  assert.equal(optimize(['QB','QB'],[{pos:'QB',mean:10}],'mean').unfilled,1);
  const fake={season:2026,week:5,rosterID:'a',target:12,rawComplete:true,oracleComplete:true,
    candidateCount:2,oracleCandidateCount:1,missingSnapEvidence:0,positionDisagreements:0,
    twpUnfilled:0,twpOptimalMissingProjection:false,rawSim:13,oracleSim:11,
    rawProjected:10,oracleProjected:10,rawP10:9,rawP90:15,oracleP10:9,oracleP90:13,
    rawCandidateActual:12,oracleCandidateActual:12,rawActualMatchesTWP:true,oracleActualMatchesTWP:true};
  assert.equal(summary([fake]).paired.rawMAE,1);
  assert.equal(summary([fake]).paired.oracleMinusRawSimPoints,-2);
  console.log('CP3d self-test OK');
}
function main(){
  const args=Object.fromEntries(process.argv.slice(2).map(x=>{
    const [k,v]=x.replace(/^--/,'').split('=');return[k,v||true];
  }));
  if(args['self-test'])return selfTest();
  const seasons=String(args.seasons||'2024,2025,2026').split(',').map(Number);
  const range=/^(\d+)-(\d+)$/.exec(String(args.weeks||'5-10'));
  if(!range)throw Error('Use --weeks=5-10');
  const weeks=Array.from({length:Number(range[2])-Number(range[1])+1},(_,i)=>Number(range[1])+i);
  const draws=Number(args.draws||1200),seed=Number(args.seed||20261119),block=Number(args.block||3);
  if(!seasons.length||seasons.some(x=>!Number.isInteger(x)||x<2000)||
     weeks.length<1||weeks.length>18||weeks.some(x=>x<1||x>18)||
     !Number.isInteger(draws)||draws<10||draws>100000||
     !Number.isInteger(seed)||!Number.isInteger(block)||block<1)throw Error('Invalid CLI args');
  const bySeason={},all=[];
  for(const season of seasons){
    const n=season===2024&&args['draws-2024']?Number(args['draws-2024']):draws;
    const result=runYear(season,weeks,n,seed,block);
    bySeason[season]={formation:result.formation,draws:n,summary:result.summary};
    all.push(...result.rows);
  }
  const report={
    researchOnly:true,method:'cp3d-snap-oracle-availability-ablation-v1',
    caveat:'Oracle participation uses realized snaps. Not available pregame; never promote as forecast. Archived full roster includes IR/Taxi.',
    seasons,weeks,seed,block,bySeason,aggregate:summary(all),
  };
  if(args.rows)report.rows=all;
  console.log(JSON.stringify(report,null,2));
}
if(require.main===module)main();
module.exports={summary,runYear,slots};
