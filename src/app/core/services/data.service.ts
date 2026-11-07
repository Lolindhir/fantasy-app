import { inject, Injectable } from '@angular/core';
import { forkJoin, Observable, of } from 'rxjs';
import { catchError, map, shareReplay, switchMap } from 'rxjs/operators';

import { mapRawLeagueData } from '../mappers/league.mapper';
import { mapRawPlayerToPlayer } from '../mappers/player.mapper';
import { mapRawTransactions } from '../mappers/transaction.mapper';
import type { DecisionWindowsReadModel } from '../models/decision-window.models';
import type { RawDraft } from '../models/draft.models';
import type {
  FantasyGameContextProjectionDisplay,
  FantasyGameContextReadModel
} from '../models/fantasy-game-context.models';
import type { FantasyTeam, League, RawLeague } from '../models/league.models';
import type { MatchupProjectionsReadModel } from '../models/matchup-projections.models';
import type { MatchupsReadModel } from '../models/matchup.models';
import type {
  PlayerWeekFantasyProjection,
  PlayerWeekFantasyReadModel
} from '../models/player-week-fantasy.models';
import type {
  NFLTeam,
  Player,
  SortField,
  TopPlayersSalaryResult
} from '../models/player.models';
import type { RawTransaction, Transaction } from '../models/transaction.models';
import type { WeeklyRecapsReadModel } from '../models/weekly-recap.models';
import { mergeCompletedRawTransactions } from '../utils/transaction-history.util';
import { buildPlayerWeekProjections, type PlayerWeekProjectionView } from '../../shared/utils/player-week-projection.util';
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
import { verifyTeamCapOutlook } from '../models/team-cap-outlook.models';

export interface LeagueWithPlayers {
  league: League;
  players: Player[];
  teams: FantasyTeam[];
  drafts: RawDraft[];
}

export interface PlayerJourneySources {
  transactions: Transaction[];
  drafts: RawDraft[];
  teams: FantasyTeam[];
}

export interface LeagueWithPlayersAndTransactions extends LeagueWithPlayers {
  transactions: Transaction[];
}

function buildProjectionByPlayerID(
  playerWeekFantasy: PlayerWeekFantasyReadModel
): Map<string, PlayerWeekFantasyProjection> | null {
  const result = new Map<string, PlayerWeekFantasyProjection>();

  for (const record of playerWeekFantasy.Records ?? []) {
    if (record.PlayerID === null || record.PlayerID === undefined || String(record.PlayerID).trim() === '') continue;
    const playerID = String(record.PlayerID);
    if (result.has(playerID)) return null;
    result.set(playerID, record.Projection);
  }

  return result;
}

function sameTarget(
  context: FantasyGameContextReadModel,
  snapshot: { Season: string | number; Week: number }
): boolean {
  return String(context.Season) === String(snapshot.Season)
    && Number(context.Week) === Number(snapshot.Week);
}

/**
 * Joins published projection data onto the current FantasyGameContext. This is a pure join:
 * projections, ranges, display level and axes are published data and are never calculated here.
 * Each snapshot joins only when its Season and Week match; otherwise the context is left as is.
 */
