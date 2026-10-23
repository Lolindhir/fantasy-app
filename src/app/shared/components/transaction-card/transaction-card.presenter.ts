import { sizedPlayerPicture } from '../../utils/player-picture.util';
import type {
  TransactionDraftPick,
  TransactionParticipant,
  TransactionPlayerAsset
} from '../../../core/models/transaction.models';
import type { Player } from '../../../core/models/player.models';
import type { RawDraft } from '../../../core/models/draft.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import type { DraftPickContext, DraftPickOwnerDisplay } from '../draft-pick-context/draft-pick-context.models';
import { getDraftRoundColor } from '../../utils/draft-ui.util';

export type TransactionDisplayDensity = 'mini' | 'compact' | 'detail';
export type TransactionDisplayCategory = 'trade' | 'add' | 'cut' | 'other';
export type TransactionAssetDirection = 'incoming' | 'outgoing';

/** A trade is one indivisible exchange: never conceal received assets in the Moves feed. */
export function getTransactionPreviewLimit(
  category: TransactionDisplayCategory,
  density: TransactionDisplayDensity,
  expanded: boolean
): number {
  if (category === 'trade' || density === 'detail' || expanded) {
    return Number.POSITIVE_INFINITY;
  }
  return density === 'mini' ? 1 : 3;
}

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
  pick?: TransactionDraftPick;
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
  const historical = asset.PlayerRef;
  // Historical facts win over today's player snapshot. Never infer past NFL team.
  return {
    kind: 'player',
    key: `player:${asset.PlayerID}`,
    label: historical ? (historical.Name || `Player ${asset.PlayerID}`) : (player?.Name || `Player ${asset.PlayerID}`),
    secondary: [historical ? historical.Position : player?.Position, historical ? null : player?.TeamNFL?.Abv].filter(Boolean).join(' · '),
    portrait: sizedPlayerPicture(historical ? historical.Picture : player?.Picture) ?? undefined,
    nflTeamLogo: historical ? undefined : player?.TeamNFL?.Logo,
    nflTeamAbv: historical ? undefined : player?.TeamNFL?.Abv,
    position: historical ? historical.Position ?? undefined : player?.Position,
    // Current snapshots carry no temporal identity proof. Do not open the
    // wrong current Player when a historical provider ID has been reused.
    player: historical ? undefined : player
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
  return {
    kind: 'pick',
    key: pick.PickKey || [pick.DraftKey ?? '', pick.Season, pick.Round, pick.OriginalOwnerRosterID, pick.PreviousOwnerRosterID, pick.NewOwnerRosterID].join(':'),
    label: `${pick.Season} ${type} · ${pickReference}`,
    secondary: '',
    originalOwner,
    pick,
    pickRound: pick.Round
  };
}

/**
 * Resolve a trade asset to the real draft read model. A round alone is not a
 * reliable pick identity; ambiguous and missing matches must remain inert.
 */
export function buildTransactionPickContext(
  asset: TransactionCardAsset,
  drafts: readonly RawDraft[],
  teams: readonly FantasyTeam[]
): DraftPickContext | null {
  const transactionPick = asset.pick;
  if (!transactionPick || asset.kind !== 'pick') return null;

  const candidates = drafts
    .filter(draft => transactionPick.DraftKey
      ? draft.DraftKey === transactionPick.DraftKey
      : draft.Season === transactionPick.Season
        && draft.DraftType.toLowerCase() === (transactionPick.DraftType ?? '').toLowerCase())
    .flatMap(draft => draft.Picks
      .filter(pick => {
        if (transactionPick.PickKey) return pick.PickKey === transactionPick.PickKey;
        return pick.Round === transactionPick.Round
          && Number(pick.OriginalOwnerRosterID) === Number(transactionPick.OriginalOwnerRosterID)
          && (!transactionPick.DisplayPick || pick.DisplayPick === transactionPick.DisplayPick);
      })
      .map(pick => ({ draft, pick })));

  if (candidates.length !== 1) return null;

  const { draft, pick } = candidates[0];
  const owner = (rosterId: number): DraftPickOwnerDisplay => {
    const team = teams.find(candidate => Number(candidate.TeamID) === Number(rosterId));
    const name = team?.Team || (team?.Owner ? `Team ${team.Owner}` : `Roster ${rosterId}`);
    return {
      id: Number(rosterId),
      name,
      abbr: team?.TeamAbbr || name,
      avatar: team?.Avatar || 'assets/default-team-avatar.png'
    };
  };

  return {
    draft,
    pick,
    label: pick.DisplayPick || `R${pick.Round}`,
    currentOwner: owner(pick.CurrentOwnerRosterID),
    originalOwner: owner(pick.OriginalOwnerRosterID),
    selectedPlayer: transactionPick.Player?.ID === pick.PlayerID ? transactionPick.Player : undefined,
    selectedPlayerName: pick.PlayerName || undefined,
    isTradedPick: (pick.TradeHistory?.length ?? 0) > 0,
    roundColor: getDraftRoundColor(pick.Round, draft.Settings?.Rounds)
  };
}
