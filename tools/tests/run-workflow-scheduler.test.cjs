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
  'update-fantasypros-rankings.yml': { timezone: 'Europe/Berlin', cron: ['20 5 * * *'] },
  'update-fantasycalc-rankings.yml': { timezone: 'Europe/Berlin', cron: ['32 5 * * *'] },
  'update-fantasy-football-calculator-adp.yml': { timezone: 'Europe/Berlin', cron: ['44 5 * * *'] },
  'update-fftoday-projections.yml': { timezone: 'Europe/Berlin', cron: ['56 5 * * *'] },
  'update-cbs-sports-projections.yml': { timezone: 'Europe/Berlin', cron: ['8 6 * * *'] },
  'update-sleeper-trending.yml': { timezone: 'Europe/Berlin', cron: ['20 6 * * *'] },
  'materialize-fantasy-operations-inputs.yml': { timezone: 'Europe/Berlin', cron: ['45 6 * * *'] },
  'clean-backups.yml': { timezone: 'Europe/Berlin', cron: ['0 17 * * 3'] },
};

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

test('central config preserves all 14 previous schedules', () => {
  const config = loadConfig();
  scheduler.validateConfig(config);
  assert.equal(config.targets.length, 14);
  const actual = Object.fromEntries(config.targets.map((target) => [target.workflow, { timezone: target.timezone, cron: target.cron }]));
  assert.deepEqual(actual, EXPECTED);
  assert.equal(new Set(config.targets.map((target) => target.eventType)).size, 14);
});

test('migrated targets have repository_dispatch and no local schedule trigger', () => {
  const config = loadConfig();
  for (const target of config.targets) {
    const content = fs.readFileSync(path.join(ROOT, target.path), 'utf8');
    assert.doesNotMatch(content, /\n  schedule:\s*\n/, `${target.path} still contains a local schedule trigger`);
    assert.match(content, /\n  repository_dispatch:\s*\n/, `${target.path} is missing repository_dispatch`);
    assert.match(content, new RegExp(target.eventType.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.match(content, /\n  workflow_dispatch:/, `${target.path} lost manual workflow_dispatch`);
  }
});

test('ten-minute cron resolves latest due slot', () => {
  const now = new Date('2026-09-01T16:27:30Z');
  const due = scheduler.latestDueSlot(['*/10 * * * *'], 'Etc/UTC', now, 60);
  assert.equal(due.toISOString(), '2026-09-01T16:20:00.000Z');
});

test('Berlin daily schedule preserves DST semantics', () => {
  const summer = scheduler.latestDueSlot(['45 6 * * *'], 'Europe/Berlin', new Date('2026-08-17T05:50:00Z'), 1440);
  const winter = scheduler.latestDueSlot(['45 6 * * *'], 'Europe/Berlin', new Date('2026-12-17T07:00:00Z'), 1440);
  assert.equal(summer.toISOString(), '2026-08-17T04:45:00.000Z');
  assert.equal(winter.toISOString(), '2026-12-17T05:45:00.000Z');
});

test('New York player schedule is evaluated in local time', () => {
  const due = scheduler.latestDueSlot(['15 1 * * *', '0 8 * * *', '30 13 * * *'], 'America/New_York', new Date('2026-09-01T13:10:00Z'), 1440);
  assert.equal(due.toISOString(), '2026-09-01T12:00:00.000Z');
});

test('weekly cron finds previous Wednesday within lookback', () => {
  const due = scheduler.latestDueSlot(['0 17 * * 3'], 'Europe/Berlin', new Date('2026-09-01T16:00:00Z'), 11520);
  assert.equal(due.toISOString(), '2026-08-26T15:00:00.000Z');
});

test('a queued or failed run after the slot prevents five-minute retrigger loops', () => {
  const target = {
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
  };
  const due = new Date('2026-09-01T16:20:00Z');
  assert.equal(scheduler.runSatisfiesSlot({ event: 'repository_dispatch', head_branch: 'main', created_at: '2026-09-01T16:21:00Z', status: 'queued', conclusion: null }, target, due, 'main'), true);
  assert.equal(scheduler.runSatisfiesSlot({ event: 'repository_dispatch', head_branch: 'main', created_at: '2026-09-01T16:21:00Z', status: 'completed', conclusion: 'failure' }, target, due, 'main'), true);
});

test('runs before the latest due slot do not satisfy catch-up', () => {
  const target = {
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
  };
  const due = new Date('2026-09-01T16:20:00Z');
  assert.equal(scheduler.runSatisfiesSlot({ event: 'repository_dispatch', head_branch: 'main', created_at: '2026-09-01T16:19:59Z' }, target, due, 'main'), false);
});

test('multiple missed slots coalesce to only the latest due slot', () => {
  const target = {
    id: 'league',
    workflow: 'update-league.yml',
    eventType: 'scheduler-update-league',
    timezone: 'Etc/UTC',
    cron: ['*/10 * * * *'],
    satisfyingEvents: ['repository_dispatch', 'schedule', 'workflow_dispatch'],
  };
  const result = scheduler.evaluateTarget(target, 'main', new Date('2026-09-01T16:47:00Z'), 180, []);
  assert.equal(result.decision, 'dispatch');
  assert.equal(result.dueAt, '2026-09-01T16:40:00.000Z');
});
