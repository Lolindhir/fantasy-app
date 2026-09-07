import type {
  DecisionWindow,
  DecisionWindowAffectedPlayer,
  DecisionWindowEvaluationState,
  DecisionWindowGame,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import {
  formatDecisionWindowIssue,
  getDecisionWindowStatusLabel
} from './decision-window-view.util';

export interface TeamDecisionWindowNflTeamGroupView {
  nflTeamId: string | null;
  teamAbbr: string;
  affectedPlayers: DecisionWindowAffectedPlayer[];
  affectedStarterCount: number;
}

export interface TeamDecisionWindowGameView {
  game: DecisionWindowGame;
  affectedPlayers: DecisionWindowAffectedPlayer[];
  affectedStarterCount: number;
  teamGroups: TeamDecisionWindowNflTeamGroupView[];
}

export interface TeamUpcomingLockView {
  window: DecisionWindow;
  affectedRosteredPlayerCount: number;
  affectedStarterCount: number;
  timeLabel: string;
  games: TeamDecisionWindowGameView[];
  unmatchedAffectedPlayerCount: number;
}

export interface TeamLineupWeekSummaryView {
  windowCount: number;
  gameCount: number;
  affectedRosteredPlayerCount: number;
  affectedStarterCount: number;
  nextWindow: TeamUpcomingLockView | null;
  windowDateLabels: string[];
}

export interface TeamLineupHealthView {
  state: DecisionWindowEvaluationState;
  statusLabel: string;
  issueTexts: string[];
}

export function isTeamDecisionWindowActiveStatus(status: string): boolean {
  return status === 'In-Season' || status === 'Playoffs';
}

export function buildTeamUpcomingLockViews(
  model: DecisionWindowsReadModel,
  fantasyTeamId: number,
  now: Date
): TeamUpcomingLockView[] {
  const nowMs = now.getTime();

  return model.DecisionWindows
    .filter(window => window.Week === model.LineupWeek && window.FantasyContextState === 'available')
    .map(window => {
      const startsAt = parseTimestamp(window.StartsAtUtc);
      const affected = window.AffectedFantasyTeams.find(
        candidate => candidate.FantasyTeamID === fantasyTeamId
      );
      return { window, startsAt, affected };
    })
    .filter(candidate =>
      candidate.startsAt !== null
      && candidate.startsAt.getTime() > nowMs
      && !!candidate.affected
      && candidate.affected.AffectedRosteredPlayerCount > 0
    )
    .sort((a, b) =>
      a.startsAt!.getTime() - b.startsAt!.getTime()
      || a.window.DecisionWindowID.localeCompare(b.window.DecisionWindowID)
    )
    .map(candidate => {
      const affected = candidate.affected!;
      const affectedPlayersByGameId = new Map<string, DecisionWindowAffectedPlayer[]>();

      affected.Players.forEach(player => {
        const players = affectedPlayersByGameId.get(player.GameID) ?? [];
        players.push(player);
        affectedPlayersByGameId.set(player.GameID, players);
      });

      const windowGameIds = new Set(candidate.window.Games.map(game => game.GameID));
      const games = candidate.window.Games
        .map(game => {
          const affectedPlayers = sortAffectedPlayers(affectedPlayersByGameId.get(game.GameID) ?? []);

          return {
            game,
            affectedPlayers,
            affectedStarterCount: affectedPlayers.filter(player => player.IsStarter).length,
            teamGroups: buildTeamGameGroups(game, affectedPlayers)
          } satisfies TeamDecisionWindowGameView;
        })
        .filter(game => game.affectedPlayers.length > 0);

      return {
        window: candidate.window,
        affectedRosteredPlayerCount: affected.AffectedRosteredPlayerCount,
        affectedStarterCount: affected.AffectedStarterCount,
        timeLabel: formatDecisionWindowShortLocalTime(candidate.window),
        games,
        unmatchedAffectedPlayerCount: affected.Players.filter(player => !windowGameIds.has(player.GameID)).length
      } satisfies TeamUpcomingLockView;
    });
}

export function buildTeamLineupWeekSummary(
  windows: TeamUpcomingLockView[]
): TeamLineupWeekSummaryView {
  return {
    windowCount: windows.length,
    gameCount: windows.reduce((sum, window) => sum + window.games.length, 0),
    affectedRosteredPlayerCount: windows.reduce(
      (sum, window) => sum + window.affectedRosteredPlayerCount,
      0
    ),
    affectedStarterCount: windows.reduce(
      (sum, window) => sum + window.affectedStarterCount,
      0
    ),
    nextWindow: windows[0] ?? null,
    windowDateLabels: windows.map(window => formatDecisionWindowCompactLocalDateTime(window.window))
  };
}

export function buildTeamLineupHealthView(
  model: DecisionWindowsReadModel,
  fantasyTeamId: number
): TeamLineupHealthView {
  const evaluation = model.TeamLineupEvaluations.find(
    candidate => candidate.FantasyTeamID === fantasyTeamId
  );

  if (!evaluation) {
    return {
      state: 'unknown',
      statusLabel: getDecisionWindowStatusLabel('unknown'),
      issueTexts: ['Lineup data unavailable']
    };
  }

  return {
    state: evaluation.State,
    statusLabel: getDecisionWindowStatusLabel(evaluation.State),
    issueTexts: Array.from(new Set(evaluation.Issues.map(formatDecisionWindowIssue)))
  };
}

export function getPendingTeamLookaheadMessage(
  model: DecisionWindowsReadModel,
  currentWeekLocks: TeamUpcomingLockView[],
  now: Date
): string | null {
  if (currentWeekLocks.length > 0) return null;

  const lookahead = model.LookaheadDecisionWindow;
  if (!lookahead || lookahead.FantasyContextState !== 'pending') return null;
  if (lookahead.Week <= model.LineupWeek) return null;

  const startsAt = parseTimestamp(lookahead.StartsAtUtc);
  if (!startsAt || startsAt.getTime() <= now.getTime()) return null;

  return `Week ${lookahead.Week} lineup not available yet`;
}

export function formatDecisionWindowShortLocalTime(window: DecisionWindow): string {
  const startsAt = parseTimestamp(window.StartsAtUtc);
  if (!startsAt) return 'Unknown';

  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit'
  }).format(startsAt).replace(',', '');
}

