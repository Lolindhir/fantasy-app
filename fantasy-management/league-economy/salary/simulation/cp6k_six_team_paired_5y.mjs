#!/usr/bin/env node
/**
 * CP6k (2026-11-19) – six-team, full-salary, paired 5-year prototype.
 * Research-only synthetic experiment, NOT a legal 2027 price forecast, policy or upper bound.
 * Usage from repository root:
 *   node fantasy-management/league-economy/salary/simulation/cp6k_six_team_paired_5y.mjs
 * Optional: --json (details), --seeds 11,29,47 --supply 0,30,50
 * One frozen historical October 2026 player CSV. No read/write of productive data.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

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
  if(team.players.length>40)throw Error('Research capacity exceeded during draft');
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
  const p=ps.find(p=>heldCost(team.players,world)+p.price<=cap+1);
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
 let cap=capFor(world),prevCap=ANCHOR,lastScores=teams.map(t=>lineup(t.players,world).score);
 const years=[],failures=[];
 const ops={mandatoryCuts:0,repairSwaps:0,optionalSwaps:0,retirementExits:0,emergencyAdds:0};
 for(let season=1;season<=5;season++){
  if(season>1){applyDynamicSalary(world,prevCap);cap=capFor(world);}
  const salaryCap=cap;
  const rookie=newRookies(world,seed,season,supply,prevCap);
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
  const observedScores=teams.map(team=>lineup(team.players,world,'realized').score);
  const topOpponent=Math.max(...observedScores.slice(1));
  years.push({year:2026+season,cap_m:salaryCap/1e6,preLegal:pre.allLegal,
   index:+observedScores[0].toFixed(3),predicted:+predictedScores[0].toFixed(3),
   bestOpponent:+topOpponent.toFixed(3),gapToBest:+(observedScores[0]-topOpponent).toFixed(3),
   relativeAllstar:null,roster:teams[0].players.length,capUse_m:heldCost(teams[0].players,world)/1e6,
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
export function simulate(csv,{seeds=[11,29,47],supplies=[0,30,50]}={}){
 const all=[];
 for(const seed of seeds){
  const initial=startWorld(csv,seed);
  for(const supply of supplies)for(const regime of ['passive','active']){
   all.push(simulateOne(initial,seed,supply,regime));
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
const file=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===file){
 const root=path.resolve(path.dirname(file),'../../../..');
 const csv=readFileSync(path.join(root,'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv'),'utf8');
 const arg=(key,fallback)=>{const i=process.argv.indexOf(key);return i<0?fallback:process.argv[i+1].split(',').map(Number);};
 const result=simulate(csv,{seeds:arg('--seeds',[11,29,47]),supplies:arg('--supply',[0,30,50])});
 console.log(JSON.stringify(process.argv.includes('--json')?result:{notes:result.notes,pairs:result.pairs},null,2));
}
