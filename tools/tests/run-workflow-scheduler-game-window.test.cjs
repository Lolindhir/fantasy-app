'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const gameWindow = require('../nfl-game-window.cjs');
const scheduler = require('../run-workflow-scheduler-runtime.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const SEASON = 2031;
// Fixture season 2031: October is EDT (UTC-4), the first Sunday of November (2031-11-02) switches to EST (UTC-5).
const WINDOW = { preKickoffMinutes: 15, postFinalMinutes: 60, idleCron: ['7 */6 * * *'] };

function game(id, day, time, extra = {}) {
  return { GameID: id, GameType: 'REG', Week: 1, GameDay: day, GameTime: time, AwayTeam: 'AAA', HomeTeam: 'BBB', ...extra };
}

function writeSeason(root, games, { finalIds = [], withFinality = true, season = SEASON } = {}) {
  const base = path.join(root, 'data-source', 'nfl');
  fs.mkdirSync(path.join(base, 'schedules'), { recursive: true });
  fs.writeFileSync(path.join(base, 'schedules', `${season}.json`), JSON.stringify({ Season: season, Games: games }));
  if (withFinality) {
    fs.mkdirSync(path.join(base, 'game-finality'), { recursive: true });
    fs.writeFileSync(
      path.join(base, 'game-finality', `${season}.json`),
      JSON.stringify({
        Season: season,
        Games: games.map((item) => ({ GameID: item.GameID, GameType: item.GameType, Week: item.Week, Final: finalIds.includes(item.GameID) })),
      }),
    );
  }
}

function tempRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'nfl-window-'));
}

function target(overrides = {}) {
  return {
    id: 'nfl-live',
    workflow: 'nfl-live.yml',
    path: '.github/workflows/nfl-live.yml',
    eventType: 'scheduler-nfl-live',
    profile: 'productive',
    timezone: 'Etc/UTC',
    cron: ['*/10 * * * *'],
    mode: 'game-window',
    gameWindow: { ...WINDOW },
    satisfyingEvents: ['repository_dispatch', 'workflow_dispatch'],
    ...overrides,
  };
}

// Sunday 2031-10-05: 13:00 ET = 17:00Z and 16:25 ET = 20:25Z (one overlapping block); Monday 2031-10-06 20:15 ET = 2031-10-07T00:15Z.
const SUNDAY = '2031-10-05';
const MONDAY = '2031-10-06';
const GAMES = [
  game('g1', SUNDAY, '13:00'),
  game('g2', SUNDAY, '16:25'),
  game('g3', MONDAY, '20:15'),
];

function status(root, nowIso, overrides = {}) {
  return gameWindow.resolveGameWindow({ target: target(overrides), now: new Date(nowIso), repoRoot: root });
}

test('Eastern kickoff conversion follows daylight saving time', () => {
  assert.equal(new Date(gameWindow.parseKickoff(game('x', '2031-10-26', '13:00')).ms).toISOString(), '2031-10-26T17:00:00.000Z');
  assert.equal(new Date(gameWindow.parseKickoff(game('x', '2031-11-02', '13:00')).ms).toISOString(), '2031-11-02T18:00:00.000Z');
  assert.equal(gameWindow.parseKickoff(game('x', '2031-03-09', '02:30')), null);
  const unknown = gameWindow.parseKickoff(game('x', '2031-10-05', ''));
  assert.equal(unknown.estimated, true);
  assert.equal(new Date(unknown.ms).toISOString(), '2031-10-05T04:00:00.000Z');
});

test('offseason is idle with the idle cron and reports no further window', () => {
  const root = tempRoot();
  writeSeason(root, GAMES);
  const winter = status(root, '2032-02-20T12:00:00Z');
  assert.equal(winter.state, 'idle');
  assert.equal(winter.nextWindowAt, null);
  assert.deepEqual(winter.cron, WINDOW.idleCron);
  const spring = status(root, '2031-04-10T12:00:00Z');
  assert.equal(spring.state, 'idle');
  assert.equal(spring.nextWindowAt, '2031-10-05T16:45:00.000Z');
});

