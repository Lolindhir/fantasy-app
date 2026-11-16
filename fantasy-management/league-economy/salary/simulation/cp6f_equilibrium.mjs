/* CP6f research-only, not a league rule or runtime model.
 * Reproduce from repository root:
 * node fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs
 * Optional --json emits the full scenario JSON instead of the compact summary.
 * Inputs: 2026-10-05 frozen player/criticality/rookie proxy and 2026 rookie draft positions.
 * Forward performance, acquisition decisions and NFL draft ranks are synthetic.
 */
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

export function simulate(csvText, draftsText, {seeds=[11,29,47], factors=[0.90,0.85,0.80,0.75,0.70], seasons=5}={}) {
  const round=x=>Math.floor(x+0.5);
  const median=values=>{const v=[...values].sort((a,b)=>a-b); return v.length%2?v[(v.length-1)/2]:(v[v.length/2-1]+v[v.length/2])/2;};
  const avg=values=>values.reduce((s,v)=>s+v,0)/Math.max(1,values.length);
  const rand=seed=>{let t=seed>>>0;return()=>{t+=0x6D2B79F5;let v=t;v=Math.imul(v^(v>>>15),v|1);v^=v+Math.imul(v^(v>>>7),v|61);return ((v^(v>>>14))>>>0)/4294967296;};};
  const gauss=rng=>(rng()+rng()+rng()+rng()-2)*1.7320508075688772; // approximately unit normal
  const baseRows=csvText.trim().split(/\r?\n/).map(line=>line.split(";"));
  const columns=baseRows.shift();
  const templates=JSON.parse(draftsText).find(x=>x.DraftKey==="2026_Rookie").Picks
    .filter(x=>x.Status==="Picked").sort((a,b)=>a.OverallPick-b.OverallPick);
  if(templates.length!==30)throw Error("Expected 30 2026 rookie draft picks");
  const prevBaseCap=428800000; // Oct 2026 model vintage proxy, not a 2027 cap forecast
  const minPct=year=>year>=8?.005:year>=5?.0045:year>=4?.004:year>=3?.0035:year>=2?.003:.0025;
  const minSalary=(year,previousCap)=>round(previousCap*minPct(year));
  const rookPct=(rank,total)=>rank==null?.0025:.003+(.035-.003)*Math.pow(1-(rank-1)/(total-1),3.5);
  const curves={
    QB:[7.78,6.28,4.99,4.48,4.08,3.27,2.7,2.08,1.7,1.54,1.12,.58],
    RB:[11.56,7.95,7.23,6.77,5.67,5.12,4.3,3.94,3.42,3.07,2.76,2.61,2.29,2.15,1.9,1.39,.99,.94,.66,.41,.1,.01],
    WR:[10.61,8.85,6.64,6,5.32,4.65,3.76,3.48,3.01,2.81,2.75,2.58,2.4,2.35,2.07,1.77,1.51,1.37,1.23,1.19,1.02,.62,.56,.45,.41,.29,.12,.05,.05,.04],
    TE:[6.79,4.75,4.41,3.28,2.88,2.52,1.76,1.57,1.26,.92,.58,.37],
    K:[2.1,1.35,1.11,.69,.24,.11]
  };
  const positions=["QB","RB","WR","TE","K"];
  const flexPositions=new Set(["RB","WR","TE"]);
  const basePlayers=baseRows.map(cols=>{
    const v=Object.fromEntries(columns.map((k,i)=>[k,cols[i]]));
    const year=Number(v.year),perf=Math.max(0,Number(v.performance_3y));
    const baseP=Number(v.salary_I_ohne_base_minimum);
    const price=v.contract==="rookie"?baseP:round(Math.max(baseP,minSalary(year,prevBaseCap)+.5*baseP));
    const baseRookieYear1=year<=3&&v.contract==="rookie"?price/({1:1,2:1.25,3:1.5}[year]):null;
    return {id:v.id,name:v.name,pos:v.position,year,history:[perf,perf,perf],current:perf,
      talent:perf,forecast:perf,price,rookieFirst:baseRookieYear1,
      active:!!v.nfl_team&&v.nfl_team!=="FA",initialRookie:v.contract==="rookie"};
  }).filter(x=>x.id&&positions.includes(x.pos));
  const totalRaw=baseRows.length;
  const capFor=(players,factor)=>round(players.map(x=>x.price).sort((a,b)=>b-a).slice(0,120).reduce((a,b)=>a+b,0)*factor/6);
  const charged=ids=>ids.map(x=>x.price).sort((a,b)=>b-a).slice(0,20).reduce((a,b)=>a+b,0);
  const scorePlayer=(x,style)=>Math.max(0,x.forecast) + (style.rookie*(x.year<=3?Math.min(5,Math.max(0,x.talent-x.forecast)+1.4):0)) + style.depth*.13*Math.max(0,x.current);
  const LINEUP={QB:2,RB:2,WR:2,TE:2,K:1};
  const lineup=(players,field="forecast")=>{
    let ids=new Set(),selected=[],missing=[],s=0;
    for(const [p,n] of Object.entries(LINEUP)){
      const a=players.filter(x=>x.pos===p&&x[field]>0).sort((a,b)=>b[field]-a[field]).slice(0,n);
      if(a.length<n)missing.push(p);
      for(const x of a){ids.add(x.id);selected.push(x);s+=x[field];}
    }
    const f=players.filter(x=>flexPositions.has(x.pos)&&!ids.has(x.id)&&x[field]>0)
      .sort((a,b)=>b[field]-a[field]).slice(0,4);
    if(f.length<4)missing.push("FLEX");
    for(const x of f){selected.push(x);s+=x[field];}
    return {value:s,valid:missing.length===0,starters:selected,missing};
  };
  const playersByRookiePos=Object.fromEntries(positions.map(pos=>[pos,basePlayers
    .filter(x=>x.pos===pos&&x.initialRookie&&x.year>=2&&x.history[0]>0)
    .sort((a,b)=>b.history[0]-a.history[0]).map(x=>x.history[0])]));
  const newDraftRookie=(t,i,seed,rng,previousCap)=>{
    const pos=templates[i].PlayerRef?.Position||"WR";
    const historic=playersByRookiePos[pos]||[7];
    const sample=historic.length?historic[Math.min(historic.length-1,Math.floor(rng()*historic.length))]:7;
    const rawNflRank=Math.max(1,Math.min(80,round((i+1)*1.8+gauss(rng)*7)));
    const fantasyRank=i+1;
    const rookiePct=.65*rookPct(fantasyRank,30)+.35*rookPct(rawNflRank,80);
    const rookieFirst=round(previousCap*rookiePct);
    const draftTrend=(30-i)/30;
    const talent=Math.max(3,Math.min(24,4.5+draftTrend*9 + sample*.45+gauss(rng)*2.0));
    return {id:"S"+seed+"Y"+t+"R"+fantasyRank,name:"Sim-Rookie-"+t+"-"+fantasyRank,pos,year:1,
      history:[0,0,0],current:0,forecast:Math.max(2,talent*.72),talent,price:rookieFirst,
      rookieFirst,active:true,initialRookie:false,rookieSeason:t};
  };
  const undraftedClass=(t,seed,rng,previousCap)=>{
    const picks=[];
    const pattern=["WR","RB","WR","TE","WR","RB","QB","WR","TE","RB"];
    for(let i=0;i<50;i++){
      const pos=pattern[i%pattern.length],historic=playersByRookiePos[pos]||[6];
      const sample=historic.length?historic[Math.floor(rng()*historic.length)]:6;
      const nflRank=rng()<.3?null:31+Math.floor(rng()*50);
      const year1=round(previousCap*(.65*.0025+.35*rookPct(nflRank,80)));
      const gem=rng()<.035?7:0;
      const talent=Math.max(1,Math.min(22,3.3+sample*.38+gauss(rng)*2.3+gem));
      picks.push({id:"S"+seed+"Y"+t+"U"+i,name:"Sim-Undrafted-"+t+"-"+i,pos,year:1,
        history:[0,0,0],current:0,forecast:Math.max(1,talent*.63),talent,price:year1,
        rookieFirst:year1,active:true,initialRookie:false,rookieSeason:t,undrafted:true});
    }
    return picks;
  };
  const salaryPerformance=(p,mod)=>{
    const signal=Math.max(0,p*mod);
    const ratio=signal/20;
    return round(50000000*(ratio<=1?Math.pow(ratio,1.5):1+(ratio-1)*1.5));
  };
  const threeYear=(h)=>{
    if(h[0]===0&&h[1]===0)return 0;
    const mx=Math.max(...h),at=h.indexOf(mx),floor=mx*[.5,.33,.17][at];
    return h.map(v=>Math.max(v,floor)).reduce((a,b)=>a+b,0)/3;
  };
  const reprice=(players,previousCap)=>{
    const ranks=new Map();
    for(const pos of positions){
      const ordered=players.filter(x=>x.pos===pos).map(x=>({id:x.id,p:threeYear(x.history)}))
        .sort((a,b)=>b.p-a.p||a.id.localeCompare(b.id));
      ordered.forEach((x,i)=>{const c=(curves[pos]||[])[i]||0;ranks.set(x.id,.75+.5*Math.min(1,Math.max(0,c/8.4417)));});
    }
    for(const p of players){
      if(p.year<=3 && p.rookieFirst!=null){
        p.price=Math.max(round(p.rookieFirst*({1:1,2:1.25,3:1.5}[p.year])),minSalary(p.year,previousCap));
      } else {
        const ps=salaryPerformance(threeYear(p.history),ranks.get(p.id)||.75);
        const m=minSalary(p.year,previousCap);
        p.price=round(Math.max(ps,m+.5*ps));
      }
    }
  };
  const strategies=[
    {name:"win-now",alpha:.20,rookie:0,depth:.07,cap:.01},
    {name:"balanced",alpha:.35,rookie:.35,depth:.25,cap:.02},
    {name:"rookie-value",alpha:.57,rookie:1.3,depth:.30,cap:.04},
    {name:"cap-value",alpha:.85,rookie:.55,depth:.45,cap:.06},
    {name:"reload",alpha:.52,rookie:1.1,depth:.18,cap:.02},
    {name:"depth",alpha:.63,rookie:.65,depth:1.2,cap:.05}
  ];
  const selectScore=(p,style,rng,stage)=>{
    const strength=scorePlayer(p,style);
    const salaryM=p.price/1e6;
    const agePenalty=p.year>10?(p.year-10)*.07:0;
    if(stage==="cheap")return -salaryM+Math.min(2,strength)*.02;
    if(stage==="depth")return strength/Math.pow(4+salaryM,style.alpha) + .2*style.depth - agePenalty*.2;
    return strength/Math.pow(8+salaryM,style.alpha) - agePenalty*.25;
  };
  const fillCheap=(team,free,C,count,rng)=>{
    for(let n=0;n<count;n++){
      const options=[...free.values()].filter(p=>p.active&&charged([...team,p])<=C);
      options.sort((a,b)=>a.price-b.price||b.forecast-a.forecast||a.id.localeCompare(b.id));
      if(!options.length)return false;
      const p=options[Math.floor(rng()*Math.min(options.length,4))];
      team.push(p);free.delete(p.id);
    }
    return true;
  };
  const fillSlot=(team,free,slot,C,style,rng)=>{
    // Protect budget for all remaining mandatory starters, rather than spending the entire cap in the first few positions.
    const starterStage=slot!=="DEPTH"&&slot!=="CHEAP"&&team.length>=17&&team.length<30;
    const capGate=starterStage?Math.min(C,C*(.18+.81*(team.length-17+1)/13)):C;
    const candidates=[...free.values()].filter(p=>p.active&&
      (slot==="DEPTH"||slot==="CHEAP"||(slot==="FLEX"?flexPositions.has(p.pos):p.pos===slot)) &&
      (slot==="DEPTH"||slot==="CHEAP"||p.forecast>0)&&charged([...team,p])<=capGate);
    if(!candidates.length)return null;
    const stage=slot==="DEPTH"?"depth":slot==="CHEAP"?"cheap":"starter";
    candidates.sort((a,b)=>selectScore(b,style,rng,stage)-selectScore(a,style,rng,stage)||
      b.forecast-a.forecast||a.id.localeCompare(b.id));
    // Controlled, seeded exploration among close-ranked options.
    const index=Math.floor(Math.pow(rng(),2)*Math.min(3,candidates.length));
    const p=candidates[index];team.push(p);free.delete(p.id);
    return p;
  };
  const initTeams=(free,C,styles,rng,N=6,veteransOnly=false)=>{
    const pool=new Map([...free.values()].filter(x=>!veteransOnly||x.year>=4).map(x=>[x.id,x]));
    const teams=Array.from({length:N},(_,i)=>({name:"Team-"+(i+1),style:styles[i%styles.length],players:[]}));
    const errors=[];
    // Reserve all 17 depth slots up front: never accept an expensive partial 13-player roster as a valid 30-player team.
    for(let k=0;k<17;k++)for(let ti=0;ti<N;ti++){
      if(!fillSlot(teams[ti].players,pool,"CHEAP",C,teams[ti].style,rng))errors.push("cheap-"+ti);
    }
    const starterSlots=["QB","RB","WR","TE","QB","RB","WR","TE","K","FLEX","FLEX","FLEX","FLEX"];
    for(let r=0;r<starterSlots.length;r++){
      const order=Array.from({length:N},(_,i)=>r%2?N-1-i:i);
      for(const ti of order)if(!fillSlot(teams[ti].players,pool,starterSlots[r],C,teams[ti].style,rng))errors.push(starterSlots[r]+"-"+ti);
    }
    return {teams,pool,errors};
  };
  const objective=(team,style)=>{
    const lin=lineup(team),s=lin.value;
    const starters=new Set(lin.starters.map(x=>x.id));
    const bench=team.filter(x=>!starters.has(x.id)).map(x=>scorePlayer(x,style)).sort((a,b)=>b-a);
    const depthScore=bench.slice(0,7).reduce((a,b)=>a+b,0);
    const rookies=team.filter(x=>x.year<=3).reduce((s,x)=>s+Math.max(0,x.talent-x.forecast),0);
    return s + style.depth*.06*depthScore + style.rookie*.16*rookies;
  };
  const teamValid=(team,C)=>team.length===30&&lineup(team).valid&&charged(team)<=C+1;
  const repair=(team,pool,C,rng,maxMoves=45)=>{
    let n=0;
    while(charged(team.players)>C&&n++<maxMoves){
      const current=charged(team.players);
      const freeCheap=[...pool.values()].filter(x=>x.active).sort((a,b)=>a.price-b.price).slice(0,48);
      const base=objective(team.players,team.style);
      let best=null,metric=-Infinity;
      for(const remove of team.players){
        const afterRemoval=team.players.filter(x=>x.id!==remove.id);
        for(const add of freeCheap){
          if(add.id===remove.id)continue;
          const next=[...afterRemoval,add],now=charged(next),relief=current-now;
          if(relief<=0||!lineup(next).valid)continue;
          const loss=Math.max(0,base-objective(next,team.style));
          const utility=relief/1e6-.34*loss;
          if(utility>metric){metric=utility;best={remove,add,next,now};}
        }
      }
      if(!best)break;
      team.players=best.next;pool.delete(best.add.id);pool.set(best.remove.id,best.remove);
    }
    return n;
  };
  const optimizeFA=(teams,pool,C,rng,passes=5)=>{
    let swaps=0;
    const ids=Array.from({length:teams.length},(_,i)=>i);
    for(let round=0;round<passes;round++){
      for(const i of (round%2?ids.slice().reverse():ids)){
        const team=teams[i],base=objective(team.players,team.style);
        const topAvailable=[...pool.values()].filter(x=>x.active&&x.forecast>0)
          .sort((a,b)=>selectScore(b,team.style,rng,"starter")-selectScore(a,team.style,rng,"starter")).slice(0,15);
        const bargain=[...pool.values()].filter(x=>x.active).sort((a,b)=>a.price-b.price).slice(0,5);
        const candidates=[...new Map([...topAvailable,...bargain].map(x=>[x.id,x])).values()];
        let best=null,bestGain=.10;
        for(const remove of team.players){
          const remaining=team.players.filter(x=>x.id!==remove.id);
          for(const add of candidates){
            const next=[...remaining,add];
            if(charged(next)>C||!lineup(next).valid)continue;
            const gain=objective(next,team.style)-base;
            const capBonus=team.style.cap*(charged(team.players)-charged(next))/1e6;
            const util=gain+capBonus;
            if(util>bestGain){bestGain=util;best={remove,add,next};}
          }
        }
        if(best){team.players=best.next;pool.delete(best.add.id);pool.set(best.remove.id,best.remove);swaps++;}
      }
    }
    return swaps;
  };
  const expansion=(free,C,rng)=>{
    const veteranPool=new Map([...free.values()].filter(x=>x.active&&x.year>=4&&x.current>0).map(x=>[x.id,x]));
    // Equal opportunity test: all shadow entrants use the same balanced style. Different incumbent styles remain in the six-team dynamics.
    const expStyles=Array.from({length:4},()=>strategies[1]);
    const e=initTeams(veteranPool,C,expStyles,rng,4,true);
    return {scores:e.teams.map(t=>lineup(t.players).value),rosters:e.teams.map(t=>t.players.length),
      compliant:e.teams.map(t=>teamValid(t.players,C)),capUses:e.teams.map(t=>charged(t.players)),
      errors:e.errors.length,freeVeterans:veteranPool.size,
      possible:e.errors.length===0&&e.teams.every(t=>teamValid(t.players,C))};
  };
  const marketStats=(players,teams,free,C)=>{
    const tierRank=new Map(),limits={QB:[6,12],RB:[12,22],WR:[12,30],TE:[6,12]};
    for(const [pos,[a,b]]of Object.entries(limits)){
      players.filter(x=>x.active&&x.pos===pos&&x.forecast>0).sort((x,y)=>y.forecast-x.forecast)
        .forEach((p,i)=>tierRank.set(p.id,i<a?1:i<b?2:3));
    }
    const candidates=[...free.values()].filter(x=>x.active&&x.year>=4&&(tierRank.get(x.id)===1||tierRank.get(x.id)===2));
    const expensive=candidates.filter(x=>x.price>=C*.05);
    const reachable=new Set(),gainful=new Set(),buyerTeams=new Set();
    for(const p of candidates){
      for(let ti=0;ti<teams.length;ti++){
        const t=teams[ti],oldScore=lineup(t.players).value;
        for(let i=0;i<t.players.length;i++){
          const next=t.players.slice();next[i]=p;
          if(charged(next)>C||!lineup(next).valid)continue;
          reachable.add(p.id);buyerTeams.add(ti);
          if(lineup(next).value>oldScore+.5)gainful.add(p.id);
          break;
        }
      }
    }
    return {freeTier1:candidates.filter(x=>tierRank.get(x.id)===1).length,
      freeTier2:candidates.filter(x=>tierRank.get(x.id)===2).length,
      expensiveT12:expensive.length,financiallyReachable:reachable.size,improvingSwap:gainful.size,
      buyersWithOnePath:buyerTeams.size,
      namedExamples:expensive.slice().sort((a,b)=>b.forecast-a.forecast).slice(0,6).map(x=>x.name)};
  };
  const summary=[];
  for(const factor of factors)for(const seed of seeds){
    const rng=rand(seed+Math.round(factor*10000)*391);
    const players=basePlayers.map(x=>({...x,history:[...x.history]}));
    const all=new Map(players.map(x=>[x.id,x]));
    let prevCap=capFor(players,factor),C=prevCap;
    const initialFree=new Map(players.filter(x=>x.active).map(x=>[x.id,x]));
    const shift=seed%6,styles=Array.from({length:6},(_,i)=>strategies[(i+shift)%6]);
    const initial=initTeams(initialFree,C,styles,rng,6);
    const teams=initial.teams,free=initial.pool;
    let priorSeasonScores=teams.map(t=>lineup(t.players).value);
    const initialValidation={missing:teams.filter(t=>!teamValid(t.players,C)).length,
      rosterSizes:teams.map(t=>t.players.length),errors:initial.errors.length};
    const yearly=[];
    for(let season=1;season<=seasons;season++){
      // Synthetic outcomes: aging, development and idiosyncratic performance variance.
      for(const p of players){
        const currentAge=p.year;
        const aging=currentAge<=3?1.035:currentAge<=6?1.007:currentAge<=8?.982:currentAge<=10?.948:currentAge<=12?.895:.79;
        const target=p.talent*(currentAge<=3?1.10:currentAge<=6?1:currentAge<=9?.93:currentAge<=12?.78:.44);
        const shock=gauss(rng)*(p.current>0?1.0:.25);
        const next=Math.max(0,Math.min(29,.64*p.current*aging+.36*target+shock));
        p.history=[next,p.history[0],p.history[1]];
        p.current=next;p.year++;
        p.forecast=Math.max(0,next*.8+p.talent*.20);
        p.talent=p.talent*(p.year>10?.974:1);
      }
      // Annual reprice (previous Cap is the Year1 rookie/minimum anchor).
      reprice(players,prevCap);
      C=capFor(players,factor);
      // Rookie picks are preassigned NFL rank proxies and evaluated at own fantasy pick.
      const entrants=templates.map((_,i)=>newDraftRookie(season,i,seed,rng,prevCap));
      const extraRookies=undraftedClass(season,seed,rng,prevCap);
      for(const rookie of [...entrants,...extraRookies]){players.push(rookie);all.set(rookie.id,rookie);}
      // Rebuild live free pool from ownership: the 30 newcomers were not previously owned.
      free.clear();
      const owned=new Set(teams.flatMap(t=>t.players.map(x=>x.id)));
      for(const p of players)if(p.active&&!owned.has(p.id))free.set(p.id,p);
      // Cap-free draft window: release 5 least valuable pieces per team, preserving 13 valid starters where possible.
      const released=[];
      for(const team of teams){
        for(let k=0;k<5;k++){
          const options=team.players.map(p=>{
            const rem=team.players.filter(x=>x.id!==p.id);
            return {p,rem,valid:lineup(rem).valid,loss:objective(team.players,team.style)-objective(rem,team.style)};
          }).sort((a,b)=>Number(b.valid)-Number(a.valid)||a.loss-b.loss||b.p.price-a.p.price);
          const chosen=options[0];
          team.players=chosen.rem;released.push(chosen.p);free.set(chosen.p.id,chosen.p);
        }
      }
      // Five rookie rounds, one pick per incumbent; order uses previous-season performance, 5th/6th/4th/3rd/2nd/1st.
      // The team standings below are synthetic; no real rookie-pick trade allocations inferred.
      const order=teams.map((t,i)=>({i,score:priorSeasonScores[i]})).sort((a,b)=>a.score-b.score).map(x=>x.i);
      const pickorder=order.length===6?[order[1],order[0],order[2],order[3],order[4],order[5]]:order;
      const unsigned=entrants.slice();
      for(let roundN=0;roundN<5;roundN++)for(const i of pickorder){
        const team=teams[i];const p=unsigned.splice(0,1)[0];
        if(!p)throw Error("Missing synthetic drafted rookie");
        team.players.push(p);free.delete(p.id);
      }
      // Deadline, mandatory 30-player rosters; deal with repriced cap before FA draft.
      let repairMoves=0;
      for(const team of teams)repairMoves+=repair(team,free,C,rng);
      const preLegal=teams.filter(t=>!teamValid(t.players,C)).length;
      const preExp=expansion(free,C,rng);
      // FA market: five rounds of voluntary full-roster one-for-one add/drop decisions.
      const faMoves=optimizeFA(teams,free,C,rng,5);
      const postLegal=teams.filter(t=>!teamValid(t.players,C)).length;
      const postExp=expansion(free,C,rng);
      const market=marketStats(players,teams,free,C);
      const scores=teams.map(t=>lineup(t.players).value);
      priorSeasonScores=scores.slice();
      const capUses=teams.map(t=>charged(t.players));
      const heldRookie=teams.map(t=>t.players.filter(p=>p.year<=3).length);
      const expansionMedian=median(postExp.scores),incumbentMedian=median(scores);
      yearly.push({season,cap:C,preLegal,postLegal,repairMoves,faMoves,
        incumbentScores:scores,incumbentCapUses:capUses,incumbentRookies:heldRookie,
        preExpansion:preExp,postExpansion:postExp,market,
        expansionRatio:postExp.possible&&postLegal===0?expansionMedian/incumbentMedian:null,
        weakestExpansionRatio:postExp.possible&&postLegal===0?Math.min(...postExp.scores)/Math.min(...scores):null,
        freePoolSize:free.size,freeVeterans:[...free.values()].filter(x=>x.active&&x.year>=4&&x.current>0).length});
      prevCap=C;
    }
    summary.push({factor,seed,initialValidation,yearly});
  }
  const grouped=factors.map(f=>{
    const scenarios=summary.filter(x=>x.factor===f);
    const last=scenarios.map(x=>x.yearly.at(-1));
    const valid=last.filter(x=>x.postLegal===0&&x.postExpansion.possible);
    const ratios=valid.map(x=>x.expansionRatio).filter(x=>x!=null);
    return {factor:f,seeds:scenarios.length,fullFiveCycleValid:scenarios.filter(x=>x.initialValidation.missing===0&&x.initialValidation.errors===0&&x.yearly.every(y=>y.postLegal===0&&y.preLegal===0)).length,
      fiveCycleOutcome:scenarios.map(x=>({seed:x.seed,allCyclesLegal:x.initialValidation.missing===0&&x.yearly.every(y=>y.preLegal===0&&y.postLegal===0),
        capM:round(x.yearly.at(-1).cap/1e5)/10,incumbentMedian:+median(x.yearly.at(-1).incumbentScores).toFixed(2),
        expMedian:+median(x.yearly.at(-1).postExpansion.scores).toFixed(2),
        expMedianRatio:x.yearly.at(-1).expansionRatio===null?null:+x.yearly.at(-1).expansionRatio.toFixed(3),
        weakestRelativeToWeakest:x.yearly.at(-1).weakestExpansionRatio===null?null:+x.yearly.at(-1).weakestExpansionRatio.toFixed(3),
        postExpansionValid:x.yearly.at(-1).postExpansion.possible,
        rosterSizes:x.yearly.at(-1).postExpansion.rosters,faMoves:x.yearly.reduce((s,y)=>s+y.faMoves,0)})),
      validFifthYearSeeds:valid.length,medianExpansionRatio:ratios.length?+median(ratios).toFixed(3):null,
      rangeExpansionRatio:ratios.length?[+Math.min(...ratios).toFixed(3),+Math.max(...ratios).toFixed(3)]:null,
      averageFAMoves:+avg(scenarios.map(x=>x.yearly.reduce((s,y)=>s+y.faMoves,0))).toFixed(1),
      incompleteCycles:scenarios.flatMap(x=>x.yearly.filter(y=>y.preLegal>0||y.postLegal>0).map(y=>({seed:x.seed,year:y.season,pre:y.preLegal,post:y.postLegal}))).slice(0,30)};
  });
  return {schemaVersion:1,status:"research-only-synthetic-5-cycle-experiment-not-forecast",
    basis:{inputRows:totalRaw,usablePlayers:basePlayers.length,rookieClassTemplate:templates.length,extraUndraftedRookiesPerYear:50,seasonCount:seasons,
      factors,seeds,starterSlots:"2QB 2RB 2WR 2TE 4FLEX 1K",roster:30,capRelevant:20,
      salary:"Criticality rank DMLI 2023-25 fixed rank curves; normalized k1.5; 3-year floor; dynamic Top120/6*factor; glide min; 3Y rookies",
      deadCap:"DISABLED for target-state isolation",trades:"NOT SIMULATED",rookieNFLRank:"sampled from 2026 fantasy pick order with Gaussian noise; not actual future NFL draft results",
      rookiePerformance:"synthetic conditional distribution from archived 2026 cohort and historical year2/3 rookie performance; 50 free undrafted rookies/year",
      startup:"neutral startup from 2026 player population, then 5 simulated seasons; no 2026 ownership rights",
      limitation:"synthetic stochastic trajectories not actual NFL 2027-2031; no dynamic future Criticality rank-curve recalculation by NFL seasons, no injuries/week-scoped decisions"},
    results:grouped,runs:summary};
}

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../../../..");
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const csv=fs.readFileSync(path.join(root,"fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv"),"utf8");
  const drafts=fs.readFileSync(path.join(root,"public/data/Drafts.json"),"utf8");
  const out=simulate(csv,drafts);
  if(process.argv.includes("--json"))console.log(JSON.stringify(out,null,2));
  else console.log(JSON.stringify({basis:out.basis,results:out.results},null,2));
}
