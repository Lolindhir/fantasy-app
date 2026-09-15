import type { FantasyTeam, League } from '../../core/models/league.models';
import type { FantasyMatchupReadModel, MatchupsReadModel } from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import {
  buildOverviewTopContext,
  getLastCompletedWeek,
  orderOverviewCurrentMatchups,
  resolveOverviewWeeklyPhase,
  selectOverviewRecap
} from './overview-weekly-dashboard.util';

function makeTeam(
  id: number,
  currentPlace: number,
  previousPlace: number,
  allTimePlace: number
): FantasyTeam {
  const regular = (place: number) => ({
    Place: place,
    PlaceOrdinal: `${place}.`,
    Wins: 0,
    Losses: 0,
    Ties: 0,
    Points: 0,
    PointsAgainst: 0,
    WinPercentage: 0,
    WinPercentageDisplay: '.000',
    Record: '0-0',
    Streak: ''
  });

  return {
    TeamID: id,
    Team: `Team ${id}`,
    TeamAbbr: `T${id}`,
    Owner: `Owner ${id}`,
    Avatar: '',
    Placements: {
      Current: { Regular: regular(currentPlace), Awards: [] },
      Previous: {
        Regular: regular(previousPlace),
        Playoffs: previousPlace < 999 ? { Place: previousPlace, PlaceOrdinal: `${previousPlace}.` } : undefined,
        Awards: []
      },
      AllTime: {
        Regular: { ...regular(allTimePlace), RegularSeasonWins: 0 },
        Playoffs: {
          Place: allTimePlace,
          PlaceOrdinal: `${allTimePlace}.`,
          Championships: 0,
          RunnerUps: 0,
          Thirds: 0,
          PlaceCumulative: allTimePlace,
          PlaceAverage: allTimePlace,
          Placements: [allTimePlace]
        }
      }
    }
  } as unknown as FantasyTeam;
}

function makeLeague(
  teams: FantasyTeam[],
  finalScoredWeek: number,
  currentPlaces = teams.map(team => team.Placements.Current.Regular.Place)
): League {
  return {
    Season: '2026',
    Status: finalScoredWeek > 0 ? 'In-Season' : 'Pre-Season',
    FinalScoredWeek: finalScoredWeek,
    Teams: teams,
    Standings: [{
      Season: '2026',
      Playoffs: null,
      RegularSeason: teams.map((team, index) => ({
        TeamID: team.TeamID,
        Place: currentPlaces[index],
        PlaceOrdinal: `${currentPlaces[index]}.`,
        Owner: team.Owner,
        TeamName: team.Team
      }))
    }]
  } as unknown as League;
}

function matchup(id: string, a: number, b: number, state: 'open' | 'final' | 'unknown' = 'open'): FantasyMatchupReadModel {
  return {
    FantasyMatchupID: id,
    CompletionState: state,
    Participants: [
      { TeamID: a, Points: state === 'final' ? 120 + a : 0, ScoreKind: 'standard' },
      { TeamID: b, Points: state === 'final' ? 120 + b : 0, ScoreKind: 'standard' }
    ],
    Result: state === 'final'
      ? { Type: 'win', WinnerTeamID: a }
      : null
  };
}

function readModel(
  lastCompletedWeek: number | null,
  activeOrNextWeek: number | null,
  week1State: 'open' | 'final' | 'unknown' = 'final',
  week2Kickoff = '2026-09-18T00:00:00Z'
): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [
      {
        Week: 1,
        Stage: 'regular-season',
        FirstKickoffUtc: '2026-09-10T00:00:00Z',
        CompletionState: week1State,
        Matchups: [matchup('m-1', 1, 2, week1State), matchup('m-2', 3, 4, week1State)]
      },
      {
        Week: 2,
        Stage: 'regular-season',
        FirstKickoffUtc: week2Kickoff,
        CompletionState: 'open',
        Matchups: [matchup('m-3', 1, 4), matchup('m-4', 2, 3)]
      }
    ],
    Summary: { LastCompletedWeek: lastCompletedWeek, ActiveOrNextWeek: activeOrNextWeek }
  };
}

