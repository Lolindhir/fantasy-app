import type { DraftPick, RawDraft } from '../../../core/models/fantasy.models';

export type TeamDisplayViewModel = {
  id: number;
  name: string;
  avatar: string;
};

export interface DraftPickViewModel {
  pick: DraftPick;
  currentOwner: TeamDisplayViewModel;
  originalOwner: TeamDisplayViewModel;
  isCurrentlyTraded: boolean;
  roundColor: string;
}

export interface DraftRoundViewModel {
  round: number;
  label: string;
  picks: DraftPickViewModel[];
}

export interface CompactRoundPickViewModel {
  label: string;
  color: string;
}

export interface CompactOwnerPickGroupViewModel {
  owner: TeamDisplayViewModel;
  picks: CompactRoundPickViewModel[];
  pickCount: number;
  roundCounts: number[];
}

export interface DraftViewModel {
  draft: RawDraft;
  statusLabel: string;
  statusClass: string;
  pickCount: number;
  tradedPickCount: number;
  pickedCount: number;
  rounds: DraftRoundViewModel[];
  ownerPickGroups: CompactOwnerPickGroupViewModel[];
}

export interface DraftsViewModel {
  currentSeason: string;
  currentSeasonDrafts: DraftViewModel[];
  futureDrafts: DraftViewModel[];
  draftCount: number;
  tradedPickCount: number;
  pickCount: number;
  pickedCount: number;
}