test('a rest day without games is idle and names the next window', () => {
  const root = tempRoot();
  writeSeason(root, GAMES, { finalIds: ['g1', 'g2', 'g3'] });
  const tuesday = status(root, '2031-10-07T15:00:00Z');
  assert.equal(tuesday.state, 'idle');
  assert.equal(tuesday.cronSet, 'idle');
  assert.deepEqual(tuesday.cron, WINDOW.idleCron);
  assert.equal(tuesday.nextWindowAt, null);
  const saturday = status(root, '2031-10-04T15:00:00Z');
  assert.equal(saturday.state, 'idle');
  assert.equal(saturday.nextWindowAt, '2031-10-05T16:45:00.000Z');
  assert.equal(saturday.nextKickoffAt, '2031-10-05T17:00:00.000Z');
});

test('the window opens exactly preKickoffMinutes before the first kickoff', () => {
  const root = tempRoot();
  writeSeason(root, GAMES);
  assert.equal(status(root, '2031-10-05T16:44:00Z').state, 'idle');
  const open = status(root, '2031-10-05T16:45:00Z');
  assert.equal(open.state, 'in-window');
  assert.deepEqual(open.cron, ['*/10 * * * *']);
  assert.equal(open.gamesInBlock, 2);
});

test('live games keep the dense cron and overlapping games form one block', () => {
  const root = tempRoot();
  writeSeason(root, GAMES);
  const live = status(root, '2031-10-05T21:30:00Z');
  assert.equal(live.state, 'in-window');
  assert.equal(live.overrun, false);
  assert.equal(live.gamesNotFinal, 2);
  // 16:25 ET kickoff = 20:25Z, assumed end 23:55Z, plus 60 minutes post-final.
  assert.equal(live.windowEndsAt, '2031-10-06T00:55:00.000Z');
});

test('after the assumed end the window closes after the post-final lag when every game is final', () => {
  const root = tempRoot();
  writeSeason(root, GAMES, { finalIds: ['g1', 'g2', 'g3'] });
  assert.equal(status(root, '2031-10-06T00:54:00Z').state, 'in-window');
  const closed = status(root, '2031-10-06T00:55:00Z');
  assert.equal(closed.state, 'idle');
  assert.equal(closed.nextWindowAt, '2031-10-07T00:00:00.000Z');
});

test('a game that is not final keeps the window open up to the overrun cap', () => {
  const root = tempRoot();
  writeSeason(root, GAMES, { finalIds: ['g1'] });
  const overrun = status(root, '2031-10-06T01:30:00Z');
  assert.equal(overrun.state, 'in-window');
  assert.equal(overrun.overrun, true);
  assert.equal(overrun.gamesNotFinal, 1);
  // Assumed end 23:55Z + 180 minutes.
  assert.equal(overrun.windowEndsAt, '2031-10-06T02:55:00.000Z');
  assert.match(overrun.reason, /not final/);
  assert.equal(status(root, '2031-10-06T02:55:00Z').state, 'idle');
});

test('two blocks on the same day leave an idle gap between them', () => {
  const root = tempRoot();
  writeSeason(root, [game('early', SUNDAY, '09:30'), game('late', SUNDAY, '20:20')], { finalIds: ['early', 'late'] });
  // 09:30 ET = 13:30Z, assumed end 17:00Z, window end 18:00Z; 20:20 ET = 00:20Z+1, window opens 00:05Z.
  assert.equal(status(root, '2031-10-05T17:59:00Z').state, 'in-window');
  const gap = status(root, '2031-10-05T20:00:00Z');
  assert.equal(gap.state, 'idle');
  assert.equal(gap.nextWindowAt, '2031-10-06T00:05:00.000Z');
  assert.equal(status(root, '2031-10-06T00:06:00Z').state, 'in-window');
});

