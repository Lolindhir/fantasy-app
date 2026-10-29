import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';
import type { MatchupProjectionTeam } from '../../../core/models/matchup-projections.models';
import {
  buildMatchupPlayerStatus,
  hasMatchupPlayerStatus,
  type MatchupPlayerStatusLookups
} from './matchup-player-status.util';

function game(id: string, away: string, home: string, status: string, teams: unknown[]): FantasyGameContextGame {
  return {
    GameID: id,
    AwayTeamID: away,
    AwayTeamAbbr: away,
    HomeTeamID: home,
    HomeTeamAbbr: home,
    Status: status,
    FantasyTeams: teams
  } as unknown as FantasyGameContextGame;
}

function starter(playerID: string) {
  return { PlayerID: playerID, IsStarter: true, Points: null };
}

function projectionTeam(teamID: string, overrides: Partial<MatchupProjectionTeam>): MatchupProjectionTeam {
  return {
    FantasyTeamID: teamID,
    OutStarterPlayerIDs: [],
    UncertainStarterPlayerIDs: [],
    ...overrides
  } as MatchupProjectionTeam;
}

describe('buildMatchupPlayerStatus', () => {
  const context = {
    Games: [
      game('g1', 'PIT', 'CLE', 'Final', [
        { FantasyTeamID: 1, Players: [starter('rb'), { ...starter('bench'), IsStarter: false }] }
      ]),
      game('g2', 'MIA', 'MIN', 'Scheduled', [{ FantasyTeamID: 1, Players: [starter('wr-out')] }]),
      game('g3', 'IND', 'WSH', 'Scheduled', [{ FantasyTeamID: 2, Players: [starter('wr-q')] }])
    ]
  } as unknown as FantasyGameContextReadModel;

  const matchup = {
    FantasyMatchupID: 'm',
    TeamIDs: [1, 2],
    Projection: {
      FantasyMatchupID: 'm',
      Axis: null,
      Teams: [
        projectionTeam('1', { OutStarterPlayerIDs: ['wr-out'] }),
        projectionTeam('2', { UncertainStarterPlayerIDs: ['wr-q'] })
      ]
    }
  } as unknown as FantasyGameContextMatchup;

  const lookups: MatchupPlayerStatusLookups = {
    teamName: id => `Team ${id}`,
    teamAvatar: () => null,
    player: id => ({ name: id, picture: null, nflLogo: null })
  };

  it('lists OUT and questionable starters with the NFL game they play in', () => {
    const [left, right] = buildMatchupPlayerStatus(matchup, [1, 2], context, lookups);

    expect(left.problems).toEqual([
      jasmine.objectContaining({ playerID: 'wr-out', kind: 'out', gameLabel: 'MIA @ MIN' })
    ]);
    expect(right.problems).toEqual([
      jasmine.objectContaining({ playerID: 'wr-q', kind: 'questionable', gameLabel: 'IND @ WSH' })
    ]);
  });

  it('honors the display order of the teams', () => {
    const [first, second] = buildMatchupPlayerStatus(matchup, [2, 1], context, lookups);

    expect(first.teamID).toBe(2);
    expect(second.teamID).toBe(1);
  });

  it('does not flag an OUT starter whose game is already final', () => {
    const finalOut = {
      ...matchup,
      Projection: {
        ...matchup.Projection!,
        Teams: [projectionTeam('1', { OutStarterPlayerIDs: ['rb'] }), matchup.Projection!.Teams[1]]
      }
    } as FantasyGameContextMatchup;
    const [left] = buildMatchupPlayerStatus(finalOut, [1, 2], context, lookups);

    expect(left.problems).toEqual([]);
  });

  it('renders nothing when no starter is out or questionable', () => {
    const empty = buildMatchupPlayerStatus(
      { ...matchup, Projection: null } as FantasyGameContextMatchup,
      [1, 2],
      { Games: [] } as unknown as FantasyGameContextReadModel,
      lookups
    );

    expect(hasMatchupPlayerStatus(empty)).toBeFalse();
  });
});
