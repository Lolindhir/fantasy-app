import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { map } from 'rxjs/operators';


export interface DataTimestamps {
  League: string;
  Players: string;
  Teams: string;
}

export interface PlayoffTeam {
  Place: number;
  PlaceOrdinal: string;
  TeamID: string;
  Owner: string;
  TeamName: string;
}

export interface RegularSeasonTeam {
  Place: number;
  PlaceOrdinal: string;
  TeamID: string;
  Owner: string;
  TeamName: string;
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
  TeamID: string;
  Owner: string;
  TeamName: string;
}

export interface Standing {
  Season: string;
  Playoffs?: PlayoffTeam[];
  RegularSeason: RegularSeasonTeam[];
  Awards?: AwardInStanding[];
}

export interface RawLeague {
  LeagueID: string;
  Name: string;
  Avatar: string;
  Season: string;
  SeasonType: string;
  Status: string;
  FinalScoredWeek: number;
  PlayoffWeek: number;
  LastLeagueWeek: number;
  TradeDeadlineWeek: number;
  CutsAllowed: boolean;
  CutsMetaText: string;
  WaiversOpen: boolean;
  WaiversMetaText: string;
  TradesOpen: boolean;
  TradesMetaText: string;
  SalaryCap: number;
  SalaryCapProjected: number;
  CapDeadline: string;
  SalaryRelevantTeamSize: number;
  Teams: RawFantasyTeam[];
  Standings: Standing[];
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
  Record: string;
  Streak: string;
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
  Placements: string[];
}

export interface Placements {
  Current: {
    Regular: PlacementRegularSeason;
    Playoffs?: PlacementPlayoffs;
    Awards: Award[];
  };
  Previous: {
    Regular: PlacementRegularSeason;
    Playoffs?: PlacementPlayoffs;
    Awards: Award[];
  };
  AllTime: {
    Regular: PlacementRegularSeasonAllTime;
    Playoffs: PlacementPlayoffsAllTime;
  };
}

export interface RawFantasyTeam {
  Owner: string;
  OwnerID: string;
  OwnerAvatar: string;
  Team: string | null;
  TeamID: number;
  TeamAvatar?: string | null;

  MatchupID: number | null;
  WaiverPosition: number;
  WaiverAdjusted: number;
  IsCommissioner: boolean;

  Placements: Placements;

  Roster: string[];
}

export interface FantasyTeam extends Omit<RawFantasyTeam, 'Roster' | 'TeamAvatar'> {
  Roster: Player[];
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
  AwardsDisplay: string;
}

export interface InjuryDetails {
  Date: string;
  ReturnDate: string;
  Description: string;
  Designation: string;
}

export interface RankingEntry {
  Type: 'Total' | 'PerGame' | 'Combined' | 'Total_Pos' | 'PerGame_Pos' | 'Combined_Pos';
  Value: number;
}

export interface PointHistorySeason {
  Season: number;
  Total: number;
  AvgGame: number;
  AvgPotentialGame: number;
  GamesPlayed: number;
  PotentialGames: number;
}

export interface PointHistory {
  SeasonMinus1: PointHistorySeason;
  SeasonMinus2: PointHistorySeason;
  SeasonMinus3: PointHistorySeason;
}

export interface PlayerStats {
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  Ranking: RankingEntry[];
  PointHistory: PointHistory;
}

export interface GameHistory {
  GameID: string;
  TeamID: string;
  TeamAbv: string;
  GameDetails: GameDetails;
  FantasyPoints: number;
  SnapCount: number;
  SnapPercentage: number;
  Attempts: number;
  Passing?: PassingStats;
  Rushing?: RushingStats;
  Receiving?: ReceivingStats;
  Kicking?: KickingStats;
}

export interface GameDetails {
  Week: number;
  WeekFinal: boolean;
  WeekPlayoff: boolean;
  WeekScored: boolean;
  Date: string;
  Home: string;
  HomeID: string;
  Away: string;
  AwayID: string;
  HomePoints: number;
  AwayPoints: number;
}

