import type { FantasyGameContextGame, FantasyGameContextReadModel } from '../../core/models/fantasy-game-context.models';
import {
  compareFantasyGameImpact,
  compareFantasyGameRelevance,
  getCompletedImpactGames,
  getFantasyMatchupContext,
  getNextFantasyMatchupGame,
  getUpcomingRelevantGames,
  isFantasyGameContextForLeagueWeek
} from './fantasy-game-context.util';

function game(overrides: Partial<FantasyGameContextGame> = {}): FantasyGameContextGame {
  return {
    GameID: 'g1',
    DecisionWindowID: 'dw1',
    StartsAtUtc: '2026-09-10T00:00:00Z',
    AwayTeamID: 'A',
    AwayTeamAbbr: 'AAA',
    HomeTeamID: 'H',
    HomeTeamAbbr: 'HHH',
    Status: 'Scheduled',
    Relevance: {
      RosteredPlayerCount: 2,
      StarterCount: 1,
      FantasyTeamCount: 1,
      FantasyMatchupCount: 1,
      UnknownAssociationCount: 0
    },
    Impact: {
      State: 'unavailable',
      RosteredPoints: null,
      StarterPoints: null,
      OutcomeSwingMatchupCount: 0
    },
    FantasyTeams: [],
    ...overrides
  };
}

const baseContext: FantasyGameContextReadModel = {
  SchemaVersion: 1,
  LeagueID: 'league',
  Season: '2026',
  Week: 1,
  ScoringState: 'pending',
  DecisionWindows: [],
  Games: [],
  FantasyMatchups: [{
    FantasyMatchupID: 'fgm-1',
    TeamIDs: [1, 2],
    FinalScores: null,
    CounterfactualState: 'unavailable-not-final',
    Games: [{
      GameID: 'g1',
      DecisionWindowID: 'dw1',
      StartsAtUtc: '2026-09-10T00:00:00Z',
      LeftStarterCount: 1,
      RightStarterCount: 2,
      LeftRosteredPlayerCount: 2,
      RightRosteredPlayerCount: 3,
      LeftStarterPoints: 0,
      RightStarterPoints: 0,
      StarterPointDelta: 0,
      OutcomeChangedWithoutGame: null,
      ScoreWithoutGame: null
    }]
  }],
  NonGameAssociations: []
};

describe('fantasy game context utilities', () => {
  it('orders relevance lexicographically by starters, matchups, teams, rostered players, kickoff and GameID', () => {
    const low = game({ GameID: 'low', Relevance: { RosteredPlayerCount: 20, StarterCount: 1, FantasyTeamCount: 6, FantasyMatchupCount: 3, UnknownAssociationCount: 0 } });
    const high = game({ GameID: 'high', Relevance: { RosteredPlayerCount: 2, StarterCount: 2, FantasyTeamCount: 1, FantasyMatchupCount: 1, UnknownAssociationCount: 0 } });
    expect([low, high].sort(compareFantasyGameRelevance).map(item => item.GameID)).toEqual(['high', 'low']);
  });

  it('orders completed impact by starter points before relevance', () => {
    const low = game({ GameID: 'low', Status: 'Final', Impact: { State: 'final', RosteredPoints: 50, StarterPoints: 10, OutcomeSwingMatchupCount: 0 } });
    const high = game({ GameID: 'high', Status: 'Final', Impact: { State: 'final', RosteredPoints: 20, StarterPoints: 18, OutcomeSwingMatchupCount: 1 } });
    expect([low, high].sort(compareFantasyGameImpact).map(item => item.GameID)).toEqual(['high', 'low']);
    expect(getCompletedImpactGames({ ...baseContext, Games: [low, high] })[0].GameID).toBe('high');
  });

  it('keeps unknown-only future games visible and matches fantasy pairings independently from provider matchup ids', () => {
    const unknown = game({ Relevance: { RosteredPlayerCount: 0, StarterCount: 0, FantasyTeamCount: 0, FantasyMatchupCount: 0, UnknownAssociationCount: 1 } });
    expect(getUpcomingRelevantGames({ ...baseContext, Games: [unknown] }, new Date('2026-09-09T00:00:00Z'))).toHaveLength(1);
    expect(getFantasyMatchupContext(baseContext, ['2', '1'])?.FantasyMatchupID).toBe('fgm-1');
  });

  it('fails safely on stale/missing context and finds the next matchup game chronologically', () => {
    expect(isFantasyGameContextForLeagueWeek(baseContext, '2026', 1)).toBeTrue();
    expect(isFantasyGameContextForLeagueWeek(baseContext, '2025', 1)).toBeFalse();
    expect(getFantasyMatchupContext(baseContext, [9, 10])).toBeNull();
    expect(getNextFantasyMatchupGame(baseContext.FantasyMatchups[0], new Date('2026-09-09T00:00:00Z'))?.GameID).toBe('g1');
  });
});
