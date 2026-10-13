import {
  recentStandingResults,
  recentStandingResultsLabel,
  standingCanonicalDelta,
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
    expect(standingMovementText(sampleRow('WWL', { delta: 0 }))).toBe('—');
    expect(standingMovementLabel(sampleRow('WWL', { delta: -2 }))).toContain('down 2 places');
    const missing = sampleRow('WWL', { delta: null });
    expect(standingCanonicalDelta(missing)).toBeNull();
    const wrongPlace = sampleRow('WWL');
    wrongPlace.team.Placements.Current.Regular.Place = 3;
    expect(standingCanonicalDelta(wrongPlace)).toBeNull();
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
