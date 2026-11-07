import type { FantasyTeam, Player } from '../../core/models/fantasy.models';
import { formatRosterNextLockValue, type RosterNextLockContext } from './team-roster-view.util';

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

const SEVERITY: Record<InjuryKind, number> = {
  out: 0, ir: 1, pup: 2, doubtful: 3, questionable: 4, unknown: 5
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

export interface InjuryReportOptions {
  /** Starter IDs of the current lineup week; omit outside the lineup phase (stale starters are not meaningful). */
  starterIds?: ReadonlySet<string> | null;
  lockContext?: RosterNextLockContext;
}

export function buildTeamInjuryReport(team: FantasyTeam, options: InjuryReportOptions = {}): InjuryReportRow[] {
  const taxiIds = new Set(team.Taxi.map(player => player.ID));
  const irIds = new Set(team.Reserve.map(player => player.ID));
  const starterIds = options.starterIds ?? null;

  return team.Roster
    .filter(isPlayerInjured)
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
        lockLabel: isStarter && options.lockContext
          ? formatRosterNextLockValue(player, options.lockContext)
          : null
      } satisfies InjuryReportRow;
    })
    .sort((a, b) =>
      Number(b.isStarter) - Number(a.isStarter)
      || SEVERITY[a.kind] - SEVERITY[b.kind]
      || a.player.Name.localeCompare(b.player.Name, 'en', { sensitivity: 'base' })
      || a.player.ID.localeCompare(b.player.ID)
    );
}
