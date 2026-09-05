import type {
  DecisionWindow,
  DecisionWindowTeamLineupEvaluation,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import type { FantasyTeam } from '../../core/models/league.models';
import {
  buildDecisionWindowStatusBadges,
  buildDecisionWindowTeamRows,
  formatDecisionWindowContext,
  formatDecisionWindowIssue,
  formatDecisionWindowsUpdatedAt,
  getDecisionWindowStatusLabel,
  getNextDecisionWindow
} from './decision-window-view.util';

describe('decision-window-view util', () => {
  const teams = [
    createTeam(1, 'Alpha'),
    createTeam(2, 'Bravo'),
    createTeam(3, 'Charlie'),
    createTeam(4, 'Delta'),
    createTeam(5, 'Echo')
  ];

  it('rolls to the next exact Decision Window at kickoff', () => {
    const first = createWindow('2026-09-06T17:00:00Z', 1);
    const second = createWindow('2026-09-06T20:05:00Z', 1);
    const model = createModel([first, second]);

    expect(getNextDecisionWindow(model, new Date('2026-09-06T16:59:59Z'))?.DecisionWindowID)
      .toBe(first.DecisionWindowID);
    expect(getNextDecisionWindow(model, new Date('2026-09-06T17:00:00Z'))?.DecisionWindowID)
      .toBe(second.DecisionWindowID);
  });

  it('promotes the pending lookahead after current-week windows are exhausted', () => {
    const current = createWindow('2026-09-06T17:00:00Z', 1);
    const lookahead = createWindow('2026-09-11T00:15:00Z', 2, { FantasyContextState: 'pending' });
    const model = createModel([current], [], lookahead);

    const next = getNextDecisionWindow(model, new Date('2026-09-06T17:00:00Z'));

    expect(next?.DecisionWindowID).toBe(lookahead.DecisionWindowID);
    expect(next?.FantasyContextState).toBe('pending');
  });

  it('keeps nearby unequal kickoffs as distinct source windows', () => {
    const early = createWindow('2026-09-06T20:05:00Z', 1);
    const late = createWindow('2026-09-06T20:25:00Z', 1);
    const model = createModel([early, late]);

    expect(getNextDecisionWindow(model, new Date('2026-09-06T20:00:00Z'))?.DecisionWindowID)
      .toBe(early.DecisionWindowID);
    expect(getNextDecisionWindow(model, new Date('2026-09-06T20:05:00Z'))?.DecisionWindowID)
      .toBe(late.DecisionWindowID);
  });

  it('uses a standalone matchup label without schedule taxonomy', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1, {
      Games: [createGame('g1', 'NE', 'SEA')]
    });

    expect(formatDecisionWindowContext(window)).toBe('NE @ SEA · Week 1');
  });

  it('uses local kickoff time and game count for simultaneous games', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1, {
      Games: [createGame('g1', 'ATL', 'PIT'), createGame('g2', 'BAL', 'IND')]
    });

    const label = formatDecisionWindowContext(window);

    expect(label).toContain('2 games · Week 1');
    expect(label).not.toContain('Sunday Early');
  });

  it('renders every League team and gives zero-affected teams explicit context', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1, {
      AffectedFantasyTeams: [{
        FantasyTeamID: 1,
        AffectedRosteredPlayerCount: 3,
        AffectedStarterCount: 2,
        Players: []
      }]
    });
    const model = createModel([window], teams.map(team => createEvaluation(team.TeamID, 'ready')));

    const rows = buildDecisionWindowTeamRows(model, window, teams);

    expect(rows.length).toBe(teams.length);
    expect(rows.find(row => row.teamId === 1)?.contextText).toBe('3 players · 2 starters');
    expect(rows.find(row => row.teamId === 2)?.contextText).toBe('No players in this window');
  });

  it('sorts commissioner rows by semantic attention and stable team order', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1);
    const model = createModel([window], [
      createEvaluation(1, 'ready'),
      createEvaluation(2, 'unknown'),
      createEvaluation(3, 'review'),
      createEvaluation(4, 'action-required'),
      createEvaluation(5, 'ready')
    ]);

    const rows = buildDecisionWindowTeamRows(model, window, teams);

    expect(rows.map(row => row.teamId)).toEqual([4, 3, 2, 1, 5]);
  });

  it('marks every team pending for lookahead without fabricated counts', () => {
    const lookahead = createWindow('2026-09-11T00:15:00Z', 2, {
      FantasyContextState: 'pending',
      AffectedFantasyTeams: []
    });
    const model = createModel([], teams.map(team => createEvaluation(team.TeamID, 'action-required')), lookahead);

    const rows = buildDecisionWindowTeamRows(model, lookahead, teams);

    expect(rows.every(row => row.state === 'pending')).toBeTrue();
    expect(rows.every(row => row.affectedRosteredPlayerCount === null)).toBeTrue();
    expect(rows.every(row => row.affectedStarterCount === null)).toBeTrue();
    expect(rows.every(row => row.contextText === 'Week 2 lineup not available yet')).toBeTrue();
  });

  it('counts fantasy teams rather than issue objects in compact status', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1);
    const evaluations = [
      createEvaluation(1, 'action-required', [
        { Code: 'OPEN_STARTER_SLOT', State: 'action-required', PlayerID: null, Count: 1 },
        { Code: 'STARTER_ON_BYE', State: 'action-required', PlayerID: 'p1', Count: null }
      ]),
      createEvaluation(2, 'review'),
      createEvaluation(3, 'unknown'),
      createEvaluation(4, 'ready'),
      createEvaluation(5, 'ready')
    ];
    const rows = buildDecisionWindowTeamRows(createModel([window], evaluations), window, teams);
    const badges = buildDecisionWindowStatusBadges(rows);

    expect(badges.find(badge => badge.state === 'action-required')?.count).toBe(1);
    expect(badges.find(badge => badge.state === 'review')?.count).toBe(1);
    expect(badges.find(badge => badge.state === 'unknown')?.count).toBe(1);
  });

  it('keeps affected players as context when generated evaluation is ready', () => {
    const window = createWindow('2026-09-06T17:00:00Z', 1, {
      AffectedFantasyTeams: [{
        FantasyTeamID: 1,
        AffectedRosteredPlayerCount: 4,
        AffectedStarterCount: 0,
        Players: []
      }]
    });
    const model = createModel([window], teams.map(team => createEvaluation(team.TeamID, 'ready')));
    const rows = buildDecisionWindowTeamRows(model, window, teams);
    const badges = buildDecisionWindowStatusBadges(rows);

    expect(rows.find(row => row.teamId === 1)?.state).toBe('ready');
    expect(badges).toEqual([jasmine.objectContaining({ state: 'ready', showCount: false })]);
  });

  it('projects all semantic status labels without turning uncertainty into ready', () => {
    expect(getDecisionWindowStatusLabel('action-required')).toBe('Action required');
    expect(getDecisionWindowStatusLabel('review')).toBe('Review');
    expect(getDecisionWindowStatusLabel('unknown')).toBe('Unknown');
    expect(getDecisionWindowStatusLabel('pending')).toBe('Pending');
    expect(getDecisionWindowStatusLabel('ready')).toBe('Ready');
  });

  it('formats objective issue text and semantic Updated freshness', () => {
    expect(formatDecisionWindowIssue({
      Code: 'OPEN_STARTER_SLOT',
      State: 'action-required',
      PlayerID: null,
      Count: 2
    })).toBe('2 starter slots empty');

    expect(formatDecisionWindowsUpdatedAt(
      '2026-09-05T09:48:00Z',
      new Date('2026-09-05T10:00:00Z')
    )).toBe('Updated 12 min ago');
    expect(formatDecisionWindowsUpdatedAt(undefined, new Date('2026-09-05T10:00:00Z'))).toBeNull();
  });
});

