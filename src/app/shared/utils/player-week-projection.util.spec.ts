import type {
  PlayerWeekFantasyReadModel,
  PlayerWeekFantasyRecord
} from '../../core/models/player-week-fantasy.models';
import {
  MISSING_PROJECTION_TEXT,
  buildPlayerWeekProjections,
  resolveWeekResult,
  weekProjectionText,
  type PlayerWeekProjectionView
} from './player-week-projection.util';

function record(playerID: string | null, overrides: Partial<PlayerWeekFantasyRecord> = {}): PlayerWeekFantasyRecord {
  return {
    PlayerID: playerID,
    CanonicalPlayerID: 'NFLP-' + playerID,
    Projection: {
      Status: 'available',
      Points: 10.64,
      PredictionRange: null,
      PredictionRanges: [
        { Level: 0.5, Lower: 7, Upper: 14 },
        { Level: 0.9, Lower: 2.04, Upper: 21.55 }
      ],
      HistoryGames: 10,
      IntervalModel: 'm',
      ParticipationCondition: 'c',
      PointModel: 'p',
      RangeQuality: 'q',
      AvailabilityAdjustmentApplied: false
    },
    Actual: { Points: null, State: 'pending' },
    ...overrides
  } as PlayerWeekFantasyRecord;
}

function model(records: PlayerWeekFantasyRecord[], display: PlayerWeekFantasyReadModel['Display'] = {
  RangeLevel: 0.9,
  RangeAxis: { Min: -15, Max: 45 }
}): PlayerWeekFantasyReadModel {
  return { Season: 2026, Week: 9, Display: display, Records: records } as PlayerWeekFantasyReadModel;
}

describe('player week projection view', () => {
  it('shows the published projection with the display level range only (90 percent, not 50)', () => {
    const view = buildPlayerWeekProjections(model([record('1')])).get('1')!;

    expect(view.projectedText).toBe('10.6');
    expect(view.rangeText).toBe('2.0 – 21.6');
    expect(view.levelLabel).toBe('90%');
    expect(view.week).toBe(9);
    expect(view.projection?.bar).not.toBeNull();
    expect(view.result).toBeNull();
  });

  it('shows a dash, never 0, when the projection is not available', () => {
    for (const status of ['insufficient-history', 'no-game', 'unavailable'] as const) {
      const rec = record('1');
      rec.Projection = { ...rec.Projection, Status: status, Points: 0 };
      const view = buildPlayerWeekProjections(model([rec])).get('1')!;
      expect(view.projectedText).toBe(MISSING_PROJECTION_TEXT);
      expect(view.projection).toBeNull();
      expect(view.rangeText).toBeNull();
    }

    const nullPoints = record('2');
    nullPoints.Projection = { ...nullPoints.Projection, Points: null };
    expect(buildPlayerWeekProjections(model([nullPoints])).get('2')!.projectedText).toBe('–');
  });

  it('keeps the number without a range when the display level has no published range', () => {
    const view = buildPlayerWeekProjections(model([record('1')], { RangeLevel: 0.8, RangeAxis: null })).get('1')!;
    expect(view.projectedText).toBe('10.6');
    expect(view.rangeText).toBeNull();
    expect(view.levelLabel).toBeNull();
  });

  it('adds the result only once the game is live or final', () => {
    const final = record('1', { Actual: { Points: 12.4, State: 'final' } });
    const live = record('2', { Actual: { Points: 3, State: 'live' } });
    const pending = record('3', { Actual: { Points: 0, State: 'pending' } });
    const projections = buildPlayerWeekProjections(model([final, live, pending]));

    expect(projections.get('1')!.result).toEqual({ state: 'final', pointsText: '12.4' });
    expect(projections.get('2')!.result).toEqual({ state: 'live', pointsText: '3' });
    expect(projections.get('3')!.result).toBeNull();
  });

  it('skips records without a Sleeper ID and drops ambiguous IDs instead of guessing', () => {
    const projections = buildPlayerWeekProjections(model([record(null), record('1'), record('1'), record('2')]));
    expect([...projections.keys()]).toEqual(['2']);
  });

  it('handles a missing snapshot and unknown players with dashes', () => {
    expect(buildPlayerWeekProjections(null).size).toBe(0);
    expect(weekProjectionText(null, '1')).toBe('–');
    expect(weekProjectionText(buildPlayerWeekProjections(model([record('1')])), '999')).toBe('–');
    expect(weekProjectionText(buildPlayerWeekProjections(model([record('1')])), '1')).toBe('10.6');
  });
});

describe('resolveWeekResult', () => {
  const view = (week: number, result: PlayerWeekProjectionView['result'] = null) =>
    ({ season: 2026, week, projection: null, projectedText: '–', rangeText: null, levelLabel: null, result }) as PlayerWeekProjectionView;
  const log = [{ GameDetails: { Week: 9 }, FantasyPoints: 9.1 }, { GameDetails: { Week: 8 }, FantasyPoints: 12.9 }];

  it('prefers the published Actual', () => {
    const published = { state: 'final', pointsText: '9.5' } as const;
    expect(resolveWeekResult(view(9, published), log)).toEqual(published);
  });

  it('falls back to the Game Log entry of the projected week', () => {
    expect(resolveWeekResult(view(9), log)).toEqual({ state: 'game-log', pointsText: '9.1' });
  });

  it('shows nothing without a Game Log entry for that week', () => {
    expect(resolveWeekResult(view(10), log)).toBeNull();
    expect(resolveWeekResult(view(9), undefined)).toBeNull();
    expect(resolveWeekResult(null, log)).toBeNull();
  });
});
