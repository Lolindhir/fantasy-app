'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const runtime = require('../run-workflow-scheduler-runtime.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const CONFIG_PATH = path.join(ROOT, '.github', 'workflow-schedules.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function healthTarget() {
  return loadConfig().targets.find((item) => item.id === 'workflow-health');
}

function healthResult(dueAt = '2026-09-01T16:07:00.000Z') {
  return {
    id: 'workflow-health',
    workflow: 'workflow-health-snapshot.yml',
    profile: 'observer',
    healthBarrier: false,
    decision: 'dispatch',
    dueAt,
    latestDueAt: '2026-09-01T16:37:00.000Z',
    eventType: 'scheduler-workflow-health',
    retryAttempt: 1,
    maxAttempts: 3,
  };
}

function productivePeer(id, decision, dueAt, extra = {}) {
  return {
    id,
    workflow: `${id}.yml`,
    profile: 'productive',
    healthBarrier: true,
    decision,
    dueAt,
    ...extra,
  };
}

test('Health scheduler config declares blocker-relative and absolute starvation bounds', () => {
  const config = loadConfig();
  runtime.validateConfig(config);
  const health = config.targets.find((item) => item.id === 'workflow-health');
  assert.deepEqual(health.deferUntilOtherTargetsSettled, { maxMinutes: 20 });
  assert.equal(health.maxStarvationMinutes, 30);
});

test('same-tick productive dispatch remains a hard Health barrier before the starvation deadline', () => {
  const target = healthTarget();
  const health = healthResult();
  const result = runtime.applyTargetDeferral(target, health, [
    health,
    productivePeer('league', 'dispatch', '2026-09-01T16:30:00.000Z'),
  ], new Date('2026-09-01T16:35:00.000Z'));

  assert.equal(result.decision, 'deferred');
  assert.equal(result.hardDispatchBarrier, true);
  assert.equal(result.deferralReason, 'productive-dispatch-this-tick');
  assert.equal(result.starvationAgeMinutes, 28);
  assert.equal(result.maxStarvationMinutes, 30);
  assert.equal(result.starvationDeadlineAt, '2026-09-01T16:37:00.000Z');
});

test('absolute Health starvation deadline overrides a fresh same-tick productive dispatch', () => {
  const target = healthTarget();
  const health = healthResult();
  const result = runtime.applyTargetDeferral(target, health, [
    health,
    productivePeer('nfl-game-finality', 'dispatch', '2026-09-01T16:30:00.000Z'),
  ], new Date('2026-09-01T16:37:00.000Z'));

  assert.equal(result.decision, 'dispatch');
  assert.equal(result.starvationLimitExpired, true);
  assert.equal(result.forcedByStarvationLimit, true);
  assert.equal(result.deferralReason, 'health-starvation-limit-expired');
  assert.equal(result.starvationAgeMinutes, 30);
  assert.deepEqual(result.blockingTargets.map((item) => [item.id, item.decision]), [
    ['nfl-game-finality', 'dispatch'],
  ]);
});

test('existing 20-minute blocker-relative expiry still works before the absolute Health deadline', () => {
  const target = healthTarget();
  const health = healthResult();
  const result = runtime.applyTargetDeferral(target, health, [
    health,
    productivePeer('players', 'in-flight', '2026-09-01T16:15:00.000Z', {
      inFlightRunId: 301,
      inFlightCreatedAt: '2026-09-01T16:15:00.000Z',
    }),
  ], new Date('2026-09-01T16:36:00.000Z'));

  assert.equal(result.decision, 'dispatch');
  assert.equal(result.deferralExpired, true);
  assert.equal(result.starvationLimitExpired, undefined);
  assert.equal(result.deferralAgeMinutes, 21);
  assert.equal(result.starvationAgeMinutes, 29);
});

test('frequently refreshed productive blockers cannot starve one retained Health slot across the next Health boundary', () => {
  const target = healthTarget();
  const health = healthResult();
  const scenarios = [
    ['2026-09-01T16:12:00.000Z', productivePeer('league', 'in-flight', '2026-09-01T16:10:00.000Z', { inFlightRunId: 401, inFlightCreatedAt: '2026-09-01T16:10:00.000Z' }), 'deferred'],
    ['2026-09-01T16:22:00.000Z', productivePeer('nfl-game-finality', 'dispatch', '2026-09-01T16:20:00.000Z'), 'deferred'],
    ['2026-09-01T16:32:00.000Z', productivePeer('league', 'in-flight', '2026-09-01T16:30:00.000Z', { inFlightRunId: 402, inFlightCreatedAt: '2026-09-01T16:30:00.000Z' }), 'deferred'],
    ['2026-09-01T16:37:00.000Z', productivePeer('nfl-game-finality', 'dispatch', '2026-09-01T16:30:00.000Z'), 'dispatch'],
  ];

  for (const [now, peer, expected] of scenarios) {
    const result = runtime.applyTargetDeferral(target, health, [health, peer], new Date(now));
    assert.equal(result.decision, expected, `${now} should be ${expected}`);
  }
});

test('operator summary calls out a Health starvation override and still-active blockers', () => {
  const config = loadConfig();
  const target = healthTarget();
  const health = healthResult();
  const forced = runtime.applyTargetDeferral(target, health, [
    health,
    productivePeer('league', 'dispatch', '2026-09-01T16:30:00.000Z'),
  ], new Date('2026-09-01T16:37:00.000Z'));
  forced.dispatched = true;

  const markdown = runtime.buildSummaryMarkdown([forced], new Date('2026-09-01T16:37:00.000Z'), config);
  assert.match(markdown, /Health starvation override/);
  assert.match(markdown, /30-minute absolute starvation limit expired/);
  assert.match(markdown, /still active: league \(dispatch\)/);
  assert.match(markdown, /"forcedByStarvationLimit": true/);
});

test('scheduler config rejects an absolute starvation bound shorter than the blocker window', () => {
  const config = loadConfig();
  const health = config.targets.find((item) => item.id === 'workflow-health');
  health.maxStarvationMinutes = 19;
  assert.throws(() => runtime.validateConfig(config), /Invalid maxStarvationMinutes for workflow-health/);
});