export interface PassingStats {
  QBRating: number;
  Rating: number;
  PassAttempts: number;
  PassAvg: number;
  PassTDs: number;
  PassYards: number;
  Interceptions: number;
  PassCompletions: number;
}

export interface RushingStats {
  RushAvg: number;
  RushYards: number;
  Carries: number;
  LongRush: number;
  RushTDs: number;
}

export interface ReceivingStats {
  Receptions: number;
  ReceptionTDs: number;
  LongReceptions: number;
  Targets: number;
  ReceptionYards: number;
  ReceptionAvg: number;
}

export interface KickingStats {
  KickingPts: number;
  FgLong: number;
  FgMade: number;
  FgAttempts: number;
  FgMissed: number;
  FgPct: number;
  XpMade: number;
  XpAttempts: number;
  XpMissed: number;
}

export type FreeAgentPredictionModel =
  | 'CurrentOnly'
  | 'RuleBasedAutoCut';

export type FreeAgentSalaryMode =
  | 'Current'
  | 'Projected';

export type FreeAgentMarketStatus =
  | 'Rostered'
  | 'FreeAgent'
  | 'ProjectedCapCut'
  | 'PossibleCapCut';

export interface FreeAgentMarketInfo {
  Status: FreeAgentMarketStatus;
  StatusDisplay: string;
  PredictionModel: FreeAgentPredictionModel;
  SalaryMode: FreeAgentSalaryMode;
  Probability: number;
  Reason: string;

  TeamID?: number;
  TeamName?: string;
  Owner?: string;

  CutOrder?: number;
  SalaryRank?: number;

  SalaryUsed?: number;
  SalaryUsedDisplay?: string;

  CapLimit?: number;
  CapLimitDisplay?: string;

  CapBeforeCut?: number;
  CapBeforeCutDisplay?: string;

  CapAfterCut?: number;
  CapAfterCutDisplay?: string;
}

export interface RawPlayer {
  ID: string;
  Name: string;
  NameFirst: string;
  NameLast: string;
  NameShort: string;
  Position: string;
  IsFreeAgent: boolean;
  Salary: number;
  SalaryProjected: number;
  Age: number;
  Year: number;
  Picture: string;
  Number: string;
  FantasyPros: string;
  ESPN: string;
  College: string;
  HighSchool: string;
  Injured: boolean;
  InjuryDetails: InjuryDetails;
  TeamID: string;
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  Ranking: RankingEntry[];
  PointHistory: PointHistory;
  GameHistory?: GameHistory[];
}

export interface Player extends Omit<RawPlayer, 'TeamID' | 'GamesPlayed' | 'GamesPotential' | 'FantasyPointsTotal' | 'FantasyPointsAvgGame' | 'FantasyPointsAvgPotentialGame' | 'FantasyPointsAvgSnap' | 'FantasyPointsAvgAttempt' | 'TouchdownsTotal' | 'TouchdownsPassing' | 'TouchdownsReceiving' | 'TouchdownsRushing' | 'Ranking' | 'PointHistory'> {
  TeamNFL: NFLTeam;
  TeamFantasy?: FantasyTeam;

  IsFantasyFreeAgent: boolean;

  IsFreeAgentDraftAvailable: boolean;
  FreeAgentMarketInfo: FreeAgentMarketInfo;

  IsFreeAgentDraftAvailableProjected: boolean;
  FreeAgentMarketInfoProjected: FreeAgentMarketInfo;

  SalaryDisplay: string;
  SalaryProjectedDisplay: string;
  Stats: PlayerStats;
  GameHistoryFull?: GameHistory[];
}

export interface RawNFLTeam {
  ID: string;
  Name: string;
  Abv: string;
  Logo: string;
}

export interface NFLTeam extends RawNFLTeam {}

export interface TopPlayersSalaryResult {
  cap: number;
  topPlayers: Player[];
}

