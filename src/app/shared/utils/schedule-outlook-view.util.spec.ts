import type { PlayoffOddsStatus, ScheduleOutlookReadModel } from '../../core/models/schedule-outlook.models';
import {
  formatPlayoffCell,
  formatPlacePercent,
  isZeroPlaceLabel,
  formatExactPlaceShares,
  playoffPillLabel,
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
    expect(formatPlayoffCell(0.9972)).toBe('99.7');
    expect(formatPlayoffCell(1)).toBe('100.0');
    expect(formatPlayoffCell(0)).toBe('');
    expect(formatPlacePercent(0.00001)).toBe('<0.1%');
    expect(formatPlacePercent(0.99999)).toBe('>99.9%');
    expect(isZeroPlaceLabel('0.0%')).toBeTrue();
    expect(isZeroPlaceLabel('<0.01%')).toBeFalse();
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

  it('rounds exact rows jointly and preserves positive support even below float precision', () => {
    expect(formatExactPlaceShares(['0', '8954', '888', '158', '0', '0'], '10000'))
      .toEqual(['0.0%', '89.5%', '8.9%', '1.6%', '0.0%', '0.0%']);
    expect(formatExactPlaceShares(['0', '6666863', '2102764', '1156076', '74297', '0'], '10000000'))
      .toEqual(['0.0%', '66.7%', '21.0%', '11.6%', '0.7%', '0.0%']);
    expect(formatExactPlaceShares(['999', '1'], '1000')).toEqual(['99.9%', '0.1%']);
    expect(formatExactPlaceShares(['9999', '1'], '10000')).toEqual(['99.99%', '0.01%']);
    expect(formatExactPlaceShares(['999999999999999999999999999999', '1'], '1000000000000000000000000000000'))
      .toEqual(['>99.99%', '<0.01%']);
    expect(formatExactPlaceShares(['1', '1', '1'], '3')).toEqual(['33.4%', '33.3%', '33.3%']);
    expect(formatExactPlaceShares(['1', '0'], '1')).toEqual(['100.0%', '0.0%']);
    expect(formatExactPlaceShares(['2', '0'], '1')).toBeNull();
    expect(formatExactPlaceShares(['1e5', '0'], '100000')).toBeNull();
  });

  it('uses the exact support rather than rounded float certainty and labels the right model', () => {
    const base = outlook();
    const model = outlook({
      Model: 'playoff-odds-v4',
      Provenance: { PlayoffTeams: 1, RegularSeasonComplete: false, PlaceMassDenominator: '100000000000000000000' },
      Teams: [
        { ...base.PlayoffOdds!.Teams[0], Status: 'alive', PlayoffProbability: 1, PlaceProbabilities: [1, 1e-20, 0],
          PlaceMassNumerators: ['99999999999999999999', '1', '0'], PossiblePlaces: [1, 2] },
        { ...base.PlayoffOdds!.Teams[1], Status: 'alive', PlayoffProbability: 1e-20, PlaceProbabilities: [1e-20, 1, 0],
          PlaceMassNumerators: ['1', '99999999999999999999', '0'], PossiblePlaces: [1, 2] },
        { ...base.PlayoffOdds!.Teams[2], PlaceMassNumerators: ['0', '0', '100000000000000000000'], PossiblePlaces: [3] }
      ]
    });
    const odds = resolvePlayoffOdds(model, 2026)!;
    expect(odds.teams.get(1)!.placeLabels).toEqual(['>99.99%', '<0.01%', '0.0%']);
    expect(playoffPillText(odds.teams.get(1)!)).toBe('>99%');
    expect(playoffPillLabel(odds.teams.get(1)!)).toContain('1% tie probability');
    expect(playoffLockedPlace(odds, 1)).toBeNull();
    expect(playoffLockedPlace(odds, 3)).toBe(3);
    model.PlayoffOdds!.Teams[0].PossiblePlaces = [1];
    expect(resolvePlayoffOdds(model, 2026)).toBeNull();
  });

  it('keeps independent schedule forecasts when exact playoff odds are unavailable', () => {
    const model = outlook({ Model: 'playoff-odds-v4', Available: false });
    model.RegularSeason!.MatchupForecast = {
      Model: 'schedule-matchup-forecast-v1',
      Provenance: { RegularSeasonComplete: false },
      Scoring: { LeagueMeanPoints: 190, PointsStdDev: 30, MeanSource: 'current-season' },
      Teams: [{ TeamID: 1, RemainingExpectedWins: 0.62, RemainingWinProbability: 0.62,
        Upcoming: [{ Week: 5, OpponentTeamID: 2, WinProbability: 0.62, OpponentExpectedPoints: 171, ExpectedMargin: 12 }] }]
    };
    expect(resolvePlayoffOdds(model, 2026)).toBeNull();
    const view = resolveTeamScheduleOutlook(model, 2026, 1)!;
    expect(view.remainingExpectedWins).toBe(0.62);
    expect(view.gameByWeek.get(5)!.margin).toBe(12);
    expect(view.leagueMeanPoints).toBe(190);
    model.RegularSeason!.MatchupForecast.Provenance.RegularSeasonComplete = true;
    expect(resolveTeamScheduleOutlook(model, 2026, 1)!.remainingExpectedWins).toBeNull();
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
