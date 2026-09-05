import type {
  DecisionWindow,
  DecisionWindowEvaluationState,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import type { League } from '../../core/models/league.models';
import {
  buildDecisionWindowStatusBadges,
  buildDecisionWindowTeamRows,
  formatDecisionWindowContext,
  formatDecisionWindowCountdown,
  getDecisionWindowAttentionState,
  getNextDecisionWindow,
  type DecisionWindowStatusBadge
} from './decision-window-view.util';

export interface LeagueTimelineDraft {
  name: string;
  statusClass: 'live' | 'upcoming' | 'completed';
  startDisplay: string | null;
}

export interface LeagueTimelineItem {
  icon: string;
  label: string;
  value: string;
  detail: string | null;
}

export interface LeagueTimelineOperationalItem extends LeagueTimelineItem {
  kind: 'lineup' | 'waiver' | 'lineup-unavailable';
  window: DecisionWindow | null;
  statusBadges: DecisionWindowStatusBadge[];
  tone: DecisionWindowEvaluationState | null;
}

export interface LeagueTimelineView {
  activeMode: boolean;
  primary: LeagueTimelineItem | null;
  secondary: LeagueTimelineItem | null;
  operational: LeagueTimelineOperationalItem[];
  milestones: LeagueTimelineItem[];
}

export interface LeagueTimelineBuildInput {
  league: League;
  drafts: LeagueTimelineDraft[];
  decisionWindows: DecisionWindowsReadModel | null;
  decisionWindowsUnavailable: boolean;
  now: Date;
}

export function buildLeagueTimelineView(input: LeagueTimelineBuildInput): LeagueTimelineView | null {
  const { league, drafts, decisionWindows, decisionWindowsUnavailable, now } = input;
  const kickoff = parseDate(league.SeasonKickoff);
  const capDeadline = parseDate(league.CapDeadline);
  const nextWaiverRun = parseDate(league.NextWaiverRun);
  const currentWeek = getCurrentWeek(league);
  const playoffItem = league.PlayoffStartWeek > currentWeek
    && league.PlayoffStartWeek <= league.LastLeagueWeek
    ? buildWeekItem('Playoffs', league.PlayoffStartWeek, '🏆')
    : null;
  const tradeDeadlineItem = league.TradeDeadlineWeek !== null
    && league.TradeDeadlineWeek <= league.LastLeagueWeek
    && league.TradeDeadlineWeek > currentWeek
    ? buildWeekItem('Trade deadline', league.TradeDeadlineWeek, '🤝')
    : null;
  const waiverItem = nextWaiverRun && nextWaiverRun.getTime() > now.getTime()
    ? buildOperationalDateItem('Next Waiver Run', nextWaiverRun, '🔄', now)
    : null;

  if (league.Status === 'In-Season' || league.Status === 'Playoffs') {
    const lineupItem = buildLineupOperationalItem(
      league,
      decisionWindows,
      decisionWindowsUnavailable,
      now
    );
    const operational = [lineupItem, waiverItem].filter(
      (item): item is LeagueTimelineOperationalItem => item !== null
    );
    const milestones = league.Status === 'Playoffs'
      ? [buildWeekItem('League final', league.LastLeagueWeek, '🏆')]
      : [tradeDeadlineItem, playoffItem].filter(
          (item): item is LeagueTimelineItem => item !== null
        );

    if (operational.length === 0 && milestones.length === 0) return null;

    return {
      activeMode: true,
      primary: null,
      secondary: null,
      operational,
      milestones
    };
  }

  if (league.Status === 'Off-Season') {
    if (capDeadline && capDeadline.getTime() > now.getTime()) {
      return buildLegacyView(
        buildDateItem(league, 'Cap deadline', capDeadline, '⏱️', now),
        getScheduledDraftItem(drafts) ?? getKickoffItem(league, kickoff, now)
      );
    }

    const scheduledDraft = getScheduledDraftItem(drafts);
    if (scheduledDraft) {
      return buildLegacyView(scheduledDraft, getKickoffItem(league, kickoff, now));
    }

    const kickoffItem = getKickoffItem(league, kickoff, now);
    return kickoffItem ? buildLegacyView(kickoffItem, null) : null;
  }

  if (league.Status === 'Draft-Season') {
    const liveDraft = getLiveDraftItem(drafts);
    if (liveDraft) return buildLegacyView(liveDraft, getKickoffItem(league, kickoff, now));

    const scheduledDraft = getScheduledDraftItem(drafts);
    if (scheduledDraft) {
      return buildLegacyView(scheduledDraft, getKickoffItem(league, kickoff, now));
    }

    const kickoffItem = getKickoffItem(league, kickoff, now);
    return kickoffItem ? buildLegacyView(kickoffItem, null) : null;
  }

  if (league.Status === 'Pre-Season') {
    const kickoffItem = getKickoffItem(league, kickoff, now);
    return kickoffItem ? buildLegacyView(kickoffItem, tradeDeadlineItem ?? playoffItem) : null;
  }

  return null;
}

function buildLineupOperationalItem(
  league: League,
  decisionWindows: DecisionWindowsReadModel | null,
  unavailable: boolean,
  now: Date
): LeagueTimelineOperationalItem | null {
  if (unavailable) {
    return {
      kind: 'lineup-unavailable',
      icon: '🏈',
      label: 'Next Lineup Lock',
      value: 'Unavailable',
      detail: 'Lineup data unavailable',
      window: null,
      statusBadges: [],
      tone: 'unknown'
    };
  }

  if (!decisionWindows) return null;
  const window = getNextDecisionWindow(decisionWindows, now);
  if (!window) return null;

  const rows = buildDecisionWindowTeamRows(decisionWindows, window, league.Teams);
  return {
    kind: 'lineup',
    icon: '🏈',
    label: 'Next Lineup Lock',
    value: formatDecisionWindowCountdown(window, now),
    detail: formatDecisionWindowContext(window),
    window,
    statusBadges: buildDecisionWindowStatusBadges(rows),
    tone: getDecisionWindowAttentionState(rows)
  };
}

function buildOperationalDateItem(
  label: string,
  date: Date,
  icon: string,
  now: Date
): LeagueTimelineOperationalItem {
  return {
    kind: 'waiver',
    icon,
    label,
    value: formatCountdown(date.getTime() - now.getTime()),
    detail: formatLocalDateTime(date),
    window: null,
    statusBadges: [],
    tone: null
  };
}

function buildLegacyView(
  primary: LeagueTimelineItem,
  secondary: LeagueTimelineItem | null
): LeagueTimelineView {
  return {
    activeMode: false,
    primary,
    secondary,
    operational: [],
    milestones: []
  };
}

function getCurrentWeek(league: League): number {
  return league.CurrentWeek
    ?? Math.min(Math.max(league.FinalScoredWeek + 1, 1), league.LastLeagueWeek);
}

function getLiveDraftItem(drafts: LeagueTimelineDraft[]): LeagueTimelineItem | null {
  const draft = drafts.find(candidate => candidate.statusClass === 'live');
  if (!draft) return null;

  return {
    icon: '🟣',
    label: draft.name,
    value: 'Live now',
    detail: 'Draft in progress'
  };
}

function getScheduledDraftItem(drafts: LeagueTimelineDraft[]): LeagueTimelineItem | null {
  const draft = drafts.find(candidate =>
    candidate.statusClass === 'upcoming'
    && !!candidate.startDisplay
    && candidate.startDisplay !== 'not scheduled'
  );
  if (!draft?.startDisplay) return null;

  return {
    icon: '📋',
    label: draft.name,
    value: draft.startDisplay,
    detail: 'Scheduled draft'
  };
}

function getKickoffItem(league: League, kickoff: Date | null, now: Date): LeagueTimelineItem | null {
  if (!kickoff || kickoff.getTime() <= now.getTime()) return null;
  return buildDateItem(league, 'Season kickoff', kickoff, '🏈', now);
}

function buildDateItem(
  league: League,
  label: string,
  date: Date,
  icon: string,
  now: Date
): LeagueTimelineItem {
  return {
    icon,
    label,
    value: formatCountdown(date.getTime() - now.getTime()),
    detail: formatDate(league, date)
  };
}

function buildWeekItem(label: string, week: number, icon: string): LeagueTimelineItem {
  return { icon, label, value: `Week ${week}`, detail: null };
}

function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T23:59:59Z` : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(league: League, date: Date): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: league.LeagueTimeZone || 'UTC'
    }).format(date);
  } catch {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'UTC'
    }).format(date);
  }
}

function formatLocalDateTime(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
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
