#!/usr/bin/env node
// CP7d pilot. Research only; execute on frozen source blobs, no live writers.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const read=(p,expected)=>{const s=readFileSync(new URL(p,import.meta.url));const h=createHash('sha1').update('blob '+s.length+'\0').update(s).digest('hex');if(h!==expected)throw Error('Source blob mismatch '+p);return s.toString('utf8');};

function evaluate(src,probe,engine,csv,seed=11,seasons=5,slots=45) {
const strip=s=>s.replace(/^#![^\n]*\n/,"").replace(/^import .*?;\n/gm,"").split("const self=fileURLToPath(import.meta.url);")[0].replace(/^export \{[\s\S]*?\};/gm,"").replace(/^export function /gm,"function ");
const f=new Function(strip(src)+"\nreturn {createCP7bBase,lineup,coverage,annual,seasonalDevelopment,applyDynamicSalary,newRookies,draft,capFor,allOwned,contract,setSlots:n=>MAX_SLOTS=n};")();
const cut=new Function(strip(probe)+"\nreturn cut;")();
function replaceOne(s,a,b){if(s.split(a).length!==2)throw Error("unexpected engine anchor: "+a);return s.replace(a,b);}
let e=strip(engine);
e=replaceOne(e,"function runOne(base,{mode,timeline,shock,seasons,wait,annualVeterans=false})","function runOne(base,{mode,timeline,shock,seasons,wait,annualVeterans=false,rosterMax=45})");
e=replaceOne(e,"s.annualVeterans=annualVeterans;","s.annualVeterans=annualVeterans;setSlots(rosterMax);const initial=allOwned(s.teams);let prev=initial;const cohort=new Map([...initial].map(([id,t])=>[id,{owner:t,since:2026}]));const initialStarters=new Set(s.teams.flatMap(t=>lineup(t.players,s.world).ids));const drafted=new Map();");
e=replaceOne(e,"t.players.length>=45","t.players.length>=rosterMax");
e=replaceOne(e,"years.push({year:Y,cap,legal:valid,opening,after,exits,capacity,", "const nowOwned=allOwned(s.teams);const interrupted=new Set([...trade.events.flatMap(t=>[t.playerSold,t.playerGiven]),...settlement.events.map(c=>c.player),...exits.map(x=>x.id),...capacity.map(x=>x.id)]);for(const [id,o] of now)if(!old.has(id))drafted.set(id,{owner:o,year:Y});const changes=[...prev].filter(([id,o])=>nowOwned.get(id)!==o||interrupted.has(id));for(const [id] of changes)cohort.delete(id);for(const [id,o] of nowOwned)if(!cohort.has(id))cohort.set(id,{owner:o,since:Y});const starters=new Set(s.teams.flatMap(t=>lineup(t.players,s.world).ids));const eligible=[...drafted].filter(([id,d])=>d.year<=Y-2);const kept=eligible.filter(([id,d])=>cohort.get(id)?.since===d.year&&cohort.get(id)?.owner===d.owner);const retention={prior:prev.size,retained:prev.size-changes.length,initialRetained:[...cohort].filter(([id,c])=>c.since===2026).length,activeInitial:[...initial].filter(([id])=>s.world.get(id).active).length,initialStarterRetained:[...cohort].filter(([id,c])=>c.since===2026&&initialStarters.has(id)).length,tenure2plus:[...cohort.values()].filter(c=>Y-c.since>=2).length,held:nowOwned.size,draftEligible:eligible.length,draftKept:kept.length,draftKeptStarter:kept.filter(([id])=>starters.has(id)).length};prev=nowOwned;years.push({year:Y,cap,legal:valid,opening,after,exits,capacity,retention,");
const run=new Function(...Object.keys(f),"cut",e+"\nreturn runOne;")(...Object.values(f),cut);
const baseWorld=f.createCP7bBase(csv,seed,.25);
const matrix=slots===45?[["none",true],["retained_cycle",true],["guaranteed_vintage",false]]:[["none",true],["retained_cycle",true]];
return matrix.map(([mode,annualVeterans])=>{
const r=run(baseWorld,{mode,timeline:"enforce_before_reset",shock:-.1,seasons,wait:.5,annualVeterans,rosterMax:slots});
return {seed,mode,annualVeterans,rosterMax:slots,seasons,legal:r.legalAll,years:r.years.map(y=>({year:y.year,legal:y.legal,cap:y.cap,retention:y.retention,trades:y.tradeCount,cuts:y.cutCount,capacity:y.capacity.length,exits:y.exits.length,avgRoster:y.after.reduce((a,t)=>a+t.roster,0)/6,maxRoster:Math.max(...y.after.map(t=>t.roster)),avgIndex:y.after.reduce((a,t)=>a+t.index,0)/6,spread:y.indexSpread,dead:y.deadCurrent,future:y.deadFuture,failures:y.failures}))};
});
}
const [seed=11,seasons=5,slots=45]=process.argv.slice(2).map(Number);const runs=evaluate(read('../salary/simulation/cp6r_45slot_trade_strategy.mjs','d874d24f3d109ec6711f39e9145ec7a98fa81425'),read('./deadcap_contract_probe.mjs','053c027050339255e3f3df013fb16d4e09ca9ab2'),read('./cp7c_annual_salary_sensitivity.mjs','09cdcc3bf7fe2401be7a317d081af76e6a02312b'),read('../salary/analyses/2026-10-05-salary-simulation-players.csv','96ef8deac5930ffc3dc84dbf12cbbf4719c58489'),seed,seasons,slots);console.log(JSON.stringify(runs,null,2));
