'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const entry = require('../run-workflow-scheduler-entry.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const STATE = { branch: 'workflow-scheduler-state', path: 'workflow-scheduler-state.json' };

function httpError(status, message = `HTTP ${status}`) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function githubClient(getContent) {
  return {
    rest: {
      repos: { getContent },
      actions: {},
      git: {},
    },
  };
}

test('state-read retry classification is limited to transient server and network failures', () => {
  assert.equal(entry.isTransientStateReadError(httpError(500)), true);
  assert.equal(entry.isTransientStateReadError(httpError(502)), true);
  assert.equal(entry.isTransientStateReadError(httpError(503)), true);
  assert.equal(entry.isTransientStateReadError(httpError(504)), true);
  assert.equal(entry.isTransientStateReadError(httpError(404)), false);
  assert.equal(entry.isTransientStateReadError(httpError(401)), false);

  const network = new Error('socket reset');
  network.code = 'ECONNRESET';
  assert.equal(entry.isTransientStateReadError(network), true);

  const wrappedNetwork = new TypeError('fetch failed');
  wrappedNetwork.cause = { code: 'UND_ERR_CONNECT_TIMEOUT' };
  assert.equal(entry.isTransientStateReadError(wrappedNetwork), true);
});

test('scheduler state read recovers after one transient GitHub API failure', async () => {
  let calls = 0;
  const delays = [];
  const warnings = [];
  const github = githubClient(async () => {
    calls += 1;
    if (calls === 1) throw httpError(504, 'gateway timeout');
    return { data: { content: 'ok' } };
  });

  const retrying = entry.createStateReadRetryClient({
    github,
    core: { warning: (message) => warnings.push(message) },
    state: STATE,
    retryDelaysMs: [1, 2],
    sleepFn: async (delay) => delays.push(delay),
  });

  const response = await retrying.rest.repos.getContent({ path: STATE.path, ref: STATE.branch });
  assert.deepEqual(response, { data: { content: 'ok' } });
  assert.equal(calls, 2);
  assert.deepEqual(delays, [1]);
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /HTTP 504/);
  assert.match(warnings[0], /attempt 2\/3/);
});

test('scheduler state read stops after the bounded retry budget', async () => {
  let calls = 0;
  const delays = [];
  const github = githubClient(async () => {
    calls += 1;
    throw httpError(503, 'service unavailable');
  });

  const retrying = entry.createStateReadRetryClient({
    github,
    core: { warning: () => {} },
    state: STATE,
    retryDelaysMs: [1, 2],
    sleepFn: async (delay) => delays.push(delay),
  });

  await assert.rejects(
    retrying.rest.repos.getContent({ path: STATE.path, ref: STATE.branch }),
    (error) => error.status === 503,
  );
  assert.equal(calls, 3);
  assert.deepEqual(delays, [1, 2]);
});

test('404 keeps scheduler-state initialization semantics without retry', async () => {
  let calls = 0;
  const delays = [];
  const github = githubClient(async () => {
    calls += 1;
    throw httpError(404, 'not found');
  });

  const retrying = entry.createStateReadRetryClient({
    github,
    core: { warning: () => {} },
    state: STATE,
    retryDelaysMs: [1, 2],
    sleepFn: async (delay) => delays.push(delay),
  });

  await assert.rejects(
    retrying.rest.repos.getContent({ path: STATE.path, ref: STATE.branch }),
    (error) => error.status === 404,
  );
  assert.equal(calls, 1);
  assert.deepEqual(delays, []);
});

test('permanent client errors and unrelated content reads are not retried', async () => {
  let authCalls = 0;
  const authGithub = githubClient(async () => {
    authCalls += 1;
    throw httpError(401, 'bad credentials');
  });
  const authRetrying = entry.createStateReadRetryClient({
    github: authGithub,
    core: { warning: () => {} },
    state: STATE,
    retryDelaysMs: [1, 2],
    sleepFn: async () => { throw new Error('sleep should not be called'); },
  });
  await assert.rejects(
    authRetrying.rest.repos.getContent({ path: STATE.path, ref: STATE.branch }),
    (error) => error.status === 401,
  );
  assert.equal(authCalls, 1);

  let unrelatedCalls = 0;
  const unrelatedGithub = githubClient(async () => {
    unrelatedCalls += 1;
    throw httpError(504, 'gateway timeout');
  });
  const unrelatedRetrying = entry.createStateReadRetryClient({
    github: unrelatedGithub,
    core: { warning: () => {} },
    state: STATE,
    retryDelaysMs: [1, 2],
    sleepFn: async () => { throw new Error('sleep should not be called'); },
  });
  await assert.rejects(
    unrelatedRetrying.rest.repos.getContent({ path: 'some-other-file.json', ref: STATE.branch }),
    (error) => error.status === 504,
  );
  assert.equal(unrelatedCalls, 1);
});

test('scheduler workflow invokes the retry-aware action entrypoint', () => {
  const content = fs.readFileSync(path.join(ROOT, '.github', 'workflows', 'scheduler.yml'), 'utf8');
  assert.match(content, /run-workflow-scheduler-entry\.cjs/);
  assert.doesNotMatch(content, /require\('\.\/tools\/run-workflow-scheduler-runtime\.cjs'\)/);
});
