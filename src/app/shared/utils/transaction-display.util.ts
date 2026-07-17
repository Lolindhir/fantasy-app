import type { FantasyTeam } from '../../core/models/league.models';
import type { TransactionDraftPick } from '../../core/models/transaction.models';

export function getTransactionTypeLabel(type: string): string {
  switch (type) {
    case 'trade':
      return 'Trade';
    case 'waiver':
      return 'Waiver';
    case 'free_agent':
      return 'Free Agency';
    case 'commissioner':
      return 'Commissioner';
    default:
      return toTitleCase(type);
  }
}

export function getTransactionTypeIcon(type: string): string {
  switch (type) {
    case 'trade':
      return 'swap_horiz';
    case 'waiver':
      return 'playlist_add_check';
    case 'free_agent':
      return 'person_add';
    case 'commissioner':
      return 'admin_panel_settings';
    default:
      return 'sync_alt';
  }
}

export function getTransactionTypeClass(type: string): string {
  return type.replace(/[^a-z0-9_-]/gi, '-').toLowerCase();
}

export function getDraftPickTitle(pick: TransactionDraftPick): string {
  return `${pick.Season} ${formatDraftType(pick.DraftType)}`;
}

export function getDraftPickRoundOrdinal(pick: TransactionDraftPick): string {
  return formatRound(pick.Round);
}

export function getDraftPickExactLabel(pick: TransactionDraftPick): string | null {
  return pick.ResolvedDraftPick?.DisplayPick || null;
}

export function getDraftPickDisplayLabel(pick: TransactionDraftPick): string {
  const exactLabel = getDraftPickExactLabel(pick);
  const roundLabel = exactLabel
    ? `${getDraftPickRoundOrdinal(pick)} round, pick ${exactLabel}`
    : `${getDraftPickRoundOrdinal(pick)} round`;

  return `${getDraftPickTitle(pick)} ${roundLabel}, original owner ${getDraftPickOriginalOwnerLabel(pick)}`;
}

export function getDraftPickOriginalOwnerLabel(pick: TransactionDraftPick): string {
  return getFantasyTeamName(pick.OriginalOwner, pick.OriginalOwnerRosterID);
}

export function getDraftPickOriginalOwnerShortLabel(pick: TransactionDraftPick): string {
  return getFantasyTeamAbbr(pick.OriginalOwner, pick.OriginalOwnerRosterID);
}

export function getDraftPickTrackKey(pick: TransactionDraftPick): string {
  return [
    pick.DraftKey,
    `R${pick.Round}`,
    `OO${pick.OriginalOwnerRosterID}`,
    `PO${pick.PreviousOwnerRosterID}`,
    `NO${pick.NewOwnerRosterID}`
  ].join('_');
}

export function getFantasyTeamName(team: FantasyTeam | undefined, rosterID?: number): string {
  return team?.Team
    || team?.TeamAbbr
    || (rosterID !== undefined ? `Team ${rosterID}` : 'Unknown team');
}

export function getFantasyTeamAbbr(team: FantasyTeam | undefined, rosterID?: number): string {
  return team?.TeamAbbr
    || abbreviateTeamName(team?.Team)
    || (rosterID !== undefined ? `T${rosterID}` : 'TEAM');
}

function abbreviateTeamName(teamName: string | null | undefined): string | null {
  if (!teamName) {
    return null;
  }

  const words = teamName.trim().split(/\s+/).filter(Boolean);

  if (words.length > 1) {
    return words.map(word => word[0]).join('').slice(0, 4).toUpperCase();
  }

  return teamName.slice(0, 4).toUpperCase();
}

function formatDraftType(draftType: string): string {
  const normalized = draftType.toLowerCase();

  if (normalized === 'free_agent') {
    return 'Free Agent';
  }

  return toTitleCase(draftType.replace(/_/g, ' '));
}

function formatRound(round: number): string {
  const remainder100 = round % 100;

  if (remainder100 >= 11 && remainder100 <= 13) {
    return `${round}th`;
  }

  switch (round % 10) {
    case 1:
      return `${round}st`;
    case 2:
      return `${round}nd`;
    case 3:
      return `${round}rd`;
    default:
      return `${round}th`;
  }
}

function toTitleCase(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, character => character.toUpperCase());
}
