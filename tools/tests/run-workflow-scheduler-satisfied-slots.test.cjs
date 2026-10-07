'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const scheduler = require('../run-workflow-scheduler-runtime.cjs');

function target(overrides = {}) {
  return {
    id: 'standings',
    workflow: 'update-standings.yml',
    path: '.github/workflows/update-standings.yml',
    eventType: 'scheduler-update-standings',
    profile: 'productive',
    timezone: 'Etc/UTC',
    cron: ['35 7 * * 3'],
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
    ...overrides,
  };
}

const productive = { healthBarrier: true, retryPolicy: 'standard' };
const retryPolicy = {
  maxAttempts: 3, backoffMinutes: [5, 10], cooldownMinutes: 60, dispatchObservationTimeoutMinutes: 15,
};
// Wednesday 2026-10-07 07:35Z is the weekly due slot.
const DUE = '2026-10-07T07:35:00.000Z';
const savedSlot = { dueAt: DUE, runId: 37614747024, recordedAt: '2026-10-07T07:40:00.000Z' };

function run(id, createdAt, status, conclusion, extra = {}) {
  return { id, event: 'repository_dispatch', head_branch: 'main', created_at: createdAt, updated_at: createdAt, status, conclusion, ...extra };
}

function evaluate(runs, now, targetState = null, satisfiedSlot = null, t = target()) {
  return scheduler.evaluateTargetWithRetry(t, productive, retryPolicy, 'main', new Date(now), 11520, runs, targetState, satisfiedSlot);
}

test('satisfied slot is never re-dispatched when the run list no longer contains the successful run', () => {
  const evaluation = evaluate([], '2026-10-07T12:15:00Z', null, savedSlot);
  assert.equal(evaluation.result.decision, 'satisfied');
  assert.equal(evaluation.result.satisfiedFromState, true);
  assert.equal(evaluation.result.satisfyingRunId, 37614747024);
  assert.equal(evaluation.nextState, null);
  assert.deepEqual(evaluation.satisfiedSlot, savedSlot);
  assert.match(scheduler.reasonForResult(evaluation.result, 'UTC'), /evidence from scheduler state/);
});

test('without stored evidence the same empty run list still dispatches', () => {
  const evaluation = evaluate([], '2026-10-07T12:15:00Z', null, null);
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.satisfiedSlot, undefined);
});

test('a live successful run is recorded as the satisfied slot and keeps stable bookkeeping', () => {
  const success = run(1, '2026-10-07T07:36:00Z', 'completed', 'success');
  const first = evaluate([success], '2026-10-07T08:00:00Z');
  assert.equal(first.result.decision, 'satisfied');
  assert.equal(first.result.satisfiedFromState, undefined);
  assert.equal(first.satisfiedSlot.dueAt, DUE);
  assert.equal(first.satisfiedSlot.runId, 1);
  assert.equal(first.satisfiedSlot.recordedAt, '2026-10-07T08:00:00.000Z');
  const second = evaluate([success], '2026-10-07T08:05:00Z', null, first.satisfiedSlot);
  assert.deepEqual(second.satisfiedSlot, first.satisfiedSlot);
});

test('a newer due slot after the stored one behaves normally', () => {
  const evaluation = evaluate([], '2026-10-14T07:50:00Z', null, savedSlot);
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.dueAt, '2026-10-14T07:35:00.000Z');
});

test('cancelled waiting runs are not failed attempts and trigger no retry wait or circuit', () => {
  const t = target({ cron: ['*/10 * * * *'] });
  const cancelled = run(2, '2026-10-07T12:20:30Z', 'completed', 'cancelled');
  const afterDispatch = { dueAt: '2026-10-07T12:20:00.000Z', attemptsDispatched: 1, lastDispatchAt: '2026-10-07T12:20:20.000Z' };
  const evaluation = evaluate([cancelled], '2026-10-07T12:25:00Z', afterDispatch, null, t);
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.retryAttempt, 1);
});