function recaps(): WeeklyRecapsReadModel {
  return {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [{
      Week: 1,
      KeyGames: [
        { GameID: 'g1', KickoffUtc: '2026-09-10T00:00:00Z', AwayNFLTeamID: 'A', HomeNFLTeamID: 'B', AwayScore: 21, HomeScore: 17, StarterPoints: 88, StarterCount: 5, FantasyTeamIDs: [1, 2], FantasyMatchupIDs: ['m-1'] },
        { GameID: 'g2', KickoffUtc: '2026-09-11T00:00:00Z', AwayNFLTeamID: 'C', HomeNFLTeamID: 'D', AwayScore: 14, HomeScore: 24, StarterPoints: 74, StarterCount: 4, FantasyTeamIDs: [3, 4], FantasyMatchupIDs: ['m-2'] }
      ],
      KeyPlayers: [
        { PlayerID: 'p1', FantasyTeamID: 1, NFLTeamID: 'A', Position: 'QB', Points: 38 },
        { PlayerID: 'p2', FantasyTeamID: 2, NFLTeamID: 'B', Position: 'RB', Points: 31 },
        { PlayerID: 'p3', FantasyTeamID: 3, NFLTeamID: 'C', Position: 'WR', Points: 28 }
      ]
    }]
  };
}

