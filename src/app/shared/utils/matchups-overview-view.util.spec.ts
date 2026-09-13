import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../core/models/fantasy-game-context.models';
import type {
  FantasyRelevanceSlotState,
  FantasyRelevanceTeamState
} from '../../core/models/decision-window.models';
import {
  buildMatchupScoringWindow,
  buildMatchupScoreboardState,
  buildMatchupStarterProgress
} from './matchups-overview-view.util';

function slot(
  slotID: string,
  state: FantasyRelevanceSlotState['State'],
  options: Partial<FantasyRelevanceSlotState> = {}
): FantasyRelevanceSlotState {
  const slotIndex = Number(slotID.split('-').at(-1)) || 1;
  return {
    SlotID: slotID,
    SlotType: slotID.split('-')[0],
    SlotOrdinal: slotIndex,
    SlotIndex: slotIndex,
    CurrentStarterID: `p-${slotID}`,
    State: state,
    GameID: null,
    DecisionWindowID: null,
    StartsAtUtc: null,
    Repairability: null,
    ...options
  };
}

function team(slots: FantasyRelevanceSlotState[]): FantasyRelevanceTeamState {
  return {
    FantasyTeamID: 1,
    ActiveRosterPlayerCount: slots.length,
    StarterCount: slots.length,
    BenchCount: 0,
    IRCount: 0,
    TaxiCount: 0,
    UnlockedStarterCount: slots.filter(item => item.State === 'unlocked').length,
    LockedActiveStarterCount: slots.filter(item => item.State === 'locked-active').length,
    CompletedStarterCount: slots.filter(item => item.State === 'completed').length,
    EligibleBenchCandidateCount: 0,
    HasRemainingScoringPath: true,
    Slots: slots,
    Players: []
  };
}

