#!/usr/bin/env node
/**
 * CP7b: Pre-cut trading in 6-owner, 45-slot synthetic snapshot. NOT a 5-year
 * market equilibrium or evidence of any real manager's willingness to trade.
 * P0 none, P1 50/30/15/5 retained salary, P2 contracted multiyear guarantees.
 *
 * Run: node fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createCP7bBase,lineup,coverage,annual} from '../salary/simulation/cp6r_45slot_trade_strategy.mjs';
import {cut} from './deadcap_contract_probe.mjs';
const MODES=['none','retained_cycle','guaranteed_vintage'];
const POS=['QB','RB','WR','TE','K'];
const W={all_in:{line:1.5,youth:.10,cap:.10},rebuild:{line:.70,youth:.52,cap:.14},
 reload:{line:1.1,youth:.27,cap:.14},flex:{line:.93,youth:.31,cap:.20}};
const money=x=>Math.floor(x+.5),M=1000000;
function assert(v,n){if(!v)throw Error(n);}
function clone(base){
 return {world:base.world,teams:base.teams.map(t=>({...t,players:[...t.players]})),
  contracts:new Map([...base.contracts].map(([id,c])=>[id,{...c}])),
  debt:[],released:new Map(),pickedFA:new Set()};
}
function salary(contract,year=2027){return annual(contract,year,.25);}
function due(team,s,year=2027){return team.players.reduce((sum,id)=>sum+(s.contracts.has(id)?
  salary(s.contracts.get(id),year):s.world.get(id).price),0)+
  s.debt.filter(d=>d.owner===team.id&&d.year===year).reduce((sum,d)=>sum+d.amount,0);}
function u(ids,team,s,cap,year=2027){
 const line=lineup(ids,s.world);if(!line.valid)return -Infinity;
 const weight=W[team.strategy]||W.reload;const chosen=new Set(line.ids);
 const youth=ids.reduce((v,id)=>{const p=s.world.get(id);return v+(p.year<=4?(5-p.year)*Math.max(0,p.known)*.28:0);},0);
 const bench=ids.filter(id=>!chosen.has(id)).map(id=>s.world.get(id).known).sort((a,b)=>b-a).slice(0,6).reduce((a,b)=>a+b,0);
 const cash=ids.reduce((sum,id)=>sum+(s.contracts.has(id)?salary(s.contracts.get(id),year):s.world.get(id).price),0);
 const existingDebt=s.debt.filter(x=>x.owner===team.id&&x.year===year).reduce((v,x)=>v+x.amount,0);
 const total=(cash+existingDebt)/M;
 return weight.line*line.score+weight.youth*youth+bench*.055-weight.cap*total-
  Math.max(0,(cash+existingDebt-cap)/M)*.30;
}
function freePool(s){const held=new Set(s.teams.flatMap(t=>t.players));
 return [...s.world.values()].filter(p=>p.active&&!held.has(p.id)&&!s.pickedFA.has(p.id));}
function guarantee(c){
 if(c.kind!=='rookie'||c.draftRound==null)return [1,.5,.25];
 return c.draftRound<=2?[1,1,1]:c.draftRound<=4?[1,1,.5]:[1,.5,.25];
}
function cutQuote(s,team,id,mode,year=2027){
 const c=s.contracts.get(id);
 assert(c&&team.players.includes(id),'seller does not own '+id);
 const terms={};
 for(let y=year;y<=c.end;y++)terms[y]=salary(c,y);
 const player=s.world.get(id);
 const opts={mode,year,salary:terms};
 if(mode==='retained_cycle'){
  opts.tenure=Math.max(0,year-c.start); // explicitly synthetic acquisition proxy
  const yr=player.year;
  const minimumPercent=yr<=1?.0025:yr===2?.003:yr===3?.0035:yr===4?.004:yr<=7?.0045:.005;
  opts.floor=money(434255984*minimumPercent); // same frozen archive/CP6r minimum anchor
 }else if(mode==='guaranteed_vintage'){
  opts.start=c.start;opts.guarantees=guarantee(c);
 }
 // Frozen archive 2027 contract; nominal P1 min is a synthetic price anchor.
 const q=cut(opts);
 return {...q,player:id,seller:team.id,teamTenureProxy:year-c.start};
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
 for(const incoming of options){
  const next=old.map(x=>x===id?incoming.id:x);
  if(!coverage(next,s.world))continue;
  // Include same-year cash replacement plus the exact cut debt.
  const oldContract=s.contracts.get(id);
  const oldAnnual=salary(oldContract);
  const newDue=due(team,s)-oldAnnual+incoming.price+quote.now;
  const altQuality=lineup(next,s.world).score;
  const w=W[team.strategy];
  const baseline=u(next,team,s,cap);
  const dueWithoutNewDead=newDue-quote.now;
  const score=baseline-w.cap*(quote.now/M)-
   .30*(Math.max(0,(newDue-cap)/M)-Math.max(0,(dueWithoutNewDead-cap)/M))-
   .5*w.cap*(quote.futureDebt/M);
  const relief=oldAnnual-incoming.price-quote.now;
  const cand={player:id,replacement:incoming.id,replacementSalary:incoming.price,relief,quote,
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
  const free=freePool(s);
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
  seller.players=seller.players.map(id=>id===outgoing.id?incoming.id:id);
  buyer.players=buyer.players.map(id=>id===incoming.id?outgoing.id:id);
  s.contracts.get(outgoing.id).owner=buyer.id;
  s.contracts.get(incoming.id).owner=seller.id;
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
   transactionCreatesDeadCap:0,actualHumanConsent:'unobserved',buyerPaidFullContract:true});
 }
 return {events,screened,examinedSellerPlayers:examinedSellers.size};
}
function settleCuts(s,mode,cap){
 const events=[],failed=[];let tried=0;
 for(const team of s.teams){
  for(let step=0;step<25&&due(team,s)>cap+1;step++){
   const pool=freePool(s);
   const choices=team.players.map(id=>alternativeCut(s,team,id,mode,cap,pool)).filter(Boolean)
    .filter(x=>x.relief>0);
   choices.sort((a,b)=>{
    const aGain=a.relief/(1+Math.max(0,lineup(team.players,s.world).score-a.afterIndex)*3),
      bGain=b.relief/(1+Math.max(0,lineup(team.players,s.world).score-b.afterIndex)*3);
    return bGain-aGain||b.relief-a.relief;
   });
   tried++;
   if(!choices.length)break;
   const b=choices[0],previous=due(team,s),contract=s.contracts.get(b.player);
   team.players=team.players.map(id=>id===b.player?b.replacement:id);
   s.contracts.delete(b.player);
   const newPlayer=s.world.get(b.replacement);
   s.contracts.set(newPlayer.id,{player:newPlayer.id,owner:team.id,start:2027,end:2029,
    kind:'veteran',base:newPlayer.price,pendingRenewal:false});
   for(const [yr,amount] of Object.entries(b.quote.dead))if(amount>0)
    s.debt.push({owner:team.id,player:b.player,year:Number(yr),amount,signYear:contract.start});
   if(mode==='retained_cycle')s.released.set(b.player,b.quote.activeAfterCut);
   s.pickedFA.add(b.replacement);
   assert(coverage(team.players,s.world),'postcut roster coverage');
   assert(due(team,s)===previous-b.relief,'postcut financial identity');
   events.push({team:team.id,player:b.player,replacement:b.replacement,
    oldSalary:b.quote.annual,replacementSalary:b.replacementSalary,
    deadNow:b.quote.now,deadFuture:b.quote.futureDebt,
    salaryAfterRelease:mode==='retained_cycle'?b.quote.activeAfterCut:null,
    netRelief:b.relief,afterUsed:due(team,s)});
  }
  if(due(team,s)>cap+1)failed.push({team:team.id,overBy:due(team,s)-cap});
 }
 return {events,failed,steps:tried};
}
function summarizeScenario(base,mode,shock,waitProbability){
 const cap=money(base.cap*(1+shock)),s=clone(base);
 const roles=['all_in','rebuild','reload','flex','all_in','rebuild'];
 s.teams.forEach(t=>{t.strategy=roles[(t.id+Math.floor(base.seed/7))%6];});
 const before=s.teams.map(t=>({team:t.id,capUsed:due(t,s),roster:t.players.length,
  index:lineup(t.players,s.world).score,overBy:Math.max(0,due(t,s)-cap)}));
 const market=tryTrades(s,mode,cap,{waitProbability});
 const cutPhase=settleCuts(s,mode,cap);
 const after=s.teams.map(t=>({team:t.id,capUsed:due(t,s),roster:t.players.length,
  index:lineup(t.players,s.world).score,overBy:Math.max(0,due(t,s)-cap)}));
 const ownerUnique=new Set(s.teams.flatMap(t=>t.players)).size===s.teams.reduce((a,t)=>a+t.players.length,0);
 const validRosters=s.teams.every(t=>coverage(t.players,s.world));
 const deadNow=s.debt.filter(d=>d.year===2027).reduce((a,d)=>a+d.amount,0);
 const deadFuture=s.debt.filter(d=>d.year>2027).reduce((a,d)=>a+d.amount,0);
 const availableCutDiscounts=[...s.released].map(([id,salary])=>({
  player:id,discountFromOriginal:Math.max(0,s.world.get(id).price-salary),salaryAfterRelease:salary}));
 const finished=ownerUnique&&validRosters&&after.every(t=>t.overBy<=1);
 return {seed:base.seed,mode,shock,cap,waitProbability,legal:finished,
  before,after,market,cutPhase,
  debt:{now:deadNow,future:deadFuture,ledger:s.debt},
  waiverDiscounts:availableCutDiscounts,
  finalOwnershipUnique:ownerUnique,finalRostersValid:validRosters,
  syntheticData:true,syntheticContractTenureProxy:true};
}
export function runCP7b(csv,{seeds=[11,29,47],shocks=[0,-.10,-.20],waitProbability=.5}={}){
 const results=[],starts=[];
 for(const seed of seeds){
  const base=createCP7bBase(csv,seed,.25);
  starts.push({seed,cap:base.cap,teams:base.teams.map(t=>({
   team:t.id,roster:t.players.length,index:lineup(t.players,base.world).score,
   initialSalary:due(t,clone(base))}))});
  for(const shock of shocks)for(const mode of MODES)
   results.push(summarizeScenario(base,mode,shock,waitProbability));
 }
 const groups=shocks.map(shock=>({shock,
  models:MODES.map(mode=>{
   const arr=results.filter(x=>x.shock===shock&&x.mode===mode);
   return {mode,scenarios:arr.length,legal:arr.filter(x=>x.legal).length,
    trades:arr.reduce((s,x)=>s+x.market.events.length,0),
    cuts:arr.reduce((s,x)=>s+x.cutPhase.events.length,0),
    hardFailures:arr.reduce((s,x)=>s+x.cutPhase.failed.length,0),
    totalCurrentDead:arr.reduce((s,x)=>s+x.debt.now,0),
    totalFutureDead:arr.reduce((s,x)=>s+x.debt.future,0),
    candidatesScreened:arr.reduce((s,x)=>s+x.market.screened.pairs,0),
    waiverWaitBlocks:arr.reduce((s,x)=>s+x.market.screened.waiverWaitBlocked,0)};
  })}));
 return {schema:'cp7b-precut-six-team-v0',date:'2026-11-26',asOf:'2026-10-05',
  status:'synthetic 2027 frozen snapshot only, not a full 5-year backtest or real offers',
  assumptions:{seeds,shocks,waitProbability,modes:MODES,regularSlotsMax:45,
   minimumResearchSlots:20,cap:'frozen 2027 Top120/6 cap times shock; separate from salary reprice',
   salary:'same CP6r frozen dynamic Criticality archival price in all models',
   tenure:'synthetic acquisition proxy uses synthetic CP6r vintage, not real historical tenure',
   trade:'one-for-one full-contract salary exchange before forced cuts; buyer financially and position legal; both proxy utility improvements; at most six league trades per world',
   cut:'same-position free-agent replacement with retained current or multiyear dead cap; reject unresolvable cases',
   freeAgent:'P1 released active Salary discounted, P2 new deal price unspecified; no postcut waiver claims or real human consent',
   limits:'no real owner history, IR/Taxi, draft picks, other trade bundles, renewals, injuries, true 2027+ NFL, playoff/championship odds'},
  starts,groups,results};
}
const self=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===self){
 const root=path.resolve(path.dirname(self),'../../../');
 const csv=readFileSync(path.join(root,'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv'),'utf8');
 const out=runCP7b(csv);
 console.log(JSON.stringify(process.argv.includes('--json')?out:{summary:out.groups,starts:out.starts},null,2));
}
