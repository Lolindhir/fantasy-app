#!/usr/bin/env node
/**
 * CP6m (2026-11-20) cap windows strategy frontier, RESEARCH ONLY.
 * Tests 2026-10-05 CP6k full-salary six-owner starting world under:
 * A: annual Cap Deadline (in-season hypothetical post-transfer overhang permitted);
 * B: every complete 1-for-1 or 2-for-2 trade bundle must be immediately under cap.
 * Neither regime implies real buyer consent, picks, 2027 settlement, market prices,
 * injury/bye/weekly performance, C-add retained salary or real historical 2026 ownership.
 * Exact CP6k model excerpt frozen from Blob 8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c, compare reference indices.
 * Usage: node fantasy-management/league-economy/salary/simulation/cp6m_cap_window_swap_frontier.mjs [--json]
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

const expected=new Map([[11,208.508],[29,208.667],[47,208.190]]);
function assert(x,label){if(!x)throw Error(label);}
function checkPositions(team,removed,incoming,world){
 const count=Object.fromEntries(POS.map(x=>[x,0]));
 for(const id of team.players)count[world.get(id).pos]++;
 for(const id of removed)count[world.get(id).pos]--;
 for(const id of incoming)count[world.get(id).pos]++;
 return POS.every(x=>count[x]>=BENCH[x])&&count.RB+count.WR+count.TE>=13;
}
function pairedCombos(ids,arity){
 const out=[];for(let i=0;i<ids.length;i++){
  if(arity===1)out.push([ids[i]]);
  if(arity===2)for(let j=i+1;j<ids.length;j++)out.push([ids[i],ids[j]]);
 }
 return out;
}
function toM(v){return +((v||0)/1e6).toFixed(6);}
function gain3(v){return +v.toFixed(3);}
function findFrontier(csv,seeds=[11,29,47]){
 const result=[];
 for(const seed of seeds){
  const {world,teams,cap}=startWorld(csv,seed),buyer=teams[0];
  const initial=lineup(buyer.players,world).score,buyerBefore=heldCost(buyer.players,world);
  assert(Math.abs(initial-expected.get(seed))<.0001,"CP6k starting index changed seed "+seed);
  assert(Math.abs(cap-489862209)<=1,"CP6k starting cap changed");
  assert(teams.every(t=>legal(t,world,cap)),"Nonlegal starting team");
  const cuts=[];
  for(const n of [1,2]){
   const groups={arity:n,evaluatedAllCoverageLegal:0,potentialBuyerImprovements:0,
     permanentCompliantBuyerImprovements:0,annualBuyerImprovementsThatWouldOverCap:0,
     buyerGainAtLeast2:0,permanentBuyerGainAtLeast2:0,mutuallyPositive:0,permanentMutuallyPositive:0,
     bestAnnual:null,bestPermanent:null};
   for(const seller of teams.slice(1)){
    const sellerBefore=heldCost(seller.players,world),sellerIndex=lineup(seller.players,world).score;
    const sellerPairs=pairedCombos(seller.players,n);
    for(const out of pairedCombos(buyer.players,n)){
     const outCost=out.reduce((s,id)=>s+world.get(id).price,0);
     for(const incoming of sellerPairs){
      if(!checkPositions(buyer,out,incoming,world)||!checkPositions(seller,incoming,out,world))continue;
      const diff=incoming.reduce((s,id)=>s+world.get(id).price,0)-outCost;
      const usedB=buyerBefore+diff,usedS=sellerBefore-diff;
      const newB=buyer.players.filter(id=>!out.includes(id)).concat(incoming);
      const newS=seller.players.filter(id=>!incoming.includes(id)).concat(out);
      const bGain=lineup(newB,world).score-initial;
      const sGain=lineup(newS,world).score-sellerIndex;
      const legalB=usedB<=cap+1&&usedS<=cap+1;
      groups.evaluatedAllCoverageLegal++;
      if(bGain>.1){
       groups.potentialBuyerImprovements++;
       if(legalB)groups.permanentCompliantBuyerImprovements++;
       else groups.annualBuyerImprovementsThatWouldOverCap++;
       if(bGain>=2){groups.buyerGainAtLeast2++;if(legalB)groups.permanentBuyerGainAtLeast2++;}
       if(sGain>.1){groups.mutuallyPositive++;if(legalB)groups.permanentMutuallyPositive++;}
      }
      const entry={sellerTeam:seller.id,buyerGains:gain3(bGain),sellerGains:gain3(sGain),
       buyerSends:out,buyerGets:incoming,incrementalBuyerSalary_m:toM(diff),
       buyerAfterCost_m:toM(usedB),sellerAfterCost_m:toM(usedS),
       buyerOverCap_m:toM(Math.max(0,usedB-cap)),sellerOverCap_m:toM(Math.max(0,usedS-cap))};
      if(bGain>0.1&&(!groups.bestAnnual||bGain>groups.bestAnnual.buyerGains+.00001))groups.bestAnnual=entry;
      if(legalB&&bGain>.1&&(!groups.bestPermanent||bGain>groups.bestPermanent.buyerGains+.00001))groups.bestPermanent=entry;
     }
    }
   }
   for(const record of [groups.bestAnnual,groups.bestPermanent]){
    if(!record)continue;
    const seller=teams.find(t=>t.id===record.sellerTeam);
    const newB=buyer.players.filter(id=>!record.buyerSends.includes(id)).concat(record.buyerGets);
    const newS=seller.players.filter(id=>!record.buyerGets.includes(id)).concat(record.buyerSends);
    assert(coverage(newB,world)&&coverage(newS,world),"Best example not slot/coverage legal");
   }
   cuts.push(groups);
  }
  result.push({seed,cap_m:toM(cap),team0StartingIndex:gain3(initial),
   team0StartingSalary_m:toM(buyerBefore),team0Headroom_m:toM(cap-buyerBefore),
   contenders:teams.map(t=>({teamId:t.id,index:gain3(lineup(t.players,world).score),salary_m:toM(heldCost(t.players,world))})),
   swaps:cuts});
 }
 return {schema:"cp6m-v0",asOf:"2026-10-05",sourceFrozenCp6kBlob:"8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c",
  teamCount:6,fullSalaryCost:true,capFactor:1,capTop120:true,allowedYears:2026,
  portfolio:result,distinctions:{
   A:"annual check permits in-season overcap as hypothetical trade envelope; next deadline still requires actual legal settlement",
   B:"permanent immediate cap compliance for both post-trade owners",
   tradeFilter:"Exactly one-for-one or two-for-two atomic player swaps. CP6k six-team synthetic ownership, 20-player rosters. Positional coverage and 13 slots must remain valid.",
   notModelled:"Trades not agreed, pick assets and their value absent, seller loss not compensated, no rookie or FA follow-up, no cuts/retained C-add, no future reprice or next-year settlement; maximum is restricted candidate-pair enumeration and NOT an achievable league optimum"
  }};
}
export {findFrontier};
const self=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===self){
 const root=path.resolve(path.dirname(self),'../../../..');
 const csv=readFileSync(path.join(root,"fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv"),"utf8");
 const out=findFrontier(csv);
 console.log(JSON.stringify(process.argv.includes('--json')?out:{distinctions:out.distinctions,portfolio:out.portfolio.map(s=>({seed:s.seed,cap_m:s.cap_m,startingIndex:s.team0StartingIndex,headroom_m:s.team0Headroom_m,swaps:s.swaps}))},null,2));
}
