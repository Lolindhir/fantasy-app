#!/usr/bin/env node
/**
 * CP7c: Repeated pre-cut trading across multiple synthetic NFL seasons. NOT a 5-year
 * market equilibrium or evidence of any real manager's willingness to trade.
 * P0 none, P1 50/30/15/5 retained salary, P2 contracted multiyear guarantees.
 *
 * Run: node fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createCP7bBase,lineup,coverage,annual,seasonalDevelopment,applyDynamicSalary,newRookies,draft,capFor,allOwned,contract} from '../salary/simulation/cp6r_45slot_trade_strategy.mjs';
import {cut} from './deadcap_contract_probe.mjs';
const MODES=['none','retained_cycle','guaranteed_vintage'];
const POS=['QB','RB','WR','TE','K'];
const W={all_in:{line:1.5,youth:.10,cap:.10},rebuild:{line:.70,youth:.52,cap:.14},
 reload:{line:1.1,youth:.27,cap:.14},flex:{line:.93,youth:.31,cap:.20}};
const money=x=>Math.floor(x+.5),M=1000000;
let Y=2027;
function assert(v,n){if(!v)throw Error(n);}
function clone(base){
 return {world:new Map([...base.world].map(([id,p])=>[id,{...p,h:[...p.h]}])),teams:base.teams.map(t=>({...t,players:[...t.players]})),
  contracts:new Map([...base.contracts].map(([id,c])=>[id,{...c,acquiredYear:c.start}])),
  debt:[],released:new Map(),pickedFA:new Set(),cutPlayers:new Set(),timeline:'enforce_before_reset',previousCap:base.cap};
}
function salary(contract,year=Y){return annual(contract,year,.25);}
function due(team,s,year=Y){return team.players.reduce((sum,id)=>sum+(s.contracts.has(id)?
  salary(s.contracts.get(id),year):s.world.get(id).price),0)+
  s.debt.filter(d=>d.owner===team.id&&d.year===year).reduce((sum,d)=>sum+d.amount,0);}
function futureDue(team,s,year){
 return team.players.reduce((sum,id)=>sum+(s.contracts.has(id)?
  salary(s.contracts.get(id),year):0),0)+
  s.debt.filter(d=>d.owner===team.id&&d.year===year).reduce((sum,d)=>sum+d.amount,0);
}
function u(ids,team,s,cap,year=Y){
 const line=lineup(ids,s.world);if(!line.valid)return -Infinity;
 const weight=W[team.strategy]||W.reload;const chosen=new Set(line.ids);
 const youth=ids.reduce((v,id)=>{const p=s.world.get(id);return v+(p.year<=4?(5-p.year)*Math.max(0,p.known)*.28:0);},0);
 const bench=ids.filter(id=>!chosen.has(id)).map(id=>s.world.get(id).known).sort((a,b)=>b-a).slice(0,6).reduce((a,b)=>a+b,0);
 const cash=ids.reduce((sum,id)=>sum+(s.contracts.has(id)?salary(s.contracts.get(id),year):freeAgentSalary(s,id)),0);
 const existingDebt=s.debt.filter(x=>x.owner===team.id&&x.year===year).reduce((v,x)=>v+x.amount,0);
 const total=(cash+existingDebt)/M;
 return weight.line*line.score+weight.youth*youth+bench*.055-weight.cap*total-
  Math.max(0,(cash+existingDebt-cap)/M)*.30;
}
function freePool(s,mode){const held=new Set(s.teams.flatMap(t=>t.players));
 return [...s.world.values()].filter(p=>p.active&&!held.has(p.id)&&!s.pickedFA.has(p.id)&&
  !(mode==='guaranteed_vintage'&&s.cutPlayers.has(p.id)));
}
function freeAgentSalary(s,id){return s.released.has(id)?s.released.get(id):s.world.get(id).price;}
function guarantee(c){
 if(c.kind!=='rookie'||c.draftRound==null)return [1,.5,.25];
 return c.draftRound<=2?[1,1,1]:c.draftRound<=4?[1,1,.5]:[1,.5,.25];
}
function cutQuote(s,team,id,mode,year=Y){
 const c=s.contracts.get(id);
 assert(c&&team.players.includes(id),'seller does not own '+id);
 if(c.end<year){
  // Already expired contract has zero remaining booked salary and no guarantee.
  return {mode:'none',year,annual:0,dead:{},now:0,relief:0,
   activeAfterCut:null,futureDebt:0,player:id,seller:team.id,expired:true};
 }
 const terms={};
 for(let y=year;y<=c.end;y++)terms[y]=salary(c,y);
 const player=s.world.get(id);
 if(c.pendingRenewal){const q=cut({mode:'none',year,salary:terms});
  return {...q,player:id,seller:team.id,teamTenureProxy:year-(c.acquiredYear??c.start),declined:true};}
 const effectiveMode=mode==='retained_cycle'&&s.timeline==='reset_before_enforce'?'none':mode;
 const opts={mode:effectiveMode,year,salary:terms};
 if(mode==='retained_cycle'){
  opts.tenure=Math.max(0,year-(c.acquiredYear??c.start)); // proxy, reset on transfer
  const yr=player.year;
  const minimumPercent=yr<=1?.0025:yr===2?.003:yr===3?.0035:yr===4?.004:yr<=7?.0045:.005;
  opts.floor=money(s.previousCap*minimumPercent); // same frozen archive/CP6r minimum anchor
 }else if(mode==='guaranteed_vintage'){
  opts.start=c.start;opts.guarantees=guarantee(c);
 }
 // Frozen archive 2027 contract; nominal P1 min is a synthetic price anchor.
 const q=cut(opts);
 return {...q,player:id,seller:team.id,teamTenureProxy:year-(c.acquiredYear??c.start)};
}
function alternativeCut(s,team,id,mode,cap,free){
 const old=team.players;const quote=cutQuote(s,team,id,mode);
 const samePos=free.filter(p=>p.pos===s.world.get(id).pos&&p.id!==id&&p.known>0);
 const optionsById=new Map();
 for(const sorter of [
  (a,b)=>a.price-b.price||b.known-a.known,
  (a,b)=>b.known/(1+a.price/M)-a.known/(1+b.price/M),
  (a,b)=>b.known-a.known||a.price-b.price
 ])for(const p of [...samePos].sort(sorter).slice(0,14))optionsById.set(p.id,p);
 const options=[...optionsById.values()];
 let best=null;
 const rest=old.filter(x=>x!==id);
 if(rest.length>=20&&coverage(rest,s.world)){
  const oldAnnual=salary(s.contracts.get(id)),newDue=due(team,s)-oldAnnual+quote.now;
  const w=W[team.strategy]||W.reload;
  best={player:id,replacement:null,replacementSalary:0,relief:oldAnnual-quote.now,
   quote,afterCost:newDue,afterIndex:lineup(rest,s.world).score,
   score:u(rest,team,s,cap)-w.cap*quote.now/M-w.cap*quote.futureDebt/M*.5};
 }
 for(const incoming of options){
  const next=old.map(x=>x===id?incoming.id:x);
  if(!coverage(next,s.world))continue;
  // Include same-year cash replacement plus the exact cut debt.
  const oldContract=s.contracts.get(id);
  const oldAnnual=salary(oldContract);
  const incomingPrice=freeAgentSalary(s,incoming.id);
  const newDue=due(team,s)-oldAnnual+incomingPrice+quote.now;
  const altQuality=lineup(next,s.world).score;
  const w=W[team.strategy];
  const baseline=u(next,team,s,cap);
  const dueWithoutNewDead=newDue-quote.now;
  const score=baseline-w.cap*(quote.now/M)-
   .30*(Math.max(0,(newDue-cap)/M)-Math.max(0,(dueWithoutNewDead-cap)/M))-
   .5*w.cap*(quote.futureDebt/M);
  const relief=oldAnnual-incomingPrice-quote.now;
  const cand={player:id,replacement:incoming.id,replacementSalary:incomingPrice,relief,quote,
   score,afterCost:newDue,afterIndex:altQuality};
  if(!best||cand.score>best.score+1e-8)best=cand;
 }
 return best;
}
function offerCandidates(team,s){
 const owned=team.players.map(id=>s.world.get(id));
 const selected=new Map(),add=a=>a.slice(0,8).forEach(p=>selected.set(p.id,p));
 add([...owned].sort((a,b)=>salary(s.contracts.get(b.id))-salary(s.contracts.get(a.id))));
 add([...owned].sort((a,b)=>a.known/(1+salary(s.contracts.get(a.id))/M)-
    b.known/(1+salary(s.contracts.get(b.id))/M)));
 return [...selected.values()];
}
function buyerGiveCandidates(team,s){
 const a=team.players.map(id=>s.world.get(id));
 const pick=new Map(),add=ls=>ls.slice(0,8).forEach(p=>pick.set(p.id,p));
 add([...a].sort((x,y)=>salary(s.contracts.get(x.id))-salary(s.contracts.get(y.id))));
 add([...a].sort((x,y)=>x.known-y.known));
 return [...pick.values()];
}
function tryTrades(s,mode,cap,{waitProbability=.5,maxTrades=6}={}){
 const events=[],screened={pairs:0,capBlocked:0,rosterBlocked:0,
  noMutualUtility:0,waiverWaitBlocked:0},previousOut=new Set();
 let examinedSellers=new Set();
 for(let iteration=0;iteration<maxTrades;iteration++){
  let best=null;
  const free=freePool(s,mode);
  const potential=s.teams.filter(t=>due(t,s)>cap+1);
  for(const seller of potential){
   const oldSeller=u(seller.players,seller,s,cap);
   for(const outgoing of offerCandidates(seller,s)){
    if(previousOut.has(outgoing.id))continue;
    examinedSellers.add(seller.id+':'+outgoing.id);
    const alt=alternativeCut(s,seller,outgoing.id,mode,cap,free);
    if(!alt)continue;
    const outCost=salary(s.contracts.get(outgoing.id)),sellerDue=due(seller,s);
    for(const buyer of s.teams){
     if(buyer.id===seller.id||due(buyer,s)>cap+1)continue;
     const buyerU=u(buyer.players,buyer,s,cap),oldBuyer=due(buyer,s);
     for(const incoming of buyerGiveCandidates(buyer,s)){
      if(previousOut.has(incoming.id))continue;
      screened.pairs++;
      const giveCost=salary(s.contracts.get(incoming.id));
      const sellerRelief=outCost-giveCost,buyerExtra=outCost-giveCost;
      if(sellerRelief<=0||oldBuyer+buyerExtra>cap+1){
       screened.capBlocked++;continue;
      }
      const aNew=seller.players.map(id=>id===outgoing.id?incoming.id:id);
      const bNew=buyer.players.map(id=>id===incoming.id?outgoing.id:id);
      if(!coverage(aNew,s.world)||!coverage(bNew,s.world)){
       screened.rosterBlocked++;continue;
      }
      // Full contract swap, no debt created and any existing debt remains with its owner.
      const aScore=u(aNew,seller,s,cap); // each player carries full current contract salary
      const bScore=u(bNew,buyer,s,cap);
      const sellerBenefit=aScore-alt.score;
      const buyerBenefit=bScore-buyerU;
      // Buyers could prefer post-cut WAIVER if P1 makes the released player cheaper.
      // 0<=waitProbability<=1 is a scenario sensitivity, not real behavior.
      const q=alt.quote;
      const buyerWouldBeUnderCapIfClaimed=oldBuyer+(q.activeAfterCut??outCost)<=cap+1;
      const waitPremium=mode==='retained_cycle'&&buyerWouldBeUnderCapIfClaimed?
       waitProbability*W[buyer.strategy].cap*((outCost-(q.activeAfterCut||outCost))/M):0;
      if(!(sellerBenefit>.10&&buyerBenefit>.10)){
       screened.noMutualUtility++;continue;
      }
      if(buyerBenefit<=waitPremium+.10){screened.waiverWaitBlocked++;continue;}
      const joint=Math.min(sellerBenefit,buyerBenefit)+.15*(sellerBenefit+buyerBenefit);
      if(!best||joint>best.joint+1e-8)best={seller,buyer,outgoing,incoming,
       outCost,giveCost,sellerBenefit,buyerBenefit,waitPremium,alt,oldSeller,
       sellerDue,buyerDue:oldBuyer,joint};
     }
    }
   }
  }
  if(!best)break;
  const {seller,buyer,outgoing,incoming,outCost,giveCost,alt}=best;
  const sumBefore=s.teams.reduce((v,t)=>v+due(t,s),0);
  const futureBefore=[Y+1,Y+2].map(y=>({year:y,seller:futureDue(seller,s,y),
   buyer:futureDue(buyer,s,y),sellerOutgoing:salary(s.contracts.get(outgoing.id),y),
   buyerOutgoing:salary(s.contracts.get(incoming.id),y)}));
  seller.players=seller.players.map(id=>id===outgoing.id?incoming.id:id);
  buyer.players=buyer.players.map(id=>id===incoming.id?outgoing.id:id);
  s.contracts.get(outgoing.id).owner=buyer.id;
  s.contracts.get(outgoing.id).acquiredYear=Y;
  s.contracts.get(incoming.id).owner=seller.id;
  s.contracts.get(incoming.id).acquiredYear=Y;
  const futureTransfers=futureBefore.map(x=>{
   const sAfter=futureDue(seller,s,x.year),bAfter=futureDue(buyer,s,x.year);
   assert(x.seller+x.buyer===sAfter+bAfter,'future trade salaries conserved');
   return {year:x.year,sellerBefore:x.seller,buyerBefore:x.buyer,
    sellerAfter:sAfter,buyerAfter:bAfter,
    salaryToBuyer:x.sellerOutgoing,salaryToSeller:x.buyerOutgoing,
    frozenCapStressBuyerHeadroom:cap-bAfter,
    frozenCapStressSellerHeadroom:cap-sAfter};
  });
  const afterSeller=due(seller,s),afterBuyer=due(buyer,s);
  assert(afterSeller===best.sellerDue-outCost+giveCost,'seller cost');
  assert(afterBuyer===best.buyerDue-giveCost+outCost,'buyer cost');
  assert(sumBefore===s.teams.reduce((v,t)=>v+due(t,s),0),'full league salary conservation');
  assert(coverage(seller.players,s.world)&&coverage(buyer.players,s.world),'posttrade coverage');
  assert(new Set(s.teams.flatMap(t=>t.players)).size===s.teams.reduce((v,t)=>v+t.players.length,0),'owner collision');
  previousOut.add(outgoing.id);previousOut.add(incoming.id);
  events.push({from:seller.id,to:buyer.id,playerSold:outgoing.id,playerGiven:incoming.id,
   salarySold:outCost,salaryGiven:giveCost,capReliefSeller:outCost-giveCost,
   sellerBefore:best.sellerDue,sellerAfter:afterSeller,buyerBefore:best.buyerDue,buyerAfter:afterBuyer,
   cutAlternative:alt.quote,cutReplacement:alt.replacement,
   cutAlternativeSellerRelief:alt.relief,
   sellerTradeVsCutRelief:(outCost-giveCost)-alt.relief,
   sellerUtilityVsCut:+best.sellerBenefit.toFixed(3),
   buyerUtilityVsStay:+best.buyerBenefit.toFixed(3),
   buyerWaiverWaitOpportunity:+best.waitPremium.toFixed(3),
   futureTransfers,contractBuyerFundingBeyond2027:'not established: future cap unknown',
   transactionCreatesDeadCap:0,actualHumanConsent:'unobserved',buyerPaidFullContract:true});
 }
 return {events,screened,examinedSellerPlayers:examinedSellers.size};
}
function settleCuts(s,mode,cap){
 const events=[],failed=[];let tried=0;
 for(const team of s.teams){
  for(let step=0;step<70&&(due(team,s)>cap+1||!coverage(team.players,s.world));step++){
   const pool=freePool(s,mode);
   const choices=team.players.map(id=>alternativeCut(s,team,id,mode,cap,pool)).filter(Boolean)
    .filter(x=>x.relief>0||!coverage(team.players,s.world));
   choices.sort((a,b)=>{
    const aGain=a.relief/(1+Math.max(0,lineup(team.players,s.world).score-a.afterIndex)*3),
      bGain=b.relief/(1+Math.max(0,lineup(team.players,s.world).score-b.afterIndex)*3);
    return bGain-aGain||b.relief-a.relief;
   });
   tried++;
   if(!choices.length)break;
   const b=choices[0],previous=due(team,s),oldContract=s.contracts.get(b.player);
   team.players=b.replacement?team.players.map(id=>id===b.player?b.replacement:id):team.players.filter(id=>id!==b.player);
   s.contracts.delete(b.player);
   if(b.replacement){
    const p=s.world.get(b.replacement),price=freeAgentSalary(s,p.id);
    assert(price===b.replacementSalary,'FA replacement cost');
    const c=contract(p.id,team.id,Y,p.year===1?'rookie':'veteran',price);
    c.acquiredYear=Y;c.draftRound=p.draftRound??null;s.contracts.set(p.id,c);
   }
   for(const [yr,amount] of Object.entries(b.quote.dead))if(amount>0)
    s.debt.push({owner:team.id,player:b.player,year:Number(yr),amount,signYear:oldContract.start});
   if(mode==='retained_cycle'&&b.quote.activeAfterCut!=null)s.released.set(b.player,b.quote.activeAfterCut);
   s.cutPlayers.add(b.player);
   if(b.replacement)s.pickedFA.add(b.replacement);
   assert(coverage(team.players,s.world),'postcut roster coverage');
   assert(due(team,s)===previous-b.relief,'postcut financial identity');
   events.push({team:team.id,player:b.player,replacement:b.replacement,
    oldSalary:b.quote.annual,replacementSalary:b.replacementSalary,
    deadNow:b.quote.now,deadFuture:b.quote.futureDebt,
    salaryAfterRelease:mode==='retained_cycle'?b.quote.activeAfterCut:null,
    netRelief:b.relief,afterUsed:due(team,s)});
  }
  if(due(team,s)>cap+1||!coverage(team.players,s.world))failed.push({team:team.id,overBy:Math.max(0,due(team,s)-cap),rosterLegal:coverage(team.players,s.world)});
 }
 return {events,failed,steps:tried};
}

function runOne(base,{mode,timeline,shock,seasons,wait}){
 const s=clone(base),roles=['all_in','rebuild','reload','flex','all_in','rebuild'];
 s.teams.forEach(t=>t.strategy=roles[(t.id+Math.floor(base.seed/7))%6]);
 s.timeline=timeline;s.previousCap=base.cap;let previousScores=s.teams.map(t=>lineup(t.players,s.world).score);
 const years=[];
 for(let index=0;index<seasons;index++){
  Y=2027+index;s.released.clear();s.pickedFA.clear();s.cutPlayers.clear();
  s.debt=s.debt.filter(d=>d.year>=Y);
  if(index){seasonalDevelopment(s.world,base.seed,index);applyDynamicSalary(s.world,s.previousCap);}
  const exits=[];
  for(const t of s.teams){
   for(const id of [...t.players])if(!s.world.get(id).active){
    const q=cutQuote(s,t,id,mode);
    t.players=t.players.filter(x=>x!==id);s.contracts.delete(id);s.cutPlayers.add(id);
    for(const [y,amount] of Object.entries(q.dead))if(amount>0)
     s.debt.push({owner:t.id,player:id,year:+y,amount,kind:'NFL-exit'});
    exits.push({team:t.id,id,deadNow:q.now,deadFuture:q.futureDebt});
   }
   for(const id of t.players){
    const c=s.contracts.get(id);assert(!!c,'missing owned contract');
    if(c.end>=Y)continue;
    const nc=contract(id,t.id,Y,'veteran',Math.max(1,s.world.get(id).price));
    nc.acquiredYear=c.acquiredYear??Y;nc.pendingRenewal=true;s.contracts.set(id,nc);
   }
  }
  for(const t of s.teams)for(let k=0;k<40&&!coverage(t.players,s.world);k++){
   const have=Object.fromEntries(POS.map(pos=>[pos,t.players.filter(id=>s.world.get(id).pos===pos).length]));
   const need=POS.find(pos=>have[pos] < ({QB:3,RB:3,WR:3,TE:3,K:2}[pos]));
   const pool=freePool(s,mode).filter(p=>p.known>0&&(need?p.pos===need:['RB','WR','TE'].includes(p.pos)))
    .sort((a,b)=>freeAgentSalary(s,a.id)-freeAgentSalary(s,b.id)||b.known-a.known);
   if(!pool.length||t.players.length>=45)break;
   const p=pool[0],price=freeAgentSalary(s,p.id),c=contract(p.id,t.id,Y,'veteran',price);
   c.acquiredYear=Y;s.contracts.set(p.id,c);t.players.push(p.id);
  }
  const rookies=newRookies(s.world,base.seed,Y-2026,30,s.previousCap);
  const old=allOwned(s.teams);
  draft(s.teams,s.world,rookies.draftable,previousScores,base.seed,Y-2026,s.previousCap);
  const now=allOwned(s.teams),capacity=[];
  for(const [id,owner] of old)if(!now.has(id)){
   const t=s.teams.find(x=>x.id===owner),q=cutQuote(s,{...t,players:[...t.players,id]},id,mode);
   s.contracts.delete(id);s.cutPlayers.add(id);
   for(const [y,amount] of Object.entries(q.dead))if(amount>0)
    s.debt.push({owner,player:id,year:+y,amount,kind:'draft-capacity'});
   capacity.push({team:owner,id,deadNow:q.now,deadFuture:q.futureDebt});
  }
  for(const [id,owner] of now)if(!old.has(id)){
   const p=s.world.get(id),c=contract(id,owner,Y,'rookie',p.price);
   c.draftRound=p.draftRound;c.acquiredYear=Y;s.contracts.set(id,c);
  }
  const cap=money(capFor(s.world)*(1+shock));
  const opening=s.teams.map(t=>({team:t.id,cost:due(t,s),roster:t.players.length,index:lineup(t.players,s.world).score}));
  const trade=tryTrades(s,mode,cap,{waitProbability:wait,maxTrades:6});
  const settlement=settleCuts(s,mode,cap);
  for(const c of s.contracts.values())if(c.pendingRenewal)c.pendingRenewal=false;
  const after=s.teams.map(t=>({team:t.id,cost:due(t,s),roster:t.players.length,index:lineup(t.players,s.world).score,
   legal:due(t,s)<=cap+1&&coverage(t.players,s.world)}));
  assert(allOwned(s.teams).size===s.teams.reduce((n,t)=>n+t.players.length,0),'duplicate player owner');
  const valid=settlement.failed.length===0&&after.every(t=>t.legal);
  years.push({year:Y,cap,legal:valid,opening,after,exits,capacity,
   rookieSignings:[...now].filter(([id])=>!old.has(id)).length,
   tradeCount:trade.events.length,cutCount:settlement.events.length,
   screened:trade.screened,operatorSteps:settlement.steps,
   deadCurrent:s.debt.filter(d=>d.year===Y).reduce((a,d)=>a+d.amount,0),
   deadFuture:s.debt.filter(d=>d.year>Y).reduce((a,d)=>a+d.amount,0),
   indexSpread:Math.max(...after.map(t=>t.index))-Math.min(...after.map(t=>t.index)),
   maxIndex:Math.max(...after.map(t=>t.index)),
   failures:settlement.failed,trades:trade.events,cuts:settlement.events});
  previousScores=after.map(t=>t.index);s.previousCap=cap;
  if(!valid)break;
 }
 return {seed:base.seed,mode,timeline,shock,seasons,years,
  legalAll:years.length===seasons&&years.every(y=>y.legal),
  failedYear:years.find(y=>!y.legal)?.year??null,
  trades:years.reduce((a,y)=>a+y.tradeCount,0),
  cuts:years.reduce((a,y)=>a+y.cutCount,0)};
}
export function runCP7c(csv,{seeds=[11,29,47],shocks=[0,-.10,-.20],
 timelines=['enforce_before_reset','reset_before_enforce'],
 modes=MODES,seasons=5,wait=.5}={}){
 assert(seasons>=3&&seasons<=10,'seasons 3-10');
 const starts=[],runs=[];
 for(const seed of seeds){
  const base=createCP7bBase(csv,seed,.25);
  starts.push({seed,cap:base.cap,teams:base.teams.map(t=>({team:t.id,roster:t.players.length,
   index:lineup(t.players,base.world).score}))});
  for(const shock of shocks)for(const timeline of timelines)for(const mode of modes)
   runs.push(runOne(base,{mode,timeline,shock,seasons,wait}));
 }
 return {schema:'cp7c-multiyear-synthetic-v0',asOf:'2026-10-05',
  status:'paired synthetic NFL futures and contracts, NOT real manager offers, salaries or future playoff odds',
  assumptions:{seeds,shocks,timelines,modes,seasons,wait,rosterMax:45,noTaxi:true,noIR:true,
   rookieDraft:5,annualSalary:'fixed remaining contract; new signings and renewal from same CP6r Criticality price',
   cap:'CP6r Top120/6 after same draft and performance update times cap-only shock',
   tenure:'2027 initial synthetic acquiredYear = synthetic contract vintage, resets on trade',
   P1:'cycle-only 50/30/15/5% on cut, P1 reset-first has zero binding cut debt at Compliance',
   P2:'contract guarantee 100/50/25 veteran, Rookie guarantees by actual fantasy round',
   market:'1:1 full contract pre-cut two-agent utility, buyer current-cap and positions legal; no picks',
   FA:'P1 same-cycle discounted active salary for cut players; P2 cut re-signing blocked (undefined price)',
   observedNFL:false,realOwners:false,realBuyerConsent:false,realInjuries:false,actualCalendar:false,
   retirement:'NFL exit triggers ordinary current-regime cut debt, experimental not approved',
   expiry:'provisional renewal can decline without binding year-1 guarantee',
   future:'future salary obligations recorded in trade, annual cap settlement; no loans or writeoffs'},
  starts,runs,summary:{paths:runs.length,legal:runs.filter(r=>r.legalAll).length,
   byMode:MODES.map(mode=>{const a=runs.filter(r=>r.mode===mode);
    return {mode,paths:a.length,legal:a.filter(r=>r.legalAll).length,
     trades:a.reduce((n,r)=>n+r.trades,0),cuts:a.reduce((n,r)=>n+r.cuts,0)};})}};
}
const self=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===self){
 const root=path.resolve(path.dirname(self),'../../../');
 const csv=readFileSync(path.join(root,'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv'),'utf8');
 const r=runCP7c(csv,{seeds:[11],shocks:[-.1],seasons:5});
 console.log(JSON.stringify(process.argv.includes('--json')?r:r.summary,null,2));
}