test('three cancelled runs never exhaust the retry circuit', () => {
  const t = target({ cron: ['*/10 * * * *'] });
  const runs = [
    run(5, '2026-10-07T12:24:00Z', 'completed', 'cancelled'),
    run(4, '2026-10-07T12:22:00Z', 'completed', 'cancelled'),
    run(3, '2026-10-07T12:20:30Z', 'completed', 'cancelled'),
  ];
  const state = { dueAt: '2026-10-07T12:20:00.000Z', attemptsDispatched: 3, lastDispatchAt: '2026-10-07T12:24:00.000Z' };
  const evaluation = evaluate(runs, '2026-10-07T12:27:00Z', state, null, t);
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.retryAttempt, 1);
});

test('a real failure next to a cancelled run keeps the normal retry behavior', () => {
  const t = target({ cron: ['*/10 * * * *'] });
  const runs = [
    run(8, '2026-10-07T12:24:00Z', 'completed', 'cancelled'),
    run(7, '2026-10-07T12:20:30Z', 'completed', 'failure'),
  ];
  const state = { dueAt: '2026-10-07T12:20:00.000Z', attemptsDispatched: 2, lastDispatchAt: '2026-10-07T12:24:00.000Z' };
  const waiting = evaluate(runs, '2026-10-07T12:25:00Z', state, null, t);
  assert.equal(waiting.result.decision, 'retry-wait');
  assert.equal(waiting.result.previousConclusion, 'failure');
  assert.equal(waiting.result.attemptsDispatched, 1);
});

test('three real failures still exhaust the circuit', () => {
  const t = target({ cron: ['*/10 * * * *'] });
  const runs = [
    run(13, '2026-10-07T12:35:00Z', 'completed', 'failure'),
    run(12, '2026-10-07T12:26:00Z', 'completed', 'failure'),
    run(11, '2026-10-07T12:20:30Z', 'completed', 'failure'),
  ];
  const state = { dueAt: '2026-10-07T12:20:00.000Z', attemptsDispatched: 3, lastDispatchAt: '2026-10-07T12:35:00.000Z' };
  const evaluation = evaluate(runs, '2026-10-07T12:38:00Z', state, null, t);
  assert.equal(evaluation.result.decision, 'retry-exhausted');
  assert.equal(evaluation.nextState.circuitOpenUntil, '2026-10-07T13:35:00.000Z');
});

function makeConfig(overrides = {}) {
  return {
    schemaVersion: 2,
    repository: 'Lolindhir/fantasy-app',
    ref: 'main',
    lookbackMinutes: 11520,
    summaryTimezone: 'Europe/Berlin',
    dispatchObservation: { timeoutMinutes: 15 },
    state: { schemaVersion: 1, branch: 'workflow-scheduler-state', path: 'workflow-scheduler-state.json' },
    retryPolicies: { standard: { maxAttempts: 3, backoffMinutes: [5, 10], cooldownMinutes: 60 } },
    profiles: { productive: { healthBarrier: true, retryPolicy: 'standard' } },
    targets: [target()],
    ...overrides,
  };
}

function harness({ stateText, listRuns, config = makeConfig() }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sched-'));
  const configPath = path.join(dir, 'schedules.json');
  fs.writeFileSync(configPath, JSON.stringify(config));
  const calls = { dispatch: [], list: [], commits: [], getContent: 0 };
  const github = {
    rest: {
      repos: {
        getContent: async () => {
          calls.getContent += 1;
          const text = typeof stateText === 'function' ? stateText(calls.getContent) : stateText;
          if (text === null) { const error = new Error('Not Found'); error.status = 404; throw error; }
          return { data: { content: Buffer.from(text).toString('base64') } };
        },
        createDispatchEvent: async (args) => { calls.dispatch.push(args); },
      },
      actions: {
        listWorkflowRuns: async (args) => { calls.list.push(args); return { data: { workflow_runs: listRuns(args) } }; },
      },
      git: {
        createBlob: async ({ content }) => { calls.commits.push(content); return { data: { sha: 'b' } }; },
        createTree: async () => ({ data: { sha: 't' } }),
        createCommit: async () => ({ data: { sha: 'c' } }),
        getRef: async () => ({}),
        updateRef: async () => ({}),
        createRef: async () => ({}),
      },
    },
  };
  const core = { info() {}, warning() {}, error() {}, summary: undefined };
  const context = { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } };
  return { github, core, context, calls, configPath };
}