export function formatDecisionWindowCompactLocalDateTime(window: DecisionWindow): string {
  const startsAt = parseTimestamp(window.StartsAtUtc);
  if (!startsAt) return 'Unknown';

  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  }).format(startsAt).replace(',', '');
}

export function formatTeamAffectedCounts(lock: TeamUpcomingLockView): string {
  const players = `${lock.affectedRosteredPlayerCount} ${lock.affectedRosteredPlayerCount === 1 ? 'player' : 'players'}`;
  const starters = `${lock.affectedStarterCount} ${lock.affectedStarterCount === 1 ? 'starter' : 'starters'}`;
  return `${players} · ${starters}`;
}

function buildTeamGameGroups(
  game: DecisionWindowGame,
  affectedPlayers: DecisionWindowAffectedPlayer[]
): TeamDecisionWindowNflTeamGroupView[] {
  const byTeam = new Map<string, DecisionWindowAffectedPlayer[]>();
  affectedPlayers.forEach(player => {
    const key = player.NFLTeamID ?? '';
    const players = byTeam.get(key) ?? [];
    players.push(player);
    byTeam.set(key, players);
  });

  const primaryTeamIds = [game.AwayTeamID, game.HomeTeamID];
  const extraTeamIds = [...byTeam.keys()]
    .filter(teamId => !primaryTeamIds.includes(teamId))
    .sort((a, b) => a.localeCompare(b));

  return [...primaryTeamIds, ...extraTeamIds]
    .filter((teamId, index, all) => all.indexOf(teamId) === index)
    .map(teamId => {
      const players = sortAffectedPlayers(byTeam.get(teamId) ?? []);
      const teamAbbr = teamId === game.AwayTeamID
        ? game.AwayTeamAbbr || game.AwayTeamID
        : teamId === game.HomeTeamID
          ? game.HomeTeamAbbr || game.HomeTeamID
          : teamId || 'Unknown';

      return {
        nflTeamId: teamId || null,
        teamAbbr,
        affectedPlayers: players,
        affectedStarterCount: players.filter(player => player.IsStarter).length
      } satisfies TeamDecisionWindowNflTeamGroupView;
    })
    .filter(group => group.affectedPlayers.length > 0);
}

function sortAffectedPlayers(players: DecisionWindowAffectedPlayer[]): DecisionWindowAffectedPlayer[] {
  return [...players].sort((a, b) =>
    Number(b.IsStarter) - Number(a.IsStarter)
    || a.PlayerID.localeCompare(b.PlayerID)
  );
}

function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