describe('Overview weekly dashboard presentation', () => {
  it('keeps Week 1 fail-closed when no LastCompletedWeek exists', () => {
    const teams = [1, 2, 3, 4].map(id => makeTeam(id, id, id, id));
    const model = readModel(null, 1, 'open');
    const context = buildOverviewTopContext(makeLeague(teams, 0), model);

    expect(context.lastCompletedWeek).toBeNull();
    expect(context.lastMatchups).toEqual([]);
    expect(selectOverviewRecap(recaps(), '2026', null, 'prep')).toBeNull();
  });

  it('uses LastCompletedWeek and scales the top context to league size', () => {
    const teams = Array.from({ length: 8 }, (_, index) => makeTeam(index + 1, index + 1, index + 1, index + 1));
    const league = makeLeague(teams, 1);
    const model: MatchupsReadModel = {
      SchemaVersion: 1,
      Season: '2026',
      Weeks: [{
        Week: 1,
        Stage: 'regular-season',
        FirstKickoffUtc: '2026-09-10T00:00:00Z',
        CompletionState: 'final',
        Matchups: [
          matchup('a', 1, 8, 'final'),
          matchup('b', 2, 7, 'final'),
          matchup('c', 3, 6, 'final'),
          matchup('d', 4, 5, 'final')
        ]
      }],
      Summary: { LastCompletedWeek: 1, ActiveOrNextWeek: null }
    };

    const context = buildOverviewTopContext(league, model);
    expect(context.standings.length).toBe(8);
    expect(context.lastMatchups.length).toBe(4);
    expect(context.lastMatchups.flatMap(row => row.participants).length).toBe(8);
  });

  it('switches Recap → Prep → Live at the explicit kickoff boundaries', () => {
    const model = readModel(1, 2, 'final', '2026-09-18T00:00:00Z');

    expect(resolveOverviewWeeklyPhase(model, new Date('2026-09-16T23:59:59Z'))).toBe('recap');
    expect(resolveOverviewWeeklyPhase(model, new Date('2026-09-17T00:00:00Z'))).toBe('prep');
    expect(resolveOverviewWeeklyPhase(model, new Date('2026-09-17T23:59:59Z'))).toBe('prep');
    expect(resolveOverviewWeeklyPhase(model, new Date('2026-09-18T00:00:00Z'))).toBe('live');
  });

  it('orders whole cards by standings keys and orients the better standing first', () => {
    const teams = [1, 2, 3, 4, 5, 6].map(id => makeTeam(id, id, id, id));
    const ordered = orderOverviewCurrentMatchups(makeLeague(teams, 1), [
      matchup('m-c', 5, 3),
      matchup('m-a', 6, 1),
      matchup('m-b', 4, 2)
    ]);

    expect(ordered.map(row => row.FantasyMatchupID)).toEqual(['m-b', 'm-a', 'm-c']);
    expect(ordered.map(row => row.Participants.map(participant => participant.TeamID))).toEqual([
      [2, 4],
      [1, 6],
      [3, 5]
    ]);
  });

  it('uses previous-season Overall standings before Week 1 instead of unresolved current places', () => {
    const previousPlaces = [4, 1, 3, 2];
    const teams = previousPlaces.map((place, index) => makeTeam(index + 1, 999, place, index + 1));
    const league = makeLeague(teams, 0, [999, 999, 999, 999]);
    const ordered = orderOverviewCurrentMatchups(league, [
      matchup('m-z', 1, 3),
      matchup('m-a', 4, 2)
    ]);

    expect(ordered.map(row => row.FantasyMatchupID)).toEqual(['m-a', 'm-z']);
    expect(ordered[0].Participants.map(participant => participant.TeamID)).toEqual([2, 4]);
    expect(ordered[1].Participants.map(participant => participant.TeamID)).toEqual([3, 1]);
  });

  it('uses #503 neutral All-Time order only when effective standings cannot distinguish participants', () => {
    const teams = [
      makeTeam(1, 999, 999, 2),
      makeTeam(2, 999, 999, 1)
    ];
    const ordered = orderOverviewCurrentMatchups(makeLeague(teams, 0, [999, 999]), [matchup('m', 1, 2)]);

    expect(ordered[0].Participants.map(participant => participant.TeamID)).toEqual([2, 1]);
  });

  it('preserves WeeklyRecaps ranking while applying prominent vs compact density only', () => {
    const source = recaps();
    const prominent = selectOverviewRecap(source, '2026', 1, 'recap');
    const prep = selectOverviewRecap(source, '2026', 1, 'prep');
    const live = selectOverviewRecap(source, '2026', 1, 'live');

    expect(prominent?.games.map(game => game.GameID)).toEqual(['g1', 'g2']);
    expect(prominent?.players.map(player => player.PlayerID)).toEqual(['p1', 'p2', 'p3']);
    expect(prep?.games.map(game => game.GameID)).toEqual(['g1']);
    expect(prep?.players.map(player => player.PlayerID)).toEqual(['p1']);
    expect(live?.games.map(game => game.GameID)).toEqual(['g1']);
    expect(live?.players.map(player => player.PlayerID)).toEqual(['p1']);
  });

  it('rejects an unknown/non-final LastCompletedWeek instead of inferring recap finality', () => {
    const model = readModel(1, 2, 'unknown');
    expect(getLastCompletedWeek(model)).toBeNull();

    const teams = [1, 2, 3, 4].map(id => makeTeam(id, id, id, id));
    const context = buildOverviewTopContext(makeLeague(teams, 1), model);
    expect(context.lastCompletedWeek).toBeNull();
    expect(context.lastMatchups).toEqual([]);
  });

  it('falls back to stable matchup identity without reordering participants when all standings evidence is unusable', () => {
    const teams = [1, 2].map(id => makeTeam(id, 999, 999, 999));
    const league = makeLeague(teams, 0, [999, 999]);
    const ordered = orderOverviewCurrentMatchups(league, [matchup('z', 2, 1), matchup('a', 1, 2)]);

    expect(ordered.map(row => row.FantasyMatchupID)).toEqual(['a', 'z']);
    expect(ordered.find(row => row.FantasyMatchupID === 'z')?.Participants.map(participant => participant.TeamID)).toEqual([2, 1]);
  });
});
