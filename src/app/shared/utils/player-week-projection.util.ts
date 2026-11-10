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
  /** "game-log" = the published Actual is not available yet; points come from the player's Game Log entry. */
  state: Extract<PlayerWeekFantasyActualState, 'live' | 'final'> | 'game-log';
  /** Real score of the week (not an estimate), e.g. "12.4". */
  pointsText: string;
}

export interface PlayerWeekProjectionView {
  season: number;
  week: number;
  /** Null unless the published projection status is "available" and carries points. */
  projection: PlayerProjectionView | null;
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
      projectedText: view ? view.projected : MISSING_PROJECTION_TEXT,
      rangeText: view?.rangeText ?? null,
      levelLabel: view?.rangeText && level !== null ? `${Math.round(level * 100)}%` : null,
      result: hasResult
        ? { state: actual.State as 'live' | 'final', pointsText: formatScore(Number(actual.Points)) }
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
  gameLog: ReadonlyArray<{ GameDetails: { Week: number }; FantasyPoints: number }> | null | undefined
): PlayerWeekResultView | null {
  if (!view) return null;
  if (view.result) return view.result;
  const entry = gameLog?.find(game => Number(game.GameDetails?.Week) === view.week);
  const points = entry?.FantasyPoints;
  if (points === null || points === undefined || !Number.isFinite(Number(points))) return null;
  return { state: 'game-log', pointsText: formatScore(Number(points)) };
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
