import {
  recentStandingResults,
  recentStandingResultsLabel,
  standingCanonicalDelta,
  standingPlacementTrend,
  standingMovementLabel,
  standingMovementText,
  standingPerGame,
  standingPlayoffCutline,
  standingPointDifferential
} from './current-standings-display.util';
import type { CurrentStandingRow } from '../../utils/league-standings-view.util';

function sampleRow(record: string, options: {
  wins?: number;
  losses?: number;
  ties?: number;
  place?: number;
  delta?: number | null;
} = {}): CurrentStandingRow {
  const wins = options.wins ?? [...record].filter(c => c === 'W').length;
  const losses = options.losses ?? [...record].filter(c => c === 'L').length;
  const ties = options.ties ?? [...record].filter(c => c === 'T').length;
  return {
    displayPlace: options.place ?? 1,
    team: {
      TeamID: 11,
      Team: 'Example Team',
      Owner: 'Example',
      Wins: wins,
      Losses: losses,
      Ties: ties,
      Points: 850,
      PointsAgainst: 790,
      Streak: '2W',
      Placements: {
        Current: { Regular: {
          Place: options.place ?? 1,
          PlaceDelta: options.delta === undefined ? 2 : options.delta,
          Wins: wins,
          Losses: losses,
          Ties: ties,
          Record: record
        } }
      }
    } as CurrentStandingRow['team']
  };
}