export type SortField = keyof Player;

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private http = inject(HttpClient);

  private timestampsUrl = 'data/Timestamps.json';

  getLeagueTimestamp(): Observable<string | undefined> {
    return this.http.get<{ League: string }>(this.timestampsUrl).pipe(
      map(ts => ts.League)
    );
  }

  getPlayersTimestamp(): Observable<string | undefined> {
    return this.http.get<{ Players: string }>(this.timestampsUrl).pipe(
      map(ts => ts.Players)
    );
  }

  getTeamsTimestamp(): Observable<string | undefined> {
    return this.http.get<{ Teams: string }>(this.timestampsUrl).pipe(
      map(ts => ts.Teams)
    );
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return forkJoin({
      league: this.getLeagueTimestamp(),
      players: this.getPlayersTimestamp(),
      teams: this.getTeamsTimestamp()
    }).pipe(
      map(({ league, players, teams }) => {
        return [league, players, teams].reduce((a, b) => {
          if (a === undefined) return b;
          if (b === undefined) return a;
          return a > b ? a : b;
        });
      })
    );
  }

  getFantasyTeams(sortFields: SortField[] = ['NameLast']): Observable<FantasyTeam[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.teams)
    );
  }

  getAllPlayers(sortFields: SortField[] = ['NameLast']): Observable<Player[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.players)
    );
  }

  getLeague(sortFields: SortField[] = ['NameLast']): Observable<League> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.league)
    );
  }

  getLeagueWithPlayers(sortFields: SortField[] = ['NameLast']): Observable<{ league: League, players: Player[], teams: FantasyTeam[] }> {
    return forkJoin({
      leagueRaw: this.http.get<RawLeague>('data/League.json'),
      playersRaw: this.http.get<RawPlayer[]>('data/Players.json'),
      nflTeamsRaw: this.http.get<RawNFLTeam[]>('data/Teams.json')
    }).pipe(
      map(({ leagueRaw, playersRaw, nflTeamsRaw }) => {

        const teams: FantasyTeam[] = leagueRaw.Teams.map(team => {

          const awards = this.ensureArray(team.Placements.Current.Awards)
            .map(a => this.mapAward(a));

          return {
            ...team,
            Team: team.Team || `Team ${team.Owner}`,
            Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
            Roster: [],
            Standing: team.Placements.Current.Playoffs?.Place && team.Placements.Current.Playoffs.Place > 0
              ? team.Placements.Current.Playoffs.Place
              : team.Placements.Current.Regular.Place ?? 0,
            Wins: team.Placements.Current.Regular.Wins ?? 0,
            Losses: team.Placements.Current.Regular.Losses ?? 0,
            Ties: team.Placements.Current.Regular.Ties ?? 0,
            Points: team.Placements.Current.Regular.Points ?? 0,
            PointsAgainst: team.Placements.Current.Regular.PointsAgainst ?? 0,
            Streak: team.Placements.Current.Regular.Streak ?? '',
            Record: team.Placements.Current.Regular.Record ?? '',
            Championships: team.Placements.AllTime.Playoffs.Championships ?? 0,
            RunnerUps: team.Placements.AllTime.Playoffs.RunnerUps ?? 0,
            Thirds: team.Placements.AllTime.Playoffs.Thirds ?? 0,
            RegularSeasonWins: team.Placements.AllTime.Regular.RegularSeasonWins ?? 0,
            AwardsDisplay: awards.map(a => a.Icon).join('')
          };
        });

        const seasonYear = Number(leagueRaw.Season);

        const FREE_AGENT_TEAM: NFLTeam = {
          ID: 'FA',
          Name: 'Free Agent',
          Abv: 'FA',
          Logo: 'assets/logo_nfl.png'
        };

        const players: Player[] = playersRaw.map(raw => {
          let nfl = nflTeamsRaw.find(t => t.ID === raw.TeamID)!;
          let jerseyNumber = raw.Number;

          if (raw.IsFreeAgent) {
            nfl = FREE_AGENT_TEAM;
            jerseyNumber = '';
          }

          const stats: PlayerStats = {
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
            PointHistory: raw.PointHistory
          };

          if (raw.InjuryDetails?.Date) {
            const rd = raw.InjuryDetails.Date;
            if (/^\d{8}$/.test(rd)) {
              const year = rd.slice(0, 4);
              const month = rd.slice(4, 6);
              const day = rd.slice(6, 8);
              raw.InjuryDetails.Date = `${year}-${month}-${day}`;
            }
          }

          if (raw.InjuryDetails?.ReturnDate) {
            const rd = raw.InjuryDetails.ReturnDate;
            if (/^\d{8}$/.test(rd)) {
              const year = rd.slice(0, 4);
              const month = rd.slice(4, 6);
              const day = rd.slice(6, 8);
              raw.InjuryDetails.ReturnDate = `${year}-${month}-${day}`;
            }
          }

          if (stats?.PointHistory) {
            const mapping = {
              SeasonMinus1: seasonYear - 1,
              SeasonMinus2: seasonYear - 2,
              SeasonMinus3: seasonYear - 3
            } as const;

            (Object.entries(stats.PointHistory) as [keyof typeof stats.PointHistory, PointHistorySeason | undefined][])
              .forEach(([key, season]) => {
                if (season) {
                  season.Season = mapping[key];
                }
              });
          }

          const currentWeek = leagueRaw.FinalScoredWeek;
          const playoffStartWeek = leagueRaw.PlayoffWeek;
          const lastWeek = leagueRaw.LastLeagueWeek;

          return {
            ...raw,
            Number: jerseyNumber,
            TeamNFL: nfl,
            TeamFantasy: undefined,

            IsFantasyFreeAgent: false,

            IsFreeAgentDraftAvailable: false,
            FreeAgentMarketInfo: this.createFreeAgentMarketInfo(
              'Rostered',
              'Rostered',
              'CurrentOnly',
              'Current',
              0,
              'Pending fantasy roster assignment.'
            ),

            IsFreeAgentDraftAvailableProjected: false,
            FreeAgentMarketInfoProjected: this.createFreeAgentMarketInfo(
              'Rostered',
              'Rostered',
              'CurrentOnly',
              'Projected',
              0,
              'Pending fantasy roster assignment.'
            ),

            Salary: raw.Salary,
            SalaryProjected: raw.SalaryProjected,
            SalaryDisplay: this.formatSalaryDollars(raw.Salary),
            SalaryProjectedDisplay: this.formatSalaryDollars(raw.SalaryProjected),
            NameShort: raw.NameShort || `${raw.NameFirst[0]}. ${raw.NameLast}`,
            Stats: stats,
            GameHistoryFull: this.prepareGameHistory(raw, currentWeek, playoffStartWeek, lastWeek)
          };
        });

        teams.forEach(team => {
          team.Roster = this.rosterIdsToPlayers(
            (leagueRaw.Teams.find(t => t.TeamID === team.TeamID)?.Roster) || [],
            players
          );

          team.Roster.forEach(player => (player.TeamFantasy = team));
        });

        this.enrichFreeAgentMarket(players, teams, leagueRaw);

        teams.sort((a, b) => a.Standing - b.Standing);

        const playersSorted = this.sortRoster(players, sortFields);

        leagueRaw.Standings.forEach(standing => {
          standing.Awards?.forEach(award => {
            award.Icon = this.unicodeToEmoji(award.IconUnicode);
          });

          standing.Playoffs?.forEach(team => {
          });

          standing.RegularSeason.forEach(team => {
          });
        });

        const league: League = {
          ...leagueRaw,
          Teams: teams,
          SalaryCap: leagueRaw.SalaryCap,
          SalaryCapDisplay: this.formatSalaryDollars(leagueRaw.SalaryCap),
          SalaryCapProjected: leagueRaw.SalaryCapProjected,
          SalaryCapProjectedDisplay: this.formatSalaryDollars(leagueRaw.SalaryCapProjected),
          IsFinished: leagueRaw.Status == 'Finished',
          SeasonAsNumber: +leagueRaw.Season
        };

        return { league, players: playersSorted, teams };
      })
    );
  }

  private rosterIdsToPlayers(rosterIds: string[], allPlayers: Player[]): Player[] {
    return rosterIds
      .map(pid => allPlayers.find(p => p.ID === pid))
      .filter((p): p is Player => !!p);
  }

  private enrichFreeAgentMarket(
    players: Player[],
    teams: FantasyTeam[],
    league: RawLeague
  ): void {

    this.applyFreeAgentPredictionModel(
      players,
      teams,
      league,
      'RuleBasedAutoCut',
      'Current'
    );

    this.applyFreeAgentPredictionModel(
      players,
      teams,
      league,
      'RuleBasedAutoCut',
      'Projected'
    );
  }

  private applyFreeAgentPredictionModel(
    players: Player[],
    teams: FantasyTeam[],
    league: RawLeague,
    model: FreeAgentPredictionModel,
    salaryMode: FreeAgentSalaryMode
  ): void {

    players.forEach(player => {
      const isFantasyFreeAgent = !player.TeamFantasy;

      if (salaryMode === 'Current') {
        player.IsFantasyFreeAgent = isFantasyFreeAgent;
      }

      const info = isFantasyFreeAgent
        ? this.createFreeAgentMarketInfo(
            'FreeAgent',
            'Free Agent',
            'CurrentOnly',
            salaryMode,
            1,
            'Player is currently not assigned to any fantasy team.'
          )
        : this.createFreeAgentMarketInfo(
            'Rostered',
            'Rostered',
            model,
            salaryMode,
            0,
            'Player is currently rostered by a fantasy team.'
          );

      this.setFreeAgentMarketInfo(player, info, salaryMode);
    });

    if (model === 'CurrentOnly') {
      return;
    }

    if (model === 'RuleBasedAutoCut') {
      this.applyRuleBasedAutoCutModel(players, teams, league, salaryMode);
    }
  }

  private applyRuleBasedAutoCutModel(
    players: Player[],
    teams: FantasyTeam[],
    league: RawLeague,
    salaryMode: FreeAgentSalaryMode
  ): void {

    const salaryRelevantTeamSize = league.SalaryRelevantTeamSize;
    const capLimit = salaryMode === 'Projected'
      ? (league.SalaryCapProjected ?? league.SalaryCap)
      : league.SalaryCap;

    const salarySelector = salaryMode === 'Projected'
      ? (p: Player) => p.SalaryProjected ?? p.Salary
      : (p: Player) => p.Salary;

    teams.forEach(team => {
      let simulatedRoster = [...team.Roster];

      let currentCap = this.calculateTopPlayersSalary(
        simulatedRoster,
        salaryRelevantTeamSize,
        salarySelector
      ).cap;

      if (currentCap <= capLimit) {
        return;
      }

      let cutOrder = 1;

      while (currentCap > capLimit) {
        const sortedRoster = [...simulatedRoster].sort(
          (a, b) => salarySelector(b) - salarySelector(a)
        );

        const nextCutCandidate = sortedRoster[5];

        if (!nextCutCandidate) {
          break;
        }

        const capBeforeCut = currentCap;
        const salaryUsed = salarySelector(nextCutCandidate);

        simulatedRoster = simulatedRoster.filter(
          p => p.ID !== nextCutCandidate.ID
        );

        currentCap = this.calculateTopPlayersSalary(
          simulatedRoster,
          salaryRelevantTeamSize,
          salarySelector
        ).cap;

        const info = this.createFreeAgentMarketInfo(
          'ProjectedCapCut',
          'Projected Cap Cut',
          'RuleBasedAutoCut',
          salaryMode,
          1,
          'Team is over the salary cap. Rule-based model cuts the current 6th highest salary player until the team is under the cap.',
          {
            TeamID: team.TeamID,
            TeamName: team.Team ?? `Team ${team.Owner}`,
            Owner: team.Owner,

            CutOrder: cutOrder,
            SalaryRank: 6,

            SalaryUsed: salaryUsed,
            SalaryUsedDisplay: this.formatSalaryDollars(salaryUsed),

            CapLimit: capLimit,
            CapLimitDisplay: this.formatSalaryDollars(capLimit),

            CapBeforeCut: capBeforeCut,
            CapBeforeCutDisplay: this.formatSalaryDollars(capBeforeCut),

            CapAfterCut: currentCap,
            CapAfterCutDisplay: this.formatSalaryDollars(currentCap)
          }
        );

        this.setFreeAgentMarketInfo(nextCutCandidate, info, salaryMode);

        cutOrder++;
      }
    });
  }

  private createFreeAgentMarketInfo(
    status: FreeAgentMarketStatus,
    statusDisplay: string,
    model: FreeAgentPredictionModel,
    salaryMode: FreeAgentSalaryMode,
    probability: number,
    reason: string,
    extra?: Partial<FreeAgentMarketInfo>
  ): FreeAgentMarketInfo {
    return {
      Status: status,
      StatusDisplay: statusDisplay,
      PredictionModel: model,
      SalaryMode: salaryMode,
      Probability: probability,
      Reason: reason,
      ...extra
    };
  }

  private setFreeAgentMarketInfo(
    player: Player,
    info: FreeAgentMarketInfo,
    salaryMode: FreeAgentSalaryMode
  ): void {
    const isAvailable =
      info.Status === 'FreeAgent' ||
      info.Status === 'ProjectedCapCut' ||
      info.Status === 'PossibleCapCut';

    if (salaryMode === 'Projected') {
      player.FreeAgentMarketInfoProjected = info;
      player.IsFreeAgentDraftAvailableProjected = isAvailable;
      return;
    }

    player.FreeAgentMarketInfo = info;
    player.IsFreeAgentDraftAvailable = isAvailable;
  }

  private formatSalaryDollars(amount: number): string {
    if (amount >= 1_000_000) {
      return `$${(amount / 1_000_000).toFixed(1)} Mio.`;
    } else if (amount >= 1_000) {
      return `$${(amount / 1_000_000).toFixed(2)} Mio.`;
    } else {
      return `$0.0 Mio.`;
    }
  }

  private sortRoster(roster: Player[], sortFields: SortField[]): Player[] {
    return roster.sort((a, b) => {
      for (const field of sortFields) {
        if (field === 'Salary' || field === 'SalaryProjected' || field === 'Age' || field === 'Year') {
          const diff = (b[field] as number) - (a[field] as number);
          if (diff !== 0) return diff;
        } else {
          const cmp = String(a[field]).localeCompare(String(b[field]), 'en', { sensitivity: 'base' });
          if (cmp !== 0) return cmp;
        }
      }

      return a.ID.localeCompare(b.ID);
    });
  }

  private prepareGameHistory(player: RawPlayer, currentWeek: number, playoffStartWeek: number, lastWeek: number): GameHistory[] {
    const existingGames = player.GameHistory ?? [];

    const weeks = Array.from({ length: currentWeek }, (_, i) => i + 1);

    return weeks.map(week => {
      const existing = existingGames.find(g => g.GameDetails.Week === week);
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
      } as GameHistory;
    });
  }

  calculateTopPlayersSalary(
    roster: Player[],
    topN: number,
    salarySelector: (player: Player) => number
  ): TopPlayersSalaryResult {

    if (!roster || roster.length === 0) {
      return { cap: 0, topPlayers: [] };
    }

    const sortedRoster = [...roster]
      .sort((a, b) => salarySelector(b) - salarySelector(a));

    const actualTopN = Math.min(topN, sortedRoster.length);
    const topPlayers = sortedRoster.slice(0, actualTopN);

    const cap = topPlayers
      .reduce((sum, p) => sum + salarySelector(p), 0);

    return { cap, topPlayers };
  }

  getRosterAfterTrade(
    currentRoster: Player[],
    outgoing: Player[],
    incoming: Player[]
  ): Player[] {
    let newRoster = [...currentRoster];

    outgoing.forEach(p => {
      newRoster = newRoster.filter(x => x.ID !== p.ID);
    });

    incoming.forEach(p => newRoster.push(p));

    return newRoster;
  }

  private unicodeToEmoji(unicode: string): string {
    return unicode
      .split(' ')
      .map(code => String.fromCodePoint(parseInt(code, 16)))
      .join('');
  }

  private mapAward(raw: RawAward): Award {
    return {
      Name: raw.Name,
      Type: raw.Type,
      IconUnicode: raw.IconUnicode,
      StatDisplay: raw.StatDisplay,
      Icon: this.unicodeToEmoji(raw.IconUnicode)
    };
  }

  private ensureArray<T>(value: T | T[] | null | undefined): T[] {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  }

}