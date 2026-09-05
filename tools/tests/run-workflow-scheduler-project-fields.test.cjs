'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const scheduler = require('../run-project-field-sync-scheduler.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const config = {
  workflow: 'sync-project-fields.yml',
  eventType: 'scheduler-sync-project-fields',
  quietMinutes: 5,
  maxWaitMinutes: 30,
  bootstrapLookbackMinutes: 30,
};

function issue(number, updatedAt, extra = {}) {
  return { number, updated_at: updatedAt, ...extra };
}

function evaluate(overrides = {}) {
  return scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:00:00Z'),
    since: '2026-09-05T05:30:00Z',
    issues: [],
    inFlight: null,
    config,
    pendingState: null,
    ...overrides,
  });
}

test('central scheduler config owns the Project field sync debounce contract', () => {
  const fullConfig = JSON.parse(fs.readFileSync(path.join(ROOT, '.github', 'workflow-schedules.json'), 'utf8'));
  assert.deepEqual(fullConfig.projectFieldSync, config);
  scheduler.validateProjectFieldSyncConfig(fullConfig);
});

test('Project field workflow is scheduler-batched and keeps manual repair without Issue-event fan-out', () => {
  const content = fs.readFileSync(path.join(ROOT, '.github', 'workflows', 'sync-project-fields.yml'), 'utf8');
  assert.doesNotMatch(content, /\n  issues:\s*\n/, 'Project field sync still starts for every Issue event');
  assert.match(content, /\n  repository_dispatch:\s*\n/);
  assert.match(content, /scheduler-sync-project-fields/);
  assert.match(content, /\n  workflow_dispatch:/);
  assert.match(content, /matrix:\s*\n\s*issue_number:/);
});

test('scheduler entry invokes the Project field sync detector after normal scheduled work', () => {
  const content = fs.readFileSync(path.join(ROOT, 'tools', 'run-workflow-scheduler-entry.cjs'), 'utf8');
  assert.match(content, /run-project-field-sync-scheduler\.cjs/);
  assert.match(content, /await projectFieldSync\.run/);
  assert.match(content, /projectFieldSync\.run\(\{ github: retryingGithub/);
});

test('idle ticks do not dispatch when no Issue changed after the watermark', () => {
  const evaluation = evaluate({ issues: [issue(10, '2026-09-05T05:30:00Z')] });
  assert.equal(evaluation.result.decision, 'idle');
  assert.deepEqual(evaluation.result.issueNumbers, []);
  assert.equal(evaluation.nextState, null);
});

test('recent Issue changes are debounced and persist the start of the pending window', () => {
  const evaluation = evaluate({
    issues: [issue(11, '2026-09-05T05:58:00Z'), issue(12, '2026-09-05T05:59:00Z')],
  });
  assert.equal(evaluation.result.decision, 'debounce');
  assert.deepEqual(evaluation.result.issueNumbers, [11, 12]);
  assert.equal(evaluation.result.pendingSince, '2026-09-05T05:58:00.000Z');
  assert.deepEqual(evaluation.nextState, { pendingSince: '2026-09-05T05:58:00.000Z' });
});

test('a quiet burst dispatches once all changed Issues have been quiet for five minutes', () => {
  const evaluation = evaluate({
    now: new Date('2026-09-05T06:05:00Z'),
    issues: [issue(11, '2026-09-05T05:56:00Z'), issue(12, '2026-09-05T06:00:00Z')],
  });
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.dispatchReason, 'quiet-period-met');
  assert.deepEqual(evaluation.result.issueNumbers, [11, 12]);
  assert.equal(evaluation.nextState, null);
});

test('continuous Issue activity is forced through after thirty minutes', () => {
  const evaluation = evaluate({
    now: new Date('2026-09-05T06:01:00Z'),
    since: '2026-09-05T05:20:00Z',
    issues: [issue(11, '2026-09-05T05:30:00Z'), issue(12, '2026-09-05T06:00:00Z')],
  });
  assert.equal(evaluation.result.decision, 'dispatch');
  assert.equal(evaluation.result.dispatchReason, 'max-wait-reached');
});

test('repeated edits to the same Issue cannot slide the thirty-minute maximum wait forward', () => {
  const first = evaluate({
    now: new Date('2026-09-05T05:31:00Z'),
    since: '2026-09-05T05:20:00Z',
    issues: [issue(11, '2026-09-05T05:30:00Z')],
  });
  assert.equal(first.result.decision, 'debounce');
  assert.deepEqual(first.nextState, { pendingSince: '2026-09-05T05:30:00.000Z' });

  const later = evaluate({
    now: new Date('2026-09-05T06:01:00Z'),
    since: '2026-09-05T05:20:00Z',
    issues: [issue(11, '2026-09-05T06:00:00Z')],
    pendingState: first.nextState,
  });
  assert.equal(later.result.pendingSince, '2026-09-05T05:30:00.000Z');
  assert.equal(later.result.latestUpdateAt, '2026-09-05T06:00:00Z');
  assert.equal(later.result.decision, 'dispatch');
  assert.equal(later.result.dispatchReason, 'max-wait-reached');
});

test('an in-flight batch suppresses a second dispatch and clears stale pending state', () => {
  const evaluation = evaluate({
    now: new Date('2026-09-05T06:30:00Z'),
    issues: [issue(11, '2026-09-05T05:45:00Z')],
    inFlight: { id: 123, created_at: '2026-09-05T06:29:00Z' },
    pendingState: { pendingSince: '2026-09-05T05:45:00Z' },
  });
  assert.equal(evaluation.result.decision, 'in-flight');
  assert.equal(evaluation.result.inFlightRunId, 123);
  assert.equal(evaluation.nextState, null);
});

test('successful scheduler batches replace legacy issue-event runs as the watermark', () => {
  const runs = [
    { id: 1, event: 'issues', status: 'completed', conclusion: 'success', created_at: '2026-09-05T05:40:00Z' },
    { id: 2, event: 'repository_dispatch', status: 'completed', conclusion: 'failure', created_at: '2026-09-05T05:50:00Z' },
    { id: 3, event: 'repository_dispatch', status: 'completed', conclusion: 'success', created_at: '2026-09-05T05:45:00Z' },
  ];
  assert.equal(scheduler.selectWatermarkRun(runs).id, 3);
  assert.equal(scheduler.selectWatermarkRun(runs.filter((run) => run.event !== 'repository_dispatch')).id, 1);
});
