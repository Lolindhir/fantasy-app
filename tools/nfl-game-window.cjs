'use strict';

// Game-window evaluation for scheduler targets with mode "game-window" (Issue #946, step S3b of #471).
//
// A game window is derived from the canonical NFL schedule (data-source/nfl/schedules/<season>.json) and,
// when available, canonical game finality (data-source/nfl/game-finality/<season>.json). It decides whether
// the target runs on its normal (dense) cron or on its idle cron. Same inputs and Eastern-time kickoff rule
// as tools/nfl_season_context.py and CanonicalScheduleUtils.psm1.
//
// Rules:
//  * A block is a group of games whose assumed durations overlap (kickoff + assumedGameDurationMinutes).
//  * A window opens preKickoffMinutes before the first kickoff of a block.
//  * It closes postFinalMinutes after the assumed end of the block. Canonical finality carries no timestamp,
//    so "final plus postFinalMinutes" is anchored on the assumed end of the last game.
//  * While a game of the block is not final after that point the window stays open (overtime, delay,
//    suspension) for at most maxOverrunMinutes beyond the assumed end, so a game that never becomes final
//    cannot keep the window open forever.
//  * Fail-closed towards the dense cron: an unreadable or invalid schedule never pauses the target.

const fs = require('node:fs');
const path = require('node:path');

const NFL_TIME_ZONE = 'America/New_York';
const MINUTE_MS = 60000;

const DEFAULTS = Object.freeze({
  assumedGameDurationMinutes: 210,
  maxOverrunMinutes: 180,
  scheduleDir: 'data-source/nfl',
});

function zoneOffsetMs(utcMs, timeZone) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone,
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
      hourCycle: 'h23',
    }).formatToParts(new Date(utcMs)).map((part) => [part.type, part.value]),
  );
  const asUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
    Number(parts.second),
  );
  return asUtc - utcMs;
}

// Converts a local wall-clock time in `timeZone` to UTC milliseconds. Returns null for times that do not
// exist (DST gap); ambiguous times (DST overlap) resolve to the earlier instant, which only widens a window.
function localToUtcMs(year, month, day, hour, minute, timeZone) {
  const naive = Date.UTC(year, month - 1, day, hour, minute, 0);
  let utc = naive - zoneOffsetMs(naive, timeZone);
  utc = naive - zoneOffsetMs(utc, timeZone);
  const check = zoneOffsetMs(utc, timeZone);
  if (utc + check !== naive) return null;
  return utc;
}

function parseKickoff(game) {
  const dayMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(game.GameDay || '').trim());
  if (!dayMatch) return null;
  const [year, month, day] = [Number(dayMatch[1]), Number(dayMatch[2]), Number(dayMatch[3])];
  const timeText = String(game.GameTime || '').trim();
  const timeMatch = /^(\d{1,2}):(\d{2})$/.exec(timeText);
  if (!timeMatch) {
    // Kickoff time unknown (for example a flexed game not yet scheduled): treat the whole Eastern day as possible.
    const start = localToUtcMs(year, month, day, 0, 0, NFL_TIME_ZONE);
    return start === null ? null : { ms: start, estimated: true };
  }
  const kickoff = localToUtcMs(year, month, day, Number(timeMatch[1]), Number(timeMatch[2]), NFL_TIME_ZONE);
  return kickoff === null ? null : { ms: kickoff, estimated: false };
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

