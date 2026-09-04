'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const scheduler = require('../run-workflow-scheduler.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const CONFIG_PATH = path.join(ROOT, '.github', 'workflow-schedules.json');

const EXPECTED = {
  'update-league.yml': { timezone: 'Etc/UTC', cron: ['*/10 * * * *'] },
  'update-games.yml': { timezone: 'America/New_York', cron: ['45 0 * * *', '0 13 * * *'] },
  'update-players.yml': { timezone: 'America/New_York', cron: ['15 1 * * *', '0 8 * * *', '30 13 * * *'] },
  'update-standings.yml': { timezone: 'America/New_York', cron: ['35 3 * * 3'] },
  'update-transactions.yml': { timezone: 'America/New_York', cron: ['5 4 * * 3'] },
  'update-teams.yml': { timezone: 'America/New_York', cron: ['35 4 * * 3'] },
  'sync-league-source-data.yml': { timezone: 'Europe/Berlin', cron: ['30 4 * * *'] },
  'update-fantasypros-rankings.yml': { timezone: 'Europe/Berlin', cron: ['20 5 * * *'] },
  'update-fantasycalc-rankings.yml': { timezone: 'Europe/Berlin', cron: ['32 5 * * *'] },
  'update-fantasy-football-calculator-adp.yml': { timezone: 'Europe/Berlin', cron: ['44 5 * * *'] },
  'update-fftoday-projections.yml': { timezone: 'Europe/Berlin', cron: ['56 5 * * *'] },
  'update-cbs-sports-projections.yml': { timezone: 'Europe/Berlin', cron: ['8 6 * * *'] },
  'update-sleeper-trending.yml': { timezone: 'Europe/Berlin', cron: ['20 6 * * *'] },
  'materialize-fantasy-operations-inputs.yml': { timezone: 'Europe/Berlin', cron: ['45 6 * * *'] },
  'clean-backups.yml': { timezone: 'Europe/Berlin', cron: ['0 17 * * 3'] },
  'workflow-health-snapshot.yml': { timezone: 'Etc/UTC', cron: ['7-59/30 * * * *'] },
};

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function target(overrides = {}) {
  return {
    id: 'league',
    workflow: 'update-league.yml',
    eventType: 'scheduler-update-league',
    profile: 'productive',
    timezone: 'Etc/UTC',
    cron: ['*/10 * * * *'],
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
    ...overrides,
  };
}

const productive = { healthBarrier: true, retryPolicy: 'standard' };
const maintenance = { healthBarrier: false, retryPolicy: 'standard' };
const retryPolicy = { maxAttempts: 3, backoffMinutes: [5, 10], cooldownMinutes: 60 };

function run(id, createdAt, status, conclusion, extra = {}) {
  return {
    id,
    event: 'repository_dispatch',
    head_branch: 'main',
    created_at: createdAt,
    updated_at: extra.updated_at || createdAt,
    status,
    conclusion,
    ...extra,
  };
}

test('central config preserves all migrated schedules, profiles and state contract', () => {
  const config = loadConfig();
  scheduler.validateConfig(config);
  assert.equal(config.schemaVersion, 2);
  assert.equal(config.targets.length, 16);
  const actual = Object.fromEntries(config.targets.map((item) => [item.workflow, { timezone: item.timezone, cron: item.cron }]));
  assert.deepEqual(actual, EXPECTED);
  assert.equal(new Set(config.targets.map((item) => item.eventType)).size, 16);
  assert.deepEqual(config.state, {
    schemaVersion: 1,
    branch: 'workflow-scheduler-state',
    path: 'workflow-scheduler-state.json',
  });
  assert.deepEqual(config.retryPolicies.standard, retryPolicy);
  assert.equal(config.targets.find((item) => item.id === 'backup-cleanup').profile, 'maintenance');
  assert.equal(config.targets.find((item) => item.id === 'workflow-health').profile, 'observer');
  assert.equal(config.targets.filter((item) => item.profile === 'productive').length, 14);
  assert.deepEqual(config.targets.find((item) => item.id === 'workflow-health').deferUntilOtherTargetsSettled, { maxMinutes: 20 });
});

test('scheduler keeps GitHub cron during external-tick transition and accepts external dispatch', () => {
  const content = fs.readFileSync(path.join(ROOT, '.github', 'workflows', 'scheduler.yml'), 'utf8');
  assert.match(content, /\n  schedule:\s*\n/, 'scheduler lost its transition GitHub schedule');
  assert.match(content, /\n  repository_dispatch:\s*\n/, 'scheduler is missing repository_dispatch');
  assert.match(content, /external-scheduler-tick/, 'scheduler is missing the external tick event type');
});

