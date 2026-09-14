import type { DecisionWindow, DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
import { formatDecisionWindowCountdown } from './decision-window-view.util';
import { buildLeagueTimelineView } from './league-timeline-view.util';
import { buildTeamUpcomingLockViews } from './team-decision-window-view.util';

describe('shared countdown consumers', () => {
  const now = new Date('2026-09-04T10:00:00Z');

  it('uses adaptive precision and terminal semantics for Decision Windows', () => {
    const window = createWindow('2026-09-04T10:43:12Z', 1, [createAffectedTeam(1)]);

    expect(formatDecisionWindowCountdown(window, now)).toBe('43 min 12 s');
    expect(formatDecisionWindowCountdown(window, new Date('2026-09-04T10:43:12Z'))).toBe('Locked');
    expect(formatDecisionWindowCountdown(window, new Date('2026-09-04T10:43:13Z'))).toBe('Locked');
  });

  it('uses the shared formatter for League Timeline date countdowns', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ NextWaiverRun: '2026-09-04T10:43:12Z' }),
      drafts: [],
      decisionWindows: createModel([]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational.find(item => item.kind === 'waiver')?.value).toBe('43 min 12 s');
  });

  it('rolls the League Timeline to the next Decision Window instead of rendering a negative countdown', () => {
    const first = createWindow('2026-09-04T10:00:05Z', 1, [createAffectedTeam(1)]);
    const second = createWindow('2026-09-04T12:00:05Z', 1, [createAffectedTeam(1)]);
    const model = createModel([first, second]);

    const before = buildLeagueTimelineView({
      league: createLeague(),
      drafts: [],
      decisionWindows: model,
      decisionWindowsUnavailable: false,
      now: new Date('2026-09-04T10:00:00Z')
    });
    const atTarget = buildLeagueTimelineView({
      league: createLeague(),
      drafts: [],
      decisionWindows: model,
      decisionWindowsUnavailable: false,
      now: new Date('2026-09-04T10:00:05Z')
    });

    expect(before?.operational[0].window?.DecisionWindowID).toBe(first.DecisionWindowID);
    expect(before?.operational[0].value).toBe('5 s');
    expect(atTarget?.operational[0].window?.DecisionWindowID).toBe(second.DecisionWindowID);
    expect(atTarget?.operational[0].value).toBe('2 h 0 min');
  });

  it('keeps team-specific Decision Window selection semantics unchanged', () => {
    const otherTeamFirst = createWindow('2026-09-04T10:15:00Z', 1, [createAffectedTeam(2)]);
    const ownTeamLater = createWindow('2026-09-04T10:45:00Z', 1, [createAffectedTeam(1)]);
    const model = createModel([otherTeamFirst, ownTeamLater]);

    const teamOne = buildTeamUpcomingLockViews(model, 1, now);
    const teamTwo = buildTeamUpcomingLockViews(model, 2, now);

    expect(teamOne.map(item => item.window.DecisionWindowID)).toEqual([ownTeamLater.DecisionWindowID]);
    expect(teamTwo.map(item => item.window.DecisionWindowID)).toEqual([otherTeamFirst.DecisionWindowID]);
    expect(formatDecisionWindowCountdown(teamOne[0].window, now)).toBe('45 min 0 s');
  });
});

function createLeague(overrides: Partial<League> = {}): League {
  return {
    Status: 'In-Season',
    Phase: '',
    Season: '2026',
    CurrentWeek: 1,
    FinalScoredWeek: 0,
    LastLeagueWeek: 17,
    PlayoffStartWeek: 14,
    TradeDeadlineWeek: 99,
    SeasonKickoff: null,
    CapDeadline: '',
    LeagueTimeZone: 'UTC',
    NextWaiverRun: null,
    Teams: [createTeam(1), createTeam(2)],
    ...overrides
  } as League;
}

function createModel(windows: DecisionWindow[]): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: windows,
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: [
      createEvaluation(1),
      createEvaluation(2)
    ]
  };
}

function createWindow(
  startsAtUtc: string,
  week: number,
  affectedFantasyTeams: DecisionWindow['AffectedFantasyTeams']
): DecisionWindow {
  return {
    DecisionWindowID: startsAtUtc,
    Week: week,
    StartsAtUtc: startsAtUtc,
    Games: [{
      GameID: `game-${startsAtUtc}`,
      Week: week,
      AwayTeamID: '22',
      AwayTeamAbbr: 'NE',
      HomeTeamID: '29',
      HomeTeamAbbr: 'SEA'
    }],
    ParticipatingNFLTeamIDs: ['22', '29'],
    FantasyContextState: 'available',
    AffectedFantasyTeams: affectedFantasyTeams
  };
}

function createAffectedTeam(teamId: number): DecisionWindow['AffectedFantasyTeams'][number] {
  return {
    FantasyTeamID: teamId,
    AffectedRosteredPlayerCount: 1,
    AffectedStarterCount: 1,
    Players: [{
      PlayerID: `player-${teamId}`,
      NFLTeamID: '22',
      GameID: 'game',
      IsStarter: true
    }]
  };
}

function createEvaluation(teamId: number): DecisionWindowsReadModel['TeamLineupEvaluations'][number] {
  return {
    FantasyTeamID: teamId,
    State: 'ready',
    ExpectedStarterCount: 13,
    StarterCount: 13,
    OpenStarterSlots: 0,
    Issues: []
  };
}

function createTeam(teamId: number): FantasyTeam {
  return {
    TeamID: teamId,
    Team: `Team ${teamId}`,
    Owner: `Owner ${teamId}`,
    OwnerAvatar: '',
    Avatar: ''
  } as FantasyTeam;
}
