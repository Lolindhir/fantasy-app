import type { FantasyTeam } from './league.models';
import type { Player } from './player.models';

export type TransactionPlayerRosterMap = Record<string, number | string>;

export interface RawTransactionDraftPick {
  DraftType: string | null;
  DraftInstance?: number | null;
  DraftCode?: string | null;
  DraftSource: string;
  DraftKey: string | null;
  Season: string;
  Round: number;
  SleeperDraftID?: string | null;
  PickKey?: string | null;
  PositionInRound?: number | null;
  OverallPick?: number | null;
  DisplayPick?: string | null;
  PlayerID?: string | null;
  PlayerName?: string | null;
  PickStatus?: string | null;
  SleeperPickNo?: number | null;
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
  CreatedAt: number;
  CreatedDate: string;
  RosterIDs: Array<number | string>;
  Adds: TransactionPlayerRosterMap | null;
  Drops: TransactionPlayerRosterMap | null;
  DraftPicks: RawTransactionDraftPick[] | null;
  Notes: string | null;
}

export interface TransactionPlayerAsset {
  PlayerID: string;
  Player?: Player;
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
  RosterIDs: number[];
  Participants: TransactionParticipant[];
  DraftPicks: TransactionDraftPick[];
}