test('migrated targets have repository_dispatch and no local schedule trigger', () => {
  const config = loadConfig();
  for (const item of config.targets) {
    const content = fs.readFileSync(path.join(ROOT, item.path), 'utf8');
    assert.doesNotMatch(content, /\n  schedule:\s*\n/, `${item.path} still contains a local schedule trigger`);
    assert.match(content, /\n  repository_dispatch:\s*\n/, `${item.path} is missing repository_dispatch`);
    assert.match(content, new RegExp(item.eventType.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.match(content, /\n  workflow_dispatch:/, `${item.path} lost manual workflow_dispatch`);
  }
});

test('ten-minute cron resolves latest due slot', () => {
  const due = scheduler.latestDueSlot(['*/10 * * * *'], 'Etc/UTC', new Date('2026-09-01T16:27:30Z'), 60);
  assert.equal(due.toISOString(), '2026-09-01T16:20:00.000Z');
});

test('Berlin daily schedules preserve DST semantics', () => {
  const sourceSummer = scheduler.latestDueSlot(['30 4 * * *'], 'Europe/Berlin', new Date('2026-08-17T03:00:00Z'), 1440);
  const sourceWinter = scheduler.latestDueSlot(['30 4 * * *'], 'Europe/Berlin', new Date('2026-12-17T04:00:00Z'), 1440);
  assert.equal(sourceSummer.toISOString(), '2026-08-17T02:30:00.000Z');
  assert.equal(sourceWinter.toISOString(), '2026-12-17T03:30:00.000Z');
});

test('New York player schedule is evaluated in local time', () => {
  const due = scheduler.latestDueSlot(['15 1 * * *', '0 8 * * *', '30 13 * * *'], 'America/New_York', new Date('2026-09-01T13:10:00Z'), 1440);
  assert.equal(due.toISOString(), '2026-09-01T12:00:00.000Z');
});

test('weekly cron finds previous Wednesday within lookback', () => {
  const due = scheduler.latestDueSlot(['0 17 * * 3'], 'Europe/Berlin', new Date('2026-09-01T16:00:00Z'), 11520);
  assert.equal(due.toISOString(), '2026-08-26T15:00:00.000Z');
});

test('only a completed successful run satisfies a due slot', () => {
  const due = new Date('2026-09-01T16:20:00Z');
  const common = { event: 'repository_dispatch', head_branch: 'main', created_at: '2026-09-01T16:21:00Z' };
  assert.equal(scheduler.runSatisfiesSlot({ ...common, status: 'completed', conclusion: 'success' }, target(), due, 'main'), true);
  assert.equal(scheduler.runSatisfiesSlot({ ...common, status: 'in_progress', conclusion: null }, target(), due, 'main'), false);
  assert.equal(scheduler.runSatisfiesSlot({ ...common, status: 'completed', conclusion: 'failure' }, target(), due, 'main'), false);
});

test('basic evaluator still treats in-flight as duplicate suppression', () => {
  const result = scheduler.evaluateTarget(target(), 'main', new Date('2026-09-01T16:27:00Z'), 180, [
    run(101, '2026-09-01T16:21:00Z', 'in_progress', null),
  ]);
  assert.equal(result.decision, 'in-flight');
  assert.equal(result.inFlightRunId, 101);
});

test('retry waits for configured backoff after the first failed attempt', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T16:25:00Z'), 180,
    [run(201, '2026-09-01T16:21:00Z', 'completed', 'failure', { updated_at: '2026-09-01T16:22:00Z' })],
    { dueAt: '2026-09-01T16:20:00.000Z', attemptsDispatched: 1, lastDispatchAt: '2026-09-01T16:21:00.000Z' },
  );
  assert.equal(evaluation.result.decision, 'retry-wait');
  assert.equal(evaluation.result.retryAttempt, 2);
  assert.equal(evaluation.result.retryNotBefore, '2026-09-01T16:27:00.000Z');
  assert.equal(evaluation.nextState.dueAt, '2026-09-01T16:20:00.000Z');
});

test('retry cycle stays anchored to the original due slot when a newer regular slot appears', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T16:32:00Z'), 180,
    [run(202, '2026-09-01T16:21:00Z', 'completed', 'failure', { updated_at: '2026-09-01T16:22:00Z' })],
    { dueAt: '2026-09-01T16:20:00.000Z', attemptsDispatched: 1, lastDispatchAt: '2026-09-01T16:21:00.000Z' },
  );
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.dueAt, '2026-09-01T16:20:00.000Z');
  assert.equal(evaluation.result.latestDueAt, '2026-09-01T16:30:00.000Z');
  assert.equal(evaluation.result.retryAttempt, 2);
});

test('deferred zero-attempt state keeps the original due slot across the next regular slot', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T16:42:00Z'), 180,
    [],
    { dueAt: '2026-09-01T16:20:00.000Z', attemptsDispatched: 0, lastDispatchAt: null },
  );
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.dueAt, '2026-09-01T16:20:00.000Z');
  assert.equal(evaluation.result.latestDueAt, '2026-09-01T16:40:00.000Z');
  assert.equal(evaluation.result.retryAttempt, 1);
});

