import type {
  TransactionDraftPick,
  TransactionParticipant,
  TransactionPlayerAsset
} from '../../../core/models/transaction.models';
import type { Player } from '../../../core/models/player.models';

export type TransactionDisplayDensity = 'mini' | 'compact' | 'detail';
export type TransactionDisplayCategory = 'trade' | 'add' | 'cut' | 'other';
export type TransactionAssetDirection = 'incoming' | 'outgoing';

export interface TransactionCardAsset {
  kind: 'player' | 'pick';
  key: string;
  label: string;
  secondary: string;
  portrait?: string;
  nflTeamLogo?: string;
  nflTeamAbv?: string;
  position?: string;
  player?: Player;
  pickRound?: number;
  originalOwner?: string;
}

export function getTransactionCardAssets(
  participant: TransactionParticipant,
  direction: TransactionAssetDirection
): TransactionCardAsset[] {
  const playerAssets = direction === 'incoming'
    ? participant.AddedPlayers
    : participant.DroppedPlayers;
  const pickAssets = direction === 'incoming'
    ? participant.AcquiredDraftPicks
    : participant.SentDraftPicks;

  return [
    ...playerAssets.map(asset => presentPlayerAsset(asset)),
    ...pickAssets.map(pick => presentDraftPick(pick))
  ];
}

function presentPlayerAsset(asset: TransactionPlayerAsset): TransactionCardAsset {
  const player = asset.Player;
  return {
    kind: 'player',
    key: `player:${asset.PlayerID}`,
    label: player?.Name || `Player ${asset.PlayerID}`,
    secondary: [player?.Position, player?.TeamNFL?.Abv].filter(Boolean).join(' · '),
    portrait: player?.Picture,
    nflTeamLogo: player?.TeamNFL?.Logo,
    nflTeamAbv: player?.TeamNFL?.Abv,
    position: player?.Position,
    player
  };
}

function presentDraftPick(pick: TransactionDraftPick): TransactionCardAsset {
  const type = pick.DraftType
    ? (pick.DraftType.toLowerCase() === 'free_agent' ? 'FA' : pick.DraftType.replace(/_/g, ' '))
    : 'Draft';
  const originalOwner = pick.OriginalOwner?.Team
    || pick.OriginalOwner?.Owner
    || `Team ${pick.OriginalOwnerRosterID}`;
  const pickReference = pick.DisplayPick || `R${pick.Round}`;
  const playerSuffix = pick.Player?.Name || pick.PlayerName;
  return {
    kind: 'pick',
    key: pick.PickKey || [pick.DraftKey ?? '', pick.Season, pick.Round, pick.OriginalOwnerRosterID, pick.PreviousOwnerRosterID, pick.NewOwnerRosterID].join(':'),
    label: `${pick.Season} ${type} · ${pickReference}`,
    secondary: playerSuffix || `Original: ${originalOwner}`,
    originalOwner,
    pickRound: pick.Round
  };
}
