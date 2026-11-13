import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../core/models/season-statistics.models';
import { buildBiggestUpsetHighlight, formatExpectedRecord, formatSigned, statisticsByTeam } from './season-statistics-view.util';

function team(id: number, owner: string): SeasonStatisticsTeam {
  return {
    TeamID: id, Owner: owner, TeamName: `Team ${id}`, Games: 3, Wins: 1, Losses: 2, Ties: 0, ExpectedWins: 1.5, Luck: -0.5,
    AllPlay: { Wins: 3, Losses: 3, Ties: 0 }, OpponentTiming: 1, UnderdogWins: 1, UpsetLosses: 0
  };
}

const doc = (season: number, extra: Partial<SeasonStatisticsReadModel> = {}): SeasonStatisticsReadModel => ({
  Season: season, IsCompleted: true, Teams: [team(1, 'Ann'), team(2, 'Bob')], BiggestUpset: null, ...extra
});

describe('season statistics view util', () => {
  it('formats signed values with English separators and keeps unknown visible', () => {
    expect(formatSigned(2.84)).toBe('+2.8');
    expect(formatSigned(-0.6)).toBe('-0.6');
    expect(formatSigned(0)).toBe('0.0');
    expect(formatSigned(null)).toBe('–');
  });

  it('shows the expected record as expected wins and remaining games', () => {
    expect(formatExpectedRecord(team(1, 'Ann'))).toBe('1.5-1.5');
    expect(formatExpectedRecord({ ...team(1, 'Ann'), ExpectedWins: null } as unknown as SeasonStatisticsTeam)).toBe('–');
  });

  it('indexes teams by TeamID text', () => {
    expect(statisticsByTeam([team(1, 'Ann')]).get('1')?.Owner).toBe('Ann');
  });

  it('renders the generator-chosen biggest upset from the season of the game', () => {
    const upset = { Season: 2025, Week: 3, WinnerTeamID: 2, LoserTeamID: 1, WinnerPoints: 228.72, LoserPoints: 177.86, WinnerPregameWinProbability: 0.1125 };
    const current = doc(2026, { IsCompleted: false, BiggestUpsetAllTime: upset });
    const highlight = buildBiggestUpsetHighlight(current, new Map([['2025', doc(2025)]]));
    expect(highlight?.owner).toBe('Bob');
    expect(highlight?.valueDisplay).toBe('11% win chance');
  });

  it('returns nothing without an all-time upset or a resolvable winner', () => {
    expect(buildBiggestUpsetHighlight(doc(2026), new Map())).toBeNull();
    expect(buildBiggestUpsetHighlight(doc(2026, { BiggestUpsetAllTime: { Season: 2020, Week: 1, WinnerTeamID: 9, LoserTeamID: 1, WinnerPoints: 1, LoserPoints: 0, WinnerPregameWinProbability: 0.1 } }), new Map())).toBeNull();
  });
});
