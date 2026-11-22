#!/usr/bin/env node
'use strict';
// CP3f research-only. Historical ESPN status comes from pregame Git commits.
// nfl-player-availability Played and league rosters are RETROSPECTIVE targets/populations.
const assert=require('node:assert/strict');
const cp=require('node:child_process');
const path=require('node:path');
const ROOT=path.resolve(__dirname,'../../..');
const BASE='5f9c6feb89441088d3aeb19765420f7563d71780';
const SAMPLES=[
  [5,'2026-10-08','2026-10-07T23:47:03Z','bf8ac8d6174bcac68a996769caf0c8237f39dae4','source-data/nfl/player-availability/espn.json'],
  [6,'2026-10-15','2026-10-14T23:47:09Z','6318ee4447ac8cdc2cf5bd008560986af9630ace','data-source/nfl/player-availability/espn.json'],
  [7,'2026-10-22','2026-10-21T23:37:06Z','c35a439c1ba1d430408cdb237456ca7410b7c4f8','data-source/nfl/player-availability/espn.json'],
  [8,'2026-10-29','2026-10-28T22:52:44Z','2061fd518588e0a347b796142546923944d92142','data-source/nfl/player-availability/espn.json'],
  [9,'2026-11-05','2026-11-04T23:53:02Z','245f0fb65404b9d95a0927d340cdbadbfa189ef3','data-source/nfl/player-availability/espn.json'],
  [10,'2026-11-12','2026-11-11T23:51:28Z','3050e8a94822445feff222803441670e8bd7f479','data-source/nfl/player-availability/espn.json'],
];
const BLOCKED=new Set(['OUT','DOUBTFUL','INJURY_RESERVE']);
function load(rev,file){
  let data;
  try {
    data=cp.execFileSync('git',['show',rev+':'+file],
      {cwd:ROOT,encoding:'utf8',maxBuffer:32*1024*1024,stdio:['ignore','pipe','pipe']});
  } catch(e){throw Error('Full Git history required for '+rev+':'+file+' ('+e.message+')');}
  return JSON.parse(data);
}
function ids(players){
  const m=new Map();
  for(const p of players) {
    const candidates=[p.IDs?.ESPN,...(Array.isArray(p.IDAliases?.ESPN)?p.IDAliases.ESPN:[])];
    for(const value of candidates){
      if(value===null || value===undefined || String(value)==='')continue;
      const key=String(value),prior=m.get(key);
      assert(!prior || prior===p.CanonicalPlayerID,'Ambiguous ESPN ID '+key);
      m.set(key,p.CanonicalPlayerID);
    }
  }
  return m;
}
function counter(){return {joined:0,played:0,notPlayed:0,unknown:0};}
function observe(groups,status,played){
  const key=status||'(blank)',r=groups[key]||(groups[key]=counter());
  r.joined++;
  if(played===true)r.played++;
  else if(played===false)r.notPlayed++;
  else r.unknown++;
}
function summarize(groups){
  const total=counter();let ruleErrors=0;
  for(const [status,r] of Object.entries(groups)){
    for(const k of Object.keys(total))total[k]+=r[k];
    ruleErrors+=BLOCKED.has(status)?r.played:r.notPlayed;
  }
  const n=total.played+total.notPlayed;
  return {total,known:n,baselineAllPlayErrors:total.notPlayed,
    ruleErrors,baselineAccuracy:n?+(1-total.notPlayed/n).toFixed(4):null,
    ruleAccuracy:n?+(1-ruleErrors/n).toFixed(4):null};
}
function merge(dest,source){
  for(const [status,r] of Object.entries(source)){
    const t=dest[status]||(dest[status]=counter());
    for(const k of Object.keys(t))t[k]+=r[k];
  }
}
function selfTest(){
  assert.equal(ids([{CanonicalPlayerID:'A',IDs:{ESPN:'1'},IDAliases:{ESPN:['2']}}]).get('2'),'A');
  const g={};observe(g,'OUT',false);observe(g,'ACTIVE',true);
  assert.equal(summarize(g).ruleErrors,0);
  assert(SAMPLES.every(s=>Date.parse(s[2])<Date.parse(s[1]+'T00:00:00Z')));
  const fixture=[['QB',10],['QB',9],['RB',8],['RB',7],['RB',6],['RB',5],
    ['WR',8],['WR',7],['WR',6],['WR',5],['TE',8],['TE',7],['TE',6],['TE',5],['K',4]]
    .map(([position,points])=>({position,points,status:position==='WR'&&points===8?'OUT':'ACTIVE'}));
  assert.deepEqual(bestBall(fixture,false),{complete:true,points:91});
  assert.deepEqual(bestBall(fixture,true),{complete:true,points:88});
  assert.deepEqual(bestBall(fixture.filter(p=>p.position!=='K'),false),{complete:false,missing:'K'});
  console.log('CP3f self-test OK');
}

