#!/usr/bin/env node
'use strict';
// CP3c research only: audit historical PWF intervals against final fantasy points.
// No data mutation, no publisher, no production model change.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const ROOT = path.resolve(__dirname, '../../..');
const POSITIONS = new Set(['QB', 'RB', 'WR', 'TE', 'K', 'FB']);
const LEVELS = [0.5, 0.8, 0.9];

function load(relative) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relative), 'utf8'));
}
function finite(value, label) {
  if (!Number.isFinite(value)) throw new Error('Non-finite ' + label);
  return value;
}
function rangeSummary(rows) {
  const n = rows.length;
  if (!n) return {count: 0};
  const result = {
    count: n, actualZeroCount: 0, meanErrorForecastMinusActual: 0,
    meanAbsoluteError: 0, meanWidth90: 0,
    coverage: {'50': 0, '80': 0, '90': 0},
    below90: 0, above90: 0,
  };
  for (const r of rows) {
    result.actualZeroCount += Number(r.actual === 0);
    result.meanErrorForecastMinusActual += r.forecast - r.actual;
    result.meanAbsoluteError += Math.abs(r.forecast - r.actual);
    for (const level of LEVELS) {
      const interval = r.intervals[String(level)];
      const key = String(Math.round(level * 100));
      result.coverage[key] += Number(r.actual >= interval.lower && r.actual <= interval.upper);
      if (level === 0.9) {
        result.meanWidth90 += interval.upper - interval.lower;
        result.below90 += Number(r.actual < interval.lower);
        result.above90 += Number(r.actual > interval.upper);
      }
    }
  }
  const round = x => Math.round(x * 10000) / 10000;
  result.actualZeroPercent = round(100 * result.actualZeroCount / n);
  result.meanErrorForecastMinusActual = round(result.meanErrorForecastMinusActual / n);
  result.meanAbsoluteError = round(result.meanAbsoluteError / n);
  result.meanWidth90 = round(result.meanWidth90 / n);
  for (const key of Object.keys(result.coverage)) {
    result.coverage[key] = round(100 * result.coverage[key] / n);
  }
  return result;
}
function grouped(rows, keyFn, keys) {
  const result = {};
  for (const key of keys) result[key] = rangeSummary(rows.filter(x => keyFn(x) === key));
  return result;
}
function projectionBucket(points) {
  if (points < 4) return '<4';
  if (points < 8) return '4-<8';
  if (points < 12) return '8-<12';
  if (points < 20) return '12-<20';
  return '20+';
}
function snapsByPlayer(payload) {
  if (!Array.isArray(payload.Records)) throw new Error('Missing snap-count Records');
  const result = new Map();
  for (const row of payload.Records) {
    if (typeof row.CanonicalPlayerID !== 'string' || !row.CanonicalPlayerID) continue;
    const current = result.get(row.CanonicalPlayerID) || {
      position: row.Position, offense: 0, special: 0,
    };
    if (current.position !== row.Position) {
      throw new Error('Conflicting snap positions for ' + row.CanonicalPlayerID);
    }
    current.offense += finite(row.OffenseSnaps ?? 0, 'OffenseSnaps');
    current.special += finite(row.SpecialTeamsSnaps ?? 0, 'SpecialTeamsSnaps');
    result.set(row.CanonicalPlayerID, current);
  }
  return result;
}
function playedFromSnap(snap) {
  if (!snap || !POSITIONS.has(snap.position)) return false;
  return snap.position === 'K' ? snap.special > 0 : snap.offense > 0;
}
function collectWeek(season, week) {
  const w = String(week).padStart(2, '0');
  const p = load('data-derived/player-week-fantasy/nfl-reise/' + season + '/' + w + '.json');
  const s = load('data-source/nfl/snap-counts/' + season + '/' + w + '.json');
  for (const doc of [p, s]) {
    assert.equal(doc.Season, season, 'Season mismatch in W' + week);
    assert.equal(doc.Week, week, 'Week mismatch in W' + week);
    assert(Array.isArray(doc.Records), 'Missing Records in W' + week);
  }
  assert.equal(p.Materialization?.ActualScoringEvidenceFinalized, true, 'PWF actual not finalized');
  const snaps = snapsByPlayer(s), seen = new Set(), rows = [];
  let skippedProjection = 0, skippedActual = 0, missingSnapRecord = 0, nonPositiveSnaps = 0;
  for (const record of p.Records) {
    const id = record.CanonicalPlayerID;
    if (typeof id !== 'string' || !id || seen.has(id)) {
      throw new Error('Missing/duplicate PWF player identity ' + season + ' W' + week);
    }
    seen.add(id);
    const projection = record.Projection, actual = record.Actual;
    if (projection?.Status !== 'available') { skippedProjection++; continue; }
    if (actual?.State !== 'final') { skippedActual++; continue; }
    if (projection.ParticipationCondition !== 'conditional-on-participation' ||
        projection.AvailabilityAdjustmentApplied !== false) {
      throw new Error('Unexpected participation semantics for ' + id);
    }
    const intervals = {}, published = projection.PredictionRanges;
    if (!Array.isArray(published)) throw new Error('Missing ranges for ' + id);
    for (const level of LEVELS) {
      const matches = published.filter(x => x.Level === level);
      if (matches.length !== 1) throw new Error('Missing/duplicate range ' + level + ' for ' + id);
      const lower = finite(matches[0].Lower, 'range lower');
      const upper = finite(matches[0].Upper, 'range upper');
      if (upper < lower) throw new Error('Inverted range for ' + id);
      intervals[String(level)] = {lower, upper};
    }
    const forecast = finite(projection.Points, 'projection points');
    const score = finite(actual.Points, 'actual points');
    const snap = snaps.get(id), played = playedFromSnap(snap);
    if (!snap) missingSnapRecord++;
    else if (!played) nonPositiveSnaps++;
    rows.push({
      season, week, id, position: snap?.position ?? 'unknown',
      rangeQuality: projection.RangeQuality, played,
      bucket: projectionBucket(forecast), forecast, actual: score, intervals,
    });
  }
  return {
    rows, input: {season, week, totalPWF: p.Records.length,
      projectedAndFinal: rows.length, skippedProjection, skippedActual,
      missingSnapRecord, nonPositiveSnaps, played: rows.filter(x => x.played).length,
      scoringSettingsHash: p.ScoringProfile?.SettingsHash,
      projectionModel: p.ProjectionModel?.PointModel,
      intervalModel: p.ProjectionModel?.IntervalModel},
  };
}
function summarize(rows, input) {
  const played = rows.filter(x => x.played);
  return {
    researchOnly: true,
    interpretation: 'snap-evidenced participation proxy, conditional on actual participation; absence of positive snaps is not proof of OUT/DNP; archived PWF may reflect later revisions',
    input,
    allProjectedFinal: rangeSummary(rows),
    snapEvidencedPlayed: rangeSummary(played),
    withoutPositiveSnapEvidence: rangeSummary(rows.filter(x => !x.played)),
    playedByPosition: grouped(played, x => x.position, ['QB', 'RB', 'WR', 'TE', 'K', 'FB']),
    playedByRangeQuality: grouped(played, x => x.rangeQuality,
      ['player-volatility', 'limited-history-fallback']),
    playedByProjectedPoints: grouped(played, x => x.bucket, ['<4', '4-<8', '8-<12', '12-<20', '20+']),
  };
}
function selfTest() {
  const r = {forecast: 8, actual: 10, intervals: {
    '0.5': {lower: 7, upper: 9}, '0.8': {lower: 6, upper: 10},
    '0.9': {lower: 4, upper: 12},
  }};
  const v = rangeSummary([r]);
  assert.equal(v.coverage['50'], 0);
  assert.equal(v.coverage['80'], 100);
  assert.equal(v.coverage['90'], 100);
  assert.equal(v.meanErrorForecastMinusActual, -2);
  assert.equal(projectionBucket(20), '20+');
  assert(playedFromSnap({position: 'K', offense: 0, special: 1}));
  assert(!playedFromSnap({position: 'WR', offense: 0, special: 10}));
  assert(!playedFromSnap(undefined));
  console.log('CP3c self-test OK');
}
function main() {
  const args = Object.fromEntries(process.argv.slice(2).map(x => {
    const [key, val] = x.replace(/^--/, '').split('=');
    return [key, val || true];
  }));
  if (args['self-test']) return selfTest();
  const seasons = String(args.seasons || '2024,2025,2026').split(',').map(Number);
  const match = /^(\d+)-(\d+)$/.exec(String(args.weeks || '5-10'));
  if (!match) throw new Error('Use --weeks=5-10');
  const weeks = Array.from({length: Number(match[2]) - Number(match[1]) + 1},
    (_, index) => Number(match[1]) + index);
  if (!weeks.length || weeks.length > 18 || weeks.some(x => x < 1 || x > 18) ||
      seasons.some(x => !Number.isInteger(x) || x < 2000)) {
    throw new Error('Invalid seasons/weeks');
  }
  const rows = [], input = [];
  for (const season of seasons) {
    for (const week of weeks) {
      const observed = collectWeek(season, week);
      rows.push(...observed.rows);
      input.push(observed.input);
    }
  }
  const report = {
    method: 'cp3c-pwf-snap-coverage-v1',
    years: Object.fromEntries(seasons.map(season =>
      [season, summarize(rows.filter(x => x.season === season), input.filter(x => x.season === season))])),
    pooled: summarize(rows, input),
    byWeek: Object.fromEntries(input.map(x => [x.season + '-W' + x.week,
      rangeSummary(rows.filter(r => r.season === x.season && r.week === x.week && r.played))])),
  };
  if (args.rows) report.rows = rows;
  console.log(JSON.stringify(report, null, 2));
}
if (require.main === module) main();
module.exports = {rangeSummary, projectionBucket, playedFromSnap, summarize, snapsByPlayer};
