import type { DraftPick, Player, RawDraft } from '../../../core/models/fantasy.models';

export interface DraftPickOwnerDisplay {
  id: number;
  name: string;
  abbr: string;
  avatar: string;
}

export interface DraftPickContext {
  draft: RawDraft;
  pick?: DraftPick;
  label: string;
  currentOwner?: DraftPickOwnerDisplay;
  originalOwner?: DraftPickOwnerDisplay;
  selectedPlayer?: Player;
  selectedPlayerName?: string;
  isTradedPick: boolean;
  roundColor?: string;
}
