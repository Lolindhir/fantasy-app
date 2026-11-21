#!/usr/bin/env node
/**
 * CP6j: one-season, full-holding-cost, exact-occupancy sensitivity.
 * Research only; not a production Salary or league-rule implementation.
 * Usage: node cp6j_full_cost_depth.mjs <2026-10-05-salary-simulation-players.csv>
 * The search yields attainable FEASIBLE lower bounds, never proven maxima.
 * Archive snapshot: 2026-10-05. Previous-cap anchor is an explicitly
 * assumed historical reference, not a validated 2027+ cap forecast.
 */
import { readFileSync } from 'node:fs';

const filename=process.argv[2];
if(!filename) throw new Error('Usage: node cp6j_full_cost_depth.mjs <archive.csv>');
const input=readFileSync(filename,'utf8').trim().split(/\r?\n/);
const fields=input.shift().split(';');
const rows=input.map(line=>Object.fromEntries(line.split(';').map((value,i)=>[fields[i],value])));
const positions=['QB','RB','WR','TE','K'];
const required={QB:2,RB:2,WR:2,TE:2,K:1};
const prevCapAnchor=434255984;
const profileDefinitions=[
  ['13-only',13,0],
  ['20-quality0',20,0],['20-quality3',20,3],['20-quality5',20,5],
  ['20-quality8',20,8],['30-quality0',30,0],['30-quality3',30,3],
  ['30-quality5',30,5],['35-quality3',35,3],['40-quality3',40,3],
];
const roundDollar=x=>Math.floor(x+0.5);
const minimumPercent=year=>year<=1?.0025:year===2?.003:year===3?.0035:year===4?.004:year<=7?.0045:.005;
function salaryDollars(row,kind){
  const P=Number(kind==='published'?row.salary_published:row.salary_I_ohne_base_minimum);
  if(!Number.isFinite(P)||P<0) throw new Error('Invalid salary for '+row.id);
  if(kind!=='criticality_plus_floor')return P;
  const year=Number(row.year);
  if(!Number.isInteger(year)||year<1) throw new Error('Unknown contract year '+row.id);
  const M=roundDollar(prevCapAnchor*minimumPercent(year));
  if(year<=3)return Math.max(P,M); // archived 3Y rookie contracts, no extra 50% addition
  return Math.max(P,roundDollar(M+.5*P));
}
const sourcePlayers=rows.filter(row=>positions.includes(row.position)&&row.nfl_team!=='FA');
if(new Set(rows.map(row=>row.id)).size!==rows.length)throw new Error('Duplicate archive player ID');
if(!sourcePlayers.some(row=>Number(row.performance_3y)===0))throw new Error('Unexpected historical quality population');
const output={as_of:'2026-10-05',input_rows:rows.length,eligible_pool:sourcePlayers.length,
  previous_cap_anchor_dollars:prevCapAnchor,scenario_price_basis:{
    published:'salary_published, archived actual salary',
    criticality_without_floor:'salary_I_ohne_base_minimum, archived 3Y rookie overlay',
    criticality_plus_floor:'same rookie dollars, plus conceptual 50%-sliding minimum on veterans',
  },assumptions:{
    cap:'sum of 120 highest player salaries from entire archive / six; f=1.00',
    scoring:'sum of archived performance_3y for the 13 modeled starters',
    starter_slots:'2 QB, 2 RB, 2 WR, 2 TE, 4 RB/WR/TE FLEX, 1 K',
    reserve_slots:'for roster size >=18: 1 additional QB/RB/WR/TE/K each, then RB/WR/TE; cheapest qualifying reserves',
    quality_threshold:'all selected reserves have performance_3y >= profile threshold; not an availability or NFL-starting-role assertion',
    roster_sizes:'exact occupied counts for sensitivity, NOT mandatory roster sizes under proposed max 20/30/35/40',
    excluded:'injury, bye scheduling, reserve/IR/taxi, transaction/Dead Cap/borrowing, six-manager market, future years',
    search:'10,001 deterministic Lagrange shadow prices and up to 7 single-player improvements; no exact optimality certificate'
  },worlds:{}};