test('a moved game moves its window', () => {
  const root = tempRoot();
  writeSeason(root, [game('moved', SUNDAY, '13:00')]);
  assert.equal(status(root, '2031-10-05T17:30:00Z').state, 'in-window');
  writeSeason(root, [game('moved', MONDAY, '13:00')]);
  assert.equal(status(root, '2031-10-05T17:30:00Z').state, 'idle');
  assert.equal(status(root, '2031-10-06T17:30:00Z').state, 'in-window');
});

test('January postseason games are found through the previous season file', () => {
  const root = tempRoot();
  writeSeason(root, [game('wc', '2032-01-11', '16:30')], { finalIds: [] });
  assert.equal(status(root, '2032-01-11T21:30:00Z').state, 'in-window');
  assert.equal(status(root, '2032-01-12T17:00:00Z').state, 'idle');
});

test('an unknown kickoff time opens a window for the whole Eastern day', () => {
  const root = tempRoot();
  writeSeason(root, [game('tbd', SUNDAY, '')]);
  assert.equal(status(root, '2031-10-05T03:00:00Z').state, 'idle');
  assert.equal(status(root, '2031-10-05T12:00:00Z').state, 'in-window');
});

test('missing finality is not an error: games count as not final and the status says so', () => {
  const root = tempRoot();
  writeSeason(root, GAMES, { withFinality: false });
  const result = status(root, '2031-10-06T01:30:00Z');
  assert.equal(result.state, 'in-window');
  assert.equal(result.finalityKnown, false);
});

test('an unreadable or missing schedule fails closed to the dense cron', () => {
  const missing = status(tempRoot(), '2031-10-05T21:30:00Z');
  assert.equal(missing.state, 'schedule-unavailable');
  assert.deepEqual(missing.cron, ['*/10 * * * *']);
  assert.match(missing.reason, /dense cron/);

  const broken = tempRoot();
  fs.mkdirSync(path.join(broken, 'data-source', 'nfl', 'schedules'), { recursive: true });
  fs.writeFileSync(path.join(broken, 'data-source', 'nfl', 'schedules', `${SEASON}.json`), '{ not json');
  assert.equal(status(broken, '2031-10-05T21:30:00Z').state, 'schedule-unavailable');

  const wrongSeason = tempRoot();
  writeSeason(wrongSeason, GAMES);
  fs.writeFileSync(
    path.join(wrongSeason, 'data-source', 'nfl', 'schedules', `${SEASON}.json`),
    JSON.stringify({ Season: 1999, Games: GAMES }),
  );
  assert.equal(status(wrongSeason, '2031-10-05T21:30:00Z').state, 'schedule-unavailable');
});

test('config validation accepts game-window targets and rejects malformed ones', () => {
  const check = (t) => gameWindow.validateGameWindowConfig(t, scheduler.cronMatches);
  check(target());
  check({ ...target(), mode: undefined, gameWindow: undefined });
  assert.throws(() => check({ ...target(), mode: 'sometimes' }), /Unsupported scheduler mode/);
  assert.throws(() => check({ ...target(), gameWindow: undefined }), /requires a gameWindow object/);
  assert.throws(() => check({ ...target(), mode: undefined }), /requires mode/);
  assert.throws(() => check(target({ gameWindow: { ...WINDOW, idleCron: [] } })), /idleCron/);
  assert.throws(() => check(target({ gameWindow: { ...WINDOW, idleCron: ['61 * * * *'] } })), /outside/);
  assert.throws(() => check(target({ gameWindow: { ...WINDOW, preKickoffMinutes: -1 } })), /preKickoffMinutes/);
  assert.throws(() => check(target({ gameWindow: { ...WINDOW, maxOverrunMinutes: 0 } })), /maxOverrunMinutes/);
});