test('successful run heals an active retry cycle', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T16:28:00Z'), 180,
    [
      run(204, '2026-09-01T16:26:00Z', 'completed', 'success'),
      run(203, '2026-09-01T16:21:00Z', 'completed', 'failure'),
    ],
    { dueAt: '2026-09-01T16:20:00.000Z', attemptsDispatched: 2, lastDispatchAt: '2026-09-01T16:25:00.000Z' },
  );
  assert.equal(evaluation.result.decision, 'satisfied');
  assert.equal(evaluation.result.satisfyingRunId, 204);
  assert.equal(evaluation.nextState, null);
});

test('three failed attempts open the retry circuit', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T16:45:00Z'), 180,
    [
      run(213, '2026-09-01T16:39:00Z', 'completed', 'failure', { updated_at: '2026-09-01T16:40:00Z' }),
      run(212, '2026-09-01T16:28:00Z', 'completed', 'failure'),
      run(211, '2026-09-01T16:21:00Z', 'completed', 'failure'),
    ],
    { dueAt: '2026-09-01T16:20:00.000Z', attemptsDispatched: 3, lastDispatchAt: '2026-09-01T16:39:00.000Z' },
  );
  assert.equal(evaluation.result.decision, 'retry-exhausted');
  assert.equal(evaluation.result.attemptsDispatched, 3);
  assert.equal(evaluation.result.circuitOpenUntil, '2026-09-01T17:40:00.000Z');
  assert.equal(evaluation.nextState.circuitOpenUntil, '2026-09-01T17:40:00.000Z');
});

test('open retry circuit suppresses further dispatches until cooldown expires', () => {
  const evaluation = scheduler.evaluateTargetWithRetry(
    target(), productive, retryPolicy, 'main', new Date('2026-09-01T17:00:00Z'), 180,
    [
      run(223, '2026-09-01T16:39:00Z', 'completed', 'failure'),
      run(222, '2026-09-01T16:28:00Z', 'completed', 'failure'),
      run(221, '2026-09-01T16:21:00Z', 'completed', 'failure'),
    ],
    {
      dueAt: '2026-09-01T16:20:00.000Z',
      attemptsDispatched: 3,
      lastDispatchAt: '2026-09-01T16:39:00.000Z',
      circuitOpenUntil: '2026-09-01T17:40:00.000Z',
      lastFailureRunId: 223,
      lastFailureConclusion: 'failure',
    },
  );
  assert.equal(evaluation.result.decision, 'cooldown');
  assert.equal(evaluation.result.latestDueAt, '2026-09-01T17:00:00.000Z');
});

