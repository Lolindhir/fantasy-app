import type { DecisionWindow, DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import {
  buildTeamLineupHealthView,
  buildTeamLineupWeekSummary,
  buildTeamUpcomingLockViews,
  getPendingTeamLookaheadMessage,
  isTeamDecisionWindowActiveStatus
} from './team-decision-window-view.util';

describe('team Decision Window view utilities', () => {
  const now = new Date('2026-09-06T16:00:00Z');

  it('enables Team Detail lineup context only for active lineup phases', () => {
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

  it('builds a team-specific week summary whose next window ignores irrelevant global windows', () => {
    const irrelevantSooner = makeWindow('other-team', 1, '2026-09-06T17:00:00Z', 3, 2, 7);
    const firstRelevant = makeWindow('first-relevant', 1, '2026-09-06T18:00:00Z', 2, 1, 42);
    const secondRelevant = makeWindow('second-relevant', 1, '2026-09-06T20:00:00Z', 3, 2, 42);
    secondRelevant.Games.push(makeGame('second-relevant-extra', 1, 'KC', 'LAC'));
    secondRelevant.AffectedFantasyTeams[0].Players.push({
      PlayerID: 'extra',
      NFLTeamID: 'KC',
      GameID: 'second-relevant-extra',
      IsStarter: false
    });
    secondRelevant.AffectedFantasyTeams[0].AffectedRosteredPlayerCount = 4;

    const windows = buildTeamUpcomingLockViews(
      makeModel([irrelevantSooner, firstRelevant, secondRelevant]),
      42,
      now
    );
    const summary = buildTeamLineupWeekSummary(windows);

    expect(summary.nextWindow?.window.DecisionWindowID).toBe('first-relevant');
    expect(summary.windowCount).toBe(2);
    expect(summary.gameCount).toBe(3);
    expect(summary.affectedRosteredPlayerCount).toBe(6);
    expect(summary.affectedStarterCount).toBe(3);
    expect(summary.windowDateLabels.length).toBe(2);
  });

  it('moves the team-specific next window forward when the prior relevant window has locked', () => {
    const first = makeWindow('first', 1, '2026-09-06T18:00:00Z', 2, 1, 42);
    const second = makeWindow('second', 1, '2026-09-06T20:00:00Z', 3, 2, 42);
    const afterFirst = new Date('2026-09-06T18:01:00Z');

    const summary = buildTeamLineupWeekSummary(
      buildTeamUpcomingLockViews(makeModel([first, second]), 42, afterFirst)
    );

    expect(summary.nextWindow?.window.DecisionWindowID).toBe('second');
  });

  it('orders selected-team affected players by home team first and starter status second', () => {
    const window = makeWindow('multi', 1, '2026-09-06T18:00:00Z', 0, 0, 42);
    window.Games = [
      makeGame('g1', 1, 'NE', 'SEA'),
      makeGame('g2', 1, 'KC', 'LAC'),
      makeGame('g3', 1, 'DAL', 'PHI')
    ];
    window.ParticipatingNFLTeamIDs = ['NE', 'SEA', 'KC', 'LAC', 'DAL', 'PHI'];
    window.AffectedFantasyTeams = [{
      FantasyTeamID: 42,
      AffectedRosteredPlayerCount: 6,
      AffectedStarterCount: 3,
      Players: [
        { PlayerID: 'ne-bench', NFLTeamID: 'NE', GameID: 'g1', IsStarter: false },
        { PlayerID: 'sea-bench', NFLTeamID: 'SEA', GameID: 'g1', IsStarter: false },
        { PlayerID: 'ne-starter', NFLTeamID: 'NE', GameID: 'g1', IsStarter: true },
        { PlayerID: 'kc-bench', NFLTeamID: 'KC', GameID: 'g2', IsStarter: false },
        { PlayerID: 'lac-starter', NFLTeamID: 'LAC', GameID: 'g2', IsStarter: true },
        { PlayerID: 'unmatched', NFLTeamID: 'BUF', GameID: 'missing-game', IsStarter: true }
      ]
    }];

    const [row] = buildTeamUpcomingLockViews(makeModel([window]), 42, now);

    expect(row.games.map(game => game.game.GameID)).toEqual(['g1', 'g2']);
    expect(row.games[0].teamGroups.map(group => group.nflTeamId)).toEqual(['SEA', 'NE']);
    expect(row.games[0].teamGroups[0].affectedPlayers.map(player => player.PlayerID)).toEqual([
      'sea-bench'
    ]);
    expect(row.games[0].teamGroups[1].affectedPlayers.map(player => player.PlayerID)).toEqual([
      'ne-starter',
      'ne-bench'
    ]);
    expect(row.games[0].teamGroups[1].affectedStarterCount).toBe(1);
    expect(row.games[1].teamGroups.map(group => group.nflTeamId)).toEqual(['LAC', 'KC']);
    expect(row.games[1].teamGroups[0].affectedStarterCount).toBe(1);
    expect(row.unmatchedAffectedPlayerCount).toBe(1);
  });

  it('sorts games inside a window by affected-player count descending and preserves generated order on ties', () => {
    const window = makeWindow('relevance', 1, '2026-09-06T18:00:00Z', 0, 0, 42);
    window.Games = [
      makeGame('g1', 1, 'NE', 'SEA'),
      makeGame('g2', 1, 'KC', 'LAC'),
      makeGame('g3', 1, 'DAL', 'PHI')
    ];
    window.ParticipatingNFLTeamIDs = ['NE', 'SEA', 'KC', 'LAC', 'DAL', 'PHI'];
    window.AffectedFantasyTeams = [{
      FantasyTeamID: 42,
      AffectedRosteredPlayerCount: 8,
      AffectedStarterCount: 4,
      Players: [
        { PlayerID: 'g1-a', NFLTeamID: 'NE', GameID: 'g1', IsStarter: true },
        { PlayerID: 'g1-b', NFLTeamID: 'SEA', GameID: 'g1', IsStarter: false },
        { PlayerID: 'g2-a', NFLTeamID: 'KC', GameID: 'g2', IsStarter: false },
        { PlayerID: 'g2-b', NFLTeamID: 'KC', GameID: 'g2', IsStarter: false },
        { PlayerID: 'g2-c', NFLTeamID: 'LAC', GameID: 'g2', IsStarter: false },
        { PlayerID: 'g3-a', NFLTeamID: 'DAL', GameID: 'g3', IsStarter: true },
        { PlayerID: 'g3-b', NFLTeamID: 'DAL', GameID: 'g3', IsStarter: true },
        { PlayerID: 'g3-c', NFLTeamID: 'PHI', GameID: 'g3', IsStarter: true }
      ]
    }];

    const [row] = buildTeamUpcomingLockViews(makeModel([window]), 42, now);

    expect(row.games.map(game => game.game.GameID)).toEqual(['g2', 'g3', 'g1']);
    expect(row.games.map(game => game.affectedPlayers.length)).toEqual([3, 3, 2]);
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

  it('shows pending next-week copy only after current-week team windows are exhausted', () => {
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
    Games: [makeGame(`${id}-game`, week, 'NE', 'SEA')],
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

function makeGame(id: string, week: number, away: string, home: string) {
  return {
    GameID: id,
    Week: week,
    AwayTeamID: away,
    AwayTeamAbbr: away,
    HomeTeamID: home,
    HomeTeamAbbr: home
  };
}
