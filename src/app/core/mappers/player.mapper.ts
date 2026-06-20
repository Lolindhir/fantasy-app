import type {
  FreeAgentMarketInfo,
  GameHistory,
  NFLTeam,
  Player,
  PlayerStats,
  PointHistory,
  PointHistorySeason,
  RawNFLTeam,
  RawPlayer
} from '../models/player.models';

export interface PlayerMappingContext {
  nflTeams: RawNFLTeam[];
  seasonYear: number;
  currentWeek: number;
  playoffStartWeek: number;
  lastWeek: number;
}

const FREE_AGENT_TEAM: NFLTeam = {
  ID: 'FA',
  Name: 'Free Agent',
  Abv: 'FA',
  Logo: 'assets/logo_nfl.png'
};

export function mapRawPlayerToPlayer(raw: RawPlayer, context: PlayerMappingContext): Player {
  const teamNfl = raw.IsFreeAgent
    ? FREE_AGENT_TEAM
    : context.nflTeams.find(team => team.ID === raw.TeamID)!;

  const stats = mapPlayerStats(raw, context.seasonYear);
  const injuryDetails = normalizeInjuryDetails(raw);

  return {
    ...raw,
    InjuryDetails: injuryDetails,
    Number: raw.IsFreeAgent ? '' : raw.Number,
    TeamNFL: teamNfl,
    TeamFantasy: undefined,
    IsFantasyFreeAgent: false,
    IsFreeAgentDraftAvailable: false,
    FreeAgentMarketInfo: createInitialFreeAgentMarketInfo('Current'),
    IsFreeAgentDraftAvailableProjected: false,
    FreeAgentMarketInfoProjected: createInitialFreeAgentMarketInfo('Projected'),
    Salary: raw.Salary,
    SalaryProjected: raw.SalaryProjected,
    SalaryDisplay: formatSalaryDollars(raw.Salary),
    SalaryProjectedDisplay: formatSalaryDollars(raw.SalaryProjected),
    NameShort: raw.NameShort || `${raw.NameFirst[0]}. ${raw.NameLast}`,
    Stats: stats,
    GameHistoryFull: prepareGameHistory(
      raw,
      context.currentWeek,
      context.playoffStartWeek,
      context.lastWeek
    )
  };
}

export function formatSalaryDollars(amount: number): string {
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)} Mio.`;
  }

  if (amount >= 1_000) {
    return `$${(amount / 1_000_000).toFixed(2)} Mio.`;
  }

  return `$0.0 Mio.`;
}

function mapPlayerStats(raw: RawPlayer, seasonYear: number): PlayerStats {
  return {
    GamesPlayed: raw.GamesPlayed,
    GamesPotential: raw.GamesPotential,
    SnapsTotal: raw.SnapsTotal,
    AttemptsTotal: raw.AttemptsTotal,
    FantasyPointsTotal: raw.FantasyPointsTotal,
    FantasyPointsAvgGame: raw.FantasyPointsAvgGame,
    FantasyPointsAvgPotentialGame: raw.FantasyPointsAvgPotentialGame,
    FantasyPointsAvgSnap: raw.FantasyPointsAvgSnap,
    FantasyPointsAvgAttempt: raw.FantasyPointsAvgAttempt,
    TouchdownsTotal: raw.TouchdownsTotal,
    TouchdownsPassing: raw.TouchdownsPassing,
    TouchdownsReceiving: raw.TouchdownsReceiving,
    TouchdownsRushing: raw.TouchdownsRushing,
    Ranking: raw.Ranking,
    PointHistory: mapPointHistory(raw.PointHistory, seasonYear)
  };
}

function mapPointHistory(pointHistory: PointHistory, seasonYear: number): PointHistory {
  return {
    SeasonMinus1: mapPointHistorySeason(pointHistory.SeasonMinus1, seasonYear - 1),
    SeasonMinus2: mapPointHistorySeason(pointHistory.SeasonMinus2, seasonYear - 2),
    SeasonMinus3: mapPointHistorySeason(pointHistory.SeasonMinus3, seasonYear - 3)
  };
}

function mapPointHistorySeason(season: PointHistorySeason, seasonNumber: number): PointHistorySeason {
  return {
    ...season,
    Season: seasonNumber
  };
}

function normalizeInjuryDetails(raw: RawPlayer): RawPlayer['InjuryDetails'] {
  return {
    ...raw.InjuryDetails,
    Date: normalizeCompactDate(raw.InjuryDetails?.Date),
    ReturnDate: normalizeCompactDate(raw.InjuryDetails?.ReturnDate)
  };
}

function normalizeCompactDate(dateValue: string | undefined): string {
  if (!dateValue) return '';

  if (/^\d{8}$/.test(dateValue)) {
    return `${dateValue.slice(0, 4)}-${dateValue.slice(4, 6)}-${dateValue.slice(6, 8)}`;
  }

  return dateValue;
}

function createInitialFreeAgentMarketInfo(salaryMode: FreeAgentMarketInfo['SalaryMode']): FreeAgentMarketInfo {
  return {
    Status: 'Rostered',
    StatusDisplay: 'Rostered',
    PredictionModel: 'CurrentOnly',
    SalaryMode: salaryMode,
    Probability: 0,
    Reason: 'Pending fantasy roster assignment.'
  };
}

function prepareGameHistory(
  player: RawPlayer,
  currentWeek: number,
  playoffStartWeek: number,
  lastWeek: number
): GameHistory[] {
  const existingGames = player.GameHistory ?? [];
  const weeks = Array.from({ length: currentWeek }, (_, i) => i + 1);

  return weeks.map(week => {
    const existing = existingGames.find(game => game.GameDetails.Week === week);
    if (existing) return existing;

    return {
      GameID: '',
      TeamID: '',
      TeamAbv: '',
      GameDetails: {
        Week: week,
        WeekFinal: false,
        WeekPlayoff: week >= playoffStartWeek && week <= lastWeek,
        WeekScored: week <= lastWeek,
        Date: '',
        Home: '-',
        HomeID: '',
        Away: '-',
        AwayID: '',
        HomePoints: 0,
        AwayPoints: 0
      },
      FantasyPoints: 0,
      SnapCount: 0,
      SnapPercentage: 0,
      Attempts: 0,
      Passing: undefined,
      Rushing: undefined,
      Receiving: undefined,
      Kicking: undefined
    };
  });
}