test('the real scheduler config validates and nfl-live uses the game-window mode', () => {
  const config = JSON.parse(fs.readFileSync(path.join(ROOT, '.github', 'workflow-schedules.json'), 'utf8'));
  scheduler.validateConfig(config);
  const windowed = config.targets.filter((item) => item.mode === 'game-window');
  assert.ok(windowed.some((item) => item.id === 'nfl-live'));
  for (const item of windowed) {
    assert.ok(item.gameWindow.idleCron.length > 0);
    assert.ok(item.gameWindow.postFinalMinutes >= 0);
  }
  const availability = config.targets.find((item) => item.id === 'nfl-player-availability');
  assert.equal(availability.mode, undefined, 'player availability keeps its ten minute cadence all season');
});

function makeConfig(t) {
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
    targets: [t],
  };
}

function harness(root, listRuns) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sched-window-'));
  const configPath = path.join(dir, 'schedules.json');
  fs.writeFileSync(configPath, JSON.stringify(makeConfig(target())));
  const calls = { dispatch: [] };
  const github = {
    rest: {
      repos: {
        getContent: async () => { const error = new Error('Not Found'); error.status = 404; throw error; },
        createDispatchEvent: async (args) => { calls.dispatch.push(args); },
      },
      actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: listRuns() } }) },
      git: {
        createBlob: async () => ({ data: { sha: 'b' } }),
        createTree: async () => ({ data: { sha: 't' } }),
        createCommit: async () => ({ data: { sha: 'c' } }),
        getRef: async () => ({}),
        updateRef: async () => ({}),
        createRef: async () => ({}),
      },
    },
  };
  const summaries = [];
  const core = {
    info() {}, warning() {}, error() {},
    summary: { addRaw(text) { summaries.push(text); return { write: async () => {} }; } },
  };
  const context = { repo: { owner: 'Lolindhir', repo: 'fantasy-app' } };
  return { github, core, context, calls, configPath, summaries, repoRoot: root };
}

test('end to end: inside a window the dense ten minute slot is dispatched', async () => {
  const root = tempRoot();
  writeSeason(root, GAMES);
  const h = harness(root, () => []);
  const results = await scheduler.run({ ...h, now: new Date('2031-10-05T21:34:00Z') });
  assert.equal(results[0].decision, 'dispatch');
  assert.equal(results[0].dueAt, '2031-10-05T21:30:00.000Z');
  assert.equal(results[0].gameWindow.state, 'in-window');
  assert.equal(h.calls.dispatch.length, 1);
  assert.match(h.summaries[0], /### NFL game windows/);
  assert.match(h.summaries[0], /in-window/);
});

test('end to end: outside a window only the idle slot is due and a satisfied idle slot stays quiet', async () => {
  const root = tempRoot();
  writeSeason(root, GAMES, { finalIds: ['g1', 'g2', 'g3'] });
  const success = {
    id: 5, event: 'repository_dispatch', head_branch: 'main', created_at: '2031-10-07T06:08:00Z', updated_at: '2031-10-07T06:09:00Z',
    status: 'completed', conclusion: 'success',
  };
  const h = harness(root, () => [success]);
  const results = await scheduler.run({ ...h, now: new Date('2031-10-07T09:34:00Z') });
  assert.equal(results[0].decision, 'satisfied');
  assert.equal(results[0].dueAt, '2031-10-07T06:07:00.000Z');
  assert.equal(results[0].gameWindow.state, 'idle');
  assert.equal(h.calls.dispatch.length, 0);
  assert.match(h.summaries[0], /Game window: idle/);
});

test('end to end: an unreadable schedule never pauses the target', async () => {
  const h = harness(tempRoot(), () => []);
  const results = await scheduler.run({ ...h, now: new Date('2031-10-07T09:34:00Z') });
  assert.equal(results[0].decision, 'dispatch');
  assert.equal(results[0].dueAt, '2031-10-07T09:30:00.000Z');
  assert.equal(results[0].gameWindow.state, 'schedule-unavailable');
});
