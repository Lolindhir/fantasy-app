#!/usr/bin/env node
/**
 * CP6i: 40-place, full-salary roster ceiling research (read-only).
 * Run from the fantasy-app repository root:
 *   node fantasy-management/league-economy/salary/simulation/cp6i_starter_ceiling.mjs
 * Optional deterministic local-fixture inputs: CP6I_PLAYERS, CP6I_CSV.
 * Prints JSON; never writes or modifies league data.
 */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = process.cwd();
const playerPath = process.env.CP6I_PLAYERS || path.join(root, 'public/data/Players.json');
const csvPath = process.env.CP6I_CSV || path.join(root, 'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv');
const priorCap = 428784607; // Archived 2025 reference cap, NOT a 2027 forecast.
const players = JSON.parse(fs.readFileSync(playerPath, 'utf8'));
const csvLines = fs.readFileSync(csvPath, 'utf8').trim().split(/\r?\n/);
const headings = csvLines.shift().split(';');
const rows = csvLines.map((line) => {
  const cells = line.split(';');
  assert.equal(cells.length, headings.length, 'Unexpected CSV row shape');
  return Object.fromEntries(headings.map((k, i) => [k, cells[i]]));
});
assert(Array.isArray(players) && players.length > 0);
assert(rows.length > 0);

function conceptSalary(row) {
  const P = Number(row.salary_I_ohne_base_minimum) || 0;
  if (row.contract === 'rookie') return P;
  const year = Number(row.year);
  assert(year >= 4, 'Unknown performance contract year');
  const rate = year === 4 ? 0.004 : year <= 7 ? 0.0045 : 0.005;
  const M = Math.round(priorCap * rate);
  return Math.round(Math.max(P, M + 0.5 * P));
}
function top120Total(values) {
  return [...values].sort((a, b) => b - a).slice(0, 120).reduce((a, b) => a + b, 0);
}
const capTotals = {
  live: top120Total(players.map((p) => Number(p.Salary) || 0)),
  concept: top120Total(rows.map(conceptSalary)),
};
const conceptById = new Map(rows.map((r) => [String(r.id), conceptSalary(r)]));
const positions = ['QB', 'RB', 'WR', 'TE', 'K'];
const coverage = { QB: 1, RB: 2, WR: 2, TE: 1, K: 1 };
const liveEligible = players.filter((p) =>
  positions.includes(p.Position) && p.TeamAbbr && p.TeamAbbr !== 'FA' &&
  !p.IsFreeAgent && ((Number(p.GamesPlayed) || 0) > 0 || (Number(p.FantasyPointsAvgGame) || 0) > 0.15)
).map((p) => {
  const games = Number(p.GamesPlayed) || 0;
  const now = Number(p.FantasyPointsAvgGame) || 0;
  const previous = Number(p.PointHistory?.SeasonMinus1?.AvgPotentialGame) || 0;
  const score = Math.max(0, games === 0 ? 0.38 * previous : previous > 0
    ? (games * now + 2.5 * previous) / (games + 2.5)
    : now * (games >= 4 ? 0.92 : games / (games + 2)));
  return {
    id: String(p.ID), name: p.Name, pos: p.Position, score,
    live: Number(p.Salary) || 0,
    concept: conceptById.get(String(p.ID)) ?? null,
  };
});
const unmatched = liveEligible.filter((p) => p.concept === null).map((p) => p.name);
const pool = liveEligible.filter((p) => p.concept !== null && p.score > 0.15);
const summedScore = (ps) => ps.reduce((v, p) => v + p.score, 0);
const cost = (ps, mode) => ps.reduce((v, p) => v + p[mode], 0);
const round = (x, places = 3) => x == null ? null : Number(x.toFixed(places));

