#!/usr/bin/env node
"use strict";

/**
 * CP3j: research-only, paired participation-aware Best Ball simulation.
 *
 * Historical fantasy rosters are archived end-of-week snapshots, not proven
 * Tuesday/as-of rosters. Availability v3 historical products are retrospective
 * revisions. This is NOT a true point-in-time experiment, production model,
 * manager-score or win-probability evaluation.
 *
 * Inputs: only existing accepted product owners plus archived league week
 * rosters and canonical weekly positions, exactly as in CP3b/CP3d.
 *
 * node research/matchup-projections/2026/backtest_product_pplay_best_ball.cjs --self-test
 * node research/matchup-projections/2026/backtest_product_pplay_best_ball.cjs --draws=1200
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { samplesForSeason, selectModel, forecast } = require("./calibrate_product_pplay.cjs");
const { optimize, randomNormal } = require("./simulate_best_ball_ranges.cjs");
const { slots } = require("./ablate_best_ball_oracle_availability.cjs");

const ROOT = path.resolve(__dirname, "../../..");
const SEASONS_TRAIN = [2016, 2017, 2018, 2019, 2020, 2021, 2022];
const SEASONS_VALIDATION = [2023, 2024];
const TEST_WEEKS = [5, 6, 7, 8, 9, 10];
const POS = new Set(["QB", "RB", "WR", "TE", "K"]);
const Z90 = 1.6448536269514722;
const ARMS = ["raw", "priorStatus", "laggedHistory", "oracle"];

function load(relative) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relative), "utf8"));
}
function indexBy(records, key) {
  const result = new Map();
  for (const rec of records) {
    const id = rec[key];
    assert.ok(typeof id === "string" && id, "Missing " + key);
    assert.ok(!result.has(id), "Duplicate " + key + ": " + id);
    result.set(id, rec);
  }
  return result;
}
function availabilityWeeks(document) {
  assert.equal(document.SchemaVersion, 3);
  assert.equal(document.ProductVersion, "nfl-player-availability-v3");
  const weeks = new Map();
  const seen = new Set();
  for (const rec of document.Records) {
    assert.ok(typeof rec.CanonicalPlayerID === "string" && rec.CanonicalPlayerID);
    assert.ok(Number.isInteger(rec.Week) && rec.Week >= 1 && rec.Week <= 22);
    assert.ok(rec.Played === true || rec.Played === false || rec.Played === null);
    const key = rec.Week + ":" + rec.CanonicalPlayerID;
    assert.ok(!seen.has(key), "Duplicate availability row " + key);
    seen.add(key);
    if (!weeks.has(rec.Week)) weeks.set(rec.Week, new Map());
    weeks.get(rec.Week).set(rec.CanonicalPlayerID, rec);
  }
  return weeks;
}
// Mirror the exact CP3i prior-week grouping, not target-week injury/report.
function rosterGroup(prior) {
  const status = prior.Roster?.Status ?? null;
  if (status === "ACT" || status === "INA") return status;
  if (status === "RES" || status === "PUP") return "RESERVE";
  return status === null ? "NONE" : "OTHER";
}
function priorGroup(prior) {
  return prior.Played === true ? "T" : prior.Played === false ? "F" : "U";
}
function lagFeatures(weeks, week, id) {
  const prior = weeks.get(week - 1)?.get(id);
  if (!prior) return null; // CP3i risk set requires the prior-week record.
  const hist = [];
  for (let w = 1; w < week; ++w) {
    const rec = weeks.get(w)?.get(id);
    if (rec?.GameType === "REG" && typeof rec.Played === "boolean") hist.push(Number(rec.Played));
  }
  return { roster: rosterGroup(prior), prior: priorGroup(prior),
    h4: hist.slice(-4), h8: hist.slice(-8) };
}
function participantProbabilities(weeks, week, id, trained, selected) {
  const feature = lagFeatures(weeks, week, id);
  if (!feature) return null;
  return {
    priorStatus: forecast(feature, trained, 20, null, 0),
    laggedHistory: forecast(feature, trained, selected.groupK, selected.alpha, selected.window),
  };
}
function fitFrozenModel(documents) {
  const train = [], validation = [];
  for (const year of [...SEASONS_TRAIN, ...SEASONS_VALIDATION]) {
    const doc = documents.get(year);
    assert.ok(doc, "Missing trained v3 product " + year);
    const rows = samplesForSeason(doc, year).rows;
    (year <= 2022 ? train : validation).push(...rows);
  }
  const model = selectModel(train, validation);
  assert.deepEqual(
    [model.best.groupK, model.best.alpha, model.best.window],
    [400, 8, 4],
    "CP3i validation choice has drifted; do not silently refit"
  );
  assert.equal(train.length, 128087, "CP3i training population drift");
  assert.equal(validation.length, 36134, "CP3i validation population drift");
  return { trained: model.trained, selected: model.best, trainCount: train.length,
    validationCount: validation.length };
}
function uniformGenerator(seed) {
  let state = seed >>> 0;
  return function uniform() {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return (state + 0.5) / 4294967296;
  };
}
function stableSeed(seed, week, rosterID) {
  let x = (seed ^ Math.imul(week, 2246822519)) >>> 0;
  for (const char of rosterID) x = (Math.imul(x ^ char.charCodeAt(0), 16777619)) >>> 0;
  return x;
}
function mean(values) { return values.reduce((sum, n) => sum + n, 0) / values.length; }
function q(sorted, frac) { return sorted[Math.floor((sorted.length - 1) * frac)]; }
function checkFinite(value, label) {
  assert.ok(Number.isFinite(value), "Nonfinite " + label);
  return value;
}
function monteCarlo(formation, candidates, draws, seed, week, rosterID, oracleValid) {
  const normal = randomNormal(stableSeed(seed, week, rosterID));
  const uniform = uniformGenerator(stableSeed(seed ^ 0x9e3779b9, week, rosterID));
  const samples = Object.fromEntries(ARMS.filter(a => a !== "oracle" || oracleValid).map(a => [a, []]));
  const oraclePlayers = oracleValid ? candidates.filter(c => c.oraclePlayed === true) : [];
  for (let draw = 0; draw < draws; ++draw) {
    for (const candidate of candidates) {
      candidate.draw = candidate.mean + candidate.sigma * normal();
      candidate.u = uniform();
    }
    samples.raw.push(optimize(formation, candidates, "draw").points);
    samples.priorStatus.push(optimize(formation,
      candidates.filter(c => c.u < c.priorStatus), "draw").points);
    samples.laggedHistory.push(optimize(formation,
      candidates.filter(c => c.u < c.laggedHistory), "draw").points);
    if (oracleValid) samples.oracle.push(optimize(formation, oraclePlayers, "draw").points);
  }
  return Object.fromEntries(Object.entries(samples).map(([arm, scores]) => {
    scores.sort((a, b) => a - b);
    return [arm, { expected: mean(scores), q10: q(scores, .10), q90: q(scores, .90) }];
  }));
}
function runWeek({ week, availability, league, pwf, weeklyRoster, matchups, twp,
  trained, selected, draws, seed }) {
  const position = indexBy(weeklyRoster.Records, "CanonicalPlayerID");
  const projection = indexBy(pwf.Records, "CanonicalPlayerID");
  const targets = indexBy(twp.Teams, "CanonicalLeagueRosterID");
  const formation = slots(league);
  assert.equal(pwf.Season, 2026);
  assert.equal(pwf.Week, week);
  assert.equal(weeklyRoster.Season, 2026);
  assert.equal(weeklyRoster.Week, week);
  assert.equal(twp.Season, 2026);
  assert.equal(twp.Week, week);
  assert.equal(pwf.Materialization?.ActualScoringEvidenceFinalized, true);
  assert.ok(twp.FinalityEvidence);
  assert.equal(matchups.length, 6);
  const rows = [];
  for (const team of matchups) {
    const id = team.CanonicalLeagueRosterID;
    const target = targets.get(id);
    assert.ok(target, "Missing TWP team " + id);
    const candidates = [], seen = new Set(), missingPrior = [], missingOutcome = [];
    let excludedProjectionOrPosition = 0, nonPlayed = 0, unknownOutcome = 0;
    for (const player of team.Players) {
      const pid = player.CanonicalPlayerID;
      assert.ok(typeof pid === "string" && pid && !seen.has(pid), "Duplicate/empty fantasy candidate");
      seen.add(pid);
      const pos = position.get(pid)?.Position;
      const rec = projection.get(pid);
      const p = rec?.Projection;
      if (!POS.has(pos) || p?.Status !== "available") {
        excludedProjectionOrPosition++;
        continue; // exact CP3b candidate pool
      }
      assert.equal(p.ParticipationCondition, "conditional-on-participation");
      assert.equal(p.AvailabilityAdjustmentApplied, false);
      assert.equal(p.PredictionRange?.Level, .90);
      assert.ok(p.PredictionRange.Upper >= p.PredictionRange.Lower);
      assert.equal(rec.Actual?.State, "final");
      const probs = participantProbabilities(availability, week, pid, trained, selected);
      if (!probs) {
        missingPrior.push(pid);
        continue; // fail-closed for this team; do not infer p=0 or 1
      }
      const outcome = availability.get(week)?.get(pid);
      let oraclePlayed = null;
      if (outcome?.GameType === "REG" && outcome.State !== "bye" &&
          typeof outcome.Played === "boolean") {
        oraclePlayed = outcome.Played; // evaluation / oracle only
        if (!oraclePlayed) nonPlayed++;
      } else {
        missingOutcome.push(pid);
        unknownOutcome++;
      }
      candidates.push({
        id: pid, pos,
        mean: checkFinite(p.Points, "PWF mean"),
        sigma: (checkFinite(p.PredictionRange.Upper, "PWF upper") -
          checkFinite(p.PredictionRange.Lower, "PWF lower")) / (2 * Z90),
        actual: checkFinite(rec.Actual.Points, "PWF actual"),
        priorStatus: probs.priorStatus, laggedHistory: probs.laggedHistory,
        oraclePlayed, draw: 0, u: 0,
      });
    }
    const row = {
      week, rosterID: id, target: checkFinite(target.PotentialPoints, "TWP potential"),
      rosterCount: team.Players.length, candidateCount: candidates.length,
      excludedProjectionOrPosition, missingPriorCount: missingPrior.length,
      missingPriorIDs: missingPrior, unknownOutcome, missingOutcomeIDs: missingOutcome,
      observedNonPlayed: nonPlayed, status: "ok",
    };
    // All original PWF-eligible candidates must have CP3i risk-set features.
    if (missingPrior.length) { row.status = "missing-prior"; rows.push(row); continue; }
    const projected = optimize(formation, candidates, "mean");
    if (projected.unfilled) {
      row.status = "unfilled-projected-slots";
      row.unfilled = projected.unfilled;
      rows.push(row); continue;
    }
    row.rawProjected = projected.points;
    const realized = optimize(formation, candidates, "actual");
    row.actualCandidateBestBall = realized.points;
    row.actualReproducesTWP = realized.unfilled === 0 &&
      Math.abs(realized.points - row.target) <= .05;
    const mc = monteCarlo(formation, candidates, draws, seed, week, id,
      missingOutcome.length === 0);
    row.arm = mc;
    row.averagePriorStatusP = mean(candidates.map(x => x.priorStatus));
    row.averageLaggedHistoryP = mean(candidates.map(x => x.laggedHistory));
    rows.push(row);
  }
  assert.equal(rows.length, 6);
  return rows;
}
function summarize(rows) {
  const valid = rows.filter(r => r.status === "ok");
  function scores(arm, subset) {
    const members = subset.filter(r => r.arm[arm]);
    if (!members.length) return null;
    const errors = members.map(r => r.arm[arm].expected - r.target);
    return {
      n: members.length,
      mae: mean(errors.map(Math.abs)),
      bias: mean(errors),
      rmse: Math.sqrt(mean(errors.map(e => e * e))),
      coverage80: mean(members.map(r => Number(r.target >= r.arm[arm].q10 &&
        r.target <= r.arm[arm].q90))),
      meanForecast: mean(members.map(r => r.arm[arm].expected)),
      meanActual: mean(members.map(r => r.target)),
    };
  }
  const byArm = Object.fromEntries(ARMS.map(a => [a, scores(a, valid)]));
  return {
    totalTeamWeeks: rows.length, paired: valid.length,
    byStatus: Object.fromEntries([...new Set(rows.map(r => r.status))].map(s =>
      [s, rows.filter(r => r.status === s).length])),
    totalProjectedCandidateCount: rows.reduce((s, r) => s + r.candidateCount + r.missingPriorCount, 0),
    totalMissingPrior: rows.reduce((s, r) => s + r.missingPriorCount, 0),
    totalMissingOutcome: rows.reduce((s, r) => s + r.unknownOutcome, 0),
    observedNonPlayedOnPaired: valid.reduce((s, r) => s + r.observedNonPlayed, 0),
    targetReproduced: valid.filter(r => r.actualReproducesTWP).length,
    byArm,
    strictlyTargetAligned: {
      n: valid.filter(r => r.actualReproducesTWP).length,
      byArm: Object.fromEntries(ARMS.map(a =>
        [a, scores(a, valid.filter(r => r.actualReproducesTWP))])),
    },
    perWeek: TEST_WEEKS.map(w => ({
      week: w, n: valid.filter(r => r.week === w).length,
      raw: scores("raw", valid.filter(r => r.week === w)),
      priorStatus: scores("priorStatus", valid.filter(r => r.week === w)),
      laggedHistory: scores("laggedHistory", valid.filter(r => r.week === w)),
    })),
    pairedDifference: {
      laggedVsRawMAE: byArm.laggedHistory && byArm.raw ?
        byArm.laggedHistory.mae - byArm.raw.mae : null,
      laggedVsPriorStatusMAE: byArm.laggedHistory && byArm.priorStatus ?
        byArm.laggedHistory.mae - byArm.priorStatus.mae : null,
    },
    skips: rows.filter(r => r.status !== "ok").map(r => ({
      week: r.week, rosterID: r.rosterID, status: r.status,
      missingPriorIDs: r.missingPriorIDs, unfilled: r.unfilled ?? 0,
    })),
  };
}
function selfTest() {
  const prior = { GameType: "REG", Played: true, Roster: { Status: "ACT" } };
  const mk = (played, week, id="P") => ({
    Week: week, CanonicalPlayerID: id, GameType: "REG",
    Played: played, State: played ? "played" : "healthy-scratch" });
  const w = new Map([
    [1, new Map([["P", mk(true, 1)]])],
    [2, new Map([["P", { ...prior, Week: 2, CanonicalPlayerID: "P" }]])],
    [3, new Map([["P", mk(false, 3)]])],
    [4, new Map([["P", mk(true, 4)]])],
    [5, new Map([["P", mk(false, 5)]])],
  ]);
  assert.deepEqual(lagFeatures(w, 5, "P"), {
    roster: "NONE", prior: "T", h4: [1, 1, 0, 1], h8: [1, 1, 0, 1],
  });
  const first = JSON.stringify(lagFeatures(w, 5, "P"));
  w.get(5).get("P").Played = true;
  w.get(5).get("P").State = "played";
  w.get(5).get("P").Report = "Out";
  assert.equal(JSON.stringify(lagFeatures(w, 5, "P")), first,
    "Target-week future facts must not affect model features");
  assert.equal(lagFeatures(w, 5, "MISSING"), null);
  assert.equal(rosterGroup({ Roster: { Status: "PUP" } }), "RESERVE");
  assert.equal(priorGroup({ Played: null }), "U");
  assert.equal(optimize(["QB"], [{ pos: "QB", draw: 4 }], "draw").points, 4);
  assert.equal(optimize(["QB"], [], "draw").unfilled, 1);
  const stubModel = { global: .5, groups: new Map() };
  assert.ok(participantProbabilities(w, 5, "P", stubModel,
    { groupK: 400, alpha: 8, window: 4 }).laggedHistory > .5);
  assert.deepEqual(uniformGenerator(17)(), uniformGenerator(17)());
  process.stdout.write("CP3j self-test OK: strict lag, target isolation, missingness, slots, paired random source\n");
}
function main() {
  const args = Object.fromEntries(process.argv.slice(2).map(v => {
    const [k, value] = v.replace(/^--/, "").split("=");
    return [k, value ?? true];
  }));
  if (args["self-test"]) return selfTest();
  const draws = Number(args.draws || 1200);
  const seed = Number(args.seed || 20261123);
  assert.ok(Number.isInteger(draws) && draws >= 20 && draws <= 50000);
  assert.ok(Number.isInteger(seed));
  const documents = new Map();
  for (const year of [...SEASONS_TRAIN, ...SEASONS_VALIDATION]) {
    documents.set(year, load("data-derived/nfl-player-availability/" + year + ".json"));
  }
  const { trained, selected, trainCount, validationCount } = fitFrozenModel(documents);
  const availability = availabilityWeeks(load("data-derived/nfl-player-availability/2026.json"));
  const league = load("data-source/leagues/nfl-reise/seasons/2026/league.json");
  assert.equal(league.Season, 2026);
  const rows = [];
  for (const week of TEST_WEEKS) {
    const w = String(week).padStart(2, "0");
    rows.push(...runWeek({
      week, availability, league, trained, selected, draws, seed,
      pwf: load("data-derived/player-week-fantasy/nfl-reise/2026/" + w + ".json"),
      weeklyRoster: load("data-source/nfl/weekly-rosters/2026/" + w + ".json"),
      matchups: load("data-source/leagues/nfl-reise/seasons/2026/matchups/week-" + week + ".json"),
      twp: load("data-derived/team-week-performance/nfl-reise/2026/" + w + ".json"),
    }));
  }
  const report = {
    researchOnly: true,
    method: "CP3j-pplay-bernoulli-pi1-bestball",
    nature: "retrospective full roster; no proven Tuesday/as-of, historical revision or independent NFL-player correlation correction",
    target: "team-week-performance.PotentialPoints (NOT actual manager points)",
    trainCount, validationCount, frozenValidationParameters: selected,
    season: 2026, weeks: TEST_WEEKS, seed, draws,
    summary: summarize(rows),
  };
  if (args.rows) report.rows = rows;
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
if (require.main === module) main();
module.exports = { availabilityWeeks, lagFeatures, participantProbabilities,
  fitFrozenModel, monteCarlo, runWeek, summarize, selfTest };
