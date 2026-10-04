import type { FantasyRelevanceTeamState } from '../../../core/models/decision-window.models';
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

function game(id: string, away: string, home: string, status: string, startsAtUtc: string, teams: unknown[]): FantasyGameContextGame {
  return {
    GameID: id,
    DecisionWindowID: `w-${id}`,
    StartsAtUtc: startsAtUtc,
    AwayTeamID: away,
    AwayTeamAbbr: away,
    HomeTeamID: home,
    HomeTeamAbbr: home,
    Status: status,
    FantasyTeams: teams
  } as unknown as FantasyGameContextGame;
}

function starter(playerID: string, points: number | null, projected: number | null = null) {
  return {
    PlayerID: playerID,
    IsStarter: true,
    Points: points,
    Prediction: projected === null ? null : { Status: 'available', Points: projected }
  };
}

function projectionTeam(teamID: string, overrides: Partial<MatchupProjectionTeam>): MatchupProjectionTeam {
  return {
    FantasyTeamID: teamID,
    StarterCount: 4,
    ByeStarterPlayerIDs: [],
    OutStarterPlayerIDs: [],
    UncertainStarterPlayerIDs: [],
    UnavailableStarterPlayerIDs: [],
    ...overrides
  } as MatchupProjectionTeam;
}

describe('buildMatchupPlayerStatus', () => {
  const context = {
    Games: [
      game('g1', 'PIT', 'CLE', 'Final', '2026-10-01T00:00:00Z', [
        { FantasyTeamID: 1, Players: [starter('rb', 15.6, 13.8), { ...starter('bench', 4), IsStarter: false }] },
        { FantasyTeamID: 2, Players: [starter('qb', 24, 14.1)] }
      ]),
      game('g2', 'MIA', 'MIN', 'Scheduled', '2026-10-04T17:00:00Z', [
        { FantasyTeamID: 1, Players: [starter('wr-out', null, 14.4)] }
      ]),
      game('g3', 'IND', 'WSH', 'Scheduled', '2026-10-04T17:00:00Z', [
        { FantasyTeamID: 1, Players: [starter('taylor', null), starter('zeta', null)] },
        { FantasyTeamID: 2, Players: [starter('wr-q', null)] }
      ])
    ]
  } as unknown as FantasyGameContextReadModel;

  const matchup = {
    FantasyMatchupID: 'm',
    TeamIDs: [1, 2],
    Projection: {
      FantasyMatchupID: 'm',
      Axis: null,
      Teams: [
        projectionTeam('1', { StarterCount: 5, OutStarterPlayerIDs: ['wr-out'] }),
        projectionTeam('2', { StarterCount: 4, UncertainStarterPlayerIDs: ['wr-q'], ByeStarterPlayerIDs: ['bye'] })
      ]
    },
    RemainingRelevance: { NextScoringGameIDs: ['g3'] }
  } as unknown as FantasyGameContextMatchup;

  const decisionTeam = {
    Players: [
      { PlayerID: 'wr-out', LineupSlotID: 'FLEX-2', LineupSlotType: 'FLEX', IsBenchCandidate: false, EligibleUnlockedSlotIDs: [] },
      { PlayerID: 'b1', LineupSlotID: null, LineupSlotType: null, IsBenchCandidate: true, EligibleUnlockedSlotIDs: ['FLEX-2', 'WR-1'] },
      { PlayerID: 'b2', LineupSlotID: null, LineupSlotType: null, IsBenchCandidate: true, EligibleUnlockedSlotIDs: ['RB-1'] }
    ]
  } as unknown as FantasyRelevanceTeamState;

  const lookups: MatchupPlayerStatusLookups = {
    teamName: id => `Team ${id}`,
    teamAvatar: () => null,
    player: id => ({ name: id, picture: null, position: id.startsWith('wr') || id === 'taylor' ? 'WR' : 'RB', nflLogo: null }),
    decisionTeam: id => (String(id) === '1' ? decisionTeam : null)
  };

  it('does not list starters from finished NFL games', () => {
    const [left] = buildMatchupPlayerStatus(matchup, [1, 2], context, lookups);

    expect(left.problems.map(problem => problem.playerID)).not.toContain('rb');
  });

  it('lists OUT starters with lineup slot, game and replacement count', () => {
    const [left] = buildMatchupPlayerStatus(matchup, [1, 2], context, lookups);

    expect(left.problems).toEqual([
      jasmine.objectContaining({
        playerID: 'wr-out',
        kind: 'out',
        slot: 'FLEX',
        gameLabel: 'MIA @ MIN',
        benchOptionCount: 1
      })
    ]);
  });

  it('lists questionable starters without replacement count and counts only remaining open starters', () => {
    const [left, right] = buildMatchupPlayerStatus(matchup, [1, 2], context, lookups);

    expect(right.problems).toEqual([
      jasmine.objectContaining({ playerID: 'wr-q', kind: 'questionable', benchOptionCount: null })
    ]);
    expect(left.openCount).toBe(3);
    expect(right.openCount).toBe(1);
  });

  it('names the next generated scoring window per team and honors display order', () => {
    const [right, left] = buildMatchupPlayerStatus(matchup, [2, 1], context, lookups);

    expect(right.teamID).toBe(2);
    expect(right.nextWindow).toEqual({ gameLabel: 'IND @ WSH', playerName: 'wr-q', extraPlayerCount: 0 });
    expect(left.nextWindow).toEqual({ gameLabel: 'IND @ WSH', playerName: 'taylor', extraPlayerCount: 1 });
  });

  it('does not flag an OUT starter whose game is already final', () => {
    const finalOut = {
      ...matchup,
      Projection: {
        ...matchup.Projection!,
        Teams: [projectionTeam('1', { StarterCount: 5, OutStarterPlayerIDs: ['rb'] }), matchup.Projection!.Teams[1]]
      }
    } as FantasyGameContextMatchup;
    const [left] = buildMatchupPlayerStatus(finalOut, [1, 2], context, lookups);

    expect(left.problems).toEqual([]);
    expect(left.openCount).toBe(4);
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