// Loads the games of the seasons that can contain games around `now` (the previous season hosts January
// postseason games). Returns { games, finalityKnown } or throws when no usable schedule exists.
function loadWindowGames({ repoRoot, scheduleDir = DEFAULTS.scheduleDir, now }) {
  const year = now.getUTCFullYear();
  const games = [];
  let usable = 0;
  let finalityKnown = true;
  for (const season of [year - 1, year]) {
    const schedulePath = path.join(repoRoot, scheduleDir, 'schedules', `${season}.json`);
    if (!fs.existsSync(schedulePath)) continue;
    const schedule = readJson(schedulePath);
    if (schedule.Season !== season || !Array.isArray(schedule.Games) || schedule.Games.length === 0) {
      throw new Error(`Invalid canonical NFL schedule contract for ${season}`);
    }
    usable += 1;

    const finalById = new Map();
    const finalityPath = path.join(repoRoot, scheduleDir, 'game-finality', `${season}.json`);
    try {
      const finality = readJson(finalityPath);
      if (!Array.isArray(finality.Games)) throw new Error('missing Games');
      for (const entry of finality.Games) finalById.set(entry.GameID, entry.Final === true);
    } catch (error) {
      finalityKnown = false;
    }

    for (const game of schedule.Games) {
      const kickoff = parseKickoff(game);
      if (!kickoff) throw new Error(`Invalid kickoff in canonical NFL schedule ${season}: ${game.GameID}`);
      games.push({
        id: game.GameID,
        season,
        gameType: game.GameType,
        kickoffMs: kickoff.ms,
        kickoffEstimated: kickoff.estimated,
        final: finalById.get(game.GameID) === true,
      });
    }
  }
  if (usable === 0) throw new Error(`No canonical NFL schedule found for seasons ${year - 1} and ${year}`);
  return { games, finalityKnown };
}

function resolveParams(gameWindow) {
  return {
    preKickoffMinutes: gameWindow.preKickoffMinutes,
    postFinalMinutes: gameWindow.postFinalMinutes,
    assumedGameDurationMinutes: gameWindow.assumedGameDurationMinutes ?? DEFAULTS.assumedGameDurationMinutes,
    maxOverrunMinutes: gameWindow.maxOverrunMinutes ?? DEFAULTS.maxOverrunMinutes,
  };
}

function buildBlocks(games, params) {
  const durationMs = params.assumedGameDurationMinutes * MINUTE_MS;
  const sorted = [...games].sort((left, right) => left.kickoffMs - right.kickoffMs || String(left.id).localeCompare(String(right.id)));
  const blocks = [];
  for (const game of sorted) {
    // An estimated kickoff (unknown time) covers its whole Eastern day.
    const endMs = game.kickoffEstimated ? game.kickoffMs + 24 * 60 * MINUTE_MS + durationMs : game.kickoffMs + durationMs;
    const current = blocks[blocks.length - 1];
    if (current && game.kickoffMs < current.assumedEndMs) {
      current.games.push(game);
      current.assumedEndMs = Math.max(current.assumedEndMs, endMs);
    } else {
      blocks.push({ firstKickoffMs: game.kickoffMs, assumedEndMs: endMs, games: [game] });
    }
  }
  const preMs = params.preKickoffMinutes * MINUTE_MS;
  const postMs = params.postFinalMinutes * MINUTE_MS;
  const overrunMs = params.maxOverrunMinutes * MINUTE_MS;
  return blocks.map((block) => {
    const allFinal = block.games.every((game) => game.final);
    return {
      ...block,
      allFinal,
      windowStartMs: block.firstKickoffMs - preMs,
      // Closes after the assumed end plus the post-final lag; extended by the overrun cap while a game is still not final.
      baseEndMs: block.assumedEndMs + postMs,
      overrunEndMs: block.assumedEndMs + Math.max(postMs, overrunMs),
    };
  });
}

function blockOpenAt(block, nowMs) {
  if (nowMs < block.windowStartMs) return false;
  if (nowMs < block.baseEndMs) return true;
  return !block.allFinal && nowMs < block.overrunEndMs;
}

