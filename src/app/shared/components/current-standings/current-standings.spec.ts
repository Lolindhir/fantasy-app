import { CurrentStandingsComponent } from './current-standings';
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
          PlaceDelta: options.delta ?? 2,
          Wins: wins,
          Losses: losses,
          Ties: ties,
          Record: record
        } }
      }
    } as CurrentStandingRow['team']
  };
}

describe('CurrentStandingsComponent detailed variant', () => {
  let component: CurrentStandingsComponent;
  beforeEach(() => { component = new CurrentStandingsComponent(); });

  it('preserves compact rendering as the default', () => {
    expect(component.variant).toBe('compact');
  });

  it('shows only available completed results early in the season', () => {
    expect(component.recentResults(sampleRow('WLW'))).toEqual([
      { week: 1, result: 'W' },
      { week: 2, result: 'L' },
      { week: 3, result: 'W' }
    ]);
  });

  it('keeps only the latest five chronological results, including ties', () => {
    const results = component.recentResults(sampleRow('WWLTWLW'));
    expect(results).toEqual([
      { week: 3, result: 'L' },
      { week: 4, result: 'T' },
      { week: 5, result: 'W' },
      { week: 6, result: 'L' },
      { week: 7, result: 'W' }
    ]);
    expect(component.recentResultsLabel(results)).toContain('week 4 tie');
  });

  it('fails closed for incomplete or inconsistent record histories', () => {
    expect(component.recentResults(sampleRow('WL?', { wins: 1, losses: 1 }))).toEqual([]);
    expect(component.recentResults(sampleRow('WL', { wins: 3 }))).toEqual([]);
  });

  it('uses canonical position movement and neutralizes missing values', () => {
    expect(component.movementText(sampleRow('WWL', { delta: 2 }))).toBe('▲2');
    expect(component.movementText(sampleRow('WWL', { delta: -1 }))).toBe('▼1');
    expect(component.movementText(sampleRow('WWL', { delta: 0 }))).toBe('—');
    const row = sampleRow('WWL');
    row.team.Placements.Current.Regular.Place = 3;
    expect(component.placeDelta(row)).toBeNull();
  });

  it('draws a cutoff only when playoff places are valid', () => {
    component.standings = [1, 2, 3, 4, 5, 6].map(place => sampleRow('WL', { place }));
    component.playoffTeams = 4;
    expect(component.isPlayoffCutline(component.standings[4])).toBeTrue();
    expect(component.isPlayoffCutline(component.standings[3])).toBeFalse();
    component.playoffTeams = 6;
    expect(component.isPlayoffCutline(component.standings[4])).toBeFalse();
  });

  it('allows only one expanded team at a time', () => {
    component.toggleDetails(1);
    expect(component.expandedTeamId).toBe(1);
    component.toggleDetails(2);
    expect(component.expandedTeamId).toBe(2);
    component.toggleDetails(2);
    expect(component.expandedTeamId).toBeNull();
  });

  it('computes additional stats and handles pre-season zero games', () => {
    const row = sampleRow('WWL');
    expect(component.pointDifferential(row)).toBe(60);
    expect(component.pointsPerGame(row)).toBeCloseTo(850 / 3, 6);
    expect(component.pointsAgainstPerGame(row)).toBeCloseTo(790 / 3, 6);
    const empty = sampleRow('');
    expect(component.pointsPerGame(empty)).toBeNull();
    expect(component.recentResults(empty)).toEqual([]);
  });
});
