import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { mapRawLeagueData } from '../core/mappers/league.mapper';
import { mapRawPlayerToPlayer } from '../core/mappers/player.mapper';
import type { RawDraft } from '../core/models/draft.models';
import type { DataTimestamps, FantasyTeam, League } from '../core/models/league.models';
import type {
  Player,
  SortField,
  TopPlayersSalaryResult
} from '../core/models/player.models';
import { DataApiService } from '../core/services/data-api.service';
import { FreeAgentMarketService } from '../core/services/free-agent-market.service';
import { sortPlayers } from '../shared/utils/player-sort.util';
import {
  calculateTopPlayersSalary,
  getRosterAfterTrade
} from '../shared/utils/trade-calculator.util';

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

  getLatestTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => {
        return [ts.League, ts.Players, ts.Teams, ts.Drafts].reduce<string | undefined>((a, b) => {
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
    return this.dataApiService.getLeagueData().pipe(
      map(({ leagueRaw, playersRaw, nflTeamsRaw, draftsRaw }) => {
        const players: Player[] = playersRaw.map(raw => mapRawPlayerToPlayer(raw, {
          nflTeams: nflTeamsRaw,
          seasonYear: Number(leagueRaw.Season),
          currentWeek: leagueRaw.FinalScoredWeek,
          playoffStartWeek: leagueRaw.PlayoffStartWeek,
          lastWeek: leagueRaw.LastLeagueWeek
        }));

        const { league, teams, drafts } = mapRawLeagueData({
          leagueRaw,
          draftsRaw,
          players
        });

        this.freeAgentMarketService.enrich(players, teams, leagueRaw);
        const playersSorted = sortPlayers(players, sortFields);

        return { league, players: playersSorted, teams, drafts };
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
}
