import type { FantasyTeam } from './league.models';
import type { Player } from './player.models';
import type { HistoricalPlayerRef } from './draft.models';

export type TransactionPlayerRosterMap = Record<string, number | string>;

export interface RawTransactionDraftPick {
  DraftType: string | null;
  DraftKey: string | null;
  Season: string;
  Round: number;
  PickKey?: string | null;
  DisplayPick?: string | null;
  PlayerID?: string | null;
  PlayerName?: string | null;
  PlayerRef?: HistoricalPlayerRef;
  OriginalOwnerRosterID: number | string;
  PreviousOwnerRosterID: number | string;
  NewOwnerRosterID: number | string;
}

export interface RawTransaction {
  Source: string;
  TransactionID: string;
  Type: string;
  Status: string;
  Season: string;
  Week: number;
  CreatedAt: number; // Submission provenance, not the effective league event time.
  CreatedDate: string;
  EffectiveAt?: number; // Shared Derived v2; optional when reading pre-migration app files.
  RosterIDs: Array<number | string>;
  Adds: TransactionPlayerRosterMap | null;
  Drops: TransactionPlayerRosterMap | null;
  PlayerRefs?: Record<string, HistoricalPlayerRef>;
  DraftPicks: RawTransactionDraftPick[] | null;
  Notes: string | null;
}

export interface TransactionPlayerAsset {
  PlayerID: string;
  Player?: Player;
  PlayerRef?: HistoricalPlayerRef;
}

export interface TransactionDraftPick extends RawTransactionDraftPick {
  OriginalOwnerRosterID: number;
  PreviousOwnerRosterID: number;
  NewOwnerRosterID: number;
  OriginalOwner?: FantasyTeam;
  PreviousOwner?: FantasyTeam;
  NewOwner?: FantasyTeam;
  Player?: Player;
}

export interface TransactionParticipant {
  RosterID: number;
  Team?: FantasyTeam;
  AddedPlayers: TransactionPlayerAsset[];
  DroppedPlayers: TransactionPlayerAsset[];
  AcquiredDraftPicks: TransactionDraftPick[];
  SentDraftPicks: TransactionDraftPick[];
}

export interface Transaction extends Omit<RawTransaction, 'RosterIDs' | 'Adds' | 'Drops' | 'DraftPicks'> {
  CreatedAtDate: Date | null;
  EffectiveAt: number;
  EffectiveAtDate: Date | null;
  RosterIDs: number[];
  Participants: TransactionParticipant[];
  DraftPicks: TransactionDraftPick[];
}
