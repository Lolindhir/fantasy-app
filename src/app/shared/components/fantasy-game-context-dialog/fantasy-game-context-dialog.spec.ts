import type { FantasyGameContextMatchup } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import {
  matchupDisplaySideValue,
  orientMatchupScore,
  resolveMatchupDisplayTeamIDs
} from './fantasy-game-context-dialog';

describe('FantasyGameContext matchup display orientation', () => {
  const league = {
    Season: '2026',
    FinalScoredWeek: 1,
    Teams: [
      { TeamID: 2, Team: 'Flo', TeamAbbr: 'FLO', Owner: 'Flo', Roster: [] },
      { TeamID: 10, Team: 'Tampa Bay', TeamAbbr: 'TB', Owner: 'Tim', Roster: [] }
    ],
    Standings: [{
      Season: '2026',
      Playoffs: null,
      RegularSeason: [
        { TeamID: 10, Place: 1 },
        { TeamID: 2, Place: 2 }
      ]
    }]
  } as unknown as League;

  const matchup = {
    FantasyMatchupID: 'm-1',
    TeamIDs: [2, 10],
    FinalScores: { Left: 91.25, Right: 123.5 },
    CounterfactualState: 'available',
    Games: [],
    RemainingRelevance: {
      State: 'right-only',
      HasRemainingScoringPaths: true,
      LeftRemainingPathCount: 1,
      RightRemainingPathCount: 3,
      LockedActiveStarterCount: 0,
      UnlockedStarterCount: 1,
      EligibleBenchCandidateCount: 0,
      NextScoringWindowID: null,
      NextScoringGameIDs: [],
      FinalScoringWindowID: null,
      FinalScoringGameIDs: [],
      IsFinalScoringWindowCommitted: false
    }
  } satisfies FantasyGameContextMatchup;

  const matchups = {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [{
      Week: 2,
      Stage: 'regular-season',
      FirstKickoffUtc: null,
      CompletionState: 'open',
      Matchups: [{
        FantasyMatchupID: 'm-1',
        Participants: [
          { TeamID: 2, Points: 91.25, ScoreKind: 'standard' },
          { TeamID: 10, Points: 123.5, ScoreKind: 'standard' }
        ],
        CompletionState: 'open',
        Result: null
      }]
    }],
    Summary: { LastCompletedWeek: 1, ActiveOrNextWeek: 2 }
  } satisfies MatchupsReadModel;

  it('uses the Overview standing orientation instead of generated TeamIDs order', () => {
    expect(resolveMatchupDisplayTeamIDs(league, matchups, '2026', 2, matchup)).toEqual([10, 2]);
  });

  it('keeps scores, remaining paths and timeline points attached to the displayed team', () => {
    const displayTeamIDs = resolveMatchupDisplayTeamIDs(league, matchups, '2026', 2, matchup);

    expect(orientMatchupScore(matchup, displayTeamIDs, matchup.FinalScores)).toEqual({
      Left: 123.5,
      Right: 91.25
    });
    expect(matchupDisplaySideValue(
      matchup,
      displayTeamIDs,
      'left',
      matchup.RemainingRelevance.LeftRemainingPathCount,
      matchup.RemainingRelevance.RightRemainingPathCount
    )).toBe(3);
    expect(matchupDisplaySideValue(
      matchup,
      displayTeamIDs,
      'right',
      matchup.RemainingRelevance.LeftRemainingPathCount,
      matchup.RemainingRelevance.RightRemainingPathCount
    )).toBe(1);
    expect(matchupDisplaySideValue(matchup, displayTeamIDs, 'left', 12.75, 27.5)).toBe(27.5);
    expect(matchupDisplaySideValue(matchup, displayTeamIDs, 'right', 12.75, 27.5)).toBe(12.75);
  });

  it('preserves generated orientation when the Overview matchup cannot be resolved', () => {
    expect(resolveMatchupDisplayTeamIDs(league, null, '2026', 2, matchup)).toEqual([2, 10]);
  });
});