// Secondary CP3f read-only pilot: contemporaneous league roster, PWF and
// published DecisionWindows join. Do not replace source products with app files
// in production: these app artifacts are historical publication evidence only.
const REQUIRED_SLOTS=[['QB',2],['RB',2],['WR',2],['TE',2],['K',1]];
function sleeperID(record,field){
  const matches=(record.ProviderMappings||[]).filter(p=>p.Provider==='Sleeper' && p[field]!==null && p[field]!==undefined);
  assert.equal(matches.length,1,'Missing/ambiguous Sleeper '+field);
  return String(matches[0][field]);
}
function bestBall(pool,blocked){
  const grouped={QB:[],RB:[],WR:[],TE:[],K:[]};
  for(const p of pool){
    if(blocked && BLOCKED.has(p.status))continue;
    assert(Object.hasOwn(grouped,p.position),'Unexpected fantasy position '+p.position);
    assert(Number.isFinite(p.points),'Nonfinite candidate projection');
    grouped[p.position].push(p.points);
  }
  for(const g of Object.values(grouped))g.sort((a,b)=>b-a);
  let points=0;
  for(const [position,count] of REQUIRED_SLOTS){
    const items=grouped[position];
    if(items.length<count)return {complete:false,missing:position};
    points+=items.splice(0,count).reduce((a,b)=>a+b,0);
  }
  const flex=[...grouped.RB,...grouped.WR,...grouped.TE].sort((a,b)=>b-a);
  if(flex.length<4)return {complete:false,missing:'FLEX'};
  points+=flex.slice(0,4).reduce((a,b)=>a+b,0);
  return {complete:true,points:+points.toFixed(4)};
}
function auditRosterPwf(){
  const outcomeRoot='data-source/leagues/nfl-reise/seasons/2026/matchups/week-';
  const result={researchOnly:true,baseline:'unadjusted as-of 13-slot best ball',
    alternative:'exclude as-of published OUT/DOUBTFUL/INJURY_RESERVE',
    target:'retrospective final Sleeper team score, not realized full-roster best ball',
    samples:[],summary:null};
  let allPlayers=0,asofStatuses=0,asofBlocked=0,paired=0,changed=0,
    baselineAbsError=0,adjustedAbsError=0,baselineSqError=0,adjustedSqError=0;
  for(const [week,day,observed,sha] of SAMPLES){
    const cut=Date.parse(observed);
    const dw=load(sha,'public/data/DecisionWindows.json');
    const pwf=load(sha,'public/data/PlayerWeekFantasy.json');
    const sourcePrefix=week===5?'source-data':'data-source';
    const sourcePath=sourcePrefix+'/leagues/nfl-reise/seasons/2026/matchups/week-'+week+'.json';
    const source=load(sha,sourcePath);
    const final=load(BASE,outcomeRoot+week+'.json');
    assert.equal(pwf.Week,week);assert.equal(pwf.Season,2026);
    assert.equal(dw.LineupWeek,week);assert.equal(String(dw.Season),'2026');
    assert(Array.isArray(source)&&source.length===6);
    assert(Array.isArray(final)&&final.length===6);
    const start=Math.min(...dw.DecisionWindows.map(d=>Date.parse(d.StartsAtUtc)));
    assert(Number.isFinite(start) && cut<start,'Snapshot must precede first kickoff');
    assert.equal(dw.FantasyRelevance.SlotDefinitions.length,13);
    const slotCounts={};
    for(const s of dw.FantasyRelevance.SlotDefinitions)
      slotCounts[s.SlotType]=(slotCounts[s.SlotType]||0)+1;
    assert.deepEqual(slotCounts,{QB:2,RB:2,WR:2,TE:2,FLEX:4,K:1});
    const projections=new Map();
    for(const record of pwf.Records){
      if(record.PlayerID===null||record.PlayerID===undefined)continue;
      const id=String(record.PlayerID);
      assert(!projections.has(id),'Duplicate PlayerID in PWF '+id);
      assert(record.Actual?.Points===null,'Pregame PWF includes actual points '+id);
      projections.set(id,record.Projection);
    }
    const asofByTeam=new Map(),finalByRoster=new Map();
    for(const team of source){
      const tid=sleeperID(team,'ProviderRosterID');
      assert(!asofByTeam.has(tid),'Duplicate as-of team '+tid);
      assert.equal(team.Week,week);assert.equal(team.Points,0,'Nonzero as-of score');
      asofByTeam.set(tid,team);
    }
    for(const team of final){
      assert(!finalByRoster.has(team.CanonicalLeagueRosterID),'Duplicate final roster ID');
      finalByRoster.set(team.CanonicalLeagueRosterID,team);
    }
    const perWeek={week,commit:sha,cutoff:observed,rosterPlayers:0,
      knownStatuses:0,blockedStatuses:0,completePairs:0,changedPairs:0,
      incomplete:[],teams:[]};
    assert.equal(dw.FantasyRelevance.Teams.length,6);
    for(const dwTeam of dw.FantasyRelevance.Teams){
      const teamID=String(dwTeam.FantasyTeamID),asof=asofByTeam.get(teamID);
      assert(asof,'No as-of matchup for team '+teamID);
      const finalTeam=finalByRoster.get(asof.CanonicalLeagueRosterID);
      assert(finalTeam && Number.isFinite(finalTeam.Points),'Missing final team score');
      const sourceIds=new Set(asof.Players.map(p=>sleeperID(p,'ProviderPlayerID')));
      const decisionIds=new Set(dwTeam.Players.map(p=>String(p.PlayerID)));
      assert.equal(sourceIds.size,asof.Players.length,'Duplicate source player');
      assert.equal(decisionIds.size,dwTeam.Players.length,'Duplicate decision player');
      assert.equal(sourceIds.size,decisionIds.size,'As-of roster size mismatch');
      for(const id of sourceIds)assert(decisionIds.has(id),'As-of roster member mismatch '+id);
      const pool=[];
      for(const p of dwTeam.Players){
        allPlayers++;perWeek.rosterPlayers++;
        const a=p.ScoringAvailability||{};
        if(a.ProviderStatus){
          asofStatuses++;perWeek.knownStatuses++;
          assert(a.ObservedAtUtc,'Missing observation date for status '+p.PlayerID);
          assert(Date.parse(a.ObservedAtUtc)<=cut,'Status observed after checkpoint');
        }
        if(BLOCKED.has(a.ProviderStatus)){
          asofBlocked++;perWeek.blockedStatuses++;
        }
        if(p.Placement!=='starter'&&p.Placement!=='bench')continue;
        if(p.GameState!=='unlocked'||!p.GameID)continue;
        const projection=projections.get(String(p.PlayerID));
        if(projection?.Status!=='available'||!Number.isFinite(projection.Points))continue;
        pool.push({position:p.Position,points:projection.Points,status:a.ProviderStatus});
      }
      const base=bestBall(pool,false),gate=bestBall(pool,true);
      const entry={teamID,projectableCandidates:pool.length,baseline:base,
        gated:gate,finalSleeperPoints:finalTeam.Points};
      if(base.complete && gate.complete){
        paired++;perWeek.completePairs++;
        const be=base.points-finalTeam.Points,ge=gate.points-finalTeam.Points;
        baselineAbsError+=Math.abs(be);adjustedAbsError+=Math.abs(ge);
        baselineSqError+=be*be;adjustedSqError+=ge*ge;
        if(Math.abs(base.points-gate.points)>0.00001){
          changed++;perWeek.changedPairs++;
          entry.errorChange=Math.abs(ge)-Math.abs(be);
        }
      }else{
        perWeek.incomplete.push({teamID,baseline:base.missing??null,gated:gate.missing??null});
      }
      perWeek.teams.push(entry);
    }
    result.samples.push(perWeek);
  }
  result.summary={totalTeamWeeks:result.samples.length*6,
    asofRosterPlayerWeeks:allPlayers,knownAsOfStatuses:asofStatuses,
    blockedAsOfStatuses:asofBlocked,completePairedTeamWeeks:paired,
    changedPairedTeamWeeks:changed,
    baselineMAE:+(baselineAbsError/paired).toFixed(4),
    gatedMAE:+(adjustedAbsError/paired).toFixed(4),
    baselineRMSE:+Math.sqrt(baselineSqError/paired).toFixed(4),
    gatedRMSE:+Math.sqrt(adjustedSqError/paired).toFixed(4)};
  assert.equal(allPlayers,1229,'Fixed historical population changed');
  assert.equal(asofStatuses,465,'Historical status coverage changed');
  assert.equal(paired,33,'Historical paired sample changed');
  console.log(JSON.stringify(result,null,2));
}

