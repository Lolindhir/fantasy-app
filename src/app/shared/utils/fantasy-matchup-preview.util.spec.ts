import type { FantasyGameContextMatchup } from '../../core/models/fantasy-game-context.models';
import { getNextFantasyMatchupGame } from './fantasy-game-context.util';

function row(gameID: string, startsAtUtc: string, starters: number) {
  return {
    GameID: gameID,
    DecisionWindowID: startsAtUtc,
    StartsAtUtc: startsAtUtc,
    LeftStarterCount: starters,
    RightStarterCount: 0,
    LeftRosteredPlayerCount: starters,
    RightRosteredPlayerCount: 0,
    LeftStarterPoints: 0,
    RightStarterPoints: 0,
    StarterPointDelta: 0,
    OutcomeChangedWithoutGame: null,
    ScoreWithoutGame: null
  };
}

describe('fantasy matchup next scoring preview', () => {
  it('uses generator-owned primary game when available', () => {
    const matchup: FantasyGameContextMatchup = {
      FantasyMatchupID: 'm1',
      TeamIDs: [1, 2],
      FinalScores: null,
      CounterfactualState: 'unavailable-not-final',
      Games: [
        row('option-first', '2026-09-10T00:20:00Z', 0),
        row('starter-later', '2026-09-13T17:00:00Z', 2)
      ],
      RemainingRelevance: {
        State: 'both-sides',
        HasRemainingScoringPaths: true,
        LeftRemainingPathCount: 2,
        RightRemainingPathCount: 1,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 2,
        EligibleBenchCandidateCount: 1,
        NextScoringWindowID: '2026-09-13T17:00:00Z',
        NextScoringGameIDs: ['starter-later'],
        NextScoringPrimaryGameID: 'starter-later',
        NextScoringWindowGameCount: 1,
        NextScoringLockedActiveStarterCount: 0,
        NextScoringUnlockedStarterCount: 2,
        NextScoringOptionCount: 0,
        FinalScoringWindowID: '2026-09-13T17:00:00Z',
        FinalScoringGameIDs: ['starter-later'],
        IsFinalScoringWindowCommitted: false
      }
    };

    expect(getNextFantasyMatchupGame(matchup, new Date('2026-09-09T00:00:00Z'))?.GameID)
      .toBe('starter-later');
  });

  it('prefers a future direct starter game while older v2 JSON has no primary preview field', () => {
    const matchup: FantasyGameContextMatchup = {
      FantasyMatchupID: 'm1',
      TeamIDs: [1, 2],
      FinalScores: null,
      CounterfactualState: 'unavailable-not-final',
      Games: [
        row('option-first', '2026-09-10T00:20:00Z', 0),
        row('starter-later', '2026-09-11T00:35:00Z', 3)
      ],
      RemainingRelevance: {
        State: 'both-sides',
        HasRemainingScoringPaths: true,
        LeftRemainingPathCount: 2,
        RightRemainingPathCount: 1,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 3,
        EligibleBenchCandidateCount: 1,
        NextScoringWindowID: '2026-09-10T00:20:00Z',
        NextScoringGameIDs: ['option-first'],
        FinalScoringWindowID: '2026-09-11T00:35:00Z',
        FinalScoringGameIDs: ['starter-later'],
        IsFinalScoringWindowCommitted: false
      }
    };

    expect(getNextFantasyMatchupGame(matchup, new Date('2026-09-09T00:00:00Z'))?.GameID)
      .toBe('starter-later');
  });
});
