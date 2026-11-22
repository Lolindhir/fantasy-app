import type { PlayoffOddsStatus, ScheduleOutlookReadModel } from '../../core/models/schedule-outlook.models';
import {
  formatPlayoffCell,
  formatPlayoffPercent,
  ordinal,
  playoffLockedPlace,
  playoffMarker,
  playoffPillText,
  resolvePlayoffOdds,
  formatExpectedWins,
  formatMargin,
  formatPoints,
  formatShare,
  formatStrength,
  resolveTeamScheduleOutlook
} from './schedule-outlook-view.util';

function outlook(overrides: Partial<ScheduleOutlookReadModel['PlayoffOdds']> = {}, season = 2026): ScheduleOutlookReadModel {
  const team = (TeamID: number, Status: PlayoffOddsStatus, p: number, places: number[]) => ({
    TeamID, Record: { Wins: 1, Losses: 1, Ties: 0 }, PlaceProbabilities: places,
    PlayoffProbability: p, EliminationProbability: 1 - p, Status
  });
  return {
    Season: season,
    RegularSeason: {
      Teams: [{
        TeamID: 1, RemainingGames: 2, RemainingSoSClass: 'harder',
        Upcoming: [
          { Week: 5, OpponentTeamID: 2, OpponentClass: 'weaker' },
          { Week: 6, OpponentTeamID: 3, OpponentClass: null }
        ]
      }]
    },
    PlayoffOdds: {
      Model: 'm', Available: true, Reason: null,
      Provenance: { PlayoffTeams: 1, RegularSeasonComplete: false },
      Teams: [
        team(1, 'clinched', 1, [1, 0, 0]),
        team(2, 'alive', 0.004, [0, 0.004, 0.996]),
        team(3, 'eliminated', 0, [0, 0, 1])
      ],
      ...overrides
    }
  };
}