// Evaluates the window state at `now`. `games` come from loadWindowGames(). Pure and deterministic.
function evaluateGameWindow({ gameWindow, games, now, finalityKnown = true }) {
  const params = resolveParams(gameWindow);
  const nowMs = now.getTime();
  const blocks = buildBlocks(games, params);
  const iso = (ms) => (ms === null || ms === undefined ? null : new Date(ms).toISOString());

  const open = blocks.find((block) => blockOpenAt(block, nowMs));
  if (open) {
    const openGames = open.games.filter((game) => !game.final).length;
    const overrun = nowMs >= open.baseEndMs;
    return {
      state: 'in-window',
      cronSet: 'active',
      windowStartsAt: iso(open.windowStartMs),
      windowEndsAt: iso(overrun ? open.overrunEndMs : open.baseEndMs),
      gamesInBlock: open.games.length,
      gamesNotFinal: openGames,
      overrun,
      finalityKnown,
      reason: overrun
        ? `${openGames} game(s) of the block are not final after the assumed end; window stays open until ${iso(open.overrunEndMs)} at the latest.`
        : `NFL game block with ${open.games.length} game(s), first kickoff ${iso(open.firstKickoffMs)}.`,
    };
  }

  const next = blocks.find((block) => block.windowStartMs > nowMs);
  const previous = [...blocks].reverse().find((block) => block.windowStartMs <= nowMs);
  return {
    state: 'idle',
    cronSet: 'idle',
    nextWindowAt: next ? iso(next.windowStartMs) : null,
    nextKickoffAt: next ? iso(next.firstKickoffMs) : null,
    lastWindowEndedAt: previous ? iso(previous.allFinal ? previous.baseEndMs : previous.overrunEndMs) : null,
    finalityKnown,
    reason: next
      ? `No game window now; next window opens at ${iso(next.windowStartMs)}.`
      : 'No game window now and no later game in the loaded schedules (offseason).',
  };
}

// Entry point used by the scheduler runtime. Never throws: any schedule problem resolves to the dense cron.
function resolveGameWindow({ target, now, repoRoot, loader = loadWindowGames }) {
  const gameWindow = target.gameWindow;
  try {
    const { games, finalityKnown } = loader({ repoRoot, scheduleDir: gameWindow.scheduleDir, now });
    const status = evaluateGameWindow({ gameWindow, games, now, finalityKnown });
    return {
      ...status,
      cron: status.cronSet === 'idle' ? gameWindow.idleCron : target.cron,
    };
  } catch (error) {
    return {
      state: 'schedule-unavailable',
      cronSet: 'active',
      cron: target.cron,
      reason: `Canonical NFL schedule not usable (${error instanceof Error ? error.message : String(error)}); keeping the dense cron.`,
    };
  }
}

function validateGameWindowConfig(target, cronMatchesFn) {
  if (target.mode === undefined) {
    if (target.gameWindow !== undefined) throw new Error(`gameWindow requires mode "game-window" for ${target.id}`);
    return;
  }
  if (target.mode !== 'game-window') throw new Error(`Unsupported scheduler mode for ${target.id}: ${target.mode}`);
  const gameWindow = target.gameWindow;
  if (!gameWindow || typeof gameWindow !== 'object' || Array.isArray(gameWindow)) {
    throw new Error(`game-window mode requires a gameWindow object for ${target.id}`);
  }
  for (const key of ['preKickoffMinutes', 'postFinalMinutes']) {
    if (!Number.isInteger(gameWindow[key]) || gameWindow[key] < 0) throw new Error(`Invalid gameWindow.${key} for ${target.id}`);
  }
  for (const key of ['assumedGameDurationMinutes', 'maxOverrunMinutes']) {
    if (gameWindow[key] !== undefined && (!Number.isInteger(gameWindow[key]) || gameWindow[key] <= 0)) {
      throw new Error(`Invalid gameWindow.${key} for ${target.id}`);
    }
  }
  if (gameWindow.scheduleDir !== undefined && (typeof gameWindow.scheduleDir !== 'string' || !gameWindow.scheduleDir)) {
    throw new Error(`Invalid gameWindow.scheduleDir for ${target.id}`);
  }
  if (!Array.isArray(gameWindow.idleCron) || gameWindow.idleCron.length === 0) {
    throw new Error(`game-window mode requires gameWindow.idleCron for ${target.id}`);
  }
  for (const expression of gameWindow.idleCron) cronMatchesFn(expression, new Date('2026-01-05T00:00:00Z'), target.timezone);
}

module.exports = {
  DEFAULTS,
  buildBlocks,
  evaluateGameWindow,
  loadWindowGames,
  localToUtcMs,
  parseKickoff,
  resolveGameWindow,
  validateGameWindowConfig,
};
