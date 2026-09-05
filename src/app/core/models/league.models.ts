import type { DraftPick } from './draft.models';
import type { Player } from './player.models';

export interface DataTimestamps {
  League?: string;
  Players?: string;
  Teams?: string;
  Drafts?: string;
  Transactions?: string;
  Standings?: string;
  Games?: string;
  Schedule?: string;
  DecisionWindows?: string;
}

export interface PlayoffTeam {
  Place: number;
  PlaceOrdinal: string;
  TeamID: string | number;
  Owner: string;
  TeamName: string | null;
  PlaceType?: string;
  Championships?: number;
  RunnerUps?: number;
  Thirds?: number;
  PlaceCumulative?: number;
  PlaceAverage?: number;
  Placements?: number[];
}

export interface RegularSeasonTeam {
  Place: number;
  PlaceOrdinal: string;
  TeamID: string | number;
  Owner: string;
  TeamName: string | null;
  NumberOfGames?: number;
  Wins?: number;
  Losses?: number;
  Ties?: number;
  Points?: number;
  PointsAgainst?: number;
  Record?: string | null;
  Streak?: string | null;
  WinPercentage?: number;
  WinPercentageDisplay?: string;
  WinPercentageDiffLeagueAvg?: number;
  WinPercentageHistory?: number[];
  PointDifference?: number;
  PointsPerGame?: number;
  PointsPerGameDiffLeagueAvg?: number;
  PointsAgainstPerGame?: number;
  PointsAgainstPerGameDiffLeagueAvg?: number;
  LongestWinStreak?: number;
  WinStreakScore?: number;
  LongestLossStreak?: number;
  LossStreakScore?: number;
  EfficiencyScore?: number;
  IronWillScore?: number;
  ClutchPeakerScore?: number;
  ImprovementScore?: number;
  RegularSeasonWins?: number;
}

export interface AwardType {
  Name: string;
  DisplayText: string;
  Order: number;
}

export interface RawAward {
  Name: string;
  Type: AwardType;
  IconUnicode: string;
  StatDisplay: string;
}

export interface Award extends RawAward {
  Icon: string;
}

export interface AwardInStanding extends Award {
  TeamID: string | number;
  Owner: string;
  TeamName: string | null;
}

export interface Standing {
  Season: string;
  Playoffs?: PlayoffTeam[] | null;
  RegularSeason: RegularSeasonTeam[];
  Awards?: AwardInStanding[];
}

export interface LeagueMatchupParticipant {
  TeamID: number;
  Points: number;
}

export interface LeagueMatchup {
  MatchupID: number;
  Participants: LeagueMatchupParticipant[];
}

export interface LeagueMatchupSnapshot {
  Season: string;
  Week: number;
  Matchups: LeagueMatchup[];
}

export interface RawLeague {
  LeagueID: string;
  Name: string;
  Avatar: string;
  Season: string;
  SeasonType: string;
  Status: string;
  Phase: string;
  CurrentWeek?: number;
  FinalScoredWeek: number;
  LastLeagueWeek: number;
  PlayoffStartWeek: number;
  TradeDeadlineWeek: number | null;
  TradeReviewDays: number;
  CutsAllowed: boolean;
  CutsMetaText: string;
  WaiversOpen: boolean;
  WaiversMetaText: string;
  NextWaiverRun?: string | null;
  TradesOpen: boolean;
  TradesMetaText: string;
  TotalTeams?: number;
  SalaryCap: number;
  SalaryCapProjected: number;
  CapDeadline: string;
  SeasonKickoff?: string | null;
  LeagueTimeZone?: string;
  SalaryRelevantTeamSize: number;
  Matchups?: LeagueMatchupSnapshot | null;
  Teams: RawFantasyTeam[];
  Standings: Standing[];
  Playoffs?: unknown;
  RosterSize?: string[];
  ScoringType?: Record<string, unknown>;
  Settings?: Record<string, unknown>;
  LeagueIDPrevious?: string;
}

export interface League extends Omit<RawLeague, 'Teams'> {
  Teams: FantasyTeam[];
  SalaryCapDisplay: string;
  SalaryCapProjectedDisplay: string;
  IsFinished: boolean;
  SeasonAsNumber: number;
}

export interface Placement {
  Place: number;
  PlaceOrdinal: string;
}

export interface PlacementRegularSeason extends Placement {
  Wins: number;
  Losses: number;
  Ties: number;
  Points: number;
  PointsAgainst: number;
  WinPercentage: number;
  WinPercentageDisplay: string;
  Record: string | null;
  Streak: string | null;
}

export interface PlacementRegularSeasonAllTime extends Omit<PlacementRegularSeason, 'Record' | 'Streak'> {
  RegularSeasonWins: number;
}

export interface PlacementPlayoffs extends Placement {}

export interface PlacementPlayoffsAllTime extends PlacementPlayoffs {
  Championships: number;
  RunnerUps: number;
  Thirds: number;
  PlaceCumulative: number;
  PlaceAverage: number;
  Placements: number[];
}

export interface Placements {
  Current: {
    Regular: PlacementRegularSeason;
    Playoffs?: PlacementPlayoffs;
    Awards: Award | Award[];
  };
  Previous: {
    Regular: PlacementRegularSeason;
    Playoffs?: PlacementPlayoffs;
    Awards: Award | Award[];
  };
  AllTime: {
    Regular: PlacementRegularSeasonAllTime;
    Awards?: Award | Award[];
    Playoffs: PlacementPlayoffsAllTime;
  };
}

export interface RawFantasyTeam {
  Owner: string;
  OwnerID: string;
  OwnerAvatar: string;
  Team: string | null;
  TeamAbbr: string | null;
  TeamID: number;
  TeamAvatar?: string | null;
  MatchupID: number | null;
  WaiverPosition: number;
  WaiverAdjusted: number | null;
  IsCommissioner: boolean;
  Placements: Placements;
  Roster: string[];
  Reserve: string[] | null;
  Taxi: string[] | null;
  Starter: string[] | null;
  DraftPicks?: string[];
}

export interface FantasyTeam extends Omit<RawFantasyTeam, 'Roster' | 'Reserve' | 'Taxi' | 'Starter' | 'DraftPicks' | 'TeamAvatar'> {
  Roster: Player[];
  Reserve: Player[];
  Taxi: Player[];
  Starter: Player[];
  DraftPickKeys: string[];
  DraftPicks: DraftPick[];
  Avatar: string;
  Standing: number;
  Wins: number;
  Losses: number;
  Ties: number;
  Points: number;
  PointsAgainst: number;
  Streak: string;
  Record: string;
  Championships: number;
  RunnerUps: number;
  Thirds: number;
  RegularSeasonWins: number;
  CurrentAwardsDisplay: string;
}