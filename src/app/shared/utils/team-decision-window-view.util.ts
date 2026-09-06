import type {
  DecisionWindow,
  DecisionWindowEvaluationState,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import {
  formatDecisionWindowIssue,
  getDecisionWindowStatusLabel
} from './decision-window-view.util';

export interface TeamUpcomingLockView {
  window: DecisionWindow;
  affectedRosteredPlayerCount: number;
  affectedStarterCount: number;
  timeLabel: string;
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
    .map(candidate => ({
      window: candidate.window,
      affectedRosteredPlayerCount: candidate.affected!.AffectedRosteredPlayerCount,
      affectedStarterCount: candidate.affected!.AffectedStarterCount,
      timeLabel: formatDecisionWindowShortLocalTime(candidate.window)
    }));
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

export function formatTeamAffectedCounts(lock: TeamUpcomingLockView): string {
  const players = `${lock.affectedRosteredPlayerCount} ${lock.affectedRosteredPlayerCount === 1 ? 'player' : 'players'}`;
  const starters = `${lock.affectedStarterCount} ${lock.affectedStarterCount === 1 ? 'starter' : 'starters'}`;
  return `${players} · ${starters}`;
}

function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
