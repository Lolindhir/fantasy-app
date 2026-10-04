import type { FantasyGameContextMatchup } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import {
  matchupSportsStateLabel,
  matchupDisplaySideValue,
  orientMatchupScore,
  resolveMatchupDisplayTeamIDs,
  starterProjectedPoints,
  starterProjectedRange,
  teamProjectedFinalScore
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

  it('keeps scores and timeline points attached to the displayed team', () => {
    const displayTeamIDs = resolveMatchupDisplayTeamIDs(league, matchups, '2026', 2, matchup);

    expect(orientMatchupScore(matchup, displayTeamIDs, matchup.FinalScores)).toEqual({
      Left: 123.5,
      Right: 91.25
    });
    expect(matchupDisplaySideValue(matchup, displayTeamIDs, 'left', 12.75, 27.5)).toBe(27.5);
    expect(matchupDisplaySideValue(matchup, displayTeamIDs, 'right', 12.75, 27.5)).toBe(12.75);
  });

  it('preserves generated orientation when the Overview matchup cannot be resolved', () => {
    expect(resolveMatchupDisplayTeamIDs(league, null, '2026', 2, matchup)).toEqual([2, 10]);
  });

  it('uses sports language for each remaining-scoring state', () => {
    expect(matchupSportsStateLabel('both-sides', 'Flo', 'Tampa Bay')).toBe('Both teams can still score');
    expect(matchupSportsStateLabel('left-only', 'Flo', 'Tampa Bay')).toBe('Only Flo can still score');
    expect(matchupSportsStateLabel('right-only', 'Flo', 'Tampa Bay')).toBe('Only Tampa Bay can still score');
    expect(matchupSportsStateLabel('none', 'Flo', 'Tampa Bay')).toBe('No more points can be scored');
  });

  it('reads the projected final score of the requested team only', () => {
    const team = (id: number, score: number | null) => ({
      FantasyTeamID: id,
      State: score === null ? 'partial' as const : 'available' as const,
      StarterCount: 1,
      ResolvedStarterCount: 1,
      FinalStarterCount: 0,
      ScoredPoints: 0,
      PregameProjectedScore: score,
      ProjectedFinalScore: score,
      StandardDeviation: score === null ? null : 10,
      Ranges: [],
      ByeStarterPlayerIDs: [],
      UnavailableStarterPlayerIDs: []
    });
    const projected = {
      ...matchup,
      Projection: {
        FantasyMatchupID: 'm-1',
        Teams: [team(2, 95.5), team(10, null)],
        Axis: { Min: 40, Max: 140, Step: 20 }
      }
    } satisfies FantasyGameContextMatchup;

    expect(teamProjectedFinalScore(projected, 2)).toBe(95.5);
    expect(teamProjectedFinalScore(projected, '2')).toBe(95.5);
    expect(teamProjectedFinalScore(projected, 10)).toBeNull();
    expect(teamProjectedFinalScore(projected, 99)).toBeNull();
    expect(teamProjectedFinalScore(matchup, 2)).toBeNull();
  });

  it('exposes the starter range of the display level only', () => {
    const base = {
      AvailabilityAdjustmentApplied: false,
      HistoryGames: 4,
      IntervalModel: 'V4-C-PI1',
      ParticipationCondition: 'conditional-on-participation',
      PointModel: 'V4-C',
      Points: 12.5,
      PredictionRange: null,
      RangeQuality: 'player-volatility',
      Status: 'available' as const
    };
    const player = {
      PlayerID: 'p1',
      IsStarter: true,
      Points: null,
      Prediction: {
        ...base,
        PredictionRanges: [
          { Level: 0.8, Lower: 6, Upper: 20 },
          { Level: 0.9, Lower: 4, Upper: 24 }
        ]
      }
    };

    expect(starterProjectedRange(player, 0.8)).toEqual({ Lower: 6, Upper: 20 });
    expect(starterProjectedRange(player, 0.5)).toBeNull();
    expect(starterProjectedRange(player, null)).toBeNull();
    expect(starterProjectedRange({ ...player, Prediction: null }, 0.8)).toBeNull();
  });

  it('exposes a starter projection only when the published projection is available', () => {
    const projection = {
      AvailabilityAdjustmentApplied: false,
      HistoryGames: 4,
      IntervalModel: 'V4-C-PI1',
      ParticipationCondition: 'conditional-on-participation',
      PointModel: 'V4-C',
      Points: 12.5,
      PredictionRange: null,
      PredictionRanges: [],
      RangeQuality: 'player-volatility'
    };

    expect(starterProjectedPoints({ PlayerID: 'p1', IsStarter: true, Points: null, Prediction: { ...projection, Status: 'available' } })).toBe(12.5);
    expect(starterProjectedPoints({ PlayerID: 'p1', IsStarter: true, Points: null, Prediction: { ...projection, Status: 'insufficient-history', Points: null } })).toBeNull();
    expect(starterProjectedPoints({ PlayerID: 'p1', IsStarter: true, Points: null })).toBeNull();
    expect(starterProjectedPoints(null)).toBeNull();
  });
});