for(const [kind,label] of [['published','published'],['criticality_without_floor','criticality_without_floor'],['criticality_plus_floor','criticality_plus_floor']]){
  const market=sourcePlayers.map(row=>({id:row.id,name:row.name,position:row.position,index:Number(row.performance_3y),cost_m:salaryDollars(row,kind)/1e6}));
  if(market.some(p=>!Number.isFinite(p.index)))throw new Error('Invalid quality');
  const startEligible=market.filter(p=>p.index>0);
  const cap_m=rows.map(row=>salaryDollars(row,kind)).sort((a,b)=>b-a).slice(0,120).reduce((a,b)=>a+b,0)/6e6;
  const groups=Object.fromEntries(positions.map(pos=>[pos,startEligible.filter(p=>p.position===pos)]));
  const reservesByThreshold={};
  for(const threshold of [0,3,5,8]){
    const qualifying=market.filter(p=>p.index>=threshold);
    const sortedByCost=(a,b)=>a.cost_m-b.cost_m||a.id.localeCompare(b.id);
    const byPosition=Object.fromEntries(positions.map(pos=>[pos,qualifying.filter(p=>p.position===pos).sort(sortedByCost)]));
    byPosition.FLEX=qualifying.filter(p=>['RB','WR','TE'].includes(p.position)).sort(sortedByCost);
    reservesByThreshold[threshold]=byPosition;
  }
  function fillBench(starters,size,quality){
    const ids=new Set(starters.map(p=>p.id));
    let cost_m=starters.reduce((sum,p)=>sum+p.cost_m,0);
    if(size===13)return {bench:[],cost_m};
    if(size<18)throw new Error('Unsupported roster size');
    const bench=[];
    const take=pool=>{const player=pool.find(p=>!ids.has(p.id));if(player){ids.add(player.id);bench.push(player);cost_m+=player.cost_m;}return Boolean(player);};
    const b=reservesByThreshold[quality];
    for(const pos of positions)if(!take(b[pos]))return null;
    for(let i=0;i<size-18;i++)if(!take(b.FLEX))return null;
    return {bench,cost_m};
  }
  const best=Object.fromEntries(profileDefinitions.map(([profile])=>[profile,null]));
  const unique=new Set();
  for(let t=0;t<=10000;t++){
    const lambda=t/10000,ids=new Set(),starters=[];
    const order=(a,b)=>(b.index-lambda*b.cost_m)-(a.index-lambda*a.cost_m)||a.id.localeCompare(b.id);
    for(const pos of positions)for(const p of [...groups[pos]].sort(order).slice(0,required[pos])){starters.push(p);ids.add(p.id);}
    starters.push(...startEligible.filter(p=>!['QB','K'].includes(p.position)&&!ids.has(p.id)).sort(order).slice(0,4));
    if(starters.length!==13||new Set(starters.map(p=>p.id)).size!==13)throw new Error('Bad starter selection');
    const key=starters.map(p=>p.id).sort().join(',');
    if(unique.has(key))continue;unique.add(key);
    const score=starters.reduce((sum,p)=>sum+p.index,0);
    for(const [profile,size,quality] of profileDefinitions){
      const coverage=fillBench(starters,size,quality);
      if(!coverage||coverage.cost_m>cap_m+1e-8)continue;
      const old=best[profile];
      if(!old||score>old.score+1e-9||(Math.abs(score-old.score)<1e-8&&coverage.cost_m<old.cost_m))
        best[profile]={starters,score,cost_m:coverage.cost_m,bench:coverage.bench,lambda};
    }
  }
  for(const [profile,size,quality] of profileDefinitions){
    let current=best[profile];
    if(!current)continue;
    for(let iter=0;iter<7;iter++){
      const counts=Object.fromEntries(positions.map(pos=>[pos,current.starters.filter(p=>p.position===pos).length]));
      const ids=new Set(current.starters.map(p=>p.id));
      let improvement=null;
      for(let i=0;i<13;i++){
        const departing=current.starters[i];
        for(const arriving of startEligible){
          if(ids.has(arriving.id)||arriving.index<=departing.index+1e-8)continue;
          if(departing.position!==arriving.position&&counts[departing.position]<=required[departing.position])continue;
          if((departing.position==='QB')!==(arriving.position==='QB')||(departing.position==='K')!==(arriving.position==='K'))continue;
          const starters=current.starters.slice();starters[i]=arriving;
          const coverage=fillBench(starters,size,quality);
          if(!coverage||coverage.cost_m>cap_m+1e-8)continue;
          const score=current.score-departing.index+arriving.index;
          if(!improvement||score>improvement.score+1e-9||(Math.abs(score-improvement.score)<1e-8&&coverage.cost_m<improvement.cost_m))
            improvement={starters,score,cost_m:coverage.cost_m,bench:coverage.bench,lambda:current.lambda};
        }
      }
      if(!improvement)break;
      current=improvement;
    }
    best[profile]=current;
  }
  const profiles={};
  for(const [profile,size,quality] of profileDefinitions){
    const candidate=best[profile];
    if(!candidate){profiles[profile]=null;continue;}
    const full=[...candidate.starters,...candidate.bench];
    if(full.length!==size||new Set(full.map(x=>x.id)).size!==size)throw new Error('Roster duplicate/count '+profile);
    if(full.reduce((sum,p)=>sum+p.cost_m,0)>cap_m+1e-7)throw new Error('Salary exceeds Cap '+profile);
    for(const pos of positions)if(candidate.starters.filter(p=>p.position===pos).length<required[pos])throw new Error('Invalid starter slot');
    if(candidate.starters.filter(p=>p.position==='QB').length!==2||candidate.starters.filter(p=>p.position==='K').length!==1)throw new Error('Invalid FLEX');
    if(candidate.bench.some(p=>p.index<quality))throw new Error('Reserve quality mismatch');
    profiles[profile]={score:+candidate.score.toFixed(3),cost_m:+candidate.cost_m.toFixed(3),
      headroom_m:+(cap_m-candidate.cost_m).toFixed(3),
      reserve_cost_m:+candidate.bench.reduce((sum,p)=>sum+p.cost_m,0).toFixed(3),
      reserve_quality_sum:+candidate.bench.reduce((sum,p)=>sum+p.index,0).toFixed(3),
      starter_ids:candidate.starters.map(p=>p.id),reserve_ids:candidate.bench.map(p=>p.id),
      shadow_price: candidate.lambda};
  }
  output.worlds[label]={cap_m:+cap_m.toFixed(5),distinct_starter_candidates:unique.size,profiles};
}
console.log(JSON.stringify(output,null,2));
