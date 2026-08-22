export interface RawDraft {
  LeagueID: string;
  DraftKey: string;
  DisplayDraftKey: string;
  DisplayAbrDraftKey: string;
  Season: string;
  DraftType: string;
  DraftInstance: number;
  DraftCode: string;
  DisplayDraftType: string;
  DraftNo: number;
  DraftSource: string;
  SleeperDraftID: string | null;
  SleeperStatus: string | null;
  SleeperStartTime: number | null | undefined;
  DraftStartTimeUtc: string | null | undefined;
  Status: string;
  DisplayStatus: string;
  PickSource: string;
  OrderSource: string;
  OrderMode: string;
  Settings: DraftSettings;
  Picks: DraftPick[];
}

export interface DraftSettings {
  Rounds: number;
  Teams: number;
  Type: string;
}

export interface DraftPickTradeHistoryEntry {
  TransactionID: string;
  Source: string;
  CreatedAt: number;
  CreatedDate: string;
  DraftSource: string;
  PreviousOwnerRosterID: number;
  NewOwnerRosterID: number;
}

export interface DraftPick {
  PickKey: string;
  LeagueID: string;
  DraftKey: string;
  Season: string;
  DraftType: string;
  DraftInstance: number;
  DraftCode: string;
  Round: number;
  PositionInRound: number | null;
  OverallPick: number | null;
  DisplayPick: string;
  OriginalOwnerRosterID: number;
  CurrentOwnerRosterID: number;
  WasTraded: boolean;
  IsCurrentlyTraded: boolean;
  TradeSource: string | null;
  TradeHistory: DraftPickTradeHistoryEntry[];
  PlayerID: string | null;
  PlayerName: string | null;
  Status: string;
  SleeperPickNo: number | null;
  SleeperPickedBy: string | null;
  Draft?: RawDraft;
}
