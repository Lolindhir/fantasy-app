#!/usr/bin/env node
/**
 * CP6n, 2026-11-22: hypothetical 3-year locked-salary contract market stress.
 * RESEARCH ONLY. Not a sports season, trade acceptance, draft/roster simulator,
 * NFL forecast, or league rule. Uses six-owner 2027 synthetic CP6k cohorts
 * extracted and reconciled against original CP6k public seed files; see input.
 *
 * This intentionally preserves the earlier CP6k market cap index (Top120
 * source 'price', including some Rookie contract-derived prices) as a
 * REFERENCE, even though a true new dual-ledger model still needs to define
 * an independent Rookie market value and recalculate future market caps.
 *
 * Reproduce from repository root:
 *   node fantasy-management/league-economy/salary/simulation/cp6n_market_cap_contract_guarantee_stress.mjs --json
 *   node fantasy-management/league-economy/salary/simulation/cp6n_market_cap_contract_guarantee_stress.mjs
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const VETERAN_ESCALATION=[0,0.05,0.10]; // => 100/100/100, 100/105/110, 100/110/120
const MARKET_CAP_SHOCK=[0,-0.10,-0.20]; // one additional step shock at 2028 & 2029, NOT compounding
const ROOKIE_FACTORS=[1,1.25,1.5];     // user-preferred established Rookie contract path
const CURRENT_YEARS=[2027,2028,2029];
const whole=x=>Math.floor(x+0.5);
const million=x=>+(x/1e6).toFixed(6);
function assert(ok,msg){if(!ok)throw Error(msg);}

export function evaluate(cohortInput){
 assert(cohortInput?.schema==='cp6n-contract-cohort-inputs-v0','Input schema mismatch');
 assert(cohortInput.cohorts.length===3,'Requires 3 paired seeds');
 const results=[];
 for(const sample of cohortInput.cohorts){
  const {seed,teams,marketCapsDollars:caps}=sample;
  assert(teams.length===6&&caps.length===3,'Invalid six-team cohort');
  assert(teams.map(t=>t.team).join(',')==='0,1,2,3,4,5','Team IDs must be stable');
  for(const t of teams){
   assert(t.newRookieFirstYearDollars+t.other2027SalaryDollars===t.year2027TeamSalaryDollars,'Cohort salary mismatch');
   assert(t.year2027TeamSalaryDollars<=caps[0],'2027 must be legal');
  }
  for(const escalation of VETERAN_ESCALATION)for(const shock of MARKET_CAP_SHOCK){
   const years=CURRENT_YEARS.map((year,i)=>{
    const baseCap=caps[i];
    const cap=whole(baseCap*(i===0?1:1+shock));
    const teamsResult=teams.map(t=>{
     const rookieDue=whole(t.newRookieFirstYearDollars*ROOKIE_FACTORS[i]);
     const otherDue=whole(t.other2027SalaryDollars*(1+escalation*i));
     const due=rookieDue+otherDue;
     assert(due>=t.year2027TeamSalaryDollars,'Escalating contract cannot decrease annual liability');
     return {team:t.team,rosterCount2027:t.rosterCount,newRookies2027:t.newRookieCount,
       rookieDueDollars:rookieDue,otherContractDueDollars:otherDue,
       annualTotalDueDollars:due,capOverhangDollars:Math.max(0,due-cap),
       capHeadroomDollars:Math.max(0,cap-due),compliant:due<=cap};
    });
    const totalDues=teamsResult.reduce((a,t)=>a+t.annualTotalDueDollars,0);
    const capacity=6*cap;
    const systemicGap=Math.max(0,totalDues-capacity);
    const targetCapPerOwnerDollars=whole(totalDues/6);
    const minCapRatioNeeded=totalDues/(6*baseCap);
    assert(teamsResult.length===6&&cap>0,'Invalid season');
    assert(teamsResult.every(t=>t.annualTotalDueDollars===t.rookieDueDollars+t.otherContractDueDollars),'Mixed salary sum');
    return {year,marketCapNoShockDollars:baseCap,marketCapAppliedDollars:cap,
      marketShockApplied:i===0?0:shock,rookieContractYearFactor:ROOKIE_FACTORS[i],
      otherContractYearFactor:1+escalation*i,
      sumAnnualObligationsDollars:totalDues,
      sumSixTeamCapDollars:capacity,
      teamOverCapCount:teamsResult.filter(t=>!t.compliant).length,
      totalPositiveTeamOverhangDollars:teamsResult.reduce((a,t)=>a+t.capOverhangDollars,0),
      leagueAggregateHardShortfallDollars:systemicGap,
      structurallyUnallocatableIfAllGuaranteed:systemicGap>0,
      impliedUtilizationPct:+(100*totalDues/capacity).toFixed(6),
      minUniformMarketCapForSumDollars:targetCapPerOwnerDollars,
      noShockMarketCapRatioNeededToFitEntireCohort:+minCapRatioNeeded.toFixed(6),
      teams:teamsResult};
   });
   assert(years[0].teamOverCapCount===0,'All first-year signings legal');
   assert(years[0].sumAnnualObligationsDollars===teams.reduce((a,t)=>a+t.year2027TeamSalaryDollars,0),'2027 due mismatch');
   results.push({seed,otherVeteranAnnualEscalationPerYear:escalation,
     year2And3HypotheticalMarketCapShock:shock,years});
  }
 }
 return {schema:'cp6n-three-year-cap-stress-v0',researchDate:'2026-11-22',
  status:'mechanical cohort liability stress, not contract-world equilibrium, NFL future prediction or adopted fantasy-league policy',
  inputSource:{archivedCp6kScriptBlob:cohortInput.cp6kSourceBlob,
   archivedPlayerCsvBlob:cohortInput.playerArchiveBlob,
   note:'2027 cohort extracted by reproducing CP6k seed 11/29/47, supply30 active T0 and 2027 legal owners; 2028/29 exogenous market indices checked against CP6k seed files'},
  policyBranches:{rookieContractY1Y2Y3:ROOKIE_FACTORS,
   veteranY2Y3:'base salary times (1+escalation * (contract year-1))',
   contractFreeze:'2027 team roster and annual locked obligations fixed 2027-29',
   veteranLegacyProxy:'all 2027 non-new-rookies treated as newly signed in 2027, not actual signed contract history',
   priceMarketCap:'unchanged CP6k market Top120/6, including some Rookie price-derived values; next research must fully separate player MarketValue from ContractSalary',
   shock:'2028 and 2029 market index independently scaled by 1+shock; 2027 untouched; actual salary/market floor recomputation not implemented',
   guarantees:'full 100% future-year annual guarantees and no asset buyer/offset for worst-case lower bound; no artificial cuts or forgiveness',
   noNewSignings:'2028 and 2029 rookie draft/FA replacement obligations NOT added, despite new rookies included in future market cap path',
   debtAccounting:'no H2/H3 cap credit; dead cap requires a cut, none simulated here; under fully guaranteed unclaimed cut, already booked amount remains due and changes classification only',
   noSellerBuyerConsent:'no trades, waiver claims, salary retention or re-signings, and no occupancy repairs; do not describe failures as a documented real transaction result'},
  scenarios:results,summary:{
   seeds:[...new Set(results.map(r=>r.seed))],
   combinations:results.length,
   annualRows:results.reduce((v,r)=>v+r.years.length,0),
   structurallyUnallocatableYearRows:results.reduce((v,r)=>v+r.years.filter(y=>y.structurallyUnallocatableIfAllGuaranteed).length,0),
   illegalOwnerYearRows:results.reduce((v,r)=>v+r.years.reduce((w,y)=>w+y.teamOverCapCount,0),0)
  }};
}

const self=fileURLToPath(import.meta.url);
if(process.argv[1]&&path.resolve(process.argv[1])===self){
 const input=path.resolve(path.dirname(self),'../analyses/2026-11-22-cp6n-contract-cohort-inputs.json');
 const r=evaluate(JSON.parse(readFileSync(input,'utf8')));
 if(process.argv.includes('--json'))console.log(JSON.stringify(r,null,2));
 else console.log(JSON.stringify({summary:r.summary,scenarioOverview:r.scenarios.map(x=>({
  seed:x.seed,veteranSlope:x.otherVeteranAnnualEscalationPerYear,
  marketShock:x.year2And3HypotheticalMarketCapShock,
  overTeams2029:x.years[2].teamOverCapCount,
  leagueHardShortfall2029_m:million(x.years[2].leagueAggregateHardShortfallDollars),
  totalDueVsCapPct2029:x.years[2].impliedUtilizationPct}))},null,2));
}
