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
  console.log('CP3f self-test OK');
}
function main(){
  if(process.argv.includes('--self-test'))return selfTest();
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
