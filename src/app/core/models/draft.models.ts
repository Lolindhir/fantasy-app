/** Historical display evidence only. It does not imply current NFL team or clickable Player. */
export interface HistoricalPlayerRef {
  Name: string | null;
  Position: string | null;
  Picture: string | null;
}

export interface RawDraft {
  DraftKey: string;
  DisplayDraftKey: string;
  DisplayAbrDraftKey: string;
  Season: string;
  DraftType: string;
  DraftInstance: number;
  DisplayDraftType: string;
  DraftNo: number;
  SleeperStatus: string | null;
  SleeperStartTime: number | null | undefined;
  DraftStartTimeUtc: string | null | undefined;
  Status: string;
  DisplayStatus: string;
  Settings: DraftSettings;
  Picks: DraftPick[];
}

export interface DraftSettings {
  Rounds: number;
  Type: string;
}

export interface DraftPickTradeHistoryEntry {
  TransactionID: string;
  CreatedAt: number; // Original submission timestamp.
  EffectiveAt?: number; // Primary historical trade timestamp (newer generated files).
  CreatedDate: string;
  PreviousOwnerRosterID: number;
  NewOwnerRosterID: number;
}

export interface DraftPick {
  PickKey: string;
  DraftKey: string;
  Season: string;
  DraftType: string;
  DraftInstance: number;
  Round: number;
  PositionInRound: number | null;
  OverallPick: number | null;
  DisplayPick: string;
  OriginalOwnerRosterID: number;
  CurrentOwnerRosterID: number;
  IsCurrentlyTraded: boolean;
  TradeHistory: DraftPickTradeHistoryEntry[];
  PlayerID: string | null;
  PlayerName: string | null;
  PlayerRef?: HistoricalPlayerRef;
  Status: string;
  SleeperPickNo: number | null;
  SleeperPickedBy: string | null;
  Draft?: RawDraft;
}
