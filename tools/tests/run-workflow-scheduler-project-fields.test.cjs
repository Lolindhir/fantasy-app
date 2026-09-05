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
});

test('idle ticks do not dispatch when no Issue changed after the watermark', () => {
  const result = scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:00:00Z'),
    since: '2026-09-05T05:30:00Z',
    issues: [issue(10, '2026-09-05T05:30:00Z')],
    inFlight: null,
    config,
  });
  assert.equal(result.decision, 'idle');
  assert.deepEqual(result.issueNumbers, []);
});

test('recent Issue changes are debounced during the five-minute quiet window', () => {
  const result = scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:00:00Z'),
    since: '2026-09-05T05:30:00Z',
    issues: [issue(11, '2026-09-05T05:58:00Z'), issue(12, '2026-09-05T05:59:00Z')],
    inFlight: null,
    config,
  });
  assert.equal(result.decision, 'debounce');
  assert.deepEqual(result.issueNumbers, [11, 12]);
});

test('a quiet burst dispatches once all changed Issues have been quiet for five minutes', () => {
  const result = scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:05:00Z'),
    since: '2026-09-05T05:30:00Z',
    issues: [issue(11, '2026-09-05T05:56:00Z'), issue(12, '2026-09-05T06:00:00Z')],
    inFlight: null,
    config,
  });
  assert.equal(result.decision, 'dispatch');
  assert.equal(result.dispatchReason, 'quiet-period-met');
  assert.deepEqual(result.issueNumbers, [11, 12]);
});

test('continuous Issue activity is forced through after thirty minutes', () => {
  const result = scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:01:00Z'),
    since: '2026-09-05T05:20:00Z',
    issues: [issue(11, '2026-09-05T05:30:00Z'), issue(12, '2026-09-05T06:00:00Z')],
    inFlight: null,
    config,
  });
  assert.equal(result.decision, 'dispatch');
  assert.equal(result.dispatchReason, 'max-wait-reached');
});

test('an in-flight batch suppresses a second dispatch', () => {
  const result = scheduler.evaluateProjectFieldSync({
    now: new Date('2026-09-05T06:30:00Z'),
    since: '2026-09-05T05:30:00Z',
    issues: [issue(11, '2026-09-05T05:45:00Z')],
    inFlight: { id: 123, created_at: '2026-09-05T06:29:00Z' },
    config,
  });
  assert.equal(result.decision, 'in-flight');
  assert.equal(result.inFlightRunId, 123);
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
