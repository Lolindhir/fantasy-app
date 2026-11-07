import type { FantasyTeam, Player } from '../../core/models/fantasy.models';
import { compareRosterNextLock, formatRosterNextLockValue, type RosterNextLockContext } from './team-roster-view.util';

/**
 * Injury statuses as reported by the provider (Players.json InjuryDetails.Designation). Only
 * statuses present in the data are shown; a missing or unrecognized designation stays Unknown.
 */
export type InjuryKind = 'out' | 'ir' | 'pup' | 'doubtful' | 'questionable' | 'unknown';
export type InjuryPlacement = 'active' | 'taxi' | 'ir';

export interface InjuryReportRow {
  player: Player;
  kind: InjuryKind;
  label: string;
  description: string;
  placement: InjuryPlacement;
  isStarter: boolean;
  /** Next lock of a starter this week ("Locked", a kickoff time, "Bye"); null for non-starters or without lock data. */
  lockLabel: string | null;
}

/** Lineup view: most urgent first (a starter who is Out matters more than a Questionable one). */
const SEVERITY: Record<InjuryKind, number> = {
  out: 0, ir: 1, pup: 2, doubtful: 3, questionable: 4, unknown: 5
};

/**
 * Roster view: the long-term cases sit at the bottom, the short-term uncertainty on top
 * (Unknown, Questionable, Doubtful, Out, PUP, IR).
 */
const ROSTER_RANK: Record<InjuryKind, number> = {
  unknown: 0, questionable: 1, doubtful: 2, out: 3, pup: 4, ir: 5
};

/** A player counts as injured when the data flags an injury (not merely roster-inactive). */
export function isPlayerInjured(player: Player): boolean {
  return player.Injured === true;
}

export function injuryKind(player: Player): InjuryKind {
  switch ((player.InjuryDetails?.Designation ?? '').trim().toLowerCase()) {
    case 'out': return 'out';
    case 'ir': return 'ir';
    case 'pup': return 'pup';
    case 'doubtful': return 'doubtful';
    case 'questionable': return 'questionable';
    default: return 'unknown';
  }
}

export function injuryLabel(kind: InjuryKind): string {
  switch (kind) {
    case 'out': return 'Out';
    case 'ir': return 'IR';
    case 'pup': return 'PUP';
    case 'doubtful': return 'Doubtful';
    case 'questionable': return 'Questionable';
    case 'unknown': return 'Unknown';
  }
}

export type InjuryReportMode = 'roster' | 'lineup';

export interface InjuryReportOptions {
  /**
   * roster: the whole roster, ordered by designation (starter/bench is irrelevant there).
   * lineup: only starters of the current lineup week, ordered by next lock, then severity.
   */
  mode?: InjuryReportMode;
  /** Starter IDs of the current lineup week; required for the lineup mode. */
  starterIds?: ReadonlySet<string> | null;
  lockContext?: RosterNextLockContext;
}

export function buildTeamInjuryReport(team: FantasyTeam, options: InjuryReportOptions = {}): InjuryReportRow[] {
  const mode = options.mode ?? 'roster';
  const taxiIds = new Set(team.Taxi.map(player => player.ID));
  const irIds = new Set(team.Reserve.map(player => player.ID));
  const starterIds = options.starterIds ?? null;

  const rows = team.Roster
    .filter(isPlayerInjured)
    .filter(player => mode === 'roster' || (starterIds?.has(player.ID) ?? false))
    .map(player => {
      const kind = injuryKind(player);
      const isStarter = starterIds?.has(player.ID) ?? false;
      return {
        player,
        kind,
        label: injuryLabel(kind),
        description: (player.InjuryDetails?.Description ?? '').trim(),
        placement: irIds.has(player.ID) ? 'ir' : taxiIds.has(player.ID) ? 'taxi' : 'active',
        isStarter,
        lockLabel: mode === 'lineup' && isStarter && options.lockContext
          ? formatRosterNextLockValue(player, options.lockContext)
          : null
      } satisfies InjuryReportRow;
    });

  const byName = (a: InjuryReportRow, b: InjuryReportRow): number =>
    a.player.Name.localeCompare(b.player.Name, 'en', { sensitivity: 'base' })
    || a.player.ID.localeCompare(b.player.ID);

  if (mode === 'lineup') {
    const byLock = options.lockContext ? compareRosterNextLock(options.lockContext) : null;
    return rows.sort((a, b) =>
      (byLock ? byLock(a.player, b.player) : 0) || SEVERITY[a.kind] - SEVERITY[b.kind] || byName(a, b));
  }
  return rows.sort((a, b) => ROSTER_RANK[a.kind] - ROSTER_RANK[b.kind] || byName(a, b));
}
