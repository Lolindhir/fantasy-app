#!/usr/bin/env node
/**
 * CP6l: Cap-deferral and rebuild financing stress overlay for CP6k.
 * 2027–2031 are SYNTHETIC CP6k cap/payroll paths, not NFL predictions.
 * No actual player purchases, trades, extra points, pick transfers or debt enforcement.
 * Usage (repo root): node fantasy-management/league-economy/salary/simulation/cp6l_cap_deferral_overlay.mjs [--json]
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const round=x=>Math.floor(x+.5);
const OPTIONS=[
 {name:'5%-draw/10%-limit',drawFraction:.05,creditLimit:.10},
 {name:'10%-draw/10%-limit',drawFraction:.10,creditLimit:.10},
 {name:'15%-draw/25%-limit',drawFraction:.15,creditLimit:.25}
];
function assert(x,msg){if(!x)throw Error(msg);}
function financialYears(run){
 assert(run.legalAll&&run.years.length===5&&run.failures.length===0,'CP6k base run must be legal for 5 years');
 return run.years.map(y=>{
  const cap=round(y.cap_m*1e6),salary=round(y.capUse_m*1e6);
  assert(cap>=salary&&salary>=0,'Illegal CP6k base full-salary use');
  return {year:y.year,cap,salary,headroom:cap-salary,index:y.index};
 });
}
function debtOverlay(run,option,term,early){
 assert(term===2||term===3,'Only H2/H3');
 const y=financialYears(run),borrow=round(y[0].cap*option.drawFraction);
 assert(borrow<=round(y[0].cap*option.creditLimit),'Initial credit limit');
 let balance=borrow;const details=[],errors=[];
 // One-season salary bill that fully uses cap AND newly borrowed amount.
 // Deliberately optimistic: increment expires after 2027, quality gain not projected.
 details.push({year:y[0].year,cap:y[0].cap,baseSalary:y[0].salary,freeCap:y[0].headroom,
  newBorrowing:borrow,incrementalOneYearSalaryEnvelope:y[0].headroom+borrow,
  hypotheticalTotalSalary:y[0].cap+borrow,mandatoryDue:0,paid:0,unpaid:balance});
 for(let t=1;t<y.length;t++){
  const remainingChecks=Math.max(1,term-t+1);
  const due=balance>0?Math.ceil(balance/remainingChecks):0;
  const paid=Math.min(balance,y[t].headroom,early?balance:due);
  const deficit=Math.max(0,due-paid);balance-=paid;
  const limit=round(y[t].cap*option.creditLimit);
  const overLimit=Math.max(0,balance-limit);
  if(deficit||overLimit)errors.push({year:y[t].year,dueShortfall: deficit,creditLimitOverhang:overLimit});
  details.push({year:y[t].year,cap:y[t].cap,baseSalary:y[t].salary,freeCap:y[t].headroom,
   mandatoryDue:due,paid,earlyPaid:Math.max(0,paid-due),dueShortfall:deficit,unpaid:balance,overLimit});
 }
 return {seed:run.seed,supply:run.supply,regime:run.regime,option:option.name,term:'H'+term,
  repayment:'minimum-only'=== (early?'early-max':'minimum-only')?'minimum-only':'early-max',
  borrow,originalH5:run.h5,projectedSportsGain:null,
  firstYearExtraPayrollEnvelope:details[0].incrementalOneYearSalaryEnvelope,
  paidByYear5:balance===0,compliantWithoutExtraRosterAction:errors.length===0&&balance===0,
  failures:errors,years:details};
}
export function evaluate(cp6kDocuments){
 const docs=cp6kDocuments.map(x=>typeof x==='string'?JSON.parse(x):x);
 const results=[],rebuild=[];
 for(const doc of docs){
  assert(doc.schema==='cp6k-v0'&&doc.simulator_sha&&doc.source_csv_sha,'Unexpected CP6k input');
  for(const run of doc.runs){
   for(const option of OPTIONS)for(const term of [2,3])for(const early of [false,true])
    results.push(debtOverlay(run,option,term,early));
   const y=financialYears(run)[0];
   for(const targetFraction of [.05,.10,.15]){
    const requiredCash=round(y.cap*targetFraction);
    rebuild.push({seed:run.seed,supply:run.supply,regime:run.regime,year:y.year,
     targetUnusedCapFraction:targetFraction,cap:y.cap,baselineFullSalary:y.salary,
     currentFreeCap:y.headroom,targetFreeCap:requiredCash,
     additionalSalaryReliefNeeded:Math.max(0,requiredCash-y.headroom),
     futureCapBalance:0,futurePicksEarned:0,
     note:'Only salary headroom. No automatic carryover, trade, buyer, pick transfer or roster move.'});
   }
  }
 }
 return {schema:'cp6l-v0',as_of:'CP6k synthetic 2027-2031, initial archive 2026-10-05',
  status:'debt service financing feasibility ONLY; not an All-in/Rebuild sports simulation',
  sourceBlobs:docs.map(x=>({seed:x.seed,simulator:x.simulator_sha,archive:x.source_csv_sha})),
  configuration:{team:'CP6k Team 0 only; other five teams in unchanged CP6k paths',
   newBorrowingYear:2027,interest:0,limits:OPTIONS,
   H2:'first mandatory due 2028; final 2029',
   H3:'first mandatory due 2028; final 2030',
   formula:'mandatory = ceil(remaining debt / remaining follow-up checks)',
   noRefinance:'installments must be paid from annual salary-cap headroom without another draw',
   repaymentChoices:['minimum-only','early-max (all unused headroom)'],
   oneYearInvestment:'extra one-year payroll equals full original unspent cap plus new borrowing; not an executable asset purchase',
   rebuild:'5/10/15% unused 2027 cap TARGET; additional salary relief computed, NO automatic cap rollover',
   missing:'new actual player salaries beyond 2027, player availability, buyer-side cap and slots, pick-asset transfer, C-add retained cut charges, debt ledger for other 5 teams, enforcement hard-failure'},
  totals:{basePaths:docs.reduce((n,x)=>n+x.runs.length,0),debtPaths:results.length,rebuildTargets:rebuild.length},
  financing:results,rebuild};
}
const f=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===f){
 const root=path.resolve(path.dirname(f),'../../../..');
 const files=[11,29,47].map(seed=>path.join(root,'fantasy-management/league-economy/salary/analyses/2026-11-19-cp6k-seed-'+seed+'-results.json'));
 const result=evaluate(files.map(p=>readFileSync(p,'utf8')));
 const out=process.argv.includes('--json')?result:{totals:result.totals,
  summary:result.financing.filter(x=>x.supply===30&&x.regime==='active').map(x=>({seed:x.seed,option:x.option,term:x.term,repayment:x.repayment,compliant:x.compliantWithoutExtraRosterAction,failures:x.failures}))};
 console.log(JSON.stringify(out,null,2));
}