function main(){
  if(process.argv.includes('--self-test'))return selfTest();
  if(process.argv.includes('--roster-pwf')){
    assert.equal(process.argv.length,3,'--roster-pwf is the only argument');
    return auditRosterPwf();
  }
  if(process.argv.length!==2)throw Error('Only --self-test is an option; input revisions are pinned');
  const ident=ids(load(BASE,'data-source/nfl/identities/players.json').Players);
  const avail=load(BASE,'data-derived/nfl-player-availability/2026.json');
  const schedule=load(BASE,'data-source/nfl/schedules/2026.json');
  assert.equal(avail.ProductVersion,'nfl-player-availability-v2');
  const targets=new Map();
  for(const r of avail.Records){
    const key=r.Week+'|'+r.CanonicalPlayerID;
    assert(!targets.has(key),'Duplicate target '+key);
    targets.set(key,r);
  }
  const allNfl={},fantasy={},byWeek=[];
  let missingEspnIdentity=0,missingFantasySnapshot=0,fantasyBye=0,fantasyNoRecord=0;
  for(const [week,day,observed,sha,file] of SAMPLES){
    assert(!Number.isNaN(Date.parse(observed))&&Date.parse(observed)<Date.parse(day+'T00:00:00Z'));
    const first=schedule.Games.filter(g=>g.Week===week&&g.GameType==='REG')
      .map(g=>g.GameDay).sort()[0];
    assert.equal(day,first,'Snapshot cutoff differs from first game day');
    const snapshot=load(sha,file);
    assert.equal(snapshot.Season,2026);assert.equal(snapshot.SourceDataset,'espn.player-availability');
    const statuses=new Map(),nflWeek={},fantasyWeek={};
    for(const p of snapshot.Players){
      assert(!Number.isNaN(Date.parse(p.StatusSinceUtc)),'Missing status timestamp');
      assert(Date.parse(p.StatusSinceUtc)<=Date.parse(observed),'Post-observation status');
      const id=ident.get(String(p.ESPNPlayerID));
      if(!id){missingEspnIdentity++;continue;}
      assert(!statuses.has(id),'Conflicting ESPN aliases for '+id);
      statuses.set(id,p.ProviderStatus);
      const r=targets.get(week+'|'+id);
      if(r?.GameID && r.GameType==='REG')observe(nflWeek,p.ProviderStatus,r.Played);
    }
    const matchups=load(BASE,'data-source/leagues/nfl-reise/seasons/2026/matchups/week-'+week+'.json');
    assert(Array.isArray(matchups)&&matchups.length===6);
    const rosterIds=new Set();
    for(const team of matchups)for(const p of team.Players){
      assert(!rosterIds.has(p.CanonicalPlayerID),'Cross-team duplicate '+p.CanonicalPlayerID);
      rosterIds.add(p.CanonicalPlayerID);
    }
    for(const id of rosterIds){
      if(!statuses.has(id)){missingFantasySnapshot++;continue;}
      const r=targets.get(week+'|'+id);
      if(!r)fantasyNoRecord++;
      else if(r.State==='bye')fantasyBye++;
      observe(fantasyWeek,statuses.get(id),r?.Played);
    }
    merge(allNfl,nflWeek);merge(fantasy,fantasyWeek);
    byWeek.push({week,cutoff:day+'T00:00:00Z',observed,commit:sha,
      snapshotPlayers:snapshot.Players.length,fantasyRosterCount:rosterIds.size,
      nfl:summarize(nflWeek),fantasy:summarize(fantasyWeek)});
  }
  console.log(JSON.stringify({researchOnly:true,baseRef:BASE,season:2026,byWeek,
    allNfl:{summary:summarize(allNfl),byStatus:allNfl},
    archivedFantasy:{summary:summarize(fantasy),byStatus:fantasy},
    missingEspnIdentity,missingFantasySnapshot,fantasyBye,fantasyNoRecord,
    limitations:'Archived fantasy rosters and current identity map are retrospective. Not a calibrated participation probability, expected team points, or win chance.'},null,2));
}
if(require.main===module)main();
module.exports={ids,observe,summarize};
