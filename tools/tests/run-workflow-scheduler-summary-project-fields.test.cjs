'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const summary = require('../run-workflow-scheduler-summary.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const now = new Date('2026-09-05T06:40:00Z');
const config = {
  summaryTimezone: 'Etc/UTC',
  projectFieldSync: {
    workflow: 'sync-project-fields.yml',
    quietMinutes: 5,
    maxWaitMinutes: 30,
  },
};
const normalResults = [{
  id: 'league',
  workflow: 'update-league.yml',
  profile: 'productive',
  decision: 'satisfied',
  dueAt: '2026-09-05T06:31:00Z',
  satisfyingRunId: 42,
}];

function project(overrides = {}) {
  return {
    id: 'project-fields',
    workflow: 'sync-project-fields.yml',
    decision: 'idle',
    since: '2026-09-05T06:31:11Z',
    issueNumbers: [],
    ...overrides,
  };
}

test('combined summary keeps normal scheduler rows and includes Project fields in human and machine-readable output', () => {
  const markdown = summary.buildCombinedSummaryMarkdown(normalResults, project({
    decision: 'debounce',
    pendingSince: '2026-09-05T06:37:00Z',
    latestUpdateAt: '2026-09-05T06:38:00Z',
    quietAgeMinutes: 2,
    pendingAgeMinutes: 3,
    issueNumbers: [356, 357],
  }), now, config);

  assert.match(markdown, /\| league \| productive \|/);
  assert.match(markdown, /### Project field synchronization/);
  assert.match(markdown, /🕒 Debouncing/);
  assert.match(markdown, /#356, #357/);
  assert.match(markdown, /quiet 2\/5 min, batch age 3\/30 min/);
  assert.match(markdown, /"id": "project-fields"/);
  assert.match(markdown, /"decision": "debounce"/);
  assert.equal((markdown.match(/Machine-readable decisions/g) || []).length, 1);
});

test('Project field summary renders every production decision state explicitly', () => {
  const cases = [
    [project(), /⚪ Idle/, /No Issue changed/],
    [project({
      decision: 'debounce',
      pendingSince: '2026-09-05T06:37:00Z',
      latestUpdateAt: '2026-09-05T06:39:00Z',
      quietAgeMinutes: 1,
      pendingAgeMinutes: 3,
      issueNumbers: [356],
    }), /🕒 Debouncing/, /1 changed Issue pending/],
    [project({
      decision: 'in-flight',
      inFlightRunId: 99,
      inFlightCreatedAt: '2026-09-05T06:39:00Z',
    }), /⏳ Batch in flight/, /duplicate batch is suppressed/],
    [project({
      decision: 'dispatch',
      dispatched: true,
      dispatchReason: 'quiet-period-met',
      pendingSince: '2026-09-05T06:32:00Z',
      latestUpdateAt: '2026-09-05T06:35:00Z',
      issueNumbers: [356, 357],
    }), /🚀 Batch dispatched/, /after the 5-minute quiet period/],
  ];

  for (const [result, statusPattern, reasonPattern] of cases) {
    const markdown = summary.buildCombinedSummaryMarkdown(normalResults, result, now, config);
    assert.match(markdown, statusPattern);
    assert.match(markdown, reasonPattern);
    assert.match(markdown, /"id": "project-fields"/);
  }
});

test('entrypoint performs Project-field evaluation before overwriting the intermediate runtime summary', () => {
  const content = fs.readFileSync(path.join(ROOT, 'tools', 'run-workflow-scheduler-entry.cjs'), 'utf8');
  const runtimeIndex = content.indexOf('await runtime.run');
  const projectIndex = content.indexOf('await projectFieldSync.run');
  const summaryIndex = content.lastIndexOf('await writeCombinedSummarySafely');

  assert.ok(runtimeIndex >= 0, 'runtime invocation missing');
  assert.ok(projectIndex > runtimeIndex, 'Project-field evaluation must follow normal scheduler work');
  assert.ok(summaryIndex > projectIndex, 'final combined summary must be written after Project-field evaluation');
  assert.match(content, /return \[\.\.\.results, projectFieldResult\]/);
});

test('combined summary records a Project detector error before the scheduler tick fails', () => {
  const markdown = summary.buildCombinedSummaryMarkdown(normalResults, project({
    decision: 'error',
    error: 'HTTP 503',
  }), now, config);

  assert.match(markdown, /❌ Detector error/);
  assert.match(markdown, /Project-field change detection failed: HTTP 503/);
  assert.match(markdown, /"decision": "error"/);
});
