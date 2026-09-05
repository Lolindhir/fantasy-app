import type {
  DecisionWindow,
  DecisionWindowEvaluationState,
  DecisionWindowIssue,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import type { FantasyTeam } from '../../core/models/league.models';

const ATTENTION_ORDER: Record<DecisionWindowEvaluationState, number> = {
  'action-required': 0,
  review: 1,
  unknown: 2,
  pending: 3,
  ready: 4
};

export interface DecisionWindowTeamRowView {
  teamId: number;
  displayName: string;
  avatar: string | null;
  fallback: string;
  state: DecisionWindowEvaluationState;
  statusLabel: string;
  affectedRosteredPlayerCount: number | null;
  affectedStarterCount: number | null;
  contextText: string;
  issueTexts: string[];
  stableOrder: number;
}

export interface DecisionWindowStatusBadge {
  state: DecisionWindowEvaluationState;
  count: number;
  label: string;
  compactLabel: string;
  showCount: boolean;
}

export function getNextDecisionWindow(
  model: DecisionWindowsReadModel,
  now: Date
): DecisionWindow | null {
  const nowMs = now.getTime();
  const candidates = [
    ...model.DecisionWindows,
    ...(model.LookaheadDecisionWindow ? [model.LookaheadDecisionWindow] : [])
  ];

  return candidates
    .map(window => ({ window, startsAt: parseTimestamp(window.StartsAtUtc) }))
    .filter(candidate => candidate.startsAt !== null && candidate.startsAt.getTime() > nowMs)
    .sort((a, b) => {
      const byTime = a.startsAt!.getTime() - b.startsAt!.getTime();
      if (byTime !== 0) return byTime;
      return a.window.DecisionWindowID.localeCompare(b.window.DecisionWindowID);
    })[0]?.window ?? null;
}

export function buildDecisionWindowTeamRows(
  model: DecisionWindowsReadModel,
  window: DecisionWindow,
  teams: FantasyTeam[]
): DecisionWindowTeamRowView[] {
  const affectedByTeam = new Map(
    window.AffectedFantasyTeams.map(affected => [affected.FantasyTeamID, affected])
  );
  const evaluationByTeam = new Map(
    model.TeamLineupEvaluations.map(evaluation => [evaluation.FantasyTeamID, evaluation])
  );
  const pending = window.FantasyContextState === 'pending';

  return teams
    .map((team, stableOrder): DecisionWindowTeamRowView => {
      const displayName = getTeamDisplayName(team);
      const affected = pending ? undefined : affectedByTeam.get(team.TeamID);
      const evaluation = pending ? undefined : evaluationByTeam.get(team.TeamID);
      const state: DecisionWindowEvaluationState = pending
        ? 'pending'
        : evaluation?.State ?? 'unknown';
      const issueTexts = pending
        ? []
        : evaluation
          ? Array.from(new Set(evaluation.Issues.map(formatDecisionWindowIssue)))
          : ['Lineup status unavailable'];

      return {
        teamId: team.TeamID,
        displayName,
        avatar: team.Avatar || team.OwnerAvatar || null,
        fallback: getTeamFallback(displayName),
        state,
        statusLabel: getDecisionWindowStatusLabel(state),
        affectedRosteredPlayerCount: pending ? null : affected?.AffectedRosteredPlayerCount ?? 0,
        affectedStarterCount: pending ? null : affected?.AffectedStarterCount ?? 0,
        contextText: pending
          ? `Week ${window.Week} lineup not available yet`
          : formatAffectedContext(
              affected?.AffectedRosteredPlayerCount ?? 0,
              affected?.AffectedStarterCount ?? 0
            ),
        issueTexts,
        stableOrder
      };
    })
    .sort((a, b) => {
      const byAttention = ATTENTION_ORDER[a.state] - ATTENTION_ORDER[b.state];
      if (byAttention !== 0) return byAttention;
      const byStableOrder = a.stableOrder - b.stableOrder;
      if (byStableOrder !== 0) return byStableOrder;
      return a.displayName.localeCompare(b.displayName);
    });
}

export function buildDecisionWindowStatusBadges(
  rows: DecisionWindowTeamRowView[]
): DecisionWindowStatusBadge[] {
  const counts = new Map<DecisionWindowEvaluationState, number>();
  for (const row of rows) {
    counts.set(row.state, (counts.get(row.state) ?? 0) + 1);
  }

  const nonReadyStates: DecisionWindowEvaluationState[] = [
    'action-required',
    'review',
    'unknown',
    'pending'
  ];
  const nonReady = nonReadyStates
    .map(state => createStatusBadge(state, counts.get(state) ?? 0, true))
    .filter(badge => badge.count > 0);

  if (nonReady.length > 0) return nonReady;

  const readyCount = counts.get('ready') ?? 0;
  if (readyCount > 0) return [createStatusBadge('ready', readyCount, false)];

  return [createStatusBadge('unknown', 0, false)];
}

export function getDecisionWindowAttentionState(
  rows: DecisionWindowTeamRowView[]
): DecisionWindowEvaluationState {
  if (rows.length === 0) return 'unknown';

  return [...rows]
    .sort((a, b) => ATTENTION_ORDER[a.state] - ATTENTION_ORDER[b.state])[0].state;
}

export function formatDecisionWindowContext(window: DecisionWindow): string {
  if (window.Games.length === 1) {
    return `${formatDecisionWindowGame(window.Games[0])} · Week ${window.Week}`;
  }

  const startsAt = parseTimestamp(window.StartsAtUtc);
  const localTime = startsAt
    ? new Intl.DateTimeFormat(undefined, {
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }).format(startsAt)
    : 'Kickoff';

  return `${localTime} · ${window.Games.length} games · Week ${window.Week}`;
}

export function formatDecisionWindowGame(
  game: DecisionWindow['Games'][number]
): string {
  const away = game.AwayTeamAbbr || game.AwayTeamID;
  const home = game.HomeTeamAbbr || game.HomeTeamID;
  return `${away} @ ${home}`;
}

export function formatDecisionWindowLocalDateTime(window: DecisionWindow): string {
  const startsAt = parseTimestamp(window.StartsAtUtc);
  if (!startsAt) return 'Lock time unavailable';

  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short'
  }).format(startsAt);
}

