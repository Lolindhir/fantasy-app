'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const scheduler = require('../run-workflow-scheduler.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const CONFIG_PATH = path.join(ROOT, '.github', 'workflow-schedules.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

test('League Live has no push coupling to generated Schedule or Games data', () => {
  const content = fs.readFileSync(
    path.join(ROOT, '.github', 'workflows', 'league-live.yml'),
    'utf8',
  );

  assert.doesNotMatch(content, /\n  push:\s*\n/);
  assert.doesNotMatch(content, /public\/data\/Games\.json/);
  assert.doesNotMatch(content, /public\/data\/Timestamps\.json/);
});

test('League Live run satisfies only an already-due scheduler slot', () => {
  const config = loadConfig();
  scheduler.validateConfig(config);
  const league = config.targets.find((item) => item.id === 'league-live');

  assert.ok(league);
  assert.deepEqual(league.cron, ['*/10 * * * *']);
  assert.ok(league.satisfyingEvents.includes('repository_dispatch'));

  const completedDispatch = {
    id: 543001,
    event: 'repository_dispatch',
    head_branch: 'main',
    created_at: '2026-09-15T13:21:00Z',
    status: 'completed',
    conclusion: 'success',
  };

  assert.equal(
    scheduler.runSatisfiesSlot(
      completedDispatch,
      league,
      new Date('2026-09-15T13:20:00Z'),
      'main',
    ),
    true,
  );

  assert.equal(
    scheduler.runSatisfiesSlot(
      completedDispatch,
      league,
      new Date('2026-09-15T13:30:00Z'),
      'main',
    ),
    false,
  );
});

test('League Live monitoring evaluates scheduler dispatch runs with a 45 minute staleness bound', () => {
  const content = fs.readFileSync(
    path.join(ROOT, '.ai-context', 'manual', 'workflow-monitoring.yaml'),
    'utf8',
  );
  const leagueStart = content.indexOf('  .github/workflows/league-live.yml:');
  const playersStart = content.indexOf('  .github/workflows/update-players.yml:', leagueStart);

  assert.notEqual(leagueStart, -1);
  assert.notEqual(playersStart, -1);

  const block = content.slice(leagueStart, playersStart);
  assert.match(block, /- repository_dispatch/);
  assert.doesNotMatch(block, /- push/);
  assert.match(block, /staleAfterMinutes: 45/);
});