function optimize(mode) {
  const cap = capTotals[mode] / 6; // Exact float for sub-dollar feasibility tests.
  const byPosition = Object.fromEntries(positions.map((p) => [p, pool.filter((x) => x.pos === p)]));
  for (const p of positions) assert(byPosition[p].length >= (p === 'K' ? 1 : 2));
  function bestPenalized(lambda) {
    const sorted = Object.fromEntries(positions.map((p) => [p,
      [...byPosition[p]].sort((a, b) =>
        (b.score - lambda * b[mode] / 1e6) - (a.score - lambda * a[mode] / 1e6) || a[mode] - b[mode])
    ]));
    const starters = [...sorted.QB.slice(0, 2), sorted.K[0]];
    const flexPool = [];
    for (const p of ['RB', 'WR', 'TE']) {
      starters.push(...sorted[p].slice(0, 2));
      flexPool.push(...sorted[p].slice(2));
    }
    flexPool.sort((a, b) =>
      (b.score - lambda * b[mode] / 1e6) - (a.score - lambda * a[mode] / 1e6));
    return starters.concat(flexPool.slice(0, 4));
  }
  const candidates = [];
  const seen = new Set();
  function add(starters) {
    const key = starters.map((p) => p.id).sort().join(',');
    if (seen.has(key)) return;
    seen.add(key);
    candidates.push({ starters, score: summedScore(starters), price: cost(starters, mode) });
  }
  let lo = 0, hi = 10, upper = Infinity;
  add(bestPenalized(0));
  for (let i = 0; i < 55; i++) {
    const lambda = (lo + hi) / 2;
    const team = bestPenalized(lambda);
    add(team);
    upper = Math.min(upper, summedScore(team) + lambda * (cap - cost(team, mode)) / 1e6);
    if (cost(team, mode) > cap) lo = lambda; else hi = lambda;
  }
  for (let i = 0; i < 280; i++) {
    const lambda = i * 0.004;
    const team = bestPenalized(lambda);
    add(team);
    upper = Math.min(upper, summedScore(team) + lambda * (cap - cost(team, mode)) / 1e6);
  }
  const starts = [...candidates].sort((a, b) => b.score - a.score).slice(0, 5);
  // One-player neighbor search: valid QB2/K1 and 2+ RB/WR/TE invariants.
  for (const start of starts) {
    const counts = Object.fromEntries(positions.map((p) => [p,
      start.starters.filter((x) => x.pos === p).length]));
    const used = new Set(start.starters.map((x) => x.id));
    for (let i = 0; i < start.starters.length; i++) {
      for (const newcomer of pool) {
        if (used.has(newcomer.id)) continue;
        const outgoing = start.starters[i];
        if (outgoing.pos !== newcomer.pos && (
          outgoing.pos === 'QB' || outgoing.pos === 'K' ||
          newcomer.pos === 'QB' || newcomer.pos === 'K' ||
          counts[outgoing.pos] <= 2
        )) continue;
        const next = [...start.starters];
        next[i] = newcomer;
        add(next);
      }
    }
  }
  const experiments = [];
  for (const roster of [13, 20, 30, 35, 40]) {
    for (const benchFloor of roster === 13 ? [0] : [0, 5, 8]) {
      const available = pool.filter((p) => p.score >= benchFloor)
        .sort((a, b) => a[mode] - b[mode]);
      const indexed = Object.fromEntries(positions.map((p) => [p,
        available.filter((x) => x.pos === p)]));
      let best = null;
      for (const c of candidates) {
        if (c.price > cap) continue;
        const used = new Set(c.starters.map((x) => x.id));
        const bench = [];
        if (roster > 13) {
          for (const p of positions) {
            let picked = 0;
            for (const x of indexed[p]) {
              if (used.has(x.id)) continue;
              bench.push(x); used.add(x.id);
              if (++picked === coverage[p]) break;
            }
            if (picked !== coverage[p]) break;
          }
          if (bench.length !== 7) continue;
          for (const x of available) {
            if (bench.length === roster - 13) break;
            if (used.has(x.id)) continue;
            bench.push(x); used.add(x.id);
          }
          if (bench.length !== roster - 13) continue;
        }
        const bankCost = cost(bench, mode);
        if (c.price + bankCost > cap) continue;
        if (!best || c.score > best.score) best = { ...c, bankCost, bench };
      }
      experiments.push({
        roster_occupied: roster, bench_score_floor: benchFloor,
        achieved_starter_index: best ? round(best.score) : null,
        starter_salary_dollars: best?.price ?? null,
        bench_salary_dollars: best?.bankCost ?? null,
        remaining_cap_dollars: best ? Math.floor(cap - best.price - best.bankCost) : null,
        avg_bench_index: best?.bench.length ? round(summedScore(best.bench) / best.bench.length, 2) : null,
        example_starters: roster === 13 && best ? best.starters.map((p) => p.name) : null,
      });
    }
  }
  return {
    cap_total_top120_dollars: capTotals[mode], cap_per_team_dollars: round(cap, 3),
    all_star_index: round(summedScore(bestPenalized(0))),
    all_star_starter_salary_dollars: cost(bestPenalized(0), mode),
    relaxed_upper_bound_index_13: round(upper),
    valid_candidate_lineups: candidates.length, experiments,
  };
}
const output = {
  research_id: 'CP6i', snapshot_date: '2026-11-19', status: 'heuristic research, no league rule',
  source_paths: { players: 'public/data/Players.json', price_proxy: 'fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv' },
  price_model: '2026 published vs historical Oct-05 candidate I + glide',
  cap_model: 'top 120 player salaries / 6, no 0.90 factor, full held salary',
  prior_cap_for_historical_veteran_minimum_dollars: priorCap,
  eligibility: { live_eligible: liveEligible.length, paired_eligible: liveEligible.length - unmatched.length,
    paired_positive_index: pool.length, missing_proxy_player_names: unmatched },
  method: 'Lagrangian starter relaxation + single-swap feasible candidates; minimum-price distinct reserve with QB1/RB2/WR2/TE1/K1; not an exact optimizer',
  worlds: { published_2026: optimize('live'), criticality_october_proxy: optimize('concept') },
};
console.log(JSON.stringify(output, null, 2));