test('same-tick productive dispatch hard-blocks Health even after the age limit', () => {
  const healthTarget = target({
    id: 'workflow-health',
    workflow: 'workflow-health-snapshot.yml',
    eventType: 'scheduler-workflow-health',
    profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-01T16:07:00.000Z',
  };
  const result = scheduler.applyTargetDeferral(healthTarget, healthResult, [
    healthResult,
    { id: 'players', workflow: 'update-players.yml', profile: 'productive', healthBarrier: true, decision: 'dispatch', dueAt: '2026-09-01T16:15:00.000Z' },
  ], new Date('2026-09-01T16:35:00Z'));
  assert.equal(result.decision, 'deferred');
  assert.equal(result.hardDispatchBarrier, true);
  assert.equal(result.deferralAgeMinutes, 28);
});

test('in-flight productive work stops blocking Health after the age limit', () => {
  const healthTarget = target({
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', eventType: 'scheduler-workflow-health', profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-01T16:07:00.000Z',
  };
  const result = scheduler.applyTargetDeferral(healthTarget, healthResult, [
    healthResult,
    { id: 'players', workflow: 'update-players.yml', profile: 'productive', healthBarrier: true, decision: 'in-flight', dueAt: '2026-09-01T16:15:00.000Z', inFlightRunId: 301 },
  ], new Date('2026-09-01T16:27:00Z'));
  assert.equal(result.decision, 'dispatch');
  assert.equal(result.deferralExpired, true);
});

test('maintenance dispatch and retry-exhausted productive target do not block Health', () => {
  const healthTarget = target({
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', eventType: 'scheduler-workflow-health', profile: 'observer',
    deferUntilOtherTargetsSettled: { maxMinutes: 20 },
  });
  const healthResult = {
    id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
    decision: 'dispatch', dueAt: '2026-09-01T16:07:00.000Z',
  };
  const result = scheduler.applyTargetDeferral(healthTarget, healthResult, [
    healthResult,
    { id: 'backup-cleanup', workflow: 'clean-backups.yml', profile: 'maintenance', healthBarrier: false, decision: 'dispatch' },
    { id: 'players', workflow: 'update-players.yml', profile: 'productive', healthBarrier: true, decision: 'retry-exhausted' },
  ], new Date('2026-09-01T16:15:00Z'));
  assert.deepEqual(result, healthResult);
});

test('human summary explains retry and Health deferral while keeping machine decisions', () => {
  const config = loadConfig();
  const markdown = scheduler.buildSummaryMarkdown([
    {
      id: 'players', workflow: 'update-players.yml', profile: 'productive', healthBarrier: true,
      decision: 'dispatch', dispatched: true, dueAt: '2026-09-01T16:15:00.000Z', retryAttempt: 2, maxAttempts: 3,
      previousRunId: 401, previousConclusion: 'failure',
    },
    {
      id: 'workflow-health', workflow: 'workflow-health-snapshot.yml', profile: 'observer', healthBarrier: false,
      decision: 'deferred', dueAt: '2026-09-01T16:07:00.000Z', hardDispatchBarrier: true,
      blockingTargets: [{ id: 'players', decision: 'dispatch' }],
    },
  ], new Date('2026-09-01T16:29:00Z'), config);
  assert.match(markdown, /Scheduler summary/);
  assert.match(markdown, /Retry 2\/3 after run #401 ended failure/);
  assert.match(markdown, /Why Health waited/);
  assert.match(markdown, /productive work starts this tick: players \(dispatch\)/);
  assert.match(markdown, /Machine-readable decisions/);
});

test('scheduler state serializes deterministically and validates schema', () => {
  const config = loadConfig();
  const state = scheduler.createEmptySchedulerState(config);
  state.targets.players = { dueAt: '2026-09-01T16:15:00.000Z', attemptsDispatched: 1 };
  scheduler.validateSchedulerState(state, config);
  assert.equal(scheduler.serializeSchedulerState(state), '{\n  "schemaVersion": 1,\n  "targets": {\n    "players": {\n      "dueAt": "2026-09-01T16:15:00.000Z",\n      "attemptsDispatched": 1\n    }\n  }\n}\n');
});

test('scheduler runtime state initializes an isolated root branch', async () => {
  const config = loadConfig();
  const calls = [];
  const github = {
    rest: {
      git: {
        createBlob: async (args) => { calls.push(['blob', args]); return { data: { sha: 'blob-sha' } }; },
        createTree: async (args) => { calls.push(['tree', args]); return { data: { sha: 'tree-sha' } }; },
        createCommit: async (args) => { calls.push(['commit', args]); return { data: { sha: 'commit-sha' } }; },
        getRef: async () => { const error = new Error('missing'); error.status = 404; throw error; },
        createRef: async (args) => { calls.push(['create-ref', args]); },
        updateRef: async () => { throw new Error('updateRef should not be called for a missing branch'); },
      },
    },
  };
  const core = { info: () => {} };
  const state = scheduler.createEmptySchedulerState(config);
  state.targets.players = { dueAt: '2026-09-01T16:15:00.000Z', attemptsDispatched: 1 };
  const changed = await scheduler.persistSchedulerState({
    github,
    context: { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } },
    config,
    core,
    state,
    previousSerialized: scheduler.serializeSchedulerState(scheduler.createEmptySchedulerState(config)),
    existed: false,
  });
  assert.equal(changed, true);
  assert.deepEqual(calls.find(([name]) => name === 'commit')[1].parents, []);
  assert.equal(calls.find(([name]) => name === 'create-ref')[1].ref, 'refs/heads/workflow-scheduler-state');
});

test('scheduler runtime state loads and validates the isolated state file', async () => {
  const config = loadConfig();
  const state = { schemaVersion: 1, targets: { players: { dueAt: '2026-09-01T16:15:00.000Z', attemptsDispatched: 2 } } };
  const github = {
    rest: {
      repos: {
        getContent: async () => ({ data: { content: Buffer.from(JSON.stringify(state)).toString('base64') } }),
      },
    },
  };
  const loaded = await scheduler.loadSchedulerState({
    github,
    context: { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } },
    config,
    core: { info: () => {} },
  });
  assert.deepEqual(loaded.state, state);
  assert.equal(loaded.exists, true);
});

test('scheduler config rejects unknown profiles and malformed retry policies', () => {
  const config = loadConfig();
  const unknown = JSON.parse(JSON.stringify(config));
  unknown.targets[0].profile = 'missing';
  assert.throws(() => scheduler.validateConfig(unknown), /Unknown profile/);

  const invalidRetry = JSON.parse(JSON.stringify(config));
  invalidRetry.retryPolicies.standard.backoffMinutes = [5];
  assert.throws(() => scheduler.validateConfig(invalidRetry), /Invalid backoffMinutes/);
});
