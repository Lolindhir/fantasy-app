import { inject, Injectable } from '@angular/core';
import { forkJoin, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';

import { mapRawLeagueData } from '../mappers/league.mapper';
import { mapRawPlayerToPlayer } from '../mappers/player.mapper';
import { mapRawTransactions } from '../mappers/transaction.mapper';
import type { DecisionWindowsReadModel } from '../models/decision-window.models';
import type { RawDraft } from '../models/draft.models';
import type { FantasyTeam, League, RawLeague } from '../models/league.models';
import type {
  Player,
  SortField,
  TopPlayersSalaryResult
} from '../models/player.models';
import type { RawTransaction, Transaction } from '../models/transaction.models';
import { mergeCompletedRawTransactions } from '../utils/transaction-history.util';
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

export interface LeagueWithPlayersAndTransactions extends LeagueWithPlayers {
  transactions: Transaction[];
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

  getDecisionWindowsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => ts.DecisionWindows)
    );
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => {
        return [ts.League, ts.Players, ts.Teams, ts.Drafts, ts.Transactions, ts.DecisionWindows]
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
    return this.getLeagueWithPlayersAndTransactions(sortFields).pipe(
      map(res => res.transactions)
    );
  }

  getDecisionWindows(): Observable<DecisionWindowsReadModel> {
    return this.dataApiService.getDecisionWindowsRaw();
  }

  getTransactionsForSources(
    includeCurrent: boolean,
    historicalPaths: string[],
    sortFields: SortField[] = ['NameLast']
  ): Observable<Transaction[]> {
    const normalizedHistoricalPaths = Array.from(new Set(
      (historicalPaths ?? []).filter(path => !!path)
    ));
    const transactionSources: Observable<RawTransaction[]>[] = [
      ...(includeCurrent ? [this.dataApiService.getTransactionsRaw()] : []),
      ...normalizedHistoricalPaths.map(path => this.dataApiService.getPastTransactionsRaw(path))
    ];
    const transactionLists$ = transactionSources.length > 0
      ? forkJoin(transactionSources)
      : of([] as RawTransaction[][]);

    return forkJoin({
      leagueData: this.dataApiService.getLeagueData(),
      transactionLists: transactionLists$
    }).pipe(
      map(({ leagueData, transactionLists }) => {
        const mappedLeagueData = this.mapLeagueData(leagueData, sortFields);
        const transactionsRaw = mergeCompletedRawTransactions(transactionLists);

        return mapRawTransactions(
          transactionsRaw,
          mappedLeagueData.teams,
          mappedLeagueData.players
        );
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

  getLeagueWithPlayersAndTransactions(
    sortFields: SortField[] = ['NameLast']
  ): Observable<LeagueWithPlayersAndTransactions> {
    return this.dataApiService.getMovesData().pipe(
      map(data => {
        const mappedLeagueData = this.mapLeagueData(data, sortFields);
        const transactionsRaw = mergeCompletedRawTransactions([data.transactionsRaw]);
        const transactions = mapRawTransactions(
          transactionsRaw,
          mappedLeagueData.teams,
          mappedLeagueData.players
        );

        return {
          ...mappedLeagueData,
          transactions
        };
      })
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
