#!/usr/bin/env node
'use strict';
// Research-only CP3e target parity audit; never use retrospective snaps for a live forecast.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {optimize} = require('./simulate_best_ball_ranges.cjs');
const {snapsByPlayer, playedFromSnap} = require('./audit_pwf_range_coverage.cjs');
const {slots} = require('./ablate_best_ball_oracle_availability.cjs');
const ROOT = path.resolve(__dirname, '../../..');
const POS = new Set(['QB', 'RB', 'WR', 'TE', 'K']);
const TARGET_TOLERANCE = 0.05;
const load = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const round = n => Math.round(n * 10000) / 10000;

// HB is a snap-provider position label for halfbacks, not a new fantasy lineup slot.
// Strictly require an RB classification from the separate weekly-roster source and
// positive offensive snaps; no unverified alias or missing-snap inference.
function snapPlayedWithDocumentedAlias(snap, weeklyPosition) {
  return playedFromSnap(snap) || Boolean(
    weeklyPosition === 'RB' && snap?.position === 'HB' && snap.offense > 0
  );
}
function uniqueIndex(records, key) {
  const indexed = new Map();
  for (const r of records) {
    if (typeof r[key] !== 'string' || !r[key] || indexed.has(r[key])) {
      throw Error('Missing/duplicate ' + key);
    }
    indexed.set(r[key], r);
  }
  return indexed;
}
function reconcileWeek(season, week, formation) {
  const w = String(week).padStart(2, '0');
  const base = 'data-source/leagues/nfl-reise/seasons/' + season;
  const pwf = load('data-derived/player-week-fantasy/nfl-reise/' + season + '/' + w + '.json');
  const weekly = load('data-source/nfl/weekly-rosters/' + season + '/' + w + '.json');
  const snaps = load('data-source/nfl/snap-counts/' + season + '/' + w + '.json');
  const matchups = load(base + '/matchups/week-' + week + '.json');
  const twp = load('data-derived/team-week-performance/nfl-reise/' + season + '/' + w + '.json');
  for (const doc of [pwf, weekly, snaps, twp]) {
    assert.equal(doc.Season, season);
    assert.equal(doc.Week, week);
  }
  assert.equal(pwf.Materialization?.ActualScoringEvidenceFinalized, true);
  assert(Array.isArray(matchups) && twp.FinalityEvidence);
  const projected = uniqueIndex(pwf.Records, 'CanonicalPlayerID');
  const positions = uniqueIndex(weekly.Records, 'CanonicalPlayerID');
  const snapIndex = snapsByPlayer(snaps);
  const targets = uniqueIndex(twp.Teams, 'CanonicalLeagueRosterID');
  assert.equal(matchups.length, targets.size);
  const result = [];
  for (const team of matchups) {
    const rosterID = team.CanonicalLeagueRosterID;
    const official = targets.get(rosterID);
    if (!official || !Number.isFinite(official.PotentialPoints)) throw Error('Missing TWP target');
    const candidates = [], aliases = [], seen = new Set();
    for (const ref of team.Players) {
      const id = ref.CanonicalPlayerID;
      if (!id || seen.has(id)) throw Error('Duplicate/invalid roster player ' + id);
      seen.add(id);
      const pos = positions.get(id)?.Position;
      const record = projected.get(id);
      if (!POS.has(pos) || record?.Projection?.Status !== 'available' ||
          record.Projection.PredictionRange?.Level !== 0.9) continue;
      if (record.Actual?.State !== 'final' || !Number.isFinite(record.Actual.Points)) {
        throw Error('Missing finalized actual ' + id);
      }
      const snap = snapIndex.get(id);
      const prior = playedFromSnap(snap);
      const revised = snapPlayedWithDocumentedAlias(snap, pos);
      if (!prior && revised) aliases.push({id, rosterPosition: pos,
        snapPosition: snap.position, offenseSnaps: snap.offense, actual: record.Actual.Points});
      candidates.push({id, pos, actual: record.Actual.Points, prior, revised});
    }
    const original = optimize(formation, candidates.filter(p => p.prior), 'actual');
    const adjusted = optimize(formation, candidates.filter(p => p.revised), 'actual');
    const raw = optimize(formation, candidates, 'actual');
    const target = official.PotentialPoints;
    const aligned = x => (official.UnfilledSlotIDs?.length ?? 0) === 0 &&
      x.unfilled === 0 && Math.abs(x.points - target) <= TARGET_TOLERANCE;
    if (adjusted.points > raw.points + 1e-8 || original.points > adjusted.points + 1e-8) {
      throw Error('Subset monotonicity violated ' + rosterID);
    }
    result.push({season, week, rosterID, target, originalActual: round(original.points),
      adjustedActual: round(adjusted.points), rawActual: round(raw.points),
      originalAligned: aligned(original), adjustedAligned: aligned(adjusted),
      rawAligned: aligned(raw), originalUnfilled: original.unfilled,
      adjustedUnfilled: adjusted.unfilled, twpUnfilled: official.UnfilledSlotIDs?.length ?? 0,
      aliases});
  }
  return result;
}
function selfTest() {
  const h = {position: 'HB', offense: 39, special: 0};
  assert.equal(playedFromSnap(h), false);
  assert.equal(snapPlayedWithDocumentedAlias(h, 'RB'), true);
  assert.equal(snapPlayedWithDocumentedAlias(h, 'WR'), false);
  assert.equal(snapPlayedWithDocumentedAlias({...h, offense: 0}, 'RB'), false);
  assert.equal(snapPlayedWithDocumentedAlias(null, 'RB'), false);
  assert.equal(snapPlayedWithDocumentedAlias({position: 'K', offense: 0, special: 2}, 'K'), true);
  const players = [{pos: 'RB', actual: 9}, {pos: 'RB', actual: 2}];
  assert.equal(optimize(['RB'], players, 'actual').points, 9);
  console.log('CP3e target reconciliation self-test OK');
}
function main() {
  const args = Object.fromEntries(process.argv.slice(2).map(arg => {
    const [name, value] = arg.replace(/^--/, '').split('=');
    return [name, value ?? true];
  }));
  if (args['self-test']) return selfTest();
  const season = Number(args.season ?? 2026);
  const range = /^(\d+)-(\d+)$/.exec(String(args.weeks ?? '5-10'));
  if (!Number.isInteger(season) || !range || +range[1] < 1 || +range[2] > 18 ||
      +range[1] > +range[2]) throw Error('Use --season=2026 --weeks=5-10');
  const formation = slots(load('data-source/leagues/nfl-reise/seasons/' + season + '/league.json'));
  const rows = [];
  for (let week = +range[1]; week <= +range[2]; week++) {
    rows.push(...reconcileWeek(season, week, formation));
  }
  const exceptions = rows.filter(r => !r.originalAligned || !r.adjustedAligned);
  console.log(JSON.stringify({researchOnly: true, method: 'cp3e-snap-alias-target-reconciliation-v1',
    provenance: 'Archived current repository revisions, not Tuesday-as-of evidence',
    season, weeks: String(args.weeks ?? '5-10'), total: rows.length,
    originalAligned: rows.filter(r => r.originalAligned).length,
    adjustedAligned: rows.filter(r => r.adjustedAligned).length,
    rawAligned: rows.filter(r => r.rawAligned).length,
    cases: exceptions, ...(args.rows ? {rows} : {})}, null, 2));
}
if (require.main === module) main();
module.exports = {snapPlayedWithDocumentedAlias, reconcileWeek};
