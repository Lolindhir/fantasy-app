export interface RawDraft {
  DraftKey: string;
  DisplayDraftKey: string;
  DisplayAbrDraftKey: string;
  Season: string;
  DraftType: string;
  DraftInstance: number;
  DisplayDraftType: string;
  DraftNo: number;
  SleeperDraftID: string | null;
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
  CreatedAt: number;
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
  Status: string;
  SleeperPickNo: number | null;
  SleeperPickedBy: string | null;
  Draft?: RawDraft;
}