describe('Current standings detailed presentation helpers', () => {
  it('shows only completed results early in the season', () => {
    expect(recentStandingResults(sampleRow('WLW'))).toEqual([
      { week: 1, result: 'W' },
      { week: 2, result: 'L' },
      { week: 3, result: 'W' }
    ]);
  });

  it('keeps only the latest five chronological results including ties', () => {
    const results = recentStandingResults(sampleRow('WWLTWLW'));
    expect(results).toEqual([
      { week: 3, result: 'L' },
      { week: 4, result: 'T' },
      { week: 5, result: 'W' },
      { week: 6, result: 'L' },
      { week: 7, result: 'W' }
    ]);
    expect(recentStandingResultsLabel(results)).toContain('week 4 tie');
  });

  it('fails closed on inconsistent or malformed records', () => {
    expect(recentStandingResults(sampleRow('WL?', { wins: 1, losses: 1 }))).toEqual([]);
    expect(recentStandingResults(sampleRow('WL', { wins: 3 }))).toEqual([]);
    expect(recentStandingResults(sampleRow(''))).toEqual([]);
  });

  it('uses canonical movement and leaves missing or wrong-place evidence neutral', () => {
    expect(standingMovementText(sampleRow('WWL', { delta: 2 }))).toBe('▲2');
    expect(standingMovementText(sampleRow('WWL', { delta: -1 }))).toBe('▼1');
    expect(standingMovementText(sampleRow('WWL', { delta: 0 }))).toBe('');
    expect(standingMovementLabel(sampleRow('WWL', { delta: -2 }))).toContain('down 2 places');
    const missing = sampleRow('WWL', { delta: null });
    expect(standingCanonicalDelta(missing)).toBeNull();
    expect(standingMovementText(missing)).toBe('');
    const wrongPlace = sampleRow('WWL');
    wrongPlace.team.Placements.Current.Regular.Place = 3;
    expect(standingCanonicalDelta(wrongPlace)).toBeNull();
  });


  it('uses only canonical completed-week placements and reconstructs week 1 from week 2', () => {
    const row = sampleRow('WLWWL', { place: 3, delta: 0 });
    row.team.Placements.Current.Regular.WeeklyMovements = [
      { Week: 2, PreviousWeekPlace: 5, Place: 4, PlaceDelta: 1 },
      { Week: 3, PreviousWeekPlace: 4, Place: 3, PlaceDelta: 1 },
      { Week: 4, PreviousWeekPlace: 3, Place: 3, PlaceDelta: 0 },
      { Week: 5, PreviousWeekPlace: 3, Place: 3, PlaceDelta: 0 }
    ];

    const trend = standingPlacementTrend(row, 6);
    expect(trend?.points.map(point => [point.week, point.place])).toEqual([
      [1, 5], [2, 4], [3, 3], [4, 3], [5, 3]
    ]);
    expect(trend?.description).toContain('week 1 place 5');
    expect(trend?.description).toContain('week 5 place 3');
    // No movement is still a horizontal line *inside* the chart.
    expect(trend?.points[2].y).toBe(trend?.points[3].y);
    expect(trend?.points[3].y).toBe(trend?.points[4].y);
    expect(trend?.points[0].y).toBeGreaterThan(trend!.points[2].y);
  });

  it('supports the first completed week and all 14 regular-season games', () => {
    const first = standingPlacementTrend(sampleRow('W', { place: 2, delta: null }), 6);
    expect(first?.points.map(point => [point.week, point.place])).toEqual([[1, 2]]);
    expect(first?.points[0].x).toBe(150);
    expect(standingPlacementTrend(sampleRow('', { place: 2 }), 6)).toBeNull();

    const allWeeks = sampleRow('W'.repeat(14), { place: 2, delta: 0 });
    allWeeks.team.Placements.Current.Regular.WeeklyMovements = Array.from(
      { length: 13 }, (_, i) => ({ Week: i + 2, PreviousWeekPlace: 2, Place: 2, PlaceDelta: 0 })
    );
    const trend = standingPlacementTrend(allWeeks, 6);
    expect(trend?.points.length).toBe(14);
    expect(trend?.points[0].x).toBe(24);
    expect(trend?.points[13].x).toBe(276);
    expect(new Set(trend?.points.map(point => point.y)).size).toBe(1);
  });

  it('fails closed on missing, nonconsecutive, contradictory or non-final movement history', () => {
    const row = sampleRow('WWL', { place: 2, delta: 0 });
    expect(standingPlacementTrend(row, 6)).toBeNull();

    const valid = [
      { Week: 2, PreviousWeekPlace: 4, Place: 3, PlaceDelta: 1 },
      { Week: 3, PreviousWeekPlace: 3, Place: 2, PlaceDelta: 1 }
    ];
    row.team.Placements.Current.Regular.WeeklyMovements = valid;
    expect(standingPlacementTrend(row, 6)?.points.length).toBe(3);

    row.team.Placements.Current.Regular.WeeklyMovements = valid.slice(0, 1);
    expect(standingPlacementTrend(row, 6)).toBeNull();

    row.team.Placements.Current.Regular.WeeklyMovements = [
      valid[0], { ...valid[1], Week: 4 }
    ];
    expect(standingPlacementTrend(row, 6)).toBeNull();

    row.team.Placements.Current.Regular.WeeklyMovements = [
      valid[0], { ...valid[1], PreviousWeekPlace: 4 }
    ];
    expect(standingPlacementTrend(row, 6)).toBeNull();

    row.team.Placements.Current.Regular.WeeklyMovements = [
      valid[0], { ...valid[1], PlaceDelta: 0 }
    ];
    expect(standingPlacementTrend(row, 6)).toBeNull();

    row.team.Placements.Current.Regular.WeeklyMovements = [
      valid[0], { ...valid[1], Place: 1, PlaceDelta: 2 }
    ];
    expect(standingPlacementTrend(row, 6)).toBeNull();

    row.team.Placements.Current.Regular.WeeklyMovements = valid;
    row.team.Placements.Current.Regular.Place = 3;
    expect(standingPlacementTrend(row, 6)).toBeNull();
    row.team.Placements.Current.Regular.Place = 2;
    row.team.Placements.Current.Regular.Record = 'WW';
    expect(standingPlacementTrend(row, 6)).toBeNull();
  });

  it('draws the cutoff only for a valid playoff count', () => {
    const fifth = sampleRow('WL', { place: 5 });
    expect(standingPlayoffCutline(fifth, 4, 6)).toBeTrue();
    expect(standingPlayoffCutline(fifth, 5, 6)).toBeFalse();
    expect(standingPlayoffCutline(fifth, 6, 6)).toBeFalse();
    expect(standingPlayoffCutline(fifth, null, 6)).toBeFalse();
  });

  it('formats point differences and per-game metrics without inventing pre-season values', () => {
    const row = sampleRow('WWL');
    expect(standingPointDifferential(row)).toBe(60);
    expect(standingPerGame(row, row.team.Points)).toBeCloseTo(850 / 3, 6);
    expect(standingPerGame(row, row.team.PointsAgainst)).toBeCloseTo(790 / 3, 6);
    expect(standingPerGame(sampleRow(''), 0)).toBeNull();
  });
});
