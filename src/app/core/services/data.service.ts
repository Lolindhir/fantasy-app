import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { mapRawLeagueData } from '../mappers/league.mapper';
import { mapRawPlayerToPlayer } from '../mappers/player.mapper';
import { mapRawTransactions } from '../mappers/transaction.mapper';
import type { RawDraft } from '../models/draft.models';
import type { FantasyTeam, League, RawLeague } from '../models/league.models';
import type {
  Player,
  SortField,
  TopPlayersSalaryResult
} from '../models/player.models';
import type { Transaction } from '../models/transaction.models';
import { sortPlayers } from '../../shared/utils/player-sort.util';
import {
  calculateTopPlayersSalary,
  getRosterAfterTrade
} from '../../shared/utils/trade-calculator.util';
import {
  DataApiService,
  type LeagueDataLoadResult,
  type PastSeasonsIndex
} from './data-api.service';
import { FreeAgentMarketService } from './free-agent-market.service';

export interface LeagueWithPlayers {
  league: League;
  players: Player[];
  teams: FantasyTeam[];
  drafts: RawDraft[];
}

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private dataApiService = inject(DataApiService);
  private freeAgentMarketService = inject(FreeAgentMarketService);

  getLeagueTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.League)
    );
  }

  getPlayersTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.Players)
    );
  }

  getTeamsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.Teams)
    );
  }

  getDraftsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.Drafts)
    );
  }

  getTransactionsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.Transactions)
    );
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => {
        return [ts.League, ts.Players, ts.Teams, ts.Drafts, ts.Transactions]
          .reduce<string | undefined>((a, b) => {
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

  getTransactions(sortFields: SortField[] = ['NameLast']): Observable<Transaction[]> {
    return this.dataApiService.getMovesData().pipe(
      map(data => {
        const leagueData = this.mapLeagueData(data, sortFields);
        return mapRawTransactions(data.transactionsRaw, leagueData.teams, leagueData.players);
      })
    );
  }

  getPastSeasonsIndex(): Observable<PastSeasonsIndex> {
    return this.dataApiService.getPastSeasonsIndex();
  }

  getPastDraftsRaw(path: string): Observable<RawDraft[]> {
    return this.dataApiService.getPastDraftsRaw(path);
  }

  getLeagueWithPlayers(sortFields: SortField[] = ['NameLast']): Observable<LeagueWithPlayers> {
    return this.dataApiService.getLeagueData().pipe(
      map(data => this.mapLeagueData(data, sortFields))
    );
  }

  calculateTopPlayersSalary(
    roster: Player[],
    topN: number,
    salarySelector: (player: Player) => number
  ): TopPlayersSalaryResult {
    return calculateTopPlayersSalary(roster, topN, salarySelector);
  }

  getRosterAfterTrade(
    currentRoster: Player[],
    outgoing: Player[],
    incoming: Player[]
  ): Player[] {
    return getRosterAfterTrade(currentRoster, outgoing, incoming);
  }

  private mapLeagueData(
    data: LeagueDataLoadResult,
    sortFields: SortField[]
  ): LeagueWithPlayers {
    const players: Player[] = data.playersRaw.map(raw => mapRawPlayerToPlayer(raw, {
      nflTeams: data.nflTeamsRaw,
      seasonYear: Number(data.leagueRaw.Season),
      currentWeek: data.leagueRaw.FinalScoredWeek,
      playoffStartWeek: data.leagueRaw.PlayoffStartWeek,
      lastWeek: data.leagueRaw.LastLeagueWeek
    }));

    const { league, teams, drafts } = mapRawLeagueData({
      leagueRaw: data.leagueRaw,
      draftsRaw: data.draftsRaw,
      players
    });

    this.freeAgentMarketService.enrich(players, teams, data.leagueRaw as RawLeague);

    return {
      league,
      players: sortPlayers(players, sortFields),
      teams,
      drafts
    };
  }
}
