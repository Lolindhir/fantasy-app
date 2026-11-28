#!/usr/bin/env node
/** CP7a economic invariants only. NOT a real trade-market simulation. */
const ok=(c,m)=>{if(!c)throw Error(m)};
const money=(v,m)=>{ok(Number.isSafeInteger(v)&&v>=0,m);return v};
const rates=[.5,.3,.15,.05];
const modes=['none','retained_cycle','guaranteed_vintage'];
export function cut({mode,year,salary,tenure=0,floor=0,start=null,guarantees=null}){
 ok(modes.includes(mode)&&Number.isInteger(year)&&Object.hasOwn(salary,year),'mode/year');
 const annual=money(salary[year],'current salary'),dead={};
 let activeAfterCut=null;
 if(mode==='retained_cycle'){
  ok(Number.isInteger(tenure)&&tenure>=0,'team tenure');
  const d=Math.floor(annual*rates[Math.min(tenure,3)]+.5);
  dead[year]=d;activeAfterCut=Math.max(money(floor,'salary floor'),annual-d);
 }else if(mode==='guaranteed_vintage'){
  ok(Number.isInteger(start)&&Array.isArray(guarantees),'contract vintage');
  for(const [ys,val] of Object.entries(salary)){
   const y=Number(ys);money(val,'scheduled salary');
   if(y<year)continue;
   const idx=y-start;ok(idx>=0&&idx<guarantees.length,'missing guaranteed vintage');
   const g=guarantees[idx];ok(g>=0&&g<=1,'guarantee fraction');
   dead[y]=Math.floor(val*g+.5);
  }
 }
 const now=dead[year]||0;
 return {mode,year,annual,dead,now,relief:annual-now,activeAfterCut,
  futureDebt:Object.entries(dead).filter(([y])=>+y>year).reduce((a,[,b])=>a+b,0),
  nextFAContractPrice:mode==='retained_cycle'?activeAfterCut:null};
}
export function tradeCandidate({mode,year,salary,buyer,seller,maxSlots=45,futureCheck=false}){
 ok(modes.includes(mode)&&Object.hasOwn(salary,year),'mode/year');
 ok(buyer&&seller,'two sides');const amount=money(salary[year],'buyer salary');
 money(buyer.used,'buyer used');money(buyer.cap,'buyer cap');money(seller.used,'seller used');
 ok(seller.used>=amount,'seller must hold full salary');
 const blockers=[];
 if(buyer.slots+1>maxSlots)blockers.push('roster');
 if(buyer.used+amount>buyer.cap)blockers.push('buyer cap');
 if(buyer.positionsLegal===false||seller.positionsLegalAfterRemoval===false)blockers.push('position');
 const future={};
 if(futureCheck){
  ok(buyer.futureUsed&&buyer.futureCaps,'future budget must be supplied');
  for(const [ys,amountFuture] of Object.entries(salary)){
   const y=+ys;if(y<=year)continue;money(amountFuture,'future salary');
   if(!Object.hasOwn(buyer.futureUsed,y)||!Object.hasOwn(buyer.futureCaps,y)){
    blockers.push('future budget unknown '+y);continue;
   }
   const total=buyer.futureUsed[y]+amountFuture;
   future[y]={assumedSalary:amountFuture,total,cap:buyer.futureCaps[y]};
   if(total>buyer.futureCaps[y])blockers.push('future cap '+y);
  }
 }
 return {mode,possible:!blockers.length,blockers,oldSellerRelief:amount,
  fullBuyerSalary:amount,buyerAfter:buyer.used+amount,sellerAfter:seller.used-amount,
  buyerSlotsAfter:buyer.slots+1,future,
  newTradeDeadCap:0,retainedSalary:0,actualOwnerConsent:'not observed'};
}
export function compare(c,t=null){
 ok(c&&c.mode,'cut required');
 return {sellerAdvantageNow:t?.possible?t.oldSellerRelief-c.relief:null,
  avoidedFutureGuarantee:t?.possible?c.futureDebt:null,
  tradeExecutableWithAssumedBuyer:t?.possible||false,
  reason:!t?'no buyer candidate':t.blockers.join('; ')||null,
  actualObservedTrades:0};
}
export function control({mode,dead,event,year}){
 ok(modes.includes(mode)&&['cap_only','salary_reprice'].includes(event),'mode/event');
 if(mode==='retained_cycle'&&event==='salary_reprice')return {};
 return Object.fromEntries(Object.entries(dead).filter(([y])=>+y>=year));
}
export function selfTest(){
 const M=1000000,salary={2027:20*M,2028:25*M,2029:30*M};
 let n=0;const v=(condition,message)=>{ok(condition,message);n++};
 const a=cut({mode:'none',year:2027,salary});
 v(a.now===0&&a.relief===20*M,'zero dead');
 const r=cut({mode:'retained_cycle',year:2027,salary});
 v(r.now===10*M&&r.relief===10*M&&r.activeAfterCut===10*M,'retained salary');
 for(const [years,rate] of [[0,.5],[1,.3],[2,.15],[3,.05],[7,.05]])
  v(cut({mode:'retained_cycle',year:2027,salary,tenure:years}).now===20*M*rate,'tenure rate');
 const floored=cut({mode:'retained_cycle',year:2027,salary:{2027:2*M},
  tenure:0,floor:1400000});
 v(floored.now===M&&floored.activeAfterCut===1400000,'floor');
 v(control({mode:'retained_cycle',dead:r.dead,event:'cap_only',year:2027})[2027]===10*M,'no cap-only reset');
 v(Object.keys(control({mode:'retained_cycle',dead:r.dead,event:'salary_reprice',year:2027})).length===0,'true reset');
 const buyer={used:60*M,cap:100*M,slots:29,positionsLegal:true,
  futureCaps:{2028:120*M,2029:120*M},futureUsed:{2028:70*M,2029:70*M}};
 const seller={used:90*M,positionsLegalAfterRemoval:true};
 const t=tradeCandidate({mode:'retained_cycle',year:2027,salary:{2027:20*M},buyer,seller});
 v(t.possible&&t.fullBuyerSalary===20*M&&t.oldSellerRelief===20*M,'full trade salary');
 v(compare(r,t).sellerAdvantageNow===10*M,'seller difference');
 const poor=tradeCandidate({mode:'retained_cycle',year:2027,salary:{2027:20*M},
  buyer:{...buyer,used:85*M},seller});
 v(!poor.possible&&poor.blockers.includes('buyer cap'),'buyer cannot afford');
 v(compare(r,poor).sellerAdvantageNow===null,'no phantom trade');
 v(compare(r).reason==='no buyer candidate','unknown buyer');
 const slots=tradeCandidate({mode:'none',year:2027,salary:{2027:20*M},
  buyer:{...buyer,slots:45},seller});
 v(!slots.possible&&slots.blockers.includes('roster'),'45 slot limit');
 const g=cut({mode:'guaranteed_vintage',year:2027,salary,start:2027,guarantees:[1,.5,.25]});
 v(g.now===20*M&&g.futureDebt===20*M,'guarantee vintage');
 v(g.nextFAContractPrice===null,'no invented new FA contract');
 const full=tradeCandidate({mode:'guaranteed_vintage',year:2027,salary,buyer,seller,futureCheck:true});
 v(full.possible&&full.future[2028].assumedSalary===25*M&&full.future[2029].assumedSalary===30*M,'full future liability');
 const bad=tradeCandidate({mode:'guaranteed_vintage',year:2027,salary,seller,
  buyer:{...buyer,futureUsed:{2028:110*M,2029:110*M}},futureCheck:true});
 v(!bad.possible&&bad.blockers.length===2,'future debt blocks deal');
 v(control({mode:'guaranteed_vintage',dead:g.dead,
  event:'salary_reprice',year:2028})[2028]===12.5*M,'guarantees persist');
 return {passed:n,modes,scope:'accounting fixtures only; market-clearing not modeled'};
}
if(typeof process!=='undefined'&&process.argv[1]?.endsWith('deadcap_contract_probe.mjs'))
 console.log(JSON.stringify(selfTest(),null,2));
