import type {
  PlayerWeekFantasyActualState,
  PlayerWeekFantasyReadModel
} from '../../core/models/player-week-fantasy.models';
import {
  playerProjectionView,
  rangeAtLevel,
  type PlayerProjectionView
} from './projection-range.util';

/** Placeholder for a missing projection. A missing projection is never shown as 0. */
export const MISSING_PROJECTION_TEXT = '–';

export interface PlayerWeekResultView {
  /**
   * "game-log" / "matchup" = the published Actual is not available yet; points come from the player's
   * Game Log entry or, before that exists, from the fantasy matchup context of the same week.
   */
  state: Extract<PlayerWeekFantasyActualState, 'live' | 'final'> | 'game-log' | 'matchup';
  /** Real score of the week (not an estimate), e.g. "12.4". */
  pointsText: string;
  /** Real points compared with the published projection; null without a projection. */
  tone: 'above' | 'below' | 'even' | null;
}

export interface PlayerWeekProjectionView {
  season: number;
  week: number;
  /** Null unless the published projection status is "available" and carries points. */
  projection: PlayerProjectionView | null;
  /** Published projected points, null without an available projection. */
  projectedValue: number | null;
  /** "10.6" or "–". */
  projectedText: string;
  /** "6.6 – 39.1" for the published display level, null without a range. */
  rangeText: string | null;
  /** "90%" etc., derived from the published display level. */
  levelLabel: string | null;
  /** Only present once the player's game is live or final. */
  result: PlayerWeekResultView | null;
}

/**
 * Pure join of the published PlayerWeekFantasy snapshot to Sleeper player IDs. All values,
 * the display level and the axis are published data; nothing is calculated here.
 * A Sleeper ID that appears more than once is ambiguous and therefore left out.
 */
export function buildPlayerWeekProjections(
  model: PlayerWeekFantasyReadModel | null | undefined
): ReadonlyMap<string, PlayerWeekProjectionView> {
  const result = new Map<string, PlayerWeekProjectionView>();
  if (!model) return result;

  const seen = new Set<string>();
  const ambiguous = new Set<string>();
  const level = model.Display?.RangeLevel ?? null;
  const axis = model.Display?.RangeAxis ?? null;

  for (const record of model.Records ?? []) {
    if (record.PlayerID === null || record.PlayerID === undefined) continue;
    const playerID = String(record.PlayerID).trim();
    if (!playerID) continue;
    if (seen.has(playerID)) {
      ambiguous.add(playerID);
      continue;
    }
    seen.add(playerID);

    const projection = record.Projection;
    const points = projection?.Points;
    const available = projection?.Status === 'available'
      && points !== null
      && points !== undefined
      && Number.isFinite(Number(points));
    const range = available ? rangeAtLevel(projection.PredictionRanges, level) : null;
    const view = available
      ? playerProjectionView({ projected: Number(points), range, axis: range ? axis : null })
      : null;

    const actual = record.Actual;
    const hasResult = (actual?.State === 'live' || actual?.State === 'final')
      && actual.Points !== null
      && actual.Points !== undefined
      && Number.isFinite(Number(actual.Points));

    result.set(playerID, {
      season: model.Season,
      week: model.Week,
      projection: view,
      projectedValue: available ? Number(points) : null,
      projectedText: view ? view.projected : MISSING_PROJECTION_TEXT,
      rangeText: view?.rangeText ?? null,
      levelLabel: view?.rangeText && level !== null ? `${Math.round(level * 100)}%` : null,
      result: hasResult
        ? {
          state: actual.State as 'live' | 'final',
          pointsText: formatScore(Number(actual.Points)),
          tone: resultTone(Number(actual.Points), available ? Number(points) : null)
        }
        : null
    });
  }

  for (const playerID of ambiguous) result.delete(playerID);
  return result;
}

/**
 * Real points of the projected week. The published Actual stays unavailable until the NFL stats of
 * the week are complete (ADR-071), so the already published Game Log entry of the same week is the
 * fallback. Pure lookup of a published value; nothing is calculated.
 */
export function resolveWeekResult(
  view: PlayerWeekProjectionView | null | undefined,
  gameLog: ReadonlyArray<{ GameDetails: { Week: number }; FantasyPoints: number }> | null | undefined,
  matchupPoints: number | null = null
): PlayerWeekResultView | null {
  if (!view) return null;
  if (view.result) return view.result;
  const entry = gameLog?.find(game => Number(game.GameDetails?.Week) === view.week);
  const logPoints = entry?.FantasyPoints;
  if (logPoints !== null && logPoints !== undefined && Number.isFinite(Number(logPoints))) {
    return {
      state: 'game-log',
      pointsText: formatScore(Number(logPoints)),
      tone: resultTone(Number(logPoints), view.projectedValue)
    };
  }
  if (matchupPoints !== null && Number.isFinite(matchupPoints)) {
    return {
      state: 'matchup',
      pointsText: formatScore(matchupPoints),
      tone: resultTone(matchupPoints, view.projectedValue)
    };
  }
  return null;
}

/**
 * Points of one player in the fantasy matchup context of the given week. Only games that have started
 * count: a scheduled game carries 0 points as a placeholder, never as a result.
 */
export function matchupPointsForPlayer(
  context: {
    Season: string | number;
    Week: number;
    Games: ReadonlyArray<{
      Status: string | null;
      FantasyTeams: ReadonlyArray<{ Players: ReadonlyArray<{ PlayerID: string; Points: number | null }> }>;
    }>;
  } | null | undefined,
  season: number,
  week: number,
  playerID: string | number
): number | null {
  if (!context || Number(context.Season) !== Number(season) || Number(context.Week) !== week) return null;
  const id = String(playerID);
  for (const game of context.Games ?? []) {
    if (!game.Status || game.Status.toLowerCase() === 'scheduled') continue;
    for (const team of game.FantasyTeams ?? []) {
      const entry = team.Players?.find(player => String(player.PlayerID) === id);
      if (entry && entry.Points !== null && entry.Points !== undefined && Number.isFinite(Number(entry.Points))) {
        return Number(entry.Points);
      }
    }
  }
  return null;
}

/** Plain comparison of two published numbers; no model rule involved. */
function resultTone(actual: number, projected: number | null): PlayerWeekResultView['tone'] {
  if (projected === null) return null;
  if (actual > projected) return 'above';
  if (actual < projected) return 'below';
  return 'even';
}

/** Cell text for lists: the projected points or "–". */
export function weekProjectionText(
  projections: ReadonlyMap<string, PlayerWeekProjectionView> | null | undefined,
  playerID: string
): string {
  return projections?.get(String(playerID))?.projectedText ?? MISSING_PROJECTION_TEXT;
}

const scoreFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
function formatScore(value: number): string {
  return scoreFormatter.format(value);
}
