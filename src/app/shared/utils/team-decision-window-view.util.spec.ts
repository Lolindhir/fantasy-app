import type { DecisionWindow, DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import {
  buildTeamLineupHealthView,
  buildTeamUpcomingLockViews,
  getPendingTeamLookaheadMessage,
  isTeamDecisionWindowActiveStatus
} from './team-decision-window-view.util';

describe('team Decision Window view utilities', () => {
  const now = new Date('2026-09-06T16:00:00Z');

  it('enables Team Detail locks only for active lineup phases', () => {
    expect(isTeamDecisionWindowActiveStatus('In-Season')).toBeTrue();
    expect(isTeamDecisionWindowActiveStatus('Playoffs')).toBeTrue();
    expect(isTeamDecisionWindowActiveStatus('Off-Season')).toBeFalse();
    expect(isTeamDecisionWindowActiveStatus('Draft-Season')).toBeFalse();
    expect(isTeamDecisionWindowActiveStatus('Pre-Season')).toBeFalse();
  });

  it('returns only future current-week windows relevant to the selected team in chronological order', () => {
    const relevantLater = makeWindow('later', 1, '2026-09-06T20:00:00Z', 7, 4, 42);
    const irrelevantTeam = makeWindow('other-team', 1, '2026-09-06T17:00:00Z', 3, 2, 7);
    const relevantEarlier = makeWindow('earlier', 1, '2026-09-06T18:00:00Z', 2, 1, 42);
    const alreadyLocked = makeWindow('locked', 1, '2026-09-06T15:00:00Z', 1, 1, 42);
    const nextWeek = makeWindow('next-week', 2, '2026-09-13T17:00:00Z', 2, 1, 42);
    const model = makeModel([relevantLater, irrelevantTeam, relevantEarlier, alreadyLocked, nextWeek]);

    const rows = buildTeamUpcomingLockViews(model, 42, now);

    expect(rows.map(row => row.window.DecisionWindowID)).toEqual(['earlier', 'later']);
    expect(rows[0].affectedRosteredPlayerCount).toBe(2);
    expect(rows[0].affectedStarterCount).toBe(1);
    expect(rows[1].affectedRosteredPlayerCount).toBe(7);
    expect(rows[1].affectedStarterCount).toBe(4);
  });

  it('does not include a global window when this team has zero affected players', () => {
    const zero = makeWindow('zero', 1, '2026-09-06T18:00:00Z', 0, 0, 42);
    expect(buildTeamUpcomingLockViews(makeModel([zero]), 42, now)).toEqual([]);
  });

  it('uses the generated team lineup evaluation and existing objective issue copy', () => {
    const model = makeModel([]);
    model.TeamLineupEvaluations = [{
      FantasyTeamID: 42,
      State: 'action-required',
      ExpectedStarterCount: 13,
      StarterCount: 12,
      OpenStarterSlots: 1,
      Issues: [{ Code: 'OPEN_STARTER_SLOT', State: 'action-required', PlayerID: null, Count: 1 }]
    }];

    const health = buildTeamLineupHealthView(model, 42);

    expect(health.state).toBe('action-required');
    expect(health.statusLabel).toBe('Action required');
    expect(health.issueTexts).toContain('1 starter slot empty');
  });

  it('treats missing team evaluation as neutral technical uncertainty rather than ready', () => {
    const health = buildTeamLineupHealthView(makeModel([]), 42);
    expect(health.state).toBe('unknown');
    expect(health.issueTexts).toEqual(['Lineup data unavailable']);
  });

  it('shows pending next-week copy only after current-week team locks are exhausted', () => {
    const model = makeModel([]);
    model.LookaheadDecisionWindow = {
      ...makeWindow('lookahead', 2, '2026-09-13T17:00:00Z', 99, 99, 7),
      FantasyContextState: 'pending'
    };

    expect(getPendingTeamLookaheadMessage(model, [], now)).toBe('Week 2 lineup not available yet');

    const currentRows = buildTeamUpcomingLockViews(
      makeModel([makeWindow('current', 1, '2026-09-06T18:00:00Z', 1, 1, 42)]),
      42,
      now
    );
    expect(getPendingTeamLookaheadMessage(model, currentRows, now)).toBeNull();
  });

  it('never turns pending lookahead associations from another team into Team Detail rows', () => {
    const model = makeModel([]);
    model.LookaheadDecisionWindow = {
      ...makeWindow('lookahead', 2, '2026-09-13T17:00:00Z', 5, 3, 7),
      FantasyContextState: 'pending'
    };

    expect(buildTeamUpcomingLockViews(model, 42, now)).toEqual([]);
    expect(getPendingTeamLookaheadMessage(model, [], now)).toBe('Week 2 lineup not available yet');
  });
});

function makeModel(windows: DecisionWindow[]): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: windows,
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: []
  };
}

function makeWindow(
  id: string,
  week: number,
  startsAtUtc: string,
  players: number,
  starters: number,
  fantasyTeamId: number
): DecisionWindow {
  return {
    DecisionWindowID: id,
    Week: week,
    StartsAtUtc: startsAtUtc,
    Games: [{
      GameID: `${id}-game`,
      Week: week,
      AwayTeamID: 'NE',
      AwayTeamAbbr: 'NE',
      HomeTeamID: 'SEA',
      HomeTeamAbbr: 'SEA'
    }],
    ParticipatingNFLTeamIDs: ['NE', 'SEA'],
    FantasyContextState: 'available',
    AffectedFantasyTeams: [{
      FantasyTeamID: fantasyTeamId,
      AffectedRosteredPlayerCount: players,
      AffectedStarterCount: starters,
      Players: Array.from({ length: players }, (_, index) => ({
        PlayerID: `p-${index}`,
        NFLTeamID: 'NE',
        GameID: `${id}-game`,
        IsStarter: index < starters
      }))
    }]
  };
}
