'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const entry = require('../run-workflow-scheduler-entry.cjs');
const scheduler = require('../run-workflow-scheduler-runtime.cjs');

const NOW = new Date('2031-10-08T12:04:00Z');

function httpError(status, extra = {}) {
  const error = new Error(`HTTP ${status}`);
  error.status = status;
  return Object.assign(error, extra);
}

function config(extra = {}) {
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
    targets: [
      {
        id: 'league-live', workflow: 'league-live.yml', path: '.github/workflows/league-live.yml', eventType: 'scheduler-league-live',
        profile: 'productive', timezone: 'Etc/UTC', cron: ['*/10 * * * *'], satisfyingEvents: ['repository_dispatch'],
      },
    ],
    ...extra,
  };
}

// persisted holds the scheduler state between ticks, like the isolated state branch.
function harness({ listRuns, dispatch, persisted = { value: null }, cfg = config() }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sched-api-'));
  const configPath = path.join(dir, 'schedules.json');
  fs.writeFileSync(configPath, JSON.stringify(cfg));
  const calls = { list: 0, dispatch: 0 };
  const github = {
    rest: {
      repos: {
        getContent: async () => {
          if (persisted.value === null) throw httpError(404);
          return { data: { content: Buffer.from(persisted.value, 'utf8').toString('base64') } };
        },
        createDispatchEvent: async (args) => { calls.dispatch += 1; return dispatch ? dispatch(args) : undefined; },
      },
      actions: { listWorkflowRuns: async (args) => { calls.list += 1; return { data: { workflow_runs: listRuns(args, calls.list) } }; } },
      git: {
        createBlob: async ({ content }) => { persisted.value = content; return { data: { sha: 'b' } }; },
        createTree: async () => ({ data: { sha: 't' } }),
        createCommit: async () => ({ data: { sha: 'c' } }),
        getRef: async () => ({}),
        updateRef: async () => ({}),
        createRef: async () => ({}),
      },
    },
  };
  const logs = { warnings: [], errors: [], info: [], summaries: [] };
  const core = {
    info: (m) => logs.info.push(m),
    warning: (m) => logs.warnings.push(m),
    error: (m) => logs.errors.push(m),
    summary: { addRaw(text) { logs.summaries.push(text); return { write: async () => {} }; } },
  };
  const context = { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } };
  return { github, core, context, calls, logs, configPath, persisted };
}

async function tick(h, now = NOW) {
  return scheduler.run({ github: h.github, core: h.core, context: h.context, configPath: h.configPath, now, stateReadRetryDelaysMs: [0], sleepFn: async () => {} });
}

test('list reads recover after a single 502 through the retrying client', async () => {
  let failures = 1;
  const delays = [];
  const warnings = [];
  const github = {
    rest: {
      repos: { getContent: async () => ({}) },
      actions: {
        listWorkflowRuns: async () => {
          if (failures > 0) { failures -= 1; throw httpError(502); }
          return { data: { workflow_runs: [] } };
        },
      },
    },
  };
  const retrying = entry.createStateReadRetryClient({
    github,
    core: { warning: (m) => warnings.push(m) },
    state: { branch: 'b', path: 'p' },
    jitterFn: () => 7,
    sleepFn: async (d) => delays.push(d),
  });
  const response = await retrying.rest.actions.listWorkflowRuns({ workflow_id: 'league-live.yml' });
  assert.deepEqual(response, { data: { workflow_runs: [] } });
  assert.deepEqual(delays, [2007]);
  assert.match(warnings[0], /league-live\.yml/);
  assert.match(warnings[0], /HTTP 502/);
  assert.match(warnings[0], /attempt 2\/4/);
});

test('list reads use backoff 2/5/10 s, honour retry-after on 429 and give up after the budget', async () => {
  const delays = [];
  let calls = 0;
  const github = {
    rest: {
      repos: { getContent: async () => ({}) },
      actions: { listWorkflowRuns: async () => { calls += 1; throw httpError(429, { response: { status: 429, headers: { 'retry-after': '20' } } }); } },
    },
  };
  const retrying = entry.createStateReadRetryClient({
    github, core: { warning() {} }, state: { branch: 'b', path: 'p' }, jitterFn: () => 0, sleepFn: async (d) => delays.push(d),
  });
  await assert.rejects(retrying.rest.actions.listWorkflowRuns({ workflow_id: 'x' }), (error) => error.status === 429);
  assert.equal(calls, 4);
  assert.deepEqual(delays, [20000, 20000, 20000]);
});

test('403, 404 and 422 on list reads fail immediately without retry', async () => {
  for (const status of [401, 403, 404, 422]) {
    let calls = 0;
    const github = {
      rest: { repos: { getContent: async () => ({}) }, actions: { listWorkflowRuns: async () => { calls += 1; throw httpError(status); } } },
    };
    const retrying = entry.createStateReadRetryClient({
      github, core: { warning() {} }, state: { branch: 'b', path: 'p' }, sleepFn: async () => assert.fail('must not sleep'),
    });
    await assert.rejects(retrying.rest.actions.listWorkflowRuns({}), (error) => error.status === status);
    assert.equal(calls, 1);
  }
});

