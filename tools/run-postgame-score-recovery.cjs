'use strict';

const fs = require('node:fs');

const DEFAULT_POLICY = Object.freeze({
  schedulePath: 'public/data/Schedule.json',
  timestampsPath: 'public/data/Timestamps.json',
  gamesWorkflow: 'update-games.yml',
  gamesEventType: 'scheduler-update-games',
  leagueWorkflow: 'update-league.yml',
  leagueEventType: 'scheduler-update-league',
  scoreRecoveryWindowHours: 72,
  gamesRetryMinutes: 10,
  leagueRetryMinutes: 5,
});

const BLOCKING_DECISIONS = new Set([
  'dispatch',
  'in-flight',
  'awaiting-observation',
  'observation-timeout',
  'observation-cooldown',
  'retry-wait',
  'retry-exhausted',
  'cooldown',
]);

function parseNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function hasCompleteScore(game) {
  const away = parseNumber(game?.awayPts ?? game?.AwayScore);
  const home = parseNumber(game?.homePts ?? game?.HomeScore);
  return away !== null && home !== null;
}

function gameStartMs(game) {
  const epoch = parseNumber(game?.gameTime_epoch);
  if (epoch !== null) return epoch * 1000;
  const rawDate = String(game?.gameDate || '');
  if (/^\d{8}$/.test(rawDate)) {
    const year = Number(rawDate.slice(0, 4));
    const month = Number(rawDate.slice(4, 6));
    const day = Number(rawDate.slice(6, 8));
    return Date.UTC(year, month - 1, day);
  }
  return null;
}

function missingRecentFinalScores(schedule, now, windowHours) {
  const cutoff = now.getTime() - windowHours * 60 * 60 * 1000;
  return (Array.isArray(schedule) ? schedule : []).filter((game) => {
    if (!/^Final/i.test(String(game?.gameStatus || ''))) return false;
    if (hasCompleteScore(game)) return false;
    const startMs = gameStartMs(game);
    return startMs === null || startMs >= cutoff;
  });
}

function parseTimestamp(value) {
  const parsed = Date.parse(String(value || ''));
  return Number.isFinite(parsed) ? parsed : null;
}

function leagueProjectionIsStale(timestamps) {
  const scheduleAt = parseTimestamp(timestamps?.Schedule);
  const contextAt = parseTimestamp(timestamps?.FantasyGameContext);
  if (scheduleAt === null) return false;
  if (contextAt === null) return true;
  return scheduleAt > contextAt;
}

function resultBlocksAdHocDispatch(results, id) {
  const result = (results || []).find((item) => item?.id === id);
  return Boolean(result && BLOCKING_DECISIONS.has(result.decision));
}

function runIsRecentOrActive(run, now, minutes) {
  if (!run) return false;
  if (run.status && run.status !== 'completed') return true;
  const createdAt = Date.parse(run.created_at || '');
  if (!Number.isFinite(createdAt)) return false;
  return now.getTime() - createdAt < minutes * 60 * 1000;
}

async function recentWorkflowRun(github, context, workflow, ref) {
  const response = await github.rest.actions.listWorkflowRuns({
    owner: context.repo.owner,
    repo: context.repo.repo,
    workflow_id: workflow,
    branch: ref,
    per_page: 20,
  });
  return (response.data.workflow_runs || [])[0] || null;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

async function dispatch(github, context, eventType, payload) {
  await github.rest.repos.createDispatchEvent({
    owner: context.repo.owner,
    repo: context.repo.repo,
    event_type: eventType,
    client_payload: payload,
  });
}

async function run({ github, context, core, schedulerResults = [], now = new Date(), ref = 'main', policy = {} }) {
  const effective = { ...DEFAULT_POLICY, ...policy };
  const schedule = readJson(effective.schedulePath);
  const timestamps = readJson(effective.timestampsPath);
  const missing = missingRecentFinalScores(schedule, now, effective.scoreRecoveryWindowHours);
  const result = {
    id: 'postgame-score-recovery',
    missingFinalScoreCount: missing.length,
    missingGameIds: missing.map((game) => String(game.gameID || '')).filter(Boolean),
    gamesDispatched: false,
    leagueProjectionStale: leagueProjectionIsStale(timestamps),
    leagueDispatched: false,
  };

  if (missing.length > 0 && !resultBlocksAdHocDispatch(schedulerResults, 'games')) {
    const latestGamesRun = await recentWorkflowRun(github, context, effective.gamesWorkflow, ref);
    if (!runIsRecentOrActive(latestGamesRun, now, effective.gamesRetryMinutes)) {
      await dispatch(github, context, effective.gamesEventType, {
        scheduler_id: 'postgame-score-recovery',
        workflow: effective.gamesWorkflow,
        reason: 'canonical-final-score-missing',
        missing_game_ids: result.missingGameIds,
        requested_at: now.toISOString(),
        ref,
      });
      result.gamesDispatched = true;
    }
  }

  if (result.leagueProjectionStale && !resultBlocksAdHocDispatch(schedulerResults, 'league')) {
    const latestLeagueRun = await recentWorkflowRun(github, context, effective.leagueWorkflow, ref);
    if (!runIsRecentOrActive(latestLeagueRun, now, effective.leagueRetryMinutes)) {
      await dispatch(github, context, effective.leagueEventType, {
        scheduler_id: 'postgame-league-convergence',
        workflow: effective.leagueWorkflow,
        reason: 'schedule-newer-than-fantasy-game-context',
        schedule_timestamp: timestamps.Schedule || null,
        fantasy_game_context_timestamp: timestamps.FantasyGameContext || null,
        requested_at: now.toISOString(),
        ref,
      });
      result.leagueDispatched = true;
    }
  }

  core.info(JSON.stringify(result));
  return result;
}

module.exports = {
  DEFAULT_POLICY,
  hasCompleteScore,
  leagueProjectionIsStale,
  missingRecentFinalScores,
  resultBlocksAdHocDispatch,
  run,
  runIsRecentOrActive,
};