function game(id: string, startsAtUtc = '2026-09-13T17:00:00Z'): FantasyGameContextGame {
  return {
    GameID: id,
    DecisionWindowID: startsAtUtc,
    StartsAtUtc: startsAtUtc,
    AwayTeamID: `A-${id}`,
    AwayTeamAbbr: `A${id}`,
    HomeTeamID: `H-${id}`,
    HomeTeamAbbr: `H${id}`,
    Status: null,
    Relevance: {
      RosteredPlayerCount: 1,
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
    RemainingRelevance: {
      HasRemainingRelevance: true,
      LockedActiveStarterCount: 0,
      UnlockedStarterCount: 1,
      EligibleBenchCandidateCount: 0,
      FantasyMatchupCount: 1,
      TwoSidedFantasyMatchupCount: 0,
      FinalWindowFantasyMatchupCount: 0,
      CommittedFinalWindowMatchupCount: 0
    }
  };
}

function matchup(gameIDs: string[]): FantasyGameContextMatchup {
  return {
    FantasyMatchupID: 'm1',
    TeamIDs: [1, 2],
    FinalScores: null,
    CounterfactualState: 'unavailable-not-final',
    Games: gameIDs.map(id => ({
      GameID: id,
      DecisionWindowID: 'window-1',
      StartsAtUtc: '2026-09-13T17:00:00Z',
      LeftStarterCount: 1,
      RightStarterCount: 0,
      LeftRosteredPlayerCount: 1,
      RightRosteredPlayerCount: 0,
      LeftStarterPoints: 0,
      RightStarterPoints: 0,
      StarterPointDelta: 0,
      OutcomeChangedWithoutGame: null,
      ScoreWithoutGame: null
    })),
    RemainingRelevance: {
      State: 'both-sides',
      HasRemainingScoringPaths: true,
      LeftRemainingPathCount: 1,
      RightRemainingPathCount: 1,
      LockedActiveStarterCount: 0,
      UnlockedStarterCount: gameIDs.length,
      EligibleBenchCandidateCount: 0,
      NextScoringWindowID: 'window-1',
      NextScoringGameIDs: gameIDs,
      NextScoringWindowGameCount: gameIDs.length,
      NextScoringLockedActiveStarterCount: 0,
      NextScoringUnlockedStarterCount: gameIDs.length,
      NextScoringOptionCount: 0,
      FinalScoringWindowID: 'window-1',
      FinalScoringGameIDs: gameIDs,
      IsFinalScoringWindowCommitted: false
    }
  };
}

function context(games: FantasyGameContextGame[]): FantasyGameContextReadModel {
  return {
    SchemaVersion: 4,
    LeagueID: 'league',
    Season: '2026',
    Week: 1,
    ScoringState: 'partial',
    DecisionWindows: [],
    Games: games,
    FantasyMatchups: [],
    NonGameAssociations: []
  };
}

describe('matchups overview view utility', () => {
  it('keeps the score plate neutral while an open matchup has no locked-active or completed starter', () => {
    expect(buildMatchupScoreboardState('open', [
      team([slot('QB-1', 'unlocked')]),
      team([slot('RB-1', 'unlocked')])
    ])).toBe('neutral');
  });

  it('marks an open score plate active when generated starter lifecycle evidence has started', () => {
    expect(buildMatchupScoreboardState('open', [
      team([slot('QB-1', 'locked-active')]),
      team([slot('RB-1', 'unlocked')])
    ])).toBe('active');

    expect(buildMatchupScoreboardState('open', [
      team([slot('QB-1', 'completed')]),
      team([slot('RB-1', 'unlocked')])
    ])).toBe('active');
  });

  it('takes final and unknown score-plate states only from authoritative matchup completion state', () => {
    const activeEvidence = team([slot('QB-1', 'locked-active')]);

    expect(buildMatchupScoreboardState('final', [activeEvidence])).toBe('final');
    expect(buildMatchupScoreboardState('unknown', [activeEvidence])).toBe('unknown');
  });

  it('keeps an authoritatively final score plate final even when a starter strip has a red irreparable problem', () => {
    const irreparable = {
      ProblemCode: 'OPEN_STARTER_SLOT' as const,
      State: 'irreparable' as const,
      Path: null,
      ReasonCode: 'NO_LEGAL_REPAIR_PATH' as const,
      InternalCandidateCount: 0,
      ExternalCandidateCount: 0
    };
    const problemTeam = team([
      slot('QB-1', 'unknown', { Repairability: irreparable })
    ]);

    expect(buildMatchupScoreboardState('final', [problemTeam])).toBe('final');
  });

  it('keeps starter count dynamic and creates no placeholder groups for absent states', () => {
    const slots = Array.from({ length: 10 }, (_, index) => slot(`WR-${index + 1}`, 'completed'));
    const view = buildMatchupStarterProgress(team(slots), 'next', 'left');

    expect(view?.slotCount).toBe(10);
    expect(view?.groups.length).toBe(1);
    expect(view?.groups[0].kind).toBe('final');
    expect(view?.groups[0].segments.length).toBe(10);
  });

  it('orders every adopted state from the left outer edge toward center and mirrors it on the right', () => {
    const repairable = {
      ProblemCode: 'OPEN_STARTER_SLOT' as const,
      State: 'repairable' as const,
      Path: 'internal-roster' as const,
      ReasonCode: 'INTERNAL_ASSIGNMENT_AVAILABLE' as const,
      InternalCandidateCount: 1,
      ExternalCandidateCount: 0
    };
    const irreparable = {
      ...repairable,
      State: 'irreparable' as const,
      Path: null,
      ReasonCode: 'NO_LEGAL_REPAIR_PATH' as const,
      InternalCandidateCount: 0
    };
    const unknown = {
      ...repairable,
      State: 'unknown' as const,
      Path: null,
      ReasonCode: 'LINEUP_EVIDENCE_UNKNOWN' as const,
      InternalCandidateCount: 0
    };
    const slots = [
      slot('QB-1', 'completed'),
      slot('RB-2', 'locked-active'),
      slot('WR-3', 'unlocked', { DecisionWindowID: 'next' }),
      slot('TE-4', 'unlocked', { DecisionWindowID: 'later' }),
      slot('FLEX-5', 'unlocked', { Repairability: repairable }),
      slot('K-6', 'unknown', { Repairability: irreparable }),
      slot('SUPER_FLEX-7', 'unknown', { Repairability: unknown })
    ];

    const left = buildMatchupStarterProgress(team(slots), 'next', 'left');
    const right = buildMatchupStarterProgress(team(slots), 'next', 'right');

    expect(left?.groups.map(group => group.kind)).toEqual([
      'irreparable', 'final', 'locked', 'next', 'future', 'repairable', 'unknown'
    ]);
    expect(right?.groups.map(group => group.kind)).toEqual([
      'unknown', 'repairable', 'future', 'next', 'locked', 'final', 'irreparable'
    ]);
    expect(left?.groups.find(group => group.kind === 'next')?.outline).toBe('next');
    expect(left?.groups.find(group => group.kind === 'repairable')?.outline).toBe('repairable');
    expect(left?.groups.find(group => group.kind === 'unknown')?.outline).toBe('unknown');
  });

  it('keeps missing lifecycle states out of the group list so styling adds only one inter-group gap', () => {
    const view = buildMatchupStarterProgress(team([
      slot('QB-1', 'completed'),
      slot('WR-2', 'unlocked', { DecisionWindowID: 'later' })
    ]), 'next', 'left');

    expect(view?.groups.map(group => group.kind)).toEqual(['final', 'future']);
  });

  it('caps the compact scoring-window preview at three games and reports informational overflow', () => {
    const oneIDs = ['g1'];
    const threeIDs = ['g1', 'g2', 'g3'];
    const fiveIDs = ['g1', 'g2', 'g3', 'g4', 'g5'];

    const one = buildMatchupScoringWindow(matchup(oneIDs), context(oneIDs.map(id => game(id))));
    const three = buildMatchupScoringWindow(matchup(threeIDs), context(threeIDs.map(id => game(id))));
    const five = buildMatchupScoringWindow(matchup(fiveIDs), context(fiveIDs.map(id => game(id))));

    expect(one?.mobileVisibleGames.map(item => item.GameID)).toEqual(oneIDs);
    expect(one?.mobileOverflowCount).toBe(0);
    expect(three?.mobileVisibleGames.map(item => item.GameID)).toEqual(threeIDs);
    expect(three?.mobileOverflowCount).toBe(0);
    expect(five?.mobileVisibleGames.map(item => item.GameID)).toEqual(threeIDs);
    expect(five?.mobileOverflowCount).toBe(2);
    expect(five?.gameCount).toBe(5);
    expect(five?.games.map(item => item.GameID)).toEqual(fiveIDs);
  });

  it('represents the whole generated scoring window and marks window-level live action once', () => {
    const ids = ['g1', 'g2', 'g3'];
    const games = ids.map(id => game(id));
    games[1].RemainingRelevance!.LockedActiveStarterCount = 1;
    const source = matchup(ids);
    source.RemainingRelevance!.NextScoringLockedActiveStarterCount = 1;

    const view = buildMatchupScoringWindow(source, context(games));

    expect(view?.gameCount).toBe(3);
    expect(view?.games.map(item => item.GameID)).toEqual(ids);
    expect(view?.isLive).toBeTrue();
    expect(view?.startsAtUtc).toBe('2026-09-13T17:00:00Z');
  });
});