export function formatDecisionWindowCountdown(window: DecisionWindow, now: Date): string {
  const startsAt = parseTimestamp(window.StartsAtUtc);
  if (!startsAt) return 'Lock time unavailable';

  const msLeft = startsAt.getTime() - now.getTime();
  if (msLeft <= 0) return 'Locked';
  return formatCountdown(msLeft);
}

export function formatDecisionWindowsUpdatedAt(
  updatedAt: string | null | undefined,
  now: Date
): string | null {
  if (!updatedAt) return null;
  const updated = parseTimestamp(updatedAt);
  if (!updated) return null;

  const diffMs = now.getTime() - updated.getTime();
  if (diffMs >= 0) {
    const minuteMs = 60_000;
    const hourMs = 60 * minuteMs;
    const dayMs = 24 * hourMs;

    if (diffMs < minuteMs) return 'Updated just now';
    if (diffMs < hourMs) {
      const minutes = Math.floor(diffMs / minuteMs);
      return `Updated ${minutes} min ago`;
    }
    if (diffMs < dayMs) {
      const hours = Math.floor(diffMs / hourMs);
      return `Updated ${hours} h ago`;
    }
    if (diffMs < 7 * dayMs) {
      const days = Math.floor(diffMs / dayMs);
      return `Updated ${days} ${days === 1 ? 'day' : 'days'} ago`;
    }
  }

  return `Updated ${new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(updated)}`;
}

export function getDecisionWindowStatusLabel(state: DecisionWindowEvaluationState): string {
  switch (state) {
    case 'action-required':
      return 'Action required';
    case 'review':
      return 'Review';
    case 'unknown':
      return 'Unknown';
    case 'pending':
      return 'Pending';
    case 'ready':
      return 'Ready';
  }
}

export function formatDecisionWindowIssue(issue: DecisionWindowIssue): string {
  switch (issue.Code) {
    case 'OPEN_STARTER_SLOT': {
      const count = issue.Count ?? 1;
      return `${count} starter ${count === 1 ? 'slot' : 'slots'} empty`;
    }
    case 'STARTER_ON_BYE':
      return 'Starter on bye';
    case 'STARTER_WITHOUT_NFL_TEAM':
      return 'Starter without NFL team';
    case 'STARTER_LOCK_UNKNOWN':
      return 'Starter lock status unknown';
    case 'UNRESOLVED_ROSTER_PLAYER':
      return 'Roster player lock status unknown';
    case 'MALFORMED_ROSTER_STRUCTURE':
      return 'Roster data unavailable';
    case 'MALFORMED_STARTER_STRUCTURE':
      return 'Starter data unavailable';
    case 'MALFORMED_ROSTER_PLAYER':
      return 'Roster player data invalid';
    case 'MALFORMED_STARTER_PLAYER':
      return 'Starter player data invalid';
    case 'DUPLICATE_ROSTER_PLAYER':
      return 'Duplicate roster player data';
    case 'DUPLICATE_STARTER':
      return 'Duplicate starter data';
    case 'STARTER_NOT_IN_ROSTER':
      return 'Starter not found on roster';
    case 'STARTER_COUNT_OVERFLOW':
      return 'Starter count is inconsistent';
    default:
      return 'Lineup data needs review';
  }
}

function createStatusBadge(
  state: DecisionWindowEvaluationState,
  count: number,
  showCount: boolean
): DecisionWindowStatusBadge {
  const compactLabels: Record<DecisionWindowEvaluationState, string> = {
    'action-required': 'Action',
    review: 'Review',
    unknown: 'Unknown',
    pending: 'Pending',
    ready: 'Ready'
  };

  return {
    state,
    count,
    label: getDecisionWindowStatusLabel(state),
    compactLabel: compactLabels[state],
    showCount
  };
}

function formatAffectedContext(rosteredCount: number, starterCount: number): string {
  if (rosteredCount === 0) return 'No players in this window';

  return `${rosteredCount} ${rosteredCount === 1 ? 'player' : 'players'} · ${starterCount} ${starterCount === 1 ? 'starter' : 'starters'}`;
}

function getTeamDisplayName(team: FantasyTeam): string {
  const teamName = team.Team?.trim();
  return teamName || team.Owner;
}

function getTeamFallback(displayName: string): string {
  const normalized = displayName.trim();
  return normalized ? normalized.slice(0, 1).toUpperCase() : '?';
}

function parseTimestamp(value: string): Date | null {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatCountdown(msLeft: number): string {
  const minuteMs = 60_000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;

  if (msLeft >= dayMs) {
    const totalHours = Math.floor(msLeft / hourMs);
    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;
    return days < 4
      ? `${days} ${days === 1 ? 'day' : 'days'} ${hours} h`
      : `${days} ${days === 1 ? 'day' : 'days'}`;
  }

  const totalMinutes = Math.max(1, Math.floor(msLeft / minuteMs));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes} min`;
  if (minutes === 0) return `${hours} h`;
  return `${hours} h ${minutes} min`;
}
