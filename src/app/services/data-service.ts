import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import type { DraftPick, RawDraft } from '../core/models/draft.models';
import type { Award, DataTimestamps, FantasyTeam, League, RawAward, RawLeague } from '../core/models/league.models';
import type {
  FreeAgentMarketInfo,
  FreeAgentPredictionModel,
  FreeAgentSalaryMode,
  GameHistory,
  NFLTeam,
  Player,
  PlayerStats,
  PointHistorySeason,
  RawNFLTeam,
  RawPlayer,
  SortField,
  TopPlayersSalaryResult
} from '../core/models/player.models';

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private http = inject(HttpClient);
  private timestampsUrl = 'data/Timestamps.json';

  getLeagueTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'League'>>(this.timestampsUrl).pipe(
      map(ts => ts.League)
    );
  }

  getPlayersTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Players'>>(this.timestampsUrl).pipe(
      map(ts => ts.Players)
    );
  }

  getTeamsTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Teams'>>(this.timestampsUrl).pipe(
      map(ts => ts.Teams)
    );
  }

  getDraftsTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Drafts'>>(this.timestampsUrl).pipe(
      map(ts => ts.Drafts)
    );
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return forkJoin({
      league: this.getLeagueTimestamp(),
      players: this.getPlayersTimestamp(),
      teams: this.getTeamsTimestamp(),
      drafts: this.getDraftsTimestamp()
    }).pipe(
      map(({ league, players, teams, drafts }) => {
        return [league, players, teams, drafts].reduce<string | undefined>((a, b) => {
          if (a === undefined) return b;
          if (b === undefined) return a;
          return a > b ? a : b;
        }, undefined);
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

  getLeagueWithPlayers(sortFields: SortField[] = ['NameLast']): Observable<{ league: League, players: Player[], teams: FantasyTeam[], drafts: RawDraft[] }> {
    return forkJoin({
      leagueRaw: this.http.get<RawLeague>('data/League.json'),
      playersRaw: this.http.get<RawPlayer[]>('data/Players.json'),
      nflTeamsRaw: this.http.get<RawNFLTeam[]>('data/Teams.json'),
      draftsRaw: this.http.get<RawDraft[]>('data/Drafts.json')
    }).pipe(
      map(({ leagueRaw, playersRaw, nflTeamsRaw, draftsRaw }) => {

        const drafts = draftsRaw ?? [];
        const draftPickByKey = new Map<string, DraftPick>();
        for (const draft of drafts) {
          for (const pick of draft.Picks ?? []) {
            draftPickByKey.set(pick.PickKey, {
              ...pick,
              Draft: draft
            });
          }
        }

        const teams: FantasyTeam[] = leagueRaw.Teams.map(team => {
          const awards = this.ensureArray(team.Placements.Current.Awards)
            .map(a => this.mapAward(a));

          const draftPickKeys = team.DraftPicks ?? [];
          const resolvedDraftPicks = draftPickKeys
            .map(key => draftPickByKey.get(key))
            .filter((pick): pick is DraftPick => !!pick);

          return {
            ...team,
            Team: team.Team || `Team ${team.Owner}`,
            Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
            Roster: [],
            Reserve: [],
            Taxi: [],
            Starter: [],
            DraftPickKeys: draftPickKeys,
            DraftPicks: resolvedDraftPicks,
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
              raw.InjuryDetails.Date = `${rd.slice(0, 4)}-${rd.slice(4, 6)}-${rd.slice(6, 8)}`;
            }
          }

          if (raw.InjuryDetails?.ReturnDate) {
            const rd = raw.InjuryDetails.ReturnDate;
            if (/^\d{8}$/.test(rd)) {
              raw.InjuryDetails.ReturnDate = `${rd.slice(0, 4)}-${rd.slice(4, 6)}-${rd.slice(6, 8)}`;
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
          const playoffStartWeek = leagueRaw.PlayoffStartWeek;
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
          const rawTeam = leagueRaw.Teams.find(t => t.TeamID === team.TeamID);

          team.Roster = this.rosterIdsToPlayers(rawTeam?.Roster ?? [], players);
          team.Reserve = this.rosterIdsToPlayers(rawTeam?.Reserve ?? [], players);
          team.Taxi = this.rosterIdsToPlayers(rawTeam?.Taxi ?? [], players);
          team.Starter = this.rosterIdsToPlayers(rawTeam?.Starter ?? [], players);

          team.Roster.forEach(player => (player.TeamFantasy = team));
        });

        this.enrichFreeAgentMarket(players, teams, leagueRaw);
        teams.sort((a, b) => a.Standing - b.Standing);
        const playersSorted = this.sortRoster(players, sortFields);

        leagueRaw.Standings.forEach(standing => {
          standing.Awards?.forEach(award => {
            award.Icon = this.unicodeToEmoji(award.IconUnicode);
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

        return { league, players: playersSorted, teams, drafts };
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
    status: FreeAgentMarketInfo['Status'],
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
    const cap = topPlayers.reduce((sum, p) => sum + salarySelector(p), 0);

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