describe('schedule outlook view', () => {
  it('formats alive percentages as whole numbers with <1% and >99% bounds', () => {
    expect(formatPlayoffPercent(0.004)).toBe('<1%');
    expect(formatPlayoffPercent(0.4632)).toBe('46%');
    expect(formatPlayoffPercent(0.996)).toBe('>99%');
    expect(formatPlayoffPercent(0.9999)).toBe('>99%');
    expect(formatPlayoffPercent(1)).toBe('100%');
    expect(formatPlayoffPercent(0)).toBe('0%');
    expect(formatPlayoffCell(0.9972)).toBe('>99');
    expect(formatPlayoffCell(1)).toBe('100');
    expect(formatPlayoffCell(0)).toBe('');
  });

  it('maps status to pill text and Overview markers', () => {
    const odds = resolvePlayoffOdds(outlook(), 2026)!;
    expect(playoffPillText(odds.teams.get(1)!)).toBe('Clinched 1st');
    expect(playoffPillText(odds.teams.get(2)!)).toBe('<1%');
    expect(playoffPillText(odds.teams.get(3)!)).toBe('Eliminated');
    expect(playoffPillText({ teamId: 9, status: 'alive', probability: 0, places: [] })).toBe('<1%');
    expect(playoffPillText({ teamId: 9, status: 'alive', probability: 1, places: [] })).toBe('>99%');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [1, 0, 0, 0] })).toBe('Clinched 1st');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [0, 0, 1, 0] })).toBe('Clinched 3rd');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [0, 0.5, 0.5, 0] })).toBe('Clinched');
    expect(ordinal(1)).toBe('1st');
    expect([2, 3, 4, 11, 12, 22].map(ordinal)).toEqual(['2nd', '3rd', '4th', '11th', '12th', '22nd']);
    expect(playoffLockedPlace(odds, 1)).toBe(1);
    expect(playoffLockedPlace(odds, 2)).toBeNull();
    expect(playoffMarker(odds, 1)).toBe('x');
    expect(playoffMarker(odds, '3')).toBe('e');
    expect(playoffMarker(odds, 2)).toBeNull();
    expect(odds.hasDecidedTeam).toBeTrue();
    expect(odds.playoffTeams).toBe(1);
  });

  it('shows nothing when unavailable, from another season or after the regular season', () => {
    expect(resolvePlayoffOdds(null, 2026)).toBeNull();
    expect(resolvePlayoffOdds(outlook({ Available: false }), 2026)).toBeNull();
    expect(resolvePlayoffOdds(outlook(), 2027)).toBeNull();
    expect(resolvePlayoffOdds(outlook({ Provenance: { PlayoffTeams: 1, RegularSeasonComplete: true } }), 2026)).toBeNull();
    expect(resolvePlayoffOdds({ ...outlook(), PlayoffOdds: undefined }, 2026)).toBeNull();
  });

  it('exposes strength classes per upcoming week and skips unknown ones', () => {
    const view = resolveTeamScheduleOutlook(outlook(), 2026, 1)!;
    expect(view.remaining).toBe('harder');
    expect(view.opponentByWeek.get(5)).toBe('weaker');
    expect(view.opponentByWeek.has(6)).toBeFalse();
    expect(resolveTeamScheduleOutlook(outlook(), 2025, 1)).toBeNull();
    expect(resolveTeamScheduleOutlook(outlook(), 2026, 9)).toBeNull();
  });

  it('exposes generated opponent points, win chance and strength mix without calculating anything', () => {
    const base = outlook();
    const model: ScheduleOutlookReadModel = {
      ...base,
      RegularSeason: {
        Teams: [
          {
            ...base.RegularSeason!.Teams[0],
            RemainingSoS: 1.1,
            Upcoming: [{ Week: 5, OpponentTeamID: 2, OpponentClass: 'weaker', OpponentStrength: 0.9 }]
          },
          {
            TeamID: 2, RemainingGames: 1, RemainingSoSClass: null, Upcoming: [],
            Strength: { Value: 0.9, CurrentRelative: 0.88, PreviousRelative: 0.95, CurrentWeight: 0.25, GamesPlayed: 1 }
          }
        ]
      },
      PlayoffOdds: {
        ...base.PlayoffOdds!,
        Scoring: { LeagueMeanPoints: 190.4, PointsStdDev: 30, MeanSource: 'current-season' },
        Teams: base.PlayoffOdds!.Teams.map(team => team.TeamID === 1
          ? { ...team, Upcoming: [{ Week: 5, OpponentTeamID: 2, WinProbability: 0.62, OpponentExpectedPoints: 171.4, ExpectedMargin: 12.4 }], RemainingExpectedWins: 0.62, RemainingWinProbability: 0.62 }
          : team)
      }
    };
    const view = resolveTeamScheduleOutlook(model, 2026, 1)!;
    const game = view.gameByWeek.get(5)!;
    expect(game.winProbability).toBe(0.62);
    expect(game.margin).toBe(12.4);
    expect(view.remainingWinProbability).toBe(0.62);
    expect(view.remainingExpectedWins).toBe(0.62);
    expect(game.opponentStrength).toBe(0.9);
    expect(game.opponentMix).toEqual({ currentWeight: 0.25, currentRelative: 0.88, previousRelative: 0.95, gamesPlayed: 1 });
    expect(view.remainingStrength).toBe(1.1);
    expect(view.leagueMeanPoints).toBe(190.4);
  });

  it('formats published numbers for display only', () => {
    expect(formatPoints(171.4)).toBe('171');
    expect(formatMargin(12.4)).toBe('+12');
    expect(formatMargin(-7.6)).toBe('−8');
    expect(formatMargin(0.2)).toBe('0');
    expect(formatExpectedWins(1.2345)).toBe('1.2');
    expect(formatStrength(0.9)).toBe('0.90×');
    expect(formatShare(0.77)).toBe('77%');
  });
});