test('dispatch events are never wrapped by the retrying client', async () => {
  let calls = 0;
  const github = {
    rest: {
      repos: { getContent: async () => ({}), createDispatchEvent: async () => { calls += 1; throw httpError(503); } },
      actions: { listWorkflowRuns: async () => ({}) },
    },
  };
  const retrying = entry.createStateReadRetryClient({ github, core: { warning() {} }, state: { branch: 'b', path: 'p' }, sleepFn: async () => {} });
  await assert.rejects(retrying.rest.repos.createDispatchEvent({}), (error) => error.status === 503);
  assert.equal(calls, 1);
});

test('first transient read failure after retries yields api-error, no dispatch, warning only', async () => {
  const h = harness({ listRuns: () => { throw httpError(503); } });
  const results = await tick(h);
  assert.equal(results.length, 1);
  assert.equal(results[0].decision, 'api-error');
  assert.equal(results[0].apiErrorPhase, 'read');
  assert.equal(results[0].consecutiveTicks, 1);
  assert.equal(h.calls.dispatch, 0);
  assert.equal(h.logs.errors.length, 0);
  assert.ok(h.logs.warnings.some((m) => /league-live/.test(m) && /1\/2/.test(m)));
  assert.match(h.logs.summaries.at(-1), /API error/);
  assert.match(h.logs.summaries.at(-1), /GitHub API errors/);
  const stored = JSON.parse(h.persisted.value);
  assert.equal(stored.apiErrors['league-live'].consecutiveTicks, 1);
  assert.deepEqual(stored.targets, {});
});

test('the same read failure in consecutive ticks turns the run red', async () => {
  const h = harness({ listRuns: () => { throw httpError(500); } });
  await tick(h);
  await assert.rejects(tick(h, new Date(NOW.getTime() + 5 * 60000)), /league-live.*persistent, 2 consecutive ticks/);
  assert.equal(h.calls.dispatch, 0);
  assert.equal(JSON.parse(h.persisted.value).apiErrors['league-live'].consecutiveTicks, 2);
});

test('a successful tick resets the consecutive api-error counter', async () => {
  let fail = true;
  const h = harness({ listRuns: () => { if (fail) throw httpError(502); return []; } });
  await tick(h);
  fail = false;
  const results = await tick(h, new Date(NOW.getTime() + 5 * 60000));
  assert.equal(results[0].decision, 'dispatch');
  assert.equal(JSON.parse(h.persisted.value).apiErrors, undefined);
  fail = true;
  const again = await tick(h, new Date(NOW.getTime() + 10 * 60000));
  assert.equal(again[0].decision, 'api-error');
  assert.equal(again[0].consecutiveTicks, 1);
});

test('a non-transient read error (403) still fails the run immediately', async () => {
  const h = harness({ listRuns: () => { throw httpError(403); } });
  await assert.rejects(tick(h), /league-live: HTTP 403/);
  assert.equal(h.calls.dispatch, 0);
});

test('a 5xx on createDispatchEvent is not retried, records no run state and is an api-error', async () => {
  const h = harness({ listRuns: () => [], dispatch: () => { throw httpError(502); } });
  const results = await tick(h);
  assert.equal(h.calls.dispatch, 1);
  assert.equal(results[0].decision, 'api-error');
  assert.equal(results[0].apiErrorPhase, 'dispatch');
  const stored = JSON.parse(h.persisted.value);
  assert.deepEqual(stored.targets, {});
  assert.equal(stored.apiErrors['league-live'].consecutiveTicks, 1);
});

test('a 403 on createDispatchEvent still fails the run', async () => {
  const h = harness({ listRuns: () => [], dispatch: () => { throw httpError(403); } });
  await assert.rejects(tick(h), /league-live: HTTP 403/);
});

test('failAfterConsecutiveTicks is configurable and validated', async () => {
  const h = harness({ listRuns: () => { throw httpError(503); }, cfg: config({ apiErrorPolicy: { failAfterConsecutiveTicks: 1 } }) });
  await assert.rejects(tick(h), /persistent, 1 consecutive ticks/);
  assert.throws(() => scheduler.validateConfig(config({ apiErrorPolicy: { failAfterConsecutiveTicks: 0 } })), /apiErrorPolicy/);
});

test('the production schedule declares the api-error policy', () => {
  const real = JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', '..', '.github', 'workflow-schedules.json'), 'utf8'));
  assert.ok(Number.isInteger(real.apiErrorPolicy.failAfterConsecutiveTicks));
  scheduler.validateConfig(real);
});