test('end to end: persisted satisfied slot prevents a dispatch when the run list is empty', async () => {
  const state = JSON.stringify({ schemaVersion: 1, targets: {}, satisfiedSlots: { standings: savedSlot } });
  const h = harness({ stateText: state, listRuns: () => [] });
  const results = await scheduler.run({ ...h, now: new Date('2026-10-07T12:15:00Z') });
  assert.equal(results[0].decision, 'satisfied');
  assert.equal(results[0].satisfiedFromState, true);
  assert.equal(h.calls.dispatch.length, 0);
  assert.equal(h.calls.commits.length, 0);
});

test('end to end: a satisfying run is persisted and obsolete target entries are pruned', async () => {
  const state = JSON.stringify({ schemaVersion: 1, targets: {}, satisfiedSlots: { removed: savedSlot } });
  const h = harness({ stateText: state, listRuns: () => [run(9, '2026-10-07T07:36:00Z', 'completed', 'success')] });
  await scheduler.run({ ...h, now: new Date('2026-10-07T08:00:00Z') });
  assert.equal(h.calls.commits.length, 1);
  const written = JSON.parse(h.calls.commits[0]);
  assert.deepEqual(Object.keys(written.satisfiedSlots), ['standings']);
  assert.equal(written.satisfiedSlots.standings.runId, 9);
});

test('end to end: fallback query finds the hidden successful run before any dispatch', async () => {
  const hidden = run(77, '2026-10-07T07:36:00Z', 'completed', 'success');
  const h = harness({
    stateText: null,
    listRuns: (args) => (args.event === 'repository_dispatch' ? [hidden] : []),
  });
  const results = await scheduler.run({ ...h, now: new Date('2026-10-07T12:15:00Z') });
  assert.equal(results[0].decision, 'satisfied');
  assert.equal(results[0].runQueryFallbackUsed, true);
  assert.equal(results[0].runQueryFallbackRecovered, true);
  assert.equal(h.calls.dispatch.length, 0);
  assert.equal(h.calls.list.length, 2);
  assert.equal(JSON.parse(h.calls.commits[0]).satisfiedSlots.standings.runId, 77);
});

test('end to end: genuinely missing runs still dispatch after the fallback query', async () => {
  const h = harness({ stateText: null, listRuns: () => [] });
  const results = await scheduler.run({ ...h, now: new Date('2026-10-07T12:15:00Z') });
  assert.equal(results[0].decision, 'dispatch');
  assert.equal(results[0].dispatched, true);
  assert.equal(h.calls.dispatch.length, 1);
  assert.equal(h.calls.list.length, 2);
});

test('state validation accepts an absent map and rejects malformed satisfied slots', () => {
  const config = makeConfig();
  scheduler.validateSchedulerState({ schemaVersion: 1, targets: {} }, config);
  scheduler.validateSchedulerState({ schemaVersion: 1, targets: {}, satisfiedSlots: { standings: savedSlot } }, config);
  assert.throws(() => scheduler.validateSchedulerState({ schemaVersion: 1, targets: {}, satisfiedSlots: [] }, config), /satisfiedSlots/);
  assert.throws(() => scheduler.validateSchedulerState({ schemaVersion: 1, targets: {}, satisfiedSlots: { standings: { dueAt: 'x' } } }, config), /dueAt/);
});

test('state read re-reads empty or truncated content before succeeding', async () => {
  const good = JSON.stringify({ schemaVersion: 1, targets: {} });
  for (const bad of ['', '{"schemaVersion": 1, "tar']) {
    const h = harness({ stateText: (call) => (call === 1 ? bad : good), listRuns: () => [run(9, '2026-10-07T07:36:00Z', 'completed', 'success')] });
    const delays = [];
    await scheduler.run({
      ...h, now: new Date('2026-10-07T08:00:00Z'), stateReadRetryDelaysMs: [1, 2], sleepFn: async (ms) => { delays.push(ms); },
    });
    assert.equal(h.calls.getContent, 2);
    assert.deepEqual(delays, [1]);
  }
});

test('state read fails closed after three empty reads', async () => {
  const h = harness({ stateText: '', listRuns: () => [] });
  const delays = [];
  await assert.rejects(
    scheduler.run({ ...h, now: new Date('2026-10-07T08:00:00Z'), stateReadRetryDelaysMs: [1, 2], sleepFn: async (ms) => { delays.push(ms); } }),
    /JSON input/,
  );
  assert.equal(h.calls.getContent, 3);
  assert.deepEqual(delays, [1, 2]);
});
