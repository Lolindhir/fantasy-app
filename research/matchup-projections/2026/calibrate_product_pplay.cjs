#!/usr/bin/env node
"use strict";

/**
 * CP3i: read-only, product-first, lag-only participation pilot.
 *
 * This is RESEARCH, not a production forecast or a true point-in-time replay.
 * It reads only the canonical historical Shared-Derived Availability v3 product.
 * The immediately preceding week's retrospective product record is used to
 * define the candidate cohort; target-week records are LABELS only.
 * Actual historical publication/revision timestamps are not established.
 *
 * Usage (from repository root):
 *   node research/matchup-projections/2026/calibrate_product_pplay.cjs --self-test
 *   node research/matchup-projections/2026/calibrate_product_pplay.cjs
 *
 * Output is read-only JSON on stdout; no repository, App or workflow writes.
 */
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "../../..");
const PRODUCT = "nfl-player-availability-v3";
const SEASONS = Array.from({ length: 10 }, (_, i) => 2016 + i);
const EPS = 1e-9;
const GROUP_KS = [5, 20, 100, 400];
const ALPHAS = [1, 2, 4, 8, 16, 32];
const WINDOWS = [4, 8];

function rosterGroup(value) {
  const status = value && value.Roster ? value.Roster.Status : null;
  if (status === "ACT" || status === "INA") return status;
  if (status === "RES" || status === "PUP") return "RESERVE";
  return status === null || status === undefined ? "NONE" : "OTHER";
}
function participationGroup(record) {
  return record.Played === true ? "T" : record.Played === false ? "F" : "U";
}
function groupKey(row) {
  return row.roster + ":" + row.prior;
}
function strictRecords(document, year) {
  assert.equal(document.ProductVersion, PRODUCT, "Expected published v3 for " + year);
  assert.equal(document.SchemaVersion, 3, "Expected schema v3 for " + year);
  assert.ok(Array.isArray(document.Records), "Missing records for " + year);
  const weeks = new Map();
  const ids = new Set();
  for (const rec of document.Records) {
    assert.ok(typeof rec.CanonicalPlayerID === "string" && rec.CanonicalPlayerID, "Missing canonical player ID");
    assert.ok(Number.isInteger(rec.Week) && rec.Week >= 1, "Unexpected NFL week");
    if (rec.Week > 18) continue; // NFL postseason is not a REG prediction target.
    assert.ok(rec.Played === true || rec.Played === false || rec.Played === null, "Played is not tri-state");
    const key = rec.Week + ":" + rec.CanonicalPlayerID;
    assert.ok(!ids.has(key), "Duplicate player-week " + year + ":" + key);
    ids.add(key);
    if (!weeks.has(rec.Week)) weeks.set(rec.Week, new Map());
    weeks.get(rec.Week).set(rec.CanonicalPlayerID, rec);
  }
  return weeks;
}
function samplesForSeason(document, year) {
  const weeks = strictRecords(document, year);
  const history = new Map();
  const rows = [];
  const coverage = { candidate: 0, known: 0, missing: 0, unknown: 0, byeOrNonRegular: 0, previousActiveKnown: 0 };
  const lastRegularWeek = Math.max(...[...weeks].filter(([, records]) =>
    [...records.values()].some(rec => rec.GameType === "REG")).map(([week]) => week));
  assert.ok(Number.isInteger(lastRegularWeek), "No regular-season weeks in product");
  for (let week = 1; week <= lastRegularWeek; ++week) {
    const current = weeks.get(week) || new Map();
    const previous = weeks.get(week - 1) || new Map();
    // A target-week record may determine its retrospective LABEL/eligibility.
    // Its Report/Roster/Available/Participation evidence is never a feature.
    if (week >= 2) for (const [id, prior] of previous) {
      coverage.candidate++;
      const outcome = current.get(id);
      if (!outcome) { coverage.missing++; continue; }
      if (outcome.State === "bye" || outcome.GameType !== "REG") {
        coverage.byeOrNonRegular++;
        continue;
      }
      if (typeof outcome.Played !== "boolean") { coverage.unknown++; continue; }
      const old = history.get(id) || [];
      const row = {
        season: year, week, roster: rosterGroup(prior),
        prior: participationGroup(prior),
        h4: old.slice(-4), h8: old.slice(-8),
        target: outcome.Played ? 1 : 0,
      };
      rows.push(row);
      coverage.known++;
      if (row.roster === "ACT" || row.roster === "INA") coverage.previousActiveKnown++;
    }
    // Update history only AFTER predicting this NFL week.
    // Only previous fully completed REG weeks with definite participation enter it.
    for (const [id, rec] of current) if (rec.GameType === "REG" && typeof rec.Played === "boolean") {
      const old = history.get(id) || [];
      old.push(rec.Played ? 1 : 0);
      if (old.length > 8) old.shift();
      history.set(id, old);
    }
  }
  assert.equal(
    coverage.candidate,
    coverage.known + coverage.missing + coverage.unknown + coverage.byeOrNonRegular,
    "Candidate cohort coverage must reconcile"
  );
  return { rows, coverage };
}
function fit(rows) {
  assert.ok(rows.length, "Empty training cohort");
  const global = rows.reduce((sum, row) => sum + row.target, 0) / rows.length;
  const groups = new Map();
  for (const row of rows) {
    const key = groupKey(row);
    const group = groups.get(key) || { count: 0, played: 0 };
    group.count++;
    group.played += row.target;
    groups.set(key, group);
  }
  return { global, groups };
}
function forecast(row, trained, groupK, alpha, window) {
  const g = trained.groups.get(groupKey(row)) || { count: 0, played: 0 };
  const base = (g.played + groupK * trained.global) / (g.count + groupK);
  if (alpha === null) return base;
  const h = window === 4 ? row.h4 : row.h8;
  const played = h.reduce((sum, value) => sum + value, 0);
  return (played + alpha * base) / (h.length + alpha);
}
function metrics(rows, fn) {
  if (!rows.length) return null;
  let squared = 0, loss = 0, bias = 0, sumP = 0, sumY = 0;
  const bins = Array.from({ length: 10 }, () => ({ count: 0, forecast: 0, actual: 0 }));
  for (const row of rows) {
    const p0 = fn(row);
    assert.ok(Number.isFinite(p0) && p0 >= 0 && p0 <= 1, "Invalid probability");
    const p = Math.min(1 - EPS, Math.max(EPS, p0));
    const y = row.target;
    squared += (p - y) ** 2;
    loss -= y * Math.log(p) + (1 - y) * Math.log(1 - p);
    bias += p - y;
    sumP += p; sumY += y;
    const b = bins[Math.min(9, Math.floor(p * 10))];
    b.count++; b.forecast += p; b.actual += y;
  }
  const round = (value, d = 6) => Number(value.toFixed(d));
  return {
    n: rows.length, brier: round(squared / rows.length),
    logLoss: round(loss / rows.length),
    bias: round(bias / rows.length),
    averageProbability: round(sumP / rows.length),
    observedParticipation: round(sumY / rows.length),
    calibration: bins.filter(x => x.count).map(x => ({
      n: x.count, forecast: round(x.forecast / x.count, 3),
      actual: round(x.actual / x.count, 3),
    })),
  };
}
function selectModel(training, validation) {
  const trained = fit(training);
  let best = null;
  for (const groupK of GROUP_KS) for (const alpha of ALPHAS) for (const window of WINDOWS) {
    const candidate = { groupK, alpha, window };
    const score = metrics(validation, row => forecast(row, trained, groupK, alpha, window)).brier;
    if (best === null || score < best.validationBrier) best = { ...candidate, validationBrier: score };
  }
  return { trained, best };
}
function run(documents) {
  const years = [...documents.keys()].sort((a, b) => a - b);
  assert.deepEqual(years, SEASONS, "Must use exactly 2016-2025 for locked split");
  const data = years.map(year => {
    const { rows, coverage } = samplesForSeason(documents.get(year), year);
    return { year, rows, coverage, recordCount: documents.get(year).Records.length };
  });
  const training = data.filter(x => x.year <= 2022).flatMap(x => x.rows);
  const validation = data.filter(x => x.year >= 2023 && x.year <= 2024).flatMap(x => x.rows);
  const holdout = data.filter(x => x.year === 2025).flatMap(x => x.rows);
  const { trained, best } = selectModel(training, validation);
  const chosen = row => forecast(row, trained, best.groupK, best.alpha, best.window);
  const bucket = row => forecast(row, trained, 20, null, 0);
  const cohort = rows => ({
    allPlay: metrics(rows, () => 1),
    trainGlobal: metrics(rows, () => trained.global),
    priorRosterAndParticipation: metrics(rows, bucket),
    laggedHistory: metrics(rows, chosen),
  });
  return {
    researchModel: "product-first-availability-lagged-v1",
    nature: "retrospective-product-label-backtest; NOT a proven point-in-time feature replay",
    split: { train: "2016-2022", validation: "2023-2024", untouchedHoldout: "2025" },
    counts: { training: training.length, validation: validation.length, holdout: holdout.length },
    productCoverage: data.map(x => ({ year: x.year, records: x.recordCount, ...x.coverage })),
    trainedGlobal: trained.global,
    selectedOnValidation: best,
    validation: cohort(validation),
    holdout: cohort(holdout),
    holdoutPreviousRosterActive: cohort(holdout.filter(x => x.roster === "ACT" || x.roster === "INA")),
    holdoutPreviousRosterOther: cohort(holdout.filter(x => x.roster !== "ACT" && x.roster !== "INA")),
    holdoutByWeekBlock: [
      { label: "W2-6", min: 2, max: 6 },
      { label: "W7-12", min: 7, max: 12 },
      { label: "W13-18", min: 13, max: 18 },
    ].map(b => ({
      block: b.label,
      selectedModel: metrics(holdout.filter(x => x.week >= b.min && x.week <= b.max), chosen),
    })),
  };
}
function selfTest() {
  const rec = (week, id, played, status, state = "played", gameType = "REG") => ({
    Week: week, CanonicalPlayerID: id, Played: played,
    GameType: gameType, State: state, Roster: status ? { Status: status } : null,
  });
  const doc = {
    ProductVersion: PRODUCT, SchemaVersion: 3,
    Records: [
      rec(1, "A", true, "ACT"),
      rec(1, "B", false, "INA"),
      rec(1, "C", null, null, "unknown"),
      rec(1, "D", false, "RES"),
      rec(1, "E", true, "ACT"),
      rec(2, "A", true, "RES"),
      rec(2, "B", null, "INA", "unknown"),
      rec(2, "C", false, "ACT", "healthy-scratch"),
      rec(2, "E", null, null, "bye", null),
    ],
  };
  const first = samplesForSeason(doc, 2025);
  assert.deepEqual(first.coverage, {
    candidate: 5, known: 2, missing: 1, unknown: 1, byeOrNonRegular: 1, previousActiveKnown: 1,
  });
  assert.deepEqual(first.rows.map(r => [r.prior, r.h4, r.target]), [
    ["T", [1], 1], ["U", [], 0],
  ]);
  const copied = JSON.parse(JSON.stringify(doc));
  copied.Records.find(x => x.Week === 2 && x.CanonicalPlayerID === "A").Roster.Status = "INA";
  copied.Records.find(x => x.Week === 2 && x.CanonicalPlayerID === "A").Report = [{ Game: "Out" }];
  assert.deepEqual(samplesForSeason(copied, 2025), first, "Target-week features must not affect prediction");
  copied.Records.push(rec(1, "A", false, "INA"));
  assert.throws(() => samplesForSeason(copied, 2025), /Duplicate player-week/);
  assert.equal(metrics(first.rows, () => 0.5).brier, 0.25);
  process.stdout.write("CP3i self-test OK: temporal feature isolation, coverage, null, bye, duplicates, Brier\n");
}
function main() {
  if (process.argv.includes("--self-test")) { selfTest(); return; }
  const documents = new Map();
  const fingerprints = [];
  for (const season of SEASONS) {
    const rel = path.join("data-derived", "nfl-player-availability", season + ".json");
    const file = path.join(ROOT, rel);
    const raw = fs.readFileSync(file);
    const document = JSON.parse(raw.toString("utf8"));
    documents.set(season, document);
    fingerprints.push({
      season, path: rel.replace(/\\/g, "/"),
      sha256: crypto.createHash("sha256").update(raw).digest("hex"),
      productVersion: document.ProductVersion,
    });
  }
  const output = run(documents);
  output.inputs = fingerprints;
  process.stdout.write(JSON.stringify(output, null, 2) + "\n");
}
if (require.main === module) main();
module.exports = { samplesForSeason, fit, forecast, metrics, selectModel, run };
