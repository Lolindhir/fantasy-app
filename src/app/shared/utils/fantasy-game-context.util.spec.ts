import type { FantasyGameContextGame, FantasyGameContextReadModel } from '../../core/models/fantasy-game-context.models';
import {
  compareFantasyGameImpact,
  compareFantasyGameRelevance,
  compareFantasyGameRemainingRelevance,
  getCompletedImpactGames,
  getFantasyMatchupContext,
  getMustWatchGames,
  getNextFantasyMatchupGame,
  getUpcomingRelevantGames,
  isFantasyGameContextForLeagueWeek,
  isFantasyGameImpactVisible,
  isFantasyMatchupFinalWindowGame
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
  it('orders legacy relevance lexicographically by starters before broad roster coverage', () => {
    const low = game({ GameID: 'low', Relevance: { RosteredPlayerCount: 20, StarterCount: 1, FantasyTeamCount: 6, FantasyMatchupCount: 3, UnknownAssociationCount: 0 } });
    const high = game({ GameID: 'high', Relevance: { RosteredPlayerCount: 2, StarterCount: 2, FantasyTeamCount: 1, FantasyMatchupCount: 1, UnknownAssociationCount: 0 } });
    expect([low, high].sort(compareFantasyGameRelevance).map(item => item.GameID)).toEqual(['high', 'low']);
  });

  it('orders remaining relevance by distinct directly affected fantasy teams before unlocked starter volume', () => {
    const wide = game({
      GameID: 'wide',
      RemainingRelevance: {
        HasRemainingRelevance: true,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 3,
        EligibleBenchCandidateCount: 0,
        DirectStarterFantasyTeamCount: 3,
        DirectStarterFantasyTeamIDs: [1, 2, 3],
        FantasyMatchupCount: 2,
        TwoSidedFantasyMatchupCount: 1,
        FinalWindowFantasyMatchupCount: 0,
        CommittedFinalWindowMatchupCount: 0
      }
    });
    const concentrated = game({
      GameID: 'concentrated',
      RemainingRelevance: {
        HasRemainingRelevance: true,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 7,
        EligibleBenchCandidateCount: 0,
        DirectStarterFantasyTeamCount: 2,
        DirectStarterFantasyTeamIDs: [1, 2],
        FantasyMatchupCount: 1,
        TwoSidedFantasyMatchupCount: 1,
        FinalWindowFantasyMatchupCount: 0,
        CommittedFinalWindowMatchupCount: 0
      }
    });

    expect([concentrated, wide].sort(compareFantasyGameRemainingRelevance).map(item => item.GameID)).toEqual(['wide', 'concentrated']);
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

  it('skips future matchup games where neither fantasy side starts a player in the legacy fallback', () => {
    const matchup = {
      ...baseContext.FantasyMatchups[0],
      Games: [
        {
          ...baseContext.FantasyMatchups[0].Games[0],
          GameID: 'zero',
          StartsAtUtc: '2026-09-09T12:00:00Z',
          LeftStarterCount: 0,
          RightStarterCount: 0
        },
        {
          ...baseContext.FantasyMatchups[0].Games[0],
          GameID: 'relevant',
          StartsAtUtc: '2026-09-09T18:00:00Z',
          LeftStarterCount: 0,
          RightStarterCount: 2
        }
      ]
    };

    expect(getNextFantasyMatchupGame(matchup, new Date('2026-09-09T00:00:00Z'))?.GameID).toBe('relevant');
  });

  it('uses generated v2 must-watch rank instead of recalculating broad roster relevance', () => {
    const first = game({ GameID: 'first', Relevance: { RosteredPlayerCount: 1, StarterCount: 1, FantasyTeamCount: 1, FantasyMatchupCount: 1, UnknownAssociationCount: 0 } });
    const second = game({ GameID: 'second', Relevance: { RosteredPlayerCount: 30, StarterCount: 10, FantasyTeamCount: 6, FantasyMatchupCount: 3, UnknownAssociationCount: 0 } });
    const context: FantasyGameContextReadModel = {
      ...baseContext,
      SchemaVersion: 2,
      Games: [second, first],
      MustWatchGames: [
        { Rank: 1, GameID: 'first', DecisionWindowID: 'dw1', StartsAtUtc: first.StartsAtUtc, CommittedFinalWindowMatchupCount: 1, LockedActiveStarterCount: 1, DirectStarterFantasyTeamCount: 1, DirectStarterFantasyTeamIDs: [1], TwoSidedFantasyMatchupCount: 0, FantasyMatchupCount: 1, UnlockedStarterCount: 0, FinalWindowFantasyMatchupCount: 1, EligibleBenchCandidateCount: 0 },
        { Rank: 2, GameID: 'second', DecisionWindowID: 'dw2', StartsAtUtc: second.StartsAtUtc, CommittedFinalWindowMatchupCount: 0, LockedActiveStarterCount: 0, DirectStarterFantasyTeamCount: 6, DirectStarterFantasyTeamIDs: [1, 2, 3, 4, 5, 6], TwoSidedFantasyMatchupCount: 1, FantasyMatchupCount: 3, UnlockedStarterCount: 10, FinalWindowFantasyMatchupCount: 0, EligibleBenchCandidateCount: 5 }
      ]
    };

    expect(getMustWatchGames(context).map(item => item.GameID)).toEqual(['first', 'second']);
  });

  it('uses generated next/final scoring windows even when a relevant window has zero current starters', () => {
    const zeroStarterRow = {
      ...baseContext.FantasyMatchups[0].Games[0],
      GameID: 'bench-path',
      DecisionWindowID: 'dw-bench',
      StartsAtUtc: '2026-09-11T00:00:00Z',
      LeftStarterCount: 0,
      RightStarterCount: 0
    };
    const matchup = {
      ...baseContext.FantasyMatchups[0],
      Games: [baseContext.FantasyMatchups[0].Games[0], zeroStarterRow],
      RemainingRelevance: {
        State: 'both-sides' as const,
        HasRemainingScoringPaths: true,
        LeftRemainingPathCount: 2,
        RightRemainingPathCount: 1,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 2,
        EligibleBenchCandidateCount: 1,
        NextScoringWindowID: 'dw-bench',
        NextScoringGameIDs: ['bench-path'],
        FinalScoringWindowID: 'dw-bench',
        FinalScoringGameIDs: ['bench-path'],
        IsFinalScoringWindowCommitted: false
      }
    };

    expect(getNextFantasyMatchupGame(matchup, new Date('2026-09-09T00:00:00Z'))?.GameID).toBe('bench-path');
    expect(isFantasyMatchupFinalWindowGame(matchup, 'bench-path')).toBeTrue();
  });

  it('hides non-unavailable impact values until the NFL game has actually started', () => {
    const scheduledWithPartialWeekImpact = game({
      StartsAtUtc: '2026-09-10T18:00:00Z',
      Impact: { State: 'partial', RosteredPoints: 0, StarterPoints: 0, OutcomeSwingMatchupCount: 0 }
    });

    expect(isFantasyGameImpactVisible(scheduledWithPartialWeekImpact, new Date('2026-09-10T12:00:00Z'))).toBeFalse();
    expect(isFantasyGameImpactVisible(scheduledWithPartialWeekImpact, new Date('2026-09-10T19:00:00Z'))).toBeTrue();
  });
});