function enrichFantasyGameContextWithProjections(
  context: FantasyGameContextReadModel,
  playerWeekFantasy: PlayerWeekFantasyReadModel | null,
  matchupProjections: MatchupProjectionsReadModel | null
): FantasyGameContextReadModel {
  let result = context;
  const display: FantasyGameContextProjectionDisplay = {
    PlayerRangeLevel: null,
    PlayerRangeAxis: null,
    TeamRangeLevel: null
  };

  const projectionByPlayerID = playerWeekFantasy && sameTarget(context, playerWeekFantasy)
    ? buildProjectionByPlayerID(playerWeekFantasy)
    : null;
  if (projectionByPlayerID && playerWeekFantasy) {
    display.PlayerRangeLevel = playerWeekFantasy.Display?.RangeLevel ?? null;
    display.PlayerRangeAxis = playerWeekFantasy.Display?.RangeAxis ?? null;
    result = {
      ...result,
      Games: result.Games.map(game => ({
        ...game,
        FantasyTeams: game.FantasyTeams.map(team => ({
          ...team,
          Players: team.Players.map(player => ({
            ...player,
            Prediction: projectionByPlayerID.get(String(player.PlayerID)) ?? null
          }))
        }))
      }))
    };
  }

  if (matchupProjections && sameTarget(context, matchupProjections)) {
    const projectionByMatchupID = new Map(
      matchupProjections.Matchups.map(matchup => [matchup.FantasyMatchupID, matchup])
    );
    display.TeamRangeLevel = matchupProjections.DisplayLevel;
    result = {
      ...result,
      FantasyMatchups: result.FantasyMatchups.map(matchup => ({
        ...matchup,
        Projection: projectionByMatchupID.get(matchup.FantasyMatchupID) ?? null
      }))
    };
  }

  return result === context ? context : { ...result, ProjectionDisplay: display };
}

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private dataApiService = inject(DataApiService);
  private freeAgentMarketService = inject(FreeAgentMarketService);
  private playerWeekProjections$?: Observable<ReadonlyMap<string, PlayerWeekProjectionView>>;
  private playerJourneySources$?: Observable<PlayerJourneySources>;

  getLeagueTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.League));
  }

  getMatchupsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.Matchups));
  }

  getPlayersTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.Players));
  }

  getTeamsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.Teams));
  }

  getDraftsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.Drafts));
  }

  getTransactionsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.Transactions));
  }

  getDecisionWindowsTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.DecisionWindows));
  }

  getFantasyGameContextTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(map(ts => ts.FantasyGameContext));
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return this.dataApiService.getTimestamps().pipe(
      map(ts => {
        return [ts.League, ts.Matchups, ts.Players, ts.Teams, ts.Drafts, ts.Transactions, ts.DecisionWindows, ts.FantasyGameContext]
          .reduce<string | undefined>((a, b) => {
            if (a === undefined) return b;
            if (b === undefined) return a;
            return a > b ? a : b;
          }, undefined);
      })
    );
  }

  getFantasyTeams(sortFields: SortField[] = ['NameLast']): Observable<FantasyTeam[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(map(res => res.teams));
  }

  getNflTeams(): Observable<NFLTeam[]> {
    return this.dataApiService.getNflTeamsRaw();
  }

  getAllPlayers(sortFields: SortField[] = ['NameLast']): Observable<Player[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(map(res => res.players));
  }

  getLeague(sortFields: SortField[] = ['NameLast']): Observable<League> {
    return this.getLeagueWithPlayers(sortFields).pipe(map(res => res.league));
  }

  getTransactions(sortFields: SortField[] = ['NameLast']): Observable<Transaction[]> {
    return this.getLeagueWithPlayersAndTransactions(sortFields).pipe(map(res => res.transactions));
  }

  getDecisionWindows(): Observable<DecisionWindowsReadModel> {
    return this.dataApiService.getDecisionWindowsRaw();
  }

  getMatchups(): Observable<MatchupsReadModel> {
    return this.dataApiService.getMatchupsRaw();
  }

  getPlayerWeekFantasy(): Observable<PlayerWeekFantasyReadModel> {
    return this.dataApiService.getPlayerWeekFantasyRaw();
  }

  /**
   * Published projection of the current App week per Sleeper player ID (pure join, nothing is
   * calculated). When the file cannot be read the map is empty and lists show "–".
   */
  getPlayerWeekProjections(): Observable<ReadonlyMap<string, PlayerWeekProjectionView>> {
    this.playerWeekProjections$ ??= this.getPlayerWeekFantasy().pipe(
      map(model => buildPlayerWeekProjections(model)),
      catchError(() => of(buildPlayerWeekProjections(null))),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.playerWeekProjections$;
  }

  /**
   * All completed transactions and drafts of the league history (current season plus every past
   * season the index lists), for chaining one player's journey. Missing past files are skipped.
   */
  getPlayerJourneySources(): Observable<PlayerJourneySources> {
    this.playerJourneySources$ ??= this.getLeagueWithPlayers().pipe(
      switchMap(({ league, drafts, teams }) =>
        this.getPastSeasonsIndex().pipe(
          catchError(() => of({ GeneratedAt: null, Seasons: [] } as PastSeasonsIndex)),
          switchMap(index => {
            const seasons = (index.Seasons ?? []).filter(entry => Number(entry.Season) < Number(league.Season));
            const transactionPaths = seasons
              .map(entry => entry.Resources?.Transactions)
              .flatMap(resource => resource?.Exists === true && resource.Path ? [resource.Path] : []);
            const draftPaths = seasons
              .map(entry => entry.Resources?.Drafts)
              .flatMap(resource => resource?.Exists === true && resource.Path ? [resource.Path] : []);
            const pastDrafts$ = draftPaths.length
              ? forkJoin(draftPaths.map(path =>
                this.getPastDraftsRaw(path).pipe(catchError(() => of([] as RawDraft[]))))
              )
              : of([] as RawDraft[][]);
            return forkJoin({
              transactions: this.getTransactionsForSources(true, transactionPaths),
              pastDrafts: pastDrafts$
            }).pipe(
              map(({ transactions, pastDrafts }) => ({
                transactions,
                drafts: [...drafts, ...pastDrafts.flat()],
                teams
              }))
            );
          })
        )
      ),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.playerJourneySources$;
  }

  getMatchupProjections(): Observable<MatchupProjectionsReadModel> {
    return this.dataApiService.getMatchupProjectionsRaw();
  }

  getFantasyGameContext(): Observable<FantasyGameContextReadModel> {
    return forkJoin({
      context: this.dataApiService.getFantasyGameContextRaw(),
      playerWeekFantasy: this.getPlayerWeekFantasy().pipe(catchError(() => of(null))),
      matchupProjections: this.getMatchupProjections().pipe(catchError(() => of(null)))
    }).pipe(
      map(({ context, playerWeekFantasy, matchupProjections }) =>
        enrichFantasyGameContextWithProjections(context, playerWeekFantasy, matchupProjections))
    );
  }

  getWeeklyRecaps(): Observable<WeeklyRecapsReadModel> {
    return this.dataApiService.getWeeklyRecapsRaw();
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

  getPastMatchupsRaw(path: string): Observable<MatchupsReadModel> {
    return this.dataApiService.getPastMatchupsRaw(path);
  }

  getPastWeeklyRecapsRaw(path: string): Observable<WeeklyRecapsReadModel> {
    return this.dataApiService.getPastWeeklyRecapsRaw(path);
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

    const outlooks = verifyTeamCapOutlook(data.capOutlookRaw, data.leagueRaw, data.playersRaw);
    teams.forEach(team => {
      team.CapOutlook = outlooks.get(team.TeamID);
      team.CapOutlookAsOfWeek = team.CapOutlook ? data.capOutlookRaw?.AsOfFinalScoredWeek : undefined;
    });
    this.freeAgentMarketService.enrich(players, teams, data.leagueRaw as RawLeague, outlooks);

    return {
      league,
      players: sortPlayers(players, sortFields),
      teams,
      drafts
    };
  }
}
