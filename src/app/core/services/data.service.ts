import { inject, Injectable } from '@angular/core';
import { forkJoin, Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { mapRawLeagueData } from '../mappers/league.mapper';
import { mapRawPlayerToPlayer } from '../mappers/player.mapper';
import { mapRawTransactions } from '../mappers/transaction.mapper';
import type { DecisionWindowsReadModel } from '../models/decision-window.models';
import type { RawDraft } from '../models/draft.models';
import type {
  FantasyGameContextReadModel,
  FantasyGameContextTeamPrediction
} from '../models/fantasy-game-context.models';
import type { FantasyTeam, League, RawLeague } from '../models/league.models';
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

function predictionTeamKey(fantasyMatchupID: string, fantasyTeamID: string | number): string {
  return `${fantasyMatchupID}::${String(fantasyTeamID)}`;
}

function roundPredictionPoints(value: number): number {
  return Math.round(value * 10_000) / 10_000;
}

interface StarterGameOutcome {
  isFinal: boolean;
  points: number | null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
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

function enrichFantasyGameContextWithPredictions(
  context: FantasyGameContextReadModel,
  playerWeekFantasy: PlayerWeekFantasyReadModel
): FantasyGameContextReadModel {
  if (
    String(context.Season) !== String(playerWeekFantasy.Season)
    || Number(context.Week) !== Number(playerWeekFantasy.Week)
  ) {
    return context;
  }

  const projectionByPlayerID = buildProjectionByPlayerID(playerWeekFantasy);
  if (!projectionByPlayerID) return context;

  const starterIDsByTeam = new Map<string, Set<string>>();
  const addStarter = (
    fantasyMatchupID: string | null | undefined,
    fantasyTeamID: string | number,
    playerID: string
  ): void => {
    if (!fantasyMatchupID) return;
    const key = predictionTeamKey(fantasyMatchupID, fantasyTeamID);
    const current = starterIDsByTeam.get(key) ?? new Set<string>();
    current.add(String(playerID));
    starterIDsByTeam.set(key, current);
  };

  const outcomesByTeam = new Map<string, Map<string, StarterGameOutcome>>();
  const games = context.Games.map(game => ({
    ...game,
    FantasyTeams: game.FantasyTeams.map(team => ({
      ...team,
      Players: team.Players.map(player => {
        if (player.IsStarter) {
          addStarter(team.FantasyMatchupID, team.FantasyTeamID, player.PlayerID);
          const key = predictionTeamKey(team.FantasyMatchupID, team.FantasyTeamID);
          const outcomes = outcomesByTeam.get(key) ?? new Map<string, StarterGameOutcome>();
          outcomes.set(String(player.PlayerID), {
            isFinal: /^Final/i.test(game.Status ?? ''),
            points: isFiniteNumber(player.Points) ? player.Points : null
          });
          outcomesByTeam.set(key, outcomes);
        }
        return {
          ...player,
          Prediction: projectionByPlayerID.get(String(player.PlayerID)) ?? null
        };
      })
    }))
  }));

  const byeStarterIDsByTeam = new Map<string, Set<string>>();
  for (const association of context.NonGameAssociations) {
    if (association.IsStarter) {
      addStarter(association.FantasyMatchupID, association.FantasyTeamID, association.PlayerID);
      // Only an explicit bye (known NFL team without a game this week) is a certain zero.
      // Unknown or team-less starters stay unresolved.
      if (association.Kind === 'bye' && association.FantasyMatchupID) {
        const key = predictionTeamKey(association.FantasyMatchupID, association.FantasyTeamID);
        const current = byeStarterIDsByTeam.get(key) ?? new Set<string>();
        current.add(String(association.PlayerID));
        byeStarterIDsByTeam.set(key, current);
      }
    }
  }

  const fantasyMatchups = context.FantasyMatchups.map(matchup => ({
    ...matchup,
    TeamPredictions: matchup.TeamIDs.map(teamID => {
      const teamKey = predictionTeamKey(matchup.FantasyMatchupID, teamID);
      const starterIDs = Array.from(starterIDsByTeam.get(teamKey) ?? []);
      const outcomes = outcomesByTeam.get(teamKey);
      const byeStarterIDs = byeStarterIDsByTeam.get(teamKey);
      const byeStarterPlayerIDs: string[] = [];
      const unavailableStarterPlayerIDs: string[] = [];
      let projectedStarterPoints = 0;
      let projectedStarterCount = 0;
      let projectedFinalPoints = 0;
      let projectedFinalComplete = starterIDs.length > 0;

      for (const playerID of starterIDs) {
        if (byeStarterIDs?.has(playerID)) {
          byeStarterPlayerIDs.push(playerID);
          projectedStarterCount += 1;
          continue;
        }

        const projection = projectionByPlayerID.get(playerID);
        const outcome = outcomes?.get(playerID);
        const projectedPoints = projection?.Status === 'available' && isFiniteNumber(projection.Points)
          ? projection.Points
          : null;

        // Final games contribute their actual points. A game that has not finished contributes its
        // projection but never less than the points already scored, so live scoring is not counted twice.
        if (outcome?.isFinal) {
          if (outcome.points === null) projectedFinalComplete = false;
          else projectedFinalPoints += outcome.points;
        } else if (projectedPoints === null) {
          projectedFinalComplete = false;
        } else {
          projectedFinalPoints += Math.max(outcome?.points ?? 0, projectedPoints);
        }

        if (projectedPoints !== null) {
          projectedStarterCount += 1;
          projectedStarterPoints += projectedPoints;
        } else {
          unavailableStarterPlayerIDs.push(playerID);
        }
      }

      const starterCount = starterIDs.length;
      const state: FantasyGameContextTeamPrediction['State'] =
        starterCount > 0 && projectedStarterCount === starterCount
          ? 'available'
          : projectedStarterCount > 0
            ? 'partial'
            : 'unavailable';
      const roundedProjectedStarterPoints = roundPredictionPoints(projectedStarterPoints);

      return {
        FantasyTeamID: teamID,
        State: state,
        StarterCount: starterCount,
        ProjectedStarterCount: projectedStarterCount,
        ProjectedStarterPoints: roundedProjectedStarterPoints,
        PredictedEndScore: state === 'available' ? roundedProjectedStarterPoints : null,
        ProjectedFinalScore: projectedFinalComplete ? roundPredictionPoints(projectedFinalPoints) : null,
        ByeStarterPlayerIDs: byeStarterPlayerIDs.sort(),
        UnavailableStarterPlayerIDs: unavailableStarterPlayerIDs.sort()
      };
    })
  }));

  return {
    ...context,
    Games: games,
    FantasyMatchups: fantasyMatchups
  };
}

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private dataApiService = inject(DataApiService);
  private freeAgentMarketService = inject(FreeAgentMarketService);

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

  getFantasyGameContext(): Observable<FantasyGameContextReadModel> {
    return forkJoin({
      context: this.dataApiService.getFantasyGameContextRaw(),
      playerWeekFantasy: this.getPlayerWeekFantasy().pipe(catchError(() => of(null)))
    }).pipe(
      map(({ context, playerWeekFantasy }) => playerWeekFantasy
        ? enrichFantasyGameContextWithPredictions(context, playerWeekFantasy)
        : context)
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
