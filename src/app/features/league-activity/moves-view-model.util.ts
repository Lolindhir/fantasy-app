import type {
  Transaction,
  TransactionDraftPick
} from '../../core/models/transaction.models';

export interface MovesDateGroup {
  DateKey: string;
  DateLabel: string;
  Transactions: Transaction[];
}

export interface MovesViewModel {
  TotalCount: number;
  TradeCount: number;
  AddedPlayerCount: number;
  TradedPickCount: number;
  Groups: MovesDateGroup[];
}

export function buildMovesViewModel(transactions: Transaction[]): MovesViewModel {
  const normalizedTransactions = transactions ?? [];
  const groupsByDate = new Map<string, Transaction[]>();

  for (const transaction of normalizedTransactions) {
    const dateKey = transaction.CreatedDate || 'Unknown date';
    const group = groupsByDate.get(dateKey) ?? [];
    group.push(transaction);
    groupsByDate.set(dateKey, group);
  }

  return {
    TotalCount: normalizedTransactions.length,
    TradeCount: normalizedTransactions.filter(transaction => transaction.Type === 'trade').length,
    AddedPlayerCount: normalizedTransactions.reduce((sum, transaction) => {
      return sum + transaction.Participants.reduce(
        (participantSum, participant) => participantSum + participant.AddedPlayers.length,
        0
      );
    }, 0),
    TradedPickCount: normalizedTransactions.reduce(
      (sum, transaction) => sum + transaction.DraftPicks.length,
      0
    ),
    Groups: Array.from(groupsByDate.entries()).map(([dateKey, groupedTransactions]) => ({
      DateKey: dateKey,
      DateLabel: formatDateLabel(dateKey),
      Transactions: groupedTransactions
    }))
  };
}

export function getMoveTypeLabel(type: string): string {
  switch (type) {
    case 'trade':
      return 'Trade';
    case 'waiver':
      return 'Waiver move';
    case 'free_agent':
      return 'Roster move';
    case 'commissioner':
      return 'Commissioner move';
    default:
      return toTitleCase(type);
  }
}

export function getMoveTypeIcon(type: string): string {
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

export function getDraftPickLabel(pick: TransactionDraftPick): string {
  return `${pick.Season} ${formatDraftType(pick.DraftType)} ${formatRound(pick.Round)}`;
}

function formatDateLabel(dateKey: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
    return dateKey;
  }

  const date = new Date(`${dateKey}T12:00:00Z`);
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC'
  }).format(date);
}

function formatDraftType(draftType: string): string {
  const normalized = draftType.toLowerCase();

  if (normalized === 'free_agent') {
    return 'FA';
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
