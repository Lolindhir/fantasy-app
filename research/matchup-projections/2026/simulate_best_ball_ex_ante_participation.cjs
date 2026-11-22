#!/usr/bin/env node
'use strict';
// CP3g research-only: before-kickoff availability Bernoulli x conditional PWF range.
// No public/data input is introduced into any productive consumer.
const assert = require('node:assert/strict');
const cp = require('node:child_process');
const path = require('node:path');
const {optimize, randomNormal} = require('./simulate_best_ball_ranges.cjs');
const {snapsByPlayer, playedFromSnap} = require('./audit_pwf_range_coverage.cjs');
const ROOT = path.resolve(__dirname, '../../..');
const FINAL = '5f9c6feb89441088d3aeb19765420f7563d71780';
const Z90 = 1.6448536269514722;
const SAMPLES = [
  [5,'2026-10-07T23:47:03Z','bf8ac8d6174bcac68a996769caf0c8237f39dae4'],
  [6,'2026-10-14T23:47:09Z','6318ee4447ac8cdc2cf5bd008560986af9630ace'],
  [7,'2026-10-21T23:37:06Z','c35a439c1ba1d430408cdb237456ca7410b7c4f8'],
  [8,'2026-10-28T22:52:44Z','2061fd518588e0a347b796142546923944d92142'],
  [9,'2026-11-04T23:53:02Z','245f0fb65404b9d95a0927d340cdbadbfa189ef3'],
  [10,'2026-11-11T23:51:28Z','3050e8a94822445feff222803441670e8bd7f479'],
];
// Explicit ILLUSTRATIVE priors, not fitted results or a claim of calibration.
// Effective prior sample size is eight per status. Unknown is separate from ACTIVE.
// The sequential walk-forward updates these only AFTER the completed prior week.
const PRIOR = Object.freeze({
  ACTIVE: .95, QUESTIONABLE: .70, OUT: .05, DOUBTFUL: .05,
  INJURY_RESERVE: .05, DAY_TO_DAY: .70, UNKNOWN: .85,
});
const STRENGTH = 8;
const POS = new Set(['QB','RB','WR','TE','K']);
function read(ref, file) {
  let txt;
  try { txt = cp.execFileSync('git', ['show', ref+':'+file],
    {cwd:ROOT, encoding:'utf8', maxBuffer:32*1024*1024, stdio:['ignore','pipe','pipe']}); }
  catch(e) { throw Error('Full Git history required for '+ref+':'+file+' ('+e.message+')'); }
  return JSON.parse(txt);
}
function distinct(rows,key) {
  const m = new Map();
  for (const x of rows) {
    const id=x[key];
    assert(typeof id==='string' && id && !m.has(id),'Missing/duplicate '+key+': '+id);
    m.set(id,x);
  }
  return m;
}
function statusOf(player,cut) {
  const a=player.ScoringAvailability||{};
  const status=a.ProviderStatus||'UNKNOWN';
  assert(Object.hasOwn(PRIOR,status),'Unsupported as-of status '+status);
  if(a.ProviderStatus) {
    assert(a.ObservedAtUtc && Number.isFinite(Date.parse(a.ObservedAtUtc)) &&
      Date.parse(a.ObservedAtUtc)<=cut,'Post-cutoff/missing status time');
  }
  return status;
}
function probability(status, history) {
  const h=history[status]||{n:0,played:0};
  assert(h.n>=0&&h.played>=0&&h.played<=h.n,'Invalid history');
  return (STRENGTH*PRIOR[status]+h.played)/(STRENGTH+h.n);
}
function uniform(seed) {
  let state=seed>>>0;
  return ()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;
    return (state+.5)/4294967296;};
}
function pct(scores,p) {
  const sorted=scores.slice().sort((a,b)=>a-b);
  return sorted[Math.floor(sorted.length*p)];
}
function mean(values) {return values.reduce((a,b)=>a+b,0)/values.length;}
function rnd(x) {return x===null?null:Math.round(x*10000)/10000;}
function summarize(rows,onlyAfterWarmup) {
  const a=rows.filter(x=>x.complete && (!onlyAfterWarmup||x.week>5));
  const metric=fn=>a.length?rnd(mean(a.map(fn))):null;
  const results={total:rows.filter(x=>!onlyAfterWarmup||x.week>5).length,complete:a.length};
  for(const [key,lower,upper] of [['raw','rawP10','rawP90'],['participation','participationP10','participationP90'],['projected','projectedP10','projectedP90'],['oracle','oracleP10','oracleP90']]){
    results[key]={bias:metric(r=>r[key]-r.target),mae:metric(r=>Math.abs(r[key]-r.target)),
      coverage80:lower&&key!=='projected'?metric(r=>+(r.target>=r[lower]&&r.target<=r[upper])):null};
  }
  return results;
}
function run(options={}) {
  const draws=options.draws??800,seed=options.seed??20261122;
  const first=options.first??5,last=options.last??10;
  assert(Number.isInteger(draws)&&draws>=10&&draws<=20000,'Invalid draw count');
  assert(Number.isInteger(seed)&&Number.isInteger(first)&&Number.isInteger(last)
    &&first>=5&&last<=10&&first<=last,'Invalid options');
  // Selecting a suffix replays earlier training weeks; predictions remain walk-forward.
  const history={},rows=[],byWeek=[];
  for(const [week,observed,sha] of SAMPLES.filter(s=>s[0]<=last)) {
    const cut=Date.parse(observed),w=String(week).padStart(2,'0');
    const dw=read(sha,'public/data/DecisionWindows.json');
    const pwf=read(sha,'public/data/PlayerWeekFantasy.json');
    const final=read(FINAL,'data-derived/player-week-fantasy/nfl-reise/2026/'+w+'.json');
    const snaps=read(FINAL,'data-source/nfl/snap-counts/2026/'+w+'.json');
    assert.equal(pwf.Season,2026);assert.equal(pwf.Week,week);
    assert.equal(dw.LineupWeek,week);assert.equal(String(dw.Season),'2026');
    assert.equal(final.Season,2026);assert.equal(final.Week,week);
    assert.equal(snaps.Season,2026);assert.equal(snaps.Week,week);
    assert.equal(final.Materialization?.ActualScoringEvidenceFinalized,true);
    assert(dw.DecisionWindows.length&&dw.DecisionWindows.every(d=>Number.isFinite(Date.parse(d.StartsAtUtc))));
    assert(cut<Math.min(...dw.DecisionWindows.map(d=>Date.parse(d.StartsAtUtc))),
      'Pregame cutoff after game start');
    const slots=dw.FantasyRelevance.SlotDefinitions.map(x=>x.SlotType);
    assert.equal(slots.length,13,'Unexpected starting slot count');
    const counts={};for(const s of slots)counts[s]=(counts[s]||0)+1;
    assert.deepEqual(counts,{QB:2,RB:2,WR:2,TE:2,FLEX:4,K:1});
    const projected=distinct(pwf.Records.filter(x=>x.PlayerID!==null&&x.PlayerID!==undefined)
      .map(x=>({...x,PlayerID:String(x.PlayerID)})),'PlayerID');
    const actual=distinct(final.Records,'CanonicalPlayerID');
    // The full NFL snap feed contains unrelated multi-position identity collisions.
    // Do not turn those into candidate non-participation or suppress them silently.
    // Only a relevant fantasy position (RB also accepts source HB) can label a player.
    const expectedPositions=new Map();
    for(const team of dw.FantasyRelevance.Teams)for(const p of team.Players) {
      if(!['starter','bench'].includes(p.Placement)||
         p.GameState!=='unlocked'||!p.GameID||!POS.has(p.Position))continue;
      const rec=projected.get(String(p.PlayerID));
      if(rec?.Projection?.Status!=='available'||rec.Projection.PredictionRange?.Level!==0.9)continue;
      const old=expectedPositions.get(rec.CanonicalPlayerID);
      assert(!old||old===p.Position,'Fantasy player position conflict '+rec.CanonicalPlayerID);
      expectedPositions.set(rec.CanonicalPlayerID,p.Position);
    }
    let conflictingSnapPositionRows=0;
    const relevantSnaps=[];
    for(const rec of snaps.Records) {
      const expected=expectedPositions.get(rec.CanonicalPlayerID);
      if(!expected)continue;
      if(rec.Position!==expected && !(expected==='RB'&&rec.Position==='HB')) {
        conflictingSnapPositionRows++;continue;
      }
      relevantSnaps.push({...rec,Position:expected});
    }
    const snapMap=snapsByPlayer({...snaps,Records:relevantSnaps});
    assert.equal(dw.FantasyRelevance.Teams.length,6);
    const updates={},stats={week,revision:sha,cutoff:observed,rosterPlayers:0,
      candidatePlayers:0,knownStatus:0,unknownStatus:0,byStatus:{},complete:0,incomplete:0,
      missingSnapEvidence:0,conflictingSnapPositionRows};
    const seenTeams=new Set(),seenPlayers=new Set();
    let teamOrdinal=0;
    for(const team of dw.FantasyRelevance.Teams) {
      const teamID=String(team.FantasyTeamID);
      teamOrdinal++;
      assert(!seenTeams.has(teamID),'Duplicate team');seenTeams.add(teamID);
      const pool=[];
      for(const p of team.Players) {
        stats.rosterPlayers++;
        const id=String(p.PlayerID);
        assert(!seenPlayers.has(id),'Duplicate/cross-team roster member '+id);
        seenPlayers.add(id);
        const status=statusOf(p,cut);
        if(status==='UNKNOWN')stats.unknownStatus++;else stats.knownStatus++;
        if(!['starter','bench'].includes(p.Placement)||
          p.GameState!=='unlocked'||!p.GameID)continue;
        const projRow=projected.get(id);
        const q=projRow?.Projection;
        if(!POS.has(p.Position)||q?.Status!=='available'||q.PredictionRange?.Level!==0.9)continue;
        assert(q.ParticipationCondition==='conditional-on-participation'&&
          q.AvailabilityAdjustmentApplied===false,'Unexpected conditional PWF model '+id);
        const nums=[q.Points,q.PredictionRange.Lower,q.PredictionRange.Upper];
        assert(nums.every(Number.isFinite)&&nums[2]>=nums[1],'Invalid PWF range '+id);
        const finalRow=actual.get(projRow.CanonicalPlayerID);
        assert(finalRow?.Actual?.State==='final'&&Number.isFinite(finalRow.Actual.Points),
          'Missing final actual for '+id);
        const snap=snapMap.get(projRow.CanonicalPlayerID);
        if(!snap)stats.missingSnapEvidence++;
        const played=playedFromSnap(snap);
        const h=updates[status]||(updates[status]={n:0,played:0});
        h.n++;h.played+=+played;
        const g=stats.byStatus[status]||(stats.byStatus[status]={n:0,played:0,pSum:0});
        g.n++;g.played+=+played;g.pSum+=probability(status,history);
        pool.push({id,pos:p.Position,mean:q.Points,sigma:(nums[2]-nums[1])/(2*Z90),
          actual:finalRow.Actual.Points,p:probability(status,history),played,draw:0});
        stats.candidatePlayers++;
      }
      const maxMean=optimize(slots,pool,'mean'),maxActual=optimize(slots,pool,'actual');
      const row={week,teamID,complete:maxMean.unfilled===0,
        target:maxActual.points,projected:maxMean.points,projectedP10:null,projectedP90:null,
        poolSize:pool.length,unfilledBefore:maxMean.unfilled};
      if(row.complete) {
        stats.complete++;
        const norm=randomNormal((seed+week*4099+teamOrdinal*13)>>>0);
        const u=uniform((seed+week*8191+teamOrdinal*37+1)>>>0);
        const raw=[],part=[],oracle=[],out=[];
        for(let i=0;i<draws;i++) {
          const active=[],knownPlayed=[];
          for(const p of pool) {
            p.draw=p.mean+p.sigma*norm();
            if(u()<p.p)active.push(p);
            if(p.played)knownPlayed.push(p);
          }
          raw.push(optimize(slots,pool,'draw').points);
          const res=optimize(slots,active,'draw');
          part.push(res.points);out.push(res.unfilled>0?1:0);
          oracle.push(optimize(slots,knownPlayed,'draw').points);
        }
        row.raw=rnd(mean(raw));row.participation=rnd(mean(part));
        row.oracle=rnd(mean(oracle));
        row.rawP10=rnd(pct(raw,.1));row.rawP90=rnd(pct(raw,.9));
        row.participationP10=rnd(pct(part,.1));row.participationP90=rnd(pct(part,.9));
        row.oracleP10=rnd(pct(oracle,.1));row.oracleP90=rnd(pct(oracle,.9));
        row.emptySlotDrawRate=rnd(mean(out));
        assert(row.participation<=row.raw+1e-5,'Participation must not raise BB under shared draws');
      } else {
        stats.incomplete++;
        row.raw=row.participation=row.oracle=null;
      }
      if(week>=first)rows.push(row);
    }
    // The current week's outcomes are never used for that week's p(play).
    for(const [status,next] of Object.entries(updates)) {
      const h=history[status]||(history[status]={n:0,played:0});
      h.n+=next.n;h.played+=next.played;
    }
    if(week>=first)byWeek.push({...stats,
      byStatus:Object.fromEntries(Object.entries(stats.byStatus).map(([s,x])=>[s,
        {count:x.n,playedProxy:x.played,meanPriorProbability:rnd(x.pSum/x.n)}]))});
  }
  const s={researchOnly:true,method:'conditional-PWF-independent-normal-with-walkforward-bernoulli-v0',
    season:2026,weeks:[first,last],draws,seed,finalOutcomeRef:FINAL,
    prior:{strength:STRENGTH,values:PRIOR},
    notes:['Week 5 is calibration warm-up for the primary W6-W10 comparison.',
      'Per-status beta prior is illustrative and uncalibrated; earlier snap proxies update later weeks only.',
      'Missing positive snap evidence is treated as nonparticipation proxy, not as injury diagnosis.',
      'As-of DecisionWindows and PWF are historical publication evidence; never productive consumer input.',
      'Target is ex-post optimal as-of roster points from later finalized PWF; NOT manager actual score or win chance.',
      'IR/Taxi and without-game roster entries are excluded from the candidate pool.',
      'Independent normal is a surrogate, no NFL-game correlation or coach-efficiency uncertainty.',
      'Insufficient 2026 W5-W10 sample for deployment or held-out calibration.'],
    byWeek,overall:summarize(rows,false),
    walkForward:summarize(rows,true)};
  if(options.rows)s.rows=rows;
  return s;
}
function selfTest(){
  assert(Math.abs(probability('ACTIVE',{})-.95)<1e-12);
  assert(Math.abs(probability('UNKNOWN',{UNKNOWN:{n:2,played:1}})-.78)<1e-12);
  assert.equal(statusOf({ScoringAvailability:{ProviderStatus:'OUT',ObservedAtUtc:'2026-10-01T00:00:00Z'}},Date.parse('2026-10-02T00:00:00Z')),'OUT');
  assert.throws(()=>statusOf({ScoringAvailability:{ProviderStatus:'OUT',ObservedAtUtc:'2026-11-01T00:00:00Z'}},Date.parse('2026-10-02T00:00:00Z')));
  const u=uniform(17);assert(u()>0 && u()<1);
  assert.equal(optimize(['QB','QB'],[{pos:'QB',draw:4}],'draw').unfilled,1);
  console.log('CP3g self-test OK');
}
function main() {
  const args=Object.fromEntries(process.argv.slice(2).map(s=>s.replace(/^--/,'').split('=')));
  if(Object.hasOwn(args,'self-test'))return selfTest();
  const from=+(args.from||5),to=+(args.to||10),draws=+(args.draws||800),seed=+(args.seed||20261122);
  console.log(JSON.stringify(run({first:from,last:to,draws,seed,rows:Object.hasOwn(args,'rows')}),null,2));
}
if(require.main===module)main();
module.exports={PRIOR,probability,uniform,statusOf,summarize,run,selfTest};