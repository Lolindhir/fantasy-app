#!/usr/bin/env node
/** CP6i dated 2026-10-05 salary/3Y-index single-team diagnostic.
 * Research only. Usage: node cp6i_starter_ceiling.mjs <archive.csv>
 * Tested syntax with node --check. Heuristic attainable bound, NOT global optimum.
 */
import { readFileSync } from 'node:fs';
const filename=process.argv[2];
if(!filename)throw new Error('Pass 2026-10-05-salary-simulation-players.csv');
const lines=readFileSync(filename,'utf8').trim().split(/\r?\n/);
const headers=lines[0].split(';');
const rows=lines.slice(1).map(line=>{const parts=line.split(';');return Object.fromEntries(headers.map((h,i)=>[h,parts[i]]));});
const positions=['QB','RB','WR','TE','K'],minimums={QB:2,RB:2,WR:2,TE:2,K:1};
const players=rows.filter(x=>positions.includes(x.position)&&x.nfl_team!=='FA'&&+x.performance_3y>0).map(x=>({
 id:x.id,name:x.name,pos:x.position,index:+x.performance_3y,
 published:(+x.salary_published)/1e6,
 criticality:(+x.salary_I_ohne_base_minimum)/1e6
}));
function optimize(kind){
 const col=kind==='published'?'salary_published':'salary_I_ohne_base_minimum';
 const cap=rows.map(x=>+x[col]||0).sort((a,b)=>b-a).slice(0,120).reduce((a,b)=>a+b,0)/6e6;
 const groups=Object.fromEntries(positions.map(pos=>[pos,players.filter(x=>x.pos===pos)]));
 function choose(lambda){
  const starters=[],ids=new Set(),order=(a,b)=>(b.index-lambda*b[kind])-(a.index-lambda*a[kind]);
  for(const pos of positions)for(const p of [...groups[pos]].sort(order).slice(0,minimums[pos])){starters.push(p);ids.add(p.id);}
  starters.push(...players.filter(p=>p.pos!=='QB'&&p.pos!=='K'&&!ids.has(p.id)).sort(order).slice(0,4));
  return starters;
 }
 function metrics(starters){return {score:starters.reduce((a,p)=>a+p.index,0),cost:starters.reduce((a,p)=>a+p[kind],0),ids:new Set(starters.map(p=>p.id))};}
 const allstar=metrics(choose(0));let best;
 for(let t=0;t<=10000;t++){const lambda=t/10000,team=choose(lambda),m=metrics(team);
  if(m.cost<=cap&&(!best||m.score>best.score))best={team,...m,lambda};}
 if(!best)throw new Error('No feasible team in '+kind);
 for(let iter=0;iter<30;iter++){
  let candidate;
  const counts=Object.fromEntries(positions.map(pos=>[pos,best.team.filter(p=>p.pos===pos).length]));
  for(let i=0;i<13;i++){const old=best.team[i];
   for(const replacement of players){
    if(best.ids.has(replacement.id))continue;
    if(old.pos!==replacement.pos&&counts[old.pos]<=minimums[old.pos])continue;
    if((old.pos==='QB')!==(replacement.pos==='QB')||(old.pos==='K')!==(replacement.pos==='K'))continue;
    const cost=best.cost-old[kind]+replacement[kind],score=best.score-old.index+replacement.index;
    if(cost<=cap&&score>best.score+1e-8&&(!candidate||score>candidate.score))candidate={i,replacement,score};
   }
  }
  if(!candidate)break;
  const team=best.team.slice();team[candidate.i]=candidate.replacement;
  best={team,...metrics(team),lambda:best.lambda};
 }
 if(best.team.length!==13||best.ids.size!==13||best.cost>cap+1e-7)throw new Error('Invalid lineup');
 for(const pos of positions)if(best.team.filter(p=>p.pos===pos).length<minimums[pos])throw new Error('Position minimum failed');
 if(best.team.filter(p=>p.pos==='K').length!==1||best.team.filter(p=>p.pos==='QB').length!==2)throw new Error('FLEX failed');
 return {price_column:col,cap_m:cap,allstar_score:allstar.score,allstar_cost_m:allstar.cost,
  feasible_score:best.score,feasible_cost_m:best.cost,remaining_cap_m:cap-best.cost,
  starters:best.team.map(p=>({id:p.id,name:p.name,position:p.pos,index:p.index,salary_m:p[kind]}))};
}
console.log(JSON.stringify({as_of:'2026-10-05',input_count:rows.length,eligible_count:players.length,
 note:'13-only, 3Y-index, local feasibility bound; no bench, minimum, IR, debt, 2027 season forecast or global proof',
 published:optimize('published'),criticality_without_floor:optimize('criticality')},null,2));
