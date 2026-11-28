#!/usr/bin/env node
/**
 * CP6o research (2026-11-22), voluntary cut/FA replacement with per-year guarantee ledger.
 * 2027 CP6k synthetically legal six-team start; 2028 and 2029: 5 Rookie picks/team,
 * full-salary rosters, all player IDs exclusive across owners, no fictitious buyer.
 * Rookie scheduled salary 100/125/150. Veteran schedule 100 / (100+s) / (100+2s).
 * Full-grant vs 100/50/25 after cut, accrued yearly at future actual due dates.
 * Market-cap price path = CP6k frozen (not yet strictly detached from rookie contracts).
 * No NFL reality after 2026, no authentic 2027 contract history, no managed trade/claim,
 * no IR/Taxi model; 2027 old owners are synthetic, all other holdings freshly signed.
 * No Auto-Rollover or Cap Credit. A 14d claim window is assumed expired without buyer.
 * Greedy actor is a diagnostic, NOT a mathematically optimal/consenting human manager.
 * Underfilled/over-cap annual roster is reported as failure, never silently legalized.
 * Script freezes CP6k engine excerpt from Blob 8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c
 * to keep original CP6k archival SHA unchanged.
 *
 * Run: node fantasy-management/league-economy/salary/simulation/cp6o_guaranteed_cut_recovery.mjs [--json]
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const POS=['QB','RB','WR','TE','K'];
const FLEX=new Set(['RB','WR','TE']);
const FIXED={QB:2,RB:2,WR:2,TE:2,K:1};
const BENCH={QB:3,RB:3,WR:3,TE:3,K:2};
const ANCHOR=434255984;
const CREF=8.4417; // frozen 2023–2025 DMLI reference: NOT dynamic curve regeneration
const CURVES={
 QB:[7.78,6.28,4.99,4.48,4.08,3.27,2.7,2.08,1.7,1.54,1.12,.58],
 RB:[11.56,7.95,7.23,6.77,5.67,5.12,4.3,3.94,3.42,3.07,2.76,2.61,2.29,2.15,1.9,1.39,.99,.94,.66,.41,.1,.01],
 WR:[10.61,8.85,6.64,6,5.32,4.65,3.76,3.48,3.01,2.81,2.75,2.58,2.4,2.35,2.07,1.77,1.51,1.37,1.23,1.19,1.02,.62,.56,.45,.41,.29,.12,.05,.05,.04],
 TE:[6.79,4.75,4.41,3.28,2.88,2.52,1.76,1.57,1.26,.92,.58,.37],
 K:[2.1,1.35,1.11,.69,.24,.11]
};
const rnd=x=>Math.floor(x+0.5);
const pct=year=>year<=1?.0025:year===2?.003:year===3?.0035:year===4?.004:year<=7?.0045:.005;
const minimum=(year,prevCap)=>rnd(prevCap*pct(year));
const dpct=(rank,n)=>rank==null?.0025:.003+.032*Math.pow(Math.max(0,1-(rank-1)/(n-1)),3.5);
function uniform(seed,id,season,key){
 let h=2166136261>>>0;const str=seed+'/'+id+'/'+season+'/'+key;
 for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619);}
 h^=h>>>16;h=Math.imul(h,0x7feb352d);h^=h>>>15;h=Math.imul(h,0x846ca68b);h^=h>>>16;
 return (h>>>0)/4294967296;
}
const noise=(seed,id,year,key)=>(uniform(seed,id,year,key+'a')+uniform(seed,id,year,key+'b')+uniform(seed,id,year,key+'c')-1.5)*1.35;
function perf3(h){
 const last=h.slice(-3);const max=Math.max(0,...last);
 if(!max)return 0;
 const best=last.lastIndexOf(max);
 const floor=max*[.17,.33,.5][best];
 return last.reduce((a,b)=>a+Math.max(0,b,floor),0)/3;
}
function lineup(roster,world,mode='known'){
 const valid=roster.filter(id=>world.get(id)?.active);
 const value=p=>mode==='realized'?p.realized:p.known;
 const pool=valid.map(id=>world.get(id)).filter(p=>value(p)>0);
 const picks=[],selected=new Set();
 for(const pos of POS){
  const sorted=pool.filter(p=>p.pos===pos).sort((a,b)=>value(b)-value(a)||a.id.localeCompare(b.id)).slice(0,FIXED[pos]);
  if(sorted.length!==FIXED[pos])return {valid:false,score:0,ids:[]};
  for(const p of sorted){picks.push(p);selected.add(p.id);}
 }
 const flex=pool.filter(p=>FLEX.has(p.pos)&&!selected.has(p.id)).sort((a,b)=>value(b)-value(a)||a.id.localeCompare(b.id)).slice(0,4);
 if(flex.length!==4)return {valid:false,score:0,ids:[]};
 picks.push(...flex);
 return {valid:true,score:picks.reduce((a,p)=>a+value(p),0),ids:picks.map(p=>p.id)};
}
const heldCost=(ids,world)=>ids.reduce((a,id)=>a+world.get(id).price,0);
function coverage(ids,world){
 if(ids.length<20||ids.length>40||new Set(ids).size!==ids.length)return false;
 const counts=Object.fromEntries(POS.map(pos=>[pos,0]));
 for(const id of ids){const p=world.get(id);if(!p||!p.active||!POS.includes(p.pos))return false;counts[p.pos]++;}
 for(const pos of POS)if(counts[pos]<BENCH[pos])return false;
 if(counts.RB+counts.WR+counts.TE<13)return false;
 return lineup(ids,world).valid;
}
function legal(team,world,cap){
 return coverage(team.players,world)&&heldCost(team.players,world)<=cap+1;
}
function scoreObjective(ids,world,style){
 const line=lineup(ids,world);if(!line.valid)return -1e9;
 const bench=ids.filter(id=>!line.ids.includes(id)).map(id=>world.get(id).known).sort((a,b)=>b-a);
 const youth=ids.reduce((a,id)=>{const p=world.get(id);return a+(p.year<=3?.75*Math.max(0,p.scout-p.known)+.5:0);},0);
 const cost=heldCost(ids,world)/1e6;
 return line.score+style.depth*bench.slice(0,7).reduce((a,b)=>a+b,0)*.08+style.youth*youth*.18-style.cap*cost*.10;
}
function capFor(world){
 const salaries=[...world.values()].filter(p=>p.active).map(p=>p.price).sort((a,b)=>b-a);
 if(salaries.length<120)throw Error('Not enough active players for 120 salaries');
 return rnd(salaries.slice(0,120).reduce((a,b)=>a+b,0)/6);
}
function applyDynamicSalary(world,prevCap){
 const ranks={};for(const pos of POS){
  const ps=[...world.values()].filter(p=>p.active&&p.pos===pos).sort((a,b)=>perf3(b.h)-perf3(a.h)||a.id.localeCompare(b.id));
  ps.forEach((p,i)=>ranks[p.id]=.75+.5*Math.min((CURVES[pos][i]||0)/CREF,1));
 }
 for(const p of world.values()){
  if(!p.active){p.price=0;continue;}
  const min=minimum(p.year,prevCap);
  if(p.year<=3&&p.rookieBase!=null){
   p.price=Math.max(min,rnd(p.rookieBase*({1:1,2:1.25,3:1.5}[p.year])));
  }else{
   const signal=perf3(p.h)*(ranks[p.id]||.75);
   const q=signal/20;
   const P=rnd(50000000*(q<=1?Math.pow(Math.max(0,q),1.5):1+(q-1)*1.5));
   p.price=Math.max(P,rnd(min+.5*P));
  }
  p.known=perf3(p.h);
 }
}
function archive(csv){
 const lines=csv.trim().split(/\r?\n/),h=lines.shift().split(';');
 const records=lines.map(line=>Object.fromEntries(line.split(';').map((v,i)=>[h[i],v])));
 if(records.length!==1268)throw Error('Expected frozen 1268 player archive; got '+records.length);
 const world=new Map();
 for(const r of records){
  if(!POS.includes(r.position))continue;
  const y=Number(r.year),s=Number(r.performance_3y),P=Number(r.salary_I_ohne_base_minimum);
  if(!Number.isFinite(y)||y<1||!Number.isFinite(s)||!Number.isFinite(P)||P<0||world.has(r.id))throw Error('Bad archive player '+r.id);
  const rookie=r.contract==='rookie'&&y<=3;
  const price=rookie?Math.max(P,minimum(y,ANCHOR)):Math.max(P,rnd(minimum(y,ANCHOR)+.5*P));
  world.set(r.id,{id:r.id,pos:r.position,year:y,active:r.nfl_team!=='FA',initial:true,
    h:[s,s,s],known:s,realized:s,talent:s,
    scout:s,price,rookieBase:rookie?P/({1:1,2:1.25,3:1.5}[y]):null});
 }
 return world;
}
function chooseInitial(world,used,cap,seed,teamIndex){
 const available=[...world.values()].filter(p=>p.active&&!used.has(p.id));
 const groups=Object.fromEntries(POS.map(pos=>[pos,available.filter(p=>p.pos===pos&&p.known>0)]));
 const pool=Object.fromEntries(POS.map(pos=>[pos,available.filter(p=>p.pos===pos&&p.known>=3).sort((a,b)=>a.price-b.price||a.id.localeCompare(b.id))]));
 pool.FLEX=available.filter(p=>FLEX.has(p.pos)&&p.known>=3).sort((a,b)=>a.price-b.price||a.id.localeCompare(b.id));
 function fillBench(starters){
  const ids=new Set(starters.map(p=>p.id)),bench=[];
  const take=a=>{const p=a.find(p=>!ids.has(p.id));if(!p)return false;ids.add(p.id);bench.push(p);return true;};
  for(const pos of POS)if(!take(pool[pos]))return null;
  for(let i=0;i<2;i++)if(!take(pool.FLEX))return null;
  return bench;
 }
 let best=null;
 for(let t=0;t<=500;t++){
  const lambda=t/500;
  const order=(a,b)=>{
    const adj=x=>x.known*(1+((uniform(seed,x.id,0,'start-'+teamIndex)-.5)*.07)) - lambda*x.price/1e6;
    return adj(b)-adj(a)||a.id.localeCompare(b.id);
  };
  const starters=[],ids=new Set();
  for(const pos of POS)for(const p of [...groups[pos]].sort(order).slice(0,FIXED[pos])){ids.add(p.id);starters.push(p);}
  starters.push(...available.filter(p=>FLEX.has(p.pos)&&p.known>0&&!ids.has(p.id)).sort(order).slice(0,4));
  if(starters.length!==13||new Set(starters.map(x=>x.id)).size!==13)continue;
  const bench=fillBench(starters);if(!bench)continue;
  const full=[...starters,...bench],total=full.reduce((s,p)=>s+p.price,0);
  if(total>cap)continue;
  const index=starters.reduce((s,p)=>s+p.known,0);
  if(!best||index>best.index+1e-7)best={players:full.map(x=>x.id),index,total};
 }
 if(!best)throw Error('No feasible six-team initial roster for team '+teamIndex);
 return best;
}
function startWorld(csv,seed){
 const world=archive(csv),cap=capFor(world),used=new Set(),teams=[];
 for(let ti=0;ti<6;ti++){
  const roster=chooseInitial(world,used,cap,seed,ti);
  for(const id of roster.players){if(used.has(id))throw Error('Initial duplicate owner');used.add(id);}
  teams.push({id:ti,players:roster.players,style:ti===0?{depth:.28,youth:.45,cap:.12}:{depth:.35+(ti%3)*.15,youth:.45+(ti%2)*.25,cap:.12}});
 }
 if(teams.some(t=>!legal(t,world,cap)))throw Error('Initial 6 teams not full-salary legal');
 return {world,teams,cap};
}
function newRookies(world,seed,season,supply,previousCap){
 const draftable=[],undrafted=[];
 const pattern=['WR','RB','WR','TE','WR','RB','QB','WR','TE','RB','WR','QB','WR','RB','TE','WR','RB','WR','QB','WR','RB','TE','WR','RB','WR','QB','RB','WR','TE','WR'];
 for(let i=0;i<30+supply;i++){
  const drafted=i<30,idx=i%30,id='S'+seed+'T'+season+(drafted?'D':'U')+i;
  if(world.has(id))throw Error('Rookie ID collision');
  const pos=drafted?pattern[i]:(['WR','RB','WR','TE','RB','WR','QB','WR','TE','K'][idx%10]);
  const fRank=drafted?i+1:null;
  const nflRank=drafted?Math.max(1,Math.min(80,rnd(1.7*(i+1)+noise(seed,id,season,'nfl')*7))):
     (uniform(seed,id,season,'undrafted')<.5?null:31+rnd(uniform(seed,id,season,'nr')*49));
  const rookieBase=rnd(previousCap*(.65*dpct(fRank,30)+.35*dpct(nflRank,80)));
  const prior=drafted?5+9*Math.pow(1-i/30,.75):2.4+3.5*uniform(seed,id,season,'ud');
  const scout=Math.max(.3,prior+noise(seed,id,season,'scout')*.75);
  const gem=!drafted&&uniform(seed,id,season,'gem')<.03?7:0;
  const talent=Math.max(.3,scout+noise(seed,id,season,'talent')*2+gem);
  const p={id,pos,year:1,active:true,initial:false,h:[0,0,0],known:scout,scout,realized:0,
   talent,price:Math.max(rookieBase,minimum(1,previousCap)),rookieBase};
  world.set(id,p);(drafted?draftable:undrafted).push(id);
 }
 return {draftable,undrafted};
}
function allOwned(teams){
 const own=new Map();for(const team of teams)for(const id of team.players){
  if(own.has(id))throw Error('Multiple owners for '+id);own.set(id,team.id);
 }
 return own;
}
function canRemoveButKeepCoverage(ids,world){
 return coverage(ids,world);
}
function repairTeam(team,world,teams,cap,ops){
 // No debt, no magical cap exceptions. Can drop redundant players; if full at 20, legal simultaneous replacement.
 const forbidden=new Set();
 for(let j=0;j<80;j++){
  const ids=team.players,healthy=coverage(ids,world),total=heldCost(ids,world);
  if(healthy&&total<=cap+1)return true;
  const owners=allOwned(teams);
  const free=[...world.values()].filter(p=>p.active&&!owners.has(p.id));
  const candidate=[];
  const mode=team.id===0?'known':'known';
  const before=lineup(ids,world,mode).score;
  for(let k=0;k<ids.length;k++){
   const out=world.get(ids[k]),remaining=ids.filter((_,i)=>i!==k);
   if(remaining.length>=20&&canRemoveButKeepCoverage(remaining,world)){
    const loss=Math.max(0,before-lineup(remaining,world).score);
    const futurePenalty=(out.year<=3?.8:0)+.1*out.scout;
    const utility=(total>cap?2.2:0)*out.price/1e6 -1.65*loss-.15*futurePenalty;
    candidate.push({k,with:null,utility,relief:out.price});
   }
   if(ids.length<20||total>cap||!healthy){
    const choices=free.filter(p=>p.pos===out.pos).sort((a,b)=>a.price-b.price||a.id.localeCompare(b.id)).slice(0,20);
    for(const incoming of choices){
     const next=ids.slice();next[k]=incoming.id;
     if(!coverage(next,world))continue;
     const relief=out.price-incoming.price;
     if(relief<=0&&total>cap)continue;
     const loss=Math.max(0,before-lineup(next,world).score);
     const utility=2.2*relief/1e6-1.5*loss;
     candidate.push({k,with:incoming.id,utility,relief});
    }
   }
  }
  if(!candidate.length)return false;
  // When extra slots are occupied, cut optional depth first unless that destroys lineup.
  candidate.sort((a,b)=>b.utility-a.utility||b.relief-a.relief);
  const best=candidate.find(c=>!forbidden.has(ids[c.k]+':'+c.with));
  if(!best)return false;
  const removed=team.players[best.k];
  if(best.with){team.players[best.k]=best.with;ops.repairSwaps++;}else{team.players.splice(best.k,1);ops.mandatoryCuts++;}
  if(!best.with&&team.players.length<20)throw Error('Cut below research minimum');
  forbidden.add(removed+':'+best.with);
 }
 return false;
}
function upgradeFA(team,world,teams,cap,ops,maxSwaps){
 for(let n=0;n<maxSwaps;n++){
  const own=allOwned(teams),free=[...world.values()].filter(p=>p.active&&!own.has(p.id)&&p.known>0);
  // Never use unavailable/retired or another manager's player. Choose only public prior-based information.
  const inPool=[...free].sort((a,b)=>(b.known/(2+b.price/1e6))-(a.known/(2+a.price/1e6))).slice(0,100);
  const original=scoreObjective(team.players,world,team.style),cost=heldCost(team.players,world);
  let best=null;
  for(let i=0;i<team.players.length;i++){
   const out=world.get(team.players[i]);
   for(const incoming of inPool){
    const newCost=cost-out.price+incoming.price;
    if(newCost>cap+1)continue;
    const next=team.players.slice();next[i]=incoming.id;
    if(!coverage(next,world))continue;
    const newScore=scoreObjective(next,world,team.style);
    const benefit=newScore-original;
    if(benefit>0.15&&(!best||benefit>best.benefit))best={i,id:incoming.id,benefit};
   }
  }
  if(!best)break;
  team.players[best.i]=best.id;ops.optionalSwaps++;
 }
}
function draft(teams,world,draftable,previousScores,seed,season){
 const sorted=previousScores.map((v,i)=>({i,v})).sort((a,b)=>b.v-a.v||a.i-b.i);
 const byRank=sorted.map(x=>x.i); // rank 1=best, ... rank 6=worst
 const order=[byRank[4],byRank[5],byRank[3],byRank[2],byRank[1],byRank[0]];
 const available=new Set(draftable);
 for(let round=0;round<5;round++)for(const ti of order){
  const team=teams[ti];const passive=team.passive;
  const choices=[...available].map(id=>world.get(id));
  choices.sort((a,b)=>{
   const value=p=>{
    if(passive)return p.scout-(p.year<=3?p.price/1e7:0)*.03;
    const cnt=team.players.filter(id=>world.get(id).pos===p.pos).length;
    const shortage=cnt<BENCH[p.pos]?1.6:0;
    return (p.scout+shortage)/(1.7+p.price/1e7)**(.35+(ti===0?.2:.06));
   };
   return value(b)-value(a)||a.id.localeCompare(b.id);
  });
  const p=choices[0];if(!p)throw Error('Not enough draftable rookies');
  team.players.push(p.id);available.delete(p.id);
  if(team.players.length>40){
   // Explicit same-draft-slot cut; never receive a free 41st regular slot.
   // The pick itself can be lost if no other legal capacity cut exists.
   const full=team.players.slice();
   const options=full.map((id,i)=>({id,i,remaining:full.filter((_,k)=>k!==i)}));
   const shortfall=ids=>{
     const cnt=Object.fromEntries(POS.map(pos=>[pos,ids.filter(id=>world.get(id).active&&world.get(id).pos===pos).length]));
     return POS.reduce((sum,pos)=>sum+Math.max(0,BENCH[pos]-cnt[pos]),0)+Math.max(0,13-cnt.RB-cnt.WR-cnt.TE);
   };
   options.sort((a,b)=>shortfall(a.remaining)-shortfall(b.remaining)||
     scoreObjective(b.remaining,world,team.style)-scoreObjective(a.remaining,world,team.style)||
     world.get(b.id).price-world.get(a.id).price);
   team.players=options[0].remaining;
  }
 }
 if(available.size!==0)throw Error('Not all 30 rookie picks allocated');
}
function seasonalDevelopment(world,seed,season){
 for(const p of world.values()){
  if(!p.active)continue;
  const aging=p.year>10?1-.05*(p.year-10):1;
  const recovered=Math.max(0,p.talent*aging+noise(seed,p.id,season,'performance')*1.75);
  p.realized=recovered;
  p.h.shift();p.h.push(recovered);
  // Player-specific deterministic NFL-exit hazard, independent of management choices
  const exit=p.year>=12?.095:p.year>=9?.035:p.year>=6?.012:.003;
  if(uniform(seed,p.id,season,'retire')<exit){p.active=false;p.realized=0;}
  p.year++;
  p.known=p.active?perf3(p.h):0;
 }
}
function settleRetired(teams,world,cap,ops){
 // Players who left NFL have no valid starter or coverage slot.
 // They remain owned until removed as a legal roster-management step.
 for(const team of teams){
  const before=team.players.length;
  team.players=team.players.filter(id=>world.get(id).active);
  ops.retirementExits+=before-team.players.length;
 }
 // Fill holes with the least expensive active unowned player that improves missing coverage.
 for(const team of teams)for(let j=0;j<45&&!coverage(team.players,world);j++){
  if(team.players.length>=40)return false;
  const owners=allOwned(teams);
  const free=[...world.values()].filter(p=>p.active&&!owners.has(p.id)).sort((a,b)=>a.price-b.price||b.known-a.known);
  const have=Object.fromEntries(POS.map(pos=>[pos,team.players.filter(id=>world.get(id).pos===pos).length]));
  let missing=POS.find(pos=>have[pos]<BENCH[pos]);
  const ps=missing?free.filter(p=>p.pos===missing):free.filter(p=>FLEX.has(p.pos));
  // A temporary over-cap repair is allowed before the *same* annual settlement;
  // final full-salary compliance is checked after legal compensating cuts/swaps.
  const p=ps[0];
  if(!p)return false;
  team.players.push(p.id);ops.emergencyAdds++;
 }
 return true;
}
function validate(teams,world,cap){
 const owned=allOwned(teams);
 const details=teams.map(team=>({team:team.id,roster:team.players.length,capUsed:heldCost(team.players,world),legal:legal(team,world,cap),
  index:lineup(team.players,world).score}));
 return {allLegal:owned.size===teams.reduce((s,t)=>s+t.players.length,0)&&details.every(d=>d.legal),details};
}
function cloneStart(source,seed){
 const world=new Map([...source.world].map(([k,p])=>[k,{...p,h:[...p.h]}]));
 const teams=source.teams.map(t=>({...t,players:[...t.players],style:{...t.style}}));
 return {world,teams,cap:source.cap};
}
function simulateOne(start,seed,supply,regime){
 const {world,teams}=cloneStart(start,seed);
 teams[0].passive=regime==='passive';
 let cap=capFor(world),prevCap=start.cap,lastScores=teams.map(t=>lineup(t.players,world).score);
 const years=[],failures=[];
 const ops={mandatoryCuts:0,repairSwaps:0,optionalSwaps:0,retirementExits:0,emergencyAdds:0};
 for(let season=1;season<=5;season++){
  if(season>1)applyDynamicSalary(world,prevCap);
  const rookie=newRookies(world,seed,season,supply,prevCap);
  cap=capFor(world); // include all new Rookie salary in the Top120 price market before annual lock
  const salaryCap=cap;
  // Offseason removals of already-retired NFL players precede the five-round Rookie Draft.
  // Missing coverage may be repaired before the picks, even if cap settlement is later.
  const preDraftReady=settleRetired(teams,world,cap,ops);
  if(!preDraftReady)failures.push({season,kind:'pre-draft-retirement-cover-failed'});
  draft(teams,world,rookie.draftable,lastScores,seed,season);
  // During draft a team can temporarily be above the cap; every team must pass the annual settlement.
  for(const team of teams){
   // First remove retired players; then legal coverage and legal cap must both hold.
   team.players=team.players.filter(id=>world.get(id).active);
  }
  const firstFill=settleRetired(teams,world,cap,ops);
  const settled=[];
  for(const team of teams)settled.push(firstFill&&repairTeam(team,world,teams,cap,ops));
  // Only cap/slots settled teams may access the Free Agent improvement market.
  if(settled.every(Boolean))for(const team of teams){
   if(team.id===0&&team.passive)continue;
   upgradeFA(team,world,teams,cap,ops,team.id===0?8:2);
  }
  const pre=validate(teams,world,cap);
  if(!pre.allLegal)failures.push({season,kind:'settlement',settled,firstFill,teams:pre.details.map(d=>({id:d.team,roster:d.roster,capUsed:d.capUsed,legal:d.legal}))});
  const predictedScores=pre.details.map(d=>d.index);
  // Exogenous observed season outcomes are the same by player and year in both regimes.
  seasonalDevelopment(world,seed,season);
  const observedScores=teams.map(team=>lineup(team.players,world,'known').score);
  // Same three-year smoothed quality definition as the October archive, not raw one-season points.
  const allstar=lineup([...world.values()].filter(p=>p.active).map(p=>p.id),world).score;
  const topOpponent=Math.max(...observedScores.slice(1));
  years.push({year:2026+season,cap_m:salaryCap/1e6,preLegal:pre.allLegal,
   index:+observedScores[0].toFixed(3),predicted:+predictedScores[0].toFixed(3),
   bestOpponent:+topOpponent.toFixed(3),gapToBest:+(observedScores[0]-topOpponent).toFixed(3),
   relativeAllstar:allstar>0?+(observedScores[0]/allstar).toFixed(5):null,
   allstar:+allstar.toFixed(3),roster:teams[0].players.length,capUse_m:pre.details[0].capUsed/1e6,
   leagueScores:observedScores.map(v=>+v.toFixed(3))});
  lastScores=observedScores;
  prevCap=cap;
  if(!pre.allLegal)break;
 }
 const legalAll=years.length===5&&years.every(y=>y.preLegal)&&failures.length===0;
 return {seed,supply,regime,initialCap_m:start.cap/1e6,
   initialScores:start.teams.map(t=>+lineup(t.players,start.world).score.toFixed(3)),
   legalAll,failures,years,
   h5:legalAll?+Math.min(...years.map(y=>y.index)).toFixed(3):null,
   gapMin:legalAll?+Math.min(...years.map(y=>y.gapToBest)).toFixed(3):null,
   ops};
}
function summary(runs){
 const pairs=[];
 for(const seed of [...new Set(runs.map(r=>r.seed))])
 for(const supply of [...new Set(runs.map(r=>r.supply))]){
  const passive=runs.find(r=>r.seed===seed&&r.supply===supply&&r.regime==='passive');
  const active=runs.find(r=>r.seed===seed&&r.supply===supply&&r.regime==='active');
  pairs.push({seed,supply,legalBoth:passive.legalAll&&active.legalAll,
   passiveH5:passive.h5,activeH5:active.h5,
   deltaH5:passive.h5!=null&&active.h5!=null?+(active.h5-passive.h5).toFixed(3):null,
   passiveGapMin:passive.gapMin,activeGapMin:active.gapMin,
   passiveActions:passive.ops,activeActions:active.ops,
   passiveYears:passive.years.map(y=>y.index),activeYears:active.years.map(y=>y.index),
   passiveIllegal:passive.failures,activeIllegal:active.failures});
 }
 return pairs;
}
function simulate(csv,{seeds=[11,29,47],supplies=[0,30,50]}={}){
 const all=[];
 for(const seed of seeds){
  const initial=startWorld(csv,seed);
  for(const supply of supplies)for(const regime of ['passive','active']){
   try{all.push(simulateOne(initial,seed,supply,regime));}
   catch(err){all.push({seed,supply,regime,legalAll:false,failures:[{kind:'uncaught-model-error',error:String(err)}],
      years:[],h5:null,gapMin:null,ops:null,initialScores:initial.teams.map(t=>+lineup(t.players,initial.world).score.toFixed(3))});}
  }
 }
 return {schema:'cp6k-v0',status:'synthetic feasibility prototype; not validated equilibrium or upper bound',
  asOf:'2026-10-05',rosterScoring:'historical 3Y quality -> seeded 3Y observed proxy',
  maxSlots:40,minimumOccupiedForResearch:20,allSalariesCount:true,capFactor:1,capTop:120,years:5,
  initialSeedCount:seeds.length,rookieSupplyScenarios:supplies,
  notes:{passive:'normal 5 round rookie picks, public scout ranking, only mandatory cap/retirement action; no proactive FA swaps',
   active:'same draft assets and exogenous futures, public scout/value ranking plus <=8 proactive FA swaps/year; other five managers <=2',
   exclusions:'no real future NFL results, no actual 2026 owner claims, no inter-team trades or buyer consent, no dead-cap/debt/IR/taxi, no realistic weekly injuries/bye, no exact MILP',
   futurePrices:'Year2+ annual 3Y salary repricing using fixed 2023–25 DMLI rank curve (rank dynamic, curve frozen); rookie 65/35 Year1, 125/150% Year2/3, sliding minimum at Year4+ and top120/6 cap every year',
   ownership:'6 disjoint teams; only truly unowned free agents accessible; no automatic free acquisition of another team’s players',
   criterion:'H5 = minimum of five realized seasonal 13-slot 3Y-quality lineups; NOT global max H5'},pairs:summary(all),runs:all};
}

const GP=[1,.5,.25],FULL=[1,1,1], YEARS=[2027,2028,2029];
function assert2(ok,msg){if(!ok)throw Error(msg);}
function dollars(x){return Math.floor(x+.5);}
function contract(player,owner,season,kind,price){
 assert2(Number.isFinite(price)&&price>0,'invalid contract base');
 return {player,owner,start:season,end:season+2,kind,base:price};
}
function factor(c,year,slope){const age=year-c.start;return c.kind==='rookie'?[1,1.25,1.5][age]:1+slope*age;}
function annual(c,year,slope){return year>=c.start&&year<=c.end?dollars(c.base*factor(c,year,slope)):0;}
function dueFor(team,year,slope,contracts,dead){
 const active=team.players.reduce((a,id)=>a+annual(contracts.get(id),year,slope),0);
 const deadDue=dead.filter(x=>x.owner===team.id&&x.year===year).reduce((a,x)=>a+x.amount,0);
 return {active,dead:deadDue,total:active+deadDue};
}
function cutEntries(c,year,slope,guarantee){
 const entries=[];
 for(let y=year;y<=c.end;y++){
  const age=y-c.start;
  const amount=dollars(annual(c,y,slope)*guarantee[age]);
  if(amount>0)entries.push({player:c.player,owner:c.owner,signSeason:c.start,year:y,age:age+1,amount});
 }
 return entries;
}
function coverageShort(ids,world){
 const count=Object.fromEntries(POS.map(p=>[p,0]));
 for(const id of ids){
  const p=world.get(id);
  if(p?.active&&POS.includes(p.pos))count[p.pos]++;
 }
 let short=POS.reduce((v,p)=>v+Math.max(0,BENCH[p]-count[p]),0);
 short+=Math.max(0,13-count.RB-count.WR-count.TE);
 short+=Math.max(0,20-ids.length);
 return short;
}
function lineIndex(ids,world){return lineup(ids,world).score;}
function makeFreePool(team,teams,world,season,contracts,retiredOrCut){
 const owned=allOwned(teams);
 const free=[...world.values()].filter(p=>p.active&&p.known>0&&p.price>0&&!owned.has(p.id)&&!retiredOrCut.has(p.id));
 // Keep the cheap tail and a few high-value choices per position: nontrivial replacements
 // but reduce O(nPlayers * all candidate cuts) from >1000 to <=90 per team.
 const options=[];
 for(const pos of POS){
  const a=free.filter(p=>p.pos===pos);
  const cheap=[...a].sort((x,y)=>x.price-y.price||x.id.localeCompare(y.id)).slice(0,6);
  const value=[...a].sort((x,y)=>(y.known/(2+y.price/1e6))-(x.known/(2+x.price/1e6))||x.id.localeCompare(y.id)).slice(0,4);
  const high=[...a].sort((x,y)=>y.known-x.known||x.id.localeCompare(y.id)).slice(0,2);
  options.push(...cheap,...value,...high);
 }
 const unique=new Map(options.map(p=>[p.id,p]));
 return [...unique.values()];
}
function runSettlement(team,teams,world,cap,year,slope,guarantee,contracts,dead,cutPool,ops){
 const before=dueFor(team,year,slope,contracts,dead);
 const startIndex=lineIndex(team.players,world);
 const events=[];
 // Market and ownership remain unchanged within a team's settlement except for
 // that same team's own cuts/adds. Pre-rank FA alternatives once per team.
 const stableFreePool=makeFreePool(team,teams,world,year,contracts,cutPool);
 let step=0;
 const maxMoves=90;
 function isLegal(){
  const used=dueFor(team,year,slope,contracts,dead);
  return {used:used.total,capLegal:used.total<=cap+1,slotsLegal:coverage(team.players,world)&&team.players.length<=40,
   positionsMissing:coverageShort(team.players,world),count:team.players.length};
 }
 let state=isLegal();
 while(!(state.capLegal&&state.slotsLegal)&&step<maxMoves){
  const cost=dueFor(team,year,slope,contracts,dead);
  const beforeIdx=lineIndex(team.players,world);
  const priorShort=coverageShort(team.players,world);
  const currentOwned=allOwned(teams);
  const freePool=stableFreePool.filter(p=>!currentOwned.has(p.id)&&!cutPool.has(p.id));
  const choices=[];
  for(let i=0;i<team.players.length;i++){
   const out=team.players[i],existing=contracts.get(out),op=world.get(out);
   assert2(!!existing,'missing contract '+out);
   const oldAnnual=annual(existing,year,slope);
   const dc=cutEntries(existing,year,slope,guarantee);
   const currentGuaranteed=dc.find(x=>x.year===year)?.amount||0;
   const retainedFuture=dc.filter(x=>x.year>year).reduce((a,x)=>a+x.amount,0);
   const remain=team.players.filter((_,k)=>k!==i);
   const allowed=(incoming)=>{
    const newPlayers=incoming?[...remain,incoming.id]:remain;
    if(newPlayers.length>40)return;
    const short=coverageShort(newPlayers,world);
    if(priorShort===0&&short>0)return;
    if(priorShort>0&&short>=priorShort)return;
    const newAnnual=incoming?incoming.price:0;
    const relief=oldAnnual-currentGuaranteed-newAnnual;
    if(cost.total>cap+1&&relief<=1&&priorShort===0)return;
    if(cost.total>cap+1&&relief<0&&priorShort>0)return;
    const quality=lineIndex(newPlayers,world);
    const loss=priorShort===0?Math.max(0,beforeIdx-quality):Math.max(0,(quality||0)-beforeIdx)*-1;
    const reliefM=relief/1e6;
    const neededM=Math.max(0,(cost.total-cap)/1e6);
    let utility;
    if(priorShort>0){
      utility=1000*(priorShort-short)+reliefM*.4-Math.max(0,loss)*1.5;
    }else{
      // Favor cheap non-starter releases, but allow a larger single cut if required.
      utility=reliefM/(1+Math.max(0,loss)*2.7)+Math.min(Math.max(0,reliefM),neededM)*.025-
       retainedFuture/1e7-Math.max(0,loss)*.06;
      if(!op.active)utility+=60;
    }
    if(!Number.isFinite(utility))return;
    choices.push({out,incoming:incoming?.id||null,relief,loss,
      utility,remainingDeadYear:currentGuaranteed,remainingDeadFuture:retainedFuture,
      oldAnnual,newAnnual,currentShort:short});
   };
   allowed(null);
   const removalAlreadyLegal=remain.length>=20&&coverage(remain,world);
   // First test high-salary, immediately free cuts. A simultaneous FA replacement
   // matters chiefly at the positional/20-slot boundary; reduce combinatorial cost.
   if(freePool.length && (!removalAlreadyLegal || priorShort>0 || team.players.length<=22)){
    for(const p of freePool){
     if(p.id===out)continue;
     allowed(p);
    }
   }
  }
  choices.sort((a,b)=>b.utility-a.utility||b.relief-a.relief||a.out.localeCompare(b.out)||String(a.incoming).localeCompare(String(b.incoming)));
  if(!choices.length)break;
  const best=choices[0],prev=dueFor(team,year,slope,contracts,dead),outContract=contracts.get(best.out);
  const newDead=cutEntries(outContract,year,slope,guarantee);
  team.players=team.players.filter(id=>id!==best.out);
  contracts.delete(best.out);cutPool.add(best.out);
  dead.push(...newDead);ops.cuts++;
  if(best.incoming){
   const p=world.get(best.incoming);
   assert2(!allOwned(teams).has(p.id),'free player ownership collision');
   const signed=contract(p.id,team.id,year,p.year===1?'rookie':'veteran',p.price);
   contracts.set(p.id,signed);team.players.push(p.id);ops.replacements++;
  }
  step++;
  const newCost=dueFor(team,year,slope,contracts,dead);
  assert2(prev.total-newCost.total===best.relief,'net salary relief mismatch');
  assert2(new Set(team.players).size===team.players.length,'duplicate team ownership');
  events.push({step,playerCut:best.out,pos:opPos(world,best.out),year,age:year-outContract.start+1,
   contractBase:outContract.base,fullScheduledCurrentSalary:best.oldAnnual,
   retainedDeadCurrent:best.remainingDeadYear,retainedDeadFuture:best.remainingDeadFuture,
   salaryReliefCurrent:best.relief,
   replacement:best.incoming,replacementSignedFirstYearSalary:best.newAnnual,
   afterCapUsed:newCost.total,afterRosterSize:team.players.length,
   afterLineupQuality:lineIndex(team.players,world)});
  state=isLegal();
 }
 const final=dueFor(team,year,slope,contracts,dead);
 return {team:team.id,startUsed:before.total,startIndex,afterUsed:final.total,activeUsed:final.active,deadUsed:final.dead,
  endIndex:lineIndex(team.players,world),teamOverCapDollars:Math.max(0,final.total-cap),legal:state.capLegal&&state.slotsLegal,
  rosterSize:team.players.length,rosterCover:state.slotsLegal,missingPositions:state.positionsMissing,
  eventCount:events.length,events,uncuredCapDollars:Math.max(0,final.total-cap)};
}
function opPos(world,id){return world.get(id)?.pos||'UNKNOWN';}
function futureCommitments(contracts,dead,year,slope,guarantee){
 const byYear={};
 for(let y=year;y<=2031;y++){
  let active=0,deadDue=0,minimumAllCut=0;
  for(const c of contracts.values())if(c.start<=y&&c.end>=y){
   active+=annual(c,y,slope);
   if(c.start<=year&&year<=c.end){
     minimumAllCut+=dollars(annual(c,y,slope)*guarantee[y-c.start]);
   }
  }
  for(const e of dead)if(e.year===y){deadDue+=e.amount;minimumAllCut+=e.amount;}
  byYear[y]={active,dead:deadDue,total:active+deadDue,guaranteedIfAllActiveReleasedNow:minimumAllCut};
 }
 return byYear;
}
function simulateContracts(csv,{seeds=[11,29,47],slopes=[0,.05,.10],shocks=[0,-.1,-.2],guarantees=[[1,.5,.25],[1,1,1]],supply=30}={}){
 const scenarios=[],errors=[];
 for(const seed of seeds){
  const start=startWorld(csv,seed);
  const futureEvents=new Map();
  // Build a single paired 2027 legal cohort from the ORIGINAL CP6k engine.
  const initial=cloneStart(start,seed),world0=initial.world,teams0=initial.teams;
  teams0[0].passive=false;
  const ops0={mandatoryCuts:0,repairSwaps:0,optionalSwaps:0,retirementExits:0,emergencyAdds:0};
  const first=newRookies(world0,seed,1,supply,start.cap),cap0=capFor(world0);
  const preScore=teams0.map(t=>lineIndex(t.players,world0));
  if(!settleRetired(teams0,world0,cap0,ops0))throw Error('2027 pre-draft holes');
  draft(teams0,world0,first.draftable,preScore,seed,1);
  if(!settleRetired(teams0,world0,cap0,ops0))throw Error('2027 post-draft holes');
  for(const t of teams0)if(!repairTeam(t,world0,teams0,cap0,ops0))throw Error('2027 cap repair failed');
  for(const t of teams0)upgradeFA(t,world0,teams0,cap0,ops0,t.id===0?8:2);
  assert2(validate(teams0,world0,cap0).allLegal,'2027 base must be six-team legal');
  const firstContract=new Map();
  for(const t of teams0)for(const id of t.players){
   const p=world0.get(id);
   firstContract.set(id,contract(id,t.id,2027,p.year===1?'rookie':'veteran',p.price));
  }
  assert2(firstContract.size===teams0.reduce((n,t)=>n+t.players.length,0),'2027 initial ownership unique');
  const rootState={world:world0,teams:teams0,contracts:firstContract,cap:cap0};
  for(const slope of slopes)for(const shock of shocks)for(const guarantee of guarantees){
   let world=new Map([...rootState.world].map(([id,p])=>[id,{...p,h:[...p.h]}]));
   let teams=rootState.teams.map(t=>({...t,players:[...t.players],style:{...t.style}}));
   let contracts=new Map([...rootState.contracts].map(([id,c])=>[id,{...c}]));
   let dead=[],cutPool=new Set(),prevCap=cap0,lastScores=teams.map(t=>lineIndex(t.players,world)),failed=false;
   const history=[{year:2027,cap:cap0,preLegal:true,legal:true,
     leagueTotalDue:teams.reduce((a,t)=>a+dueFor(t,2027,slope,contracts,dead).total,0),
     teamStates:teams.map(t=>({team:t.id,used:dueFor(t,2027,slope,contracts,dead).total,roster:t.players.length})),
     events:[],contractBook:futureCommitments(contracts,dead,2027,slope,guarantee)}];
   const counts={cuts:0,replacements:0,draftSignings:0,retireeCuts:0};
   for(const year of [2028,2029]){
    // Development happens AFTER prior-year completed lineup. Uses same exogenous
    // seed and player market future as CP6k, but contract ownership can diverge.
    seasonalDevelopment(world,seed,year-2027);
    applyDynamicSalary(world,prevCap);
    const newPlayers=newRookies(world,seed,year-2026,supply,prevCap);
    const capBase=capFor(world),cap=dollars(capBase*(1+shock));
    assert2(cap>0,'invalid cap');
    // Six team draft order from previous year's observed performance. This is
    // a research heuristic, not a result of real future wins/standings.
    const beforeDraft=allOwned(teams);
    draft(teams,world,newPlayers.draftable,lastScores,seed,year-2026);
    for(const t of teams)for(const id of t.players)if(!beforeDraft.has(id)){
     const p=world.get(id);
     assert2(p.year===1,'expected only newly drafted rookies');
     contracts.set(id,contract(id,t.id,year,'rookie',p.price));counts.draftSignings++;
    }
    const live=allOwned(teams);
    assert2(live.size===teams.reduce((a,t)=>a+t.players.length,0),'all owners distinct post draft');
    const marketCapBeforeCut=teams.map(t=>dueFor(t,year,slope,contracts,dead));
    const operator={cuts:0,replacements:0};
    const order=teams.map(t=>t.id).sort((a,b)=> ((a+seed+year)%6)-((b+seed+year)%6));
    const settlement=[];
    for(const teamId of order){
     const t=teams.find(u=>u.id===teamId);
     const r=runSettlement(t,teams,world,cap,year,slope,guarantee,contracts,dead,cutPool,operator);
     settlement.push(r);
    }
    counts.cuts+=operator.cuts;counts.replacements+=operator.replacements;
    // With no real voluntary buyer/waiver claim in this model, every Cut stays
    // on the old owner as recorded by its actual future-year guarantee schedule.
    const owners=allOwned(teams);
    assert2(owners.size===teams.reduce((a,t)=>a+t.players.length,0),'multiple owners');
    const allLegal=settlement.every(s=>s.legal),finalByTeam=teams.map(t=>dueFor(t,year,slope,contracts,dead));
    const leagueTotal=finalByTeam.reduce((a,b)=>a+b.total,0);
    const hardFloor=futureCommitments(contracts,dead,year,slope,guarantee)[year].guaranteedIfAllActiveReleasedNow;
    const book=futureCommitments(contracts,dead,year,slope,guarantee);
    const row={year,cap,baseMarketCap:capBase,shock,
     prevTeamOverCount:marketCapBeforeCut.filter(q=>q.total>cap).length,
     capOverAfter:finalByTeam.filter(q=>q.total>cap).length,legal:allLegal,
     leagueTotalDue:leagueTotal,leagueTotalCap:cap*6,
     ligaHardGapAfter:Math.max(0,leagueTotal-6*cap),
     structuralGuaranteedFloor:hardFloor,
     structuralHardGapAfterAllCut:Math.max(0,hardFloor-6*cap),
     totalDeadDue:finalByTeam.reduce((a,b)=>a+b.dead,0),
     deadByTeam:finalByTeam.map((q,i)=>({team:i,dead:q.dead})),
     futureDead:book,
     teamStates:settlement.sort((a,b)=>a.team-b.team),
     events:settlement.flatMap(x=>x.events.map(e=>({team:x.team,...e}))),
     draftedNewRookies:30,
     newRosterOwners:teams.map(t=>t.players.length)};
    history.push(row);
    if(!allLegal){failed=true;break;}
    lastScores=teams.map(t=>lineIndex(t.players,world));
    prevCap=capBase;
   }
   const key=guarantee.join('/');
   scenarios.push({seed,slope,shock,guarantee:key,fullGuarantee:guarantee[1]===1,
    status:failed?'failed':'settled',years:history,counters:counts,
    finalContractCount:contracts.size,finalUnclaimedCutCount:cutPool.size,
    finalDeadEntries:dead.length,finalFutureDead:history.at(-1).futureDead||history.at(-1).contractBook});
  }
 }
 const byGuarantee={};
 for(const g of guarantees){
  const key=g.join('/'),rs=scenarios.filter(x=>x.guarantee===key);
  byGuarantee[key]={total:rs.length,fullyLegal:rs.filter(x=>x.status==='settled').length,
   failing:rs.filter(x=>x.status==='failed').length,
   cuts:rs.reduce((a,x)=>a+x.counters.cuts,0),
   replacements:rs.reduce((a,x)=>a+x.counters.replacements,0),
   year2029Legal:rs.filter(x=>x.years.some(y=>y.year===2029&&y.legal)).length};
 }
 return {schema:'cp6o-contract-cut-recovery-v0',asOf:'2026-11-22',
  cp6kFrozenSourceBlob:'8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c',
  sourceCsvBlob:'96ef8deac5930ffc3dc84dbf12cbbf4719c58489',
  policy:{strategy:'sequential greedily cap-repair teams after mandatory 5 rookie-pick contracts/team; avoid losing projected lineup quality, cheaper unowned FA signings on 3Y schedule',
   rookies:'Year1/Year2/Year3 100/125/150%; signed at projected pick salary every draft year',
   veterans:'100% / (100+s)% / (100+2s)% of signing-year price; existing old players synthetic 2027 newly signed 3Y',
   release:'all cuts at annual preseason settlement; only guaranteed fraction due, recorded per year until original expiration; not transferable without a documented real buyer',
   noClaims:'14-day claim window assumed expired, no willing buyer observed, no waiver of retained salary',
   fullSalary:true,cap:'CP6k top120/6 price market (includes rookie contract values, not truly separate MarketValue)',
   threeYearAnnualCap:'2027 unchanged; 2028 and 2029 base market multiplied by (1+shock), not cumulative; same exogenous NFL player performance for paired worlds',
   signing:'all 30 rookie draft selections per year are treated as automatically signed; 100% first-year guarantee; no 14d cancel-for-free option',
   freeAgent:'signs 3Y at current performance market price; cannot reacquire cut player as fresh 3Y under old dead-cap; no actual free agent bids, authorization or buyer offers',
   offseasonOnly:'no weekly partial salary, no midseason cuts; current year 100% for players signed in current year',
   allTeam:'all 6 managers, up to 40 players, minimum 20 research occupancy, CP6k fixed slot/position counts',
   exclusions:'no accurate historical legacy contract vintages, real NFL 2027+, IR/Taxi, approved picks, claims, trades, competing FA bids, cap-independent rookie market value or hindsight optimization',
   noHiddenSanction:'failure when no candidate bundle legalizes team; does not invent auto-cut, loan or commissioner action'},
  summary:{scenarioCount:scenarios.length,byGuarantee},scenarios};
}
export {simulateContracts};
const self=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===self){
 const root=path.resolve(path.dirname(self),'../../../..');
 const csv=readFileSync(path.join(root,'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv'),'utf8');
 const r=simulateContracts(csv);
 console.log(JSON.stringify(process.argv.includes('--json')?r:{summary:r.summary,selected:r.scenarios.filter(x=>x.shock===-.2&&x.slope===.1).map(x=>({seed:x.seed,guarantee:x.guarantee,status:x.status,counts:x.counters,annual:x.years.map(y=>({year:y.year,cap_m:+(y.cap/1e6).toFixed(3),legal:y.legal,cut:y.events.length,leagueTotalDue_m:+(y.leagueTotalDue/1e6).toFixed(3),dead_m:+((y.totalDeadDue||0)/1e6).toFixed(3)}))}))},null,2));
}
