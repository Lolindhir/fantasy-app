import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../core/models/season-statistics.models';
import { buildSeasonUpsetCard, formatExpectedRecord, formatPercent, formatSigned, statisticsByTeam } from './season-statistics-view.util';

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

  it('formats percentages and keeps unknown visible', () => {
    expect(formatPercent(82.2565)).toBe('82.3%');
    expect(formatPercent(null)).toBe('–');
  });

  it('builds the season upset card from the generator-chosen game and hides it without one', () => {
    const upset = { Week: 4, WinnerTeamID: 1, LoserTeamID: 2, WinnerPoints: 100.5, LoserPoints: 90, WinnerPregameWinProbability: 0.0954 };
    expect(buildSeasonUpsetCard(doc(2025, { BiggestUpset: upset }))).toEqual({
      week: 4, winnerName: 'Team 1', loserName: 'Team 2', scoreDisplay: '100.50–90.00', chanceDisplay: '10%'
    });
    expect(buildSeasonUpsetCard(doc(2025))).toBeNull();
    expect(buildSeasonUpsetCard(doc(2025, { BiggestUpset: { ...upset, LoserTeamID: 99 } }))).toBeNull();
  });
});