function createModel(
  windows: DecisionWindow[],
  evaluations: DecisionWindowTeamLineupEvaluation[] = [],
  lookahead: DecisionWindow | null = null
): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: windows,
    LookaheadDecisionWindow: lookahead,
    PlayerLockFacts: [],
    TeamLineupEvaluations: evaluations
  };
}

function createWindow(
  startsAtUtc: string,
  week: number,
  overrides: Partial<DecisionWindow> = {}
): DecisionWindow {
  return {
    DecisionWindowID: startsAtUtc,
    Week: week,
    StartsAtUtc: startsAtUtc,
    Games: [createGame('g1', 'NE', 'SEA')],
    ParticipatingNFLTeamIDs: ['NE', 'SEA'],
    FantasyContextState: 'available',
    AffectedFantasyTeams: [],
    ...overrides
  };
}

function createGame(gameId: string, away: string, home: string): DecisionWindow['Games'][number] {
  return {
    GameID: gameId,
    Week: 1,
    AwayTeamID: away,
    AwayTeamAbbr: away,
    HomeTeamID: home,
    HomeTeamAbbr: home
  };
}

function createEvaluation(
  teamId: number,
  state: DecisionWindowTeamLineupEvaluation['State'],
  issues: DecisionWindowTeamLineupEvaluation['Issues'] = []
): DecisionWindowTeamLineupEvaluation {
  return {
    FantasyTeamID: teamId,
    State: state,
    ExpectedStarterCount: 13,
    StarterCount: 13,
    OpenStarterSlots: 0,
    Issues: issues
  };
}

function createTeam(teamId: number, name: string): FantasyTeam {
  return {
    TeamID: teamId,
    Team: name,
    Owner: `${name} Owner`,
    OwnerAvatar: '',
    Avatar: ''
  } as FantasyTeam;
}
