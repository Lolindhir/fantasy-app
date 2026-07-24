import type {
  Transaction,
  TransactionDraftPick
} from '../../core/models/transaction.models';

export type MovesFilter = 'all' | 'trade' | 'waiver' | 'roster';

export interface MovesFilterOption {
  Id: MovesFilter;
  Label: string;
  Icon: string;
  Count: number;
}

export interface MovesDateGroup {
  DateKey: string;
  DateLabel: string;
  Transactions: Transaction[];
}

export interface MovesViewModel {
  SeasonLabel: string;
  SelectedFilter: MovesFilter;
  TotalCount: number;
  VisibleCount: number;
  TradeCount: number;
  RosterMoveCount: number;
  PlayerMoveCount: number;
  DraftPickCount: number;
  CutCount: number;
  WaiverAddCount: number;
  Filters: MovesFilterOption[];
  Groups: MovesDateGroup[];
}

export function buildMovesViewModel(
  transactions: Transaction[],
  selectedFilter: MovesFilter = 'all'
): MovesViewModel {
  const normalizedTransactions = [...(transactions ?? [])].sort(
    (left, right) => right.CreatedAt - left.CreatedAt
  );
  const tradeCount = normalizedTransactions.filter(transaction => transaction.Type === 'trade').length;
  const waiverCount = normalizedTransactions.filter(transaction => transaction.Type === 'waiver').length;
  const rosterMoveCount = normalizedTransactions.filter(isRosterMove).length;
  const filteredTransactions = normalizedTransactions.filter(transaction =>
    matchesFilter(transaction, selectedFilter)
  );
  const groupsByDate = new Map<string, Transaction[]>();

  for (const transaction of filteredTransactions) {
    const dateKey = transaction.CreatedDate || 'Unknown date';
    const group = groupsByDate.get(dateKey) ?? [];
    group.push(transaction);
    groupsByDate.set(dateKey, group);
  }

  return {
    SeasonLabel: normalizedTransactions[0]?.Season || 'Current',
    SelectedFilter: selectedFilter,
    TotalCount: normalizedTransactions.length,
    VisibleCount: filteredTransactions.length,
    TradeCount: tradeCount,
    RosterMoveCount: rosterMoveCount,
    PlayerMoveCount: normalizedTransactions.reduce(
      (sum, transaction) => sum + countDistinctPlayerMoves(transaction),
      0
    ),
    DraftPickCount: normalizedTransactions.reduce(
      (sum, transaction) => sum + transaction.DraftPicks.length,
      0
    ),
    CutCount: normalizedTransactions.reduce((sum, transaction) => {
      return transaction.Type === 'trade'
        ? sum
        : sum + countDroppedPlayers(transaction);
    }, 0),
    WaiverAddCount: normalizedTransactions.reduce((sum, transaction) => {
      return transaction.Type === 'waiver'
        ? sum + countAddedPlayers(transaction)
        : sum;
    }, 0),
    Filters: [
      {
        Id: 'all',
        Label: 'All moves',
        Icon: 'dynamic_feed',
        Count: normalizedTransactions.length
      },
      {
        Id: 'trade',
        Label: 'Trades',
        Icon: 'swap_horiz',
        Count: tradeCount
      },
      {
        Id: 'waiver',
        Label: 'Waivers',
        Icon: 'playlist_add_check',
        Count: waiverCount
      },
      {
        Id: 'roster',
        Label: 'Adds & cuts',
        Icon: 'group_add',
        Count: rosterMoveCount
      }
    ],
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
      return 'Free agent move';
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

export function getIncomingAssetLabel(type: string): string {
  return type === 'trade' ? 'Receives' : 'Added';
}

export function getOutgoingAssetLabel(type: string): string {
  return type === 'trade' ? 'Sends' : 'Dropped';
}

export function getIncomingAssetIcon(type: string): string {
  return type === 'trade' ? 'call_received' : 'add';
}

export function getOutgoingAssetIcon(type: string): string {
  return type === 'trade' ? 'call_made' : 'remove';
}

export function getDraftPickLabel(pick: TransactionDraftPick): string {
  const pickLabel = getDraftPickAssetLabel(pick);
  return `${pickLabel} (${getDraftPickOriginalOwnerShortLabel(pick)})`;
}

export function getDraftPickAssetLabel(pick: TransactionDraftPick): string {
  const pickReference = pick.DisplayPick || formatRound(pick.Round);
  const playerName = pick.Player?.Name || pick.PlayerName;
  const playerSuffix = playerName ? ` · ${playerName}` : '';

  return `${pick.Season} ${formatDraftType(pick.DraftType)} ${pickReference}${playerSuffix}`;
}

export function getDraftPickOriginalOwnerLabel(pick: TransactionDraftPick): string {
  return pick.OriginalOwner?.Team
    || pick.OriginalOwner?.Owner
    || `Team ${pick.OriginalOwnerRosterID}`;
}

export function getDraftPickTrackKey(pick: TransactionDraftPick): string {
  return pick.PickKey || [
    pick.DraftKey,
    `R${pick.Round}`,
    `OO${pick.OriginalOwnerRosterID}`,
    `PO${pick.PreviousOwnerRosterID}`,
    `NO${pick.NewOwnerRosterID}`
  ].join('_');
}

function matchesFilter(transaction: Transaction, filter: MovesFilter): boolean {
  switch (filter) {
    case 'trade':
      return transaction.Type === 'trade';
    case 'waiver':
      return transaction.Type === 'waiver';
    case 'roster':
      return isRosterMove(transaction);
    default:
      return true;
  }
}

function isRosterMove(transaction: Transaction): boolean {
  return transaction.Type !== 'trade' && transaction.Type !== 'waiver';
}

function countAddedPlayers(transaction: Transaction): number {
  return transaction.Participants.reduce(
    (sum, participant) => sum + participant.AddedPlayers.length,
    0
  );
}

function countDroppedPlayers(transaction: Transaction): number {
  return transaction.Participants.reduce(
    (sum, participant) => sum + participant.DroppedPlayers.length,
    0
  );
}

function countDistinctPlayerMoves(transaction: Transaction): number {
  const playerIDs = new Set<string>();

  for (const participant of transaction.Participants) {
    for (const player of participant.AddedPlayers) {
      playerIDs.add(player.PlayerID);
    }

    for (const player of participant.DroppedPlayers) {
      playerIDs.add(player.PlayerID);
    }
  }

  return playerIDs.size;
}

function getDraftPickOriginalOwnerShortLabel(pick: TransactionDraftPick): string {
  return pick.OriginalOwner?.TeamAbbr
    || pick.OriginalOwner?.Team
    || pick.OriginalOwner?.Owner
    || `T${pick.OriginalOwnerRosterID}`;
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
