import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of, throwError } from 'rxjs';

import type { FantasyGameContextReadModel } from '../models/fantasy-game-context.models';
import type { RawLeague } from '../models/league.models';
import type { MatchupProjectionsReadModel } from '../models/matchup-projections.models';
import type {
  PlayerWeekFantasyProjectionStatus,
  PlayerWeekFantasyReadModel,
  PlayerWeekFantasyRecord
} from '../models/player-week-fantasy.models';
import type { RawTransaction } from '../models/transaction.models';
import { DataApiService, type MovesDataLoadResult } from './data-api.service';
import { DataService } from './data.service';
import { FreeAgentMarketService } from './free-agent-market.service';

describe('DataService', () => {
  let service: DataService;
  let dataApiService: jasmine.SpyObj<DataApiService>;
  let freeAgentMarketService: jasmine.SpyObj<FreeAgentMarketService>;

  beforeEach(() => {
    dataApiService = jasmine.createSpyObj<DataApiService>('DataApiService', [
      'getMovesData',
      'getTimestamps',
      'getFantasyGameContextRaw',
      'getPlayerWeekFantasyRaw',
      'getMatchupProjectionsRaw'
    ]);
    freeAgentMarketService = jasmine.createSpyObj<FreeAgentMarketService>(
      'FreeAgentMarketService',
      ['enrich']
    );

    TestBed.configureTestingModule({
      providers: [
        DataService,
        { provide: DataApiService, useValue: dataApiService },
        { provide: FreeAgentMarketService, useValue: freeAgentMarketService }
      ]
    });

    service = TestBed.inject(DataService);
  });

  it('maps raw move data through the shared league context', async () => {
    const rawTransaction = createRawTransaction();
    const movesData: MovesDataLoadResult = {
      leagueRaw: createRawLeague(),
      playersRaw: [],
      nflTeamsRaw: [],
      draftsRaw: [],
      transactionsRaw: [rawTransaction]
    };
    dataApiService.getMovesData.and.returnValue(of(movesData));

    const transactions = await firstValueFrom(service.getTransactions());

    expect(dataApiService.getMovesData).toHaveBeenCalledTimes(1);
    expect(freeAgentMarketService.enrich).toHaveBeenCalled();
    expect(transactions.length).toBe(1);
    expect(transactions[0].TransactionID).toBe(rawTransaction.TransactionID);
    expect(transactions[0].Participants[0].RosterID).toBe(1);
  });

  it('exposes the transaction timestamp and includes it in the latest timestamp', async () => {
    dataApiService.getTimestamps.and.returnValue(of({
      League: '2026-07-15T07:33:08Z',
      Players: '2026-07-15T09:51:25Z',
      Teams: '2025-09-29T18:38:52Z',
      Drafts: '2026-07-15T05:44:52Z',
      Transactions: '2026-07-15T10:00:00Z'
    }));

    const transactionTimestamp = await firstValueFrom(service.getTransactionsTimestamp());
    const latestTimestamp = await firstValueFrom(service.getLatestTimestamp());

    expect(transactionTimestamp).toBe('2026-07-15T10:00:00Z');
    expect(latestTimestamp).toBe('2026-07-15T10:00:00Z');
  });


  describe('published projections', () => {
    function stub(
      context: FantasyGameContextReadModel,
      playerWeekFantasy: PlayerWeekFantasyReadModel | null,
      matchupProjections: MatchupProjectionsReadModel | null
    ): void {
      dataApiService.getFantasyGameContextRaw.and.returnValue(of(context));
      dataApiService.getPlayerWeekFantasyRaw.and.returnValue(
        playerWeekFantasy ? of(playerWeekFantasy) : throwError(() => new Error('unavailable'))
      );
      dataApiService.getMatchupProjectionsRaw.and.returnValue(
        matchupProjections ? of(matchupProjections) : throwError(() => new Error('unavailable'))
      );
    }

    it('joins player projections, display settings and matchup projections by id', async () => {
      stub(createFantasyGameContext(), createPlayerWeekFantasy(), createMatchupProjections());

      const result = await firstValueFrom(service.getFantasyGameContext());

      expect(result.Games[0].FantasyTeams[0].Players[0].Prediction?.Points).toBe(10);
      expect(result.Games[0].FantasyTeams[0].Players[1].Prediction?.Points).toBe(99);
      expect(result.Games[1].FantasyTeams[0].Players[0].Prediction?.PredictionRanges.length).toBe(1);
      expect(result.ProjectionDisplay).toEqual({
        PlayerRangeLevel: 0.9,
        PlayerRangeAxis: { Min: -5, Max: 45 },
        TeamRangeLevel: 0.8
      });
      expect(result.FantasyMatchups[0].Projection?.Teams.length).toBe(2);
      expect(result.FantasyMatchups[0].Projection?.Axis).toEqual({ Min: 120, Max: 260, Step: 20 });
    });

    it('passes published team values through without calculating anything', async () => {
      const projections = createMatchupProjections();
      projections.Matchups[0].Teams[0].ProjectedFinalScore = 123.45;
      projections.Matchups[0].Teams[0].Ranges = [{ Level: 0.8, Lower: 100.5, Upper: 150.25 }];
      stub(createFantasyGameContext(), createPlayerWeekFantasy(), projections);

      const result = await firstValueFrom(service.getFantasyGameContext());
      const team = result.FantasyMatchups[0].Projection?.Teams[0];

      // The starters' projections in the player snapshot sum to something else (15).
      expect(team?.ProjectedFinalScore).toBe(123.45);
      expect(team?.Ranges).toEqual([{ Level: 0.8, Lower: 100.5, Upper: 150.25 }]);
    });

    it('marks matchups the publication does not know with a null projection', async () => {
      const projections = createMatchupProjections();
      projections.Matchups[0].FantasyMatchupID = 'other';
      stub(createFantasyGameContext(), createPlayerWeekFantasy(), projections);

      const result = await firstValueFrom(service.getFantasyGameContext());

      expect(result.FantasyMatchups[0].Projection).toBeNull();
    });

    it('joins each snapshot independently by Season and Week', async () => {
      const staleMatchups = createMatchupProjections();
      staleMatchups.Week = 2;
      stub(createFantasyGameContext(), createPlayerWeekFantasy(), staleMatchups);
      const playersOnly = await firstValueFrom(service.getFantasyGameContext());
      expect(playersOnly.Games[0].FantasyTeams[0].Players[0].Prediction?.Points).toBe(10);
      expect(playersOnly.FantasyMatchups[0].Projection).toBeUndefined();
      expect(playersOnly.ProjectionDisplay?.TeamRangeLevel).toBeNull();

      const stalePlayers = createPlayerWeekFantasy();
      stalePlayers.Week = 4;
      stub(createFantasyGameContext(), stalePlayers, createMatchupProjections());
      const matchupsOnly = await firstValueFrom(service.getFantasyGameContext());
      expect(matchupsOnly.Games[0].FantasyTeams[0].Players[0].Prediction).toBeUndefined();
      expect(matchupsOnly.FantasyMatchups[0].Projection?.Teams.length).toBe(2);
      expect(matchupsOnly.ProjectionDisplay?.PlayerRangeLevel).toBeNull();
    });

    it('keeps raw FantasyGameContext when both snapshots target another week', async () => {
      const context = createFantasyGameContext();
      const players = createPlayerWeekFantasy();
      const matchups = createMatchupProjections();
      players.Week = 4;
      matchups.Week = 4;
      stub(context, players, matchups);

      const result = await firstValueFrom(service.getFantasyGameContext());

      expect(result).toBe(context);
    });

    it('does not join players when the snapshot has duplicate App PlayerIDs', async () => {
      const players = createPlayerWeekFantasy();
      players.Records.push(createPlayerWeekRecord('p1', 'available', 7));
      stub(createFantasyGameContext(), players, createMatchupProjections());

      const result = await firstValueFrom(service.getFantasyGameContext());

      expect(result.Games[0].FantasyTeams[0].Players[0].Prediction).toBeUndefined();
      expect(result.FantasyMatchups[0].Projection?.Teams.length).toBe(2);
    });

    it('keeps raw FantasyGameContext when no publication can be loaded', async () => {
      const context = createFantasyGameContext();
      stub(context, null, null);

      const result = await firstValueFrom(service.getFantasyGameContext());

      expect(result).toBe(context);
    });
  });

  function createRawTransaction(): RawTransaction {
    return {
      Source: 'Sleeper',
      TransactionID: 'transaction-1',
      Type: 'free_agent',
      Status: 'complete',
      Season: '2026',
      Week: 1,
      CreatedAt: 1782125163269,
      CreatedDate: '2026-06-22',
      RosterIDs: [1],
      Adds: {},
      Drops: { 'player-1': 1 },
      DraftPicks: [],
      Notes: null
    };
  }


  function createFantasyGameContext(): FantasyGameContextReadModel {
    const relevance = {
      RosteredPlayerCount: 0,
      StarterCount: 0,
      FantasyTeamCount: 0,
      FantasyMatchupCount: 0,
      UnknownAssociationCount: 0
    };
    const impact = {
      State: 'unavailable' as const,
      RosteredPoints: null,
      StarterPoints: null,
      OutcomeSwingMatchupCount: 0
    };

    return {
      SchemaVersion: 5,
      LeagueID: 'league-1',
      Season: '2026',
      Week: 3,
      ScoringState: 'partial',
      DecisionWindows: [],
      Games: [
        {
          GameID: 'g1',
          DecisionWindowID: 'w1',
          StartsAtUtc: '2026-09-27T17:00:00Z',
          AwayTeamID: 'A',
          AwayTeamAbbr: 'A',
          HomeTeamID: 'B',
          HomeTeamAbbr: 'B',
          Status: 'Scheduled',
          Relevance: relevance,
          Impact: impact,
          FantasyTeams: [
            {
              FantasyTeamID: 1,
              FantasyMatchupID: 'm1',
              RosteredPlayerCount: 2,
              StarterCount: 1,
              RosteredPoints: 0,
              StarterPoints: 0,
              Players: [
                { PlayerID: 'p1', IsStarter: true, Points: null },
                { PlayerID: 'p2', IsStarter: false, Points: null }
              ]
            },
            {
              FantasyTeamID: 2,
              FantasyMatchupID: 'm1',
              RosteredPlayerCount: 1,
              StarterCount: 1,
              RosteredPoints: 0,
              StarterPoints: 0,
              Players: [
                { PlayerID: 'p3', IsStarter: true, Points: null }
              ]
            }
          ]
        },
        {
          GameID: 'g2',
          DecisionWindowID: 'w2',
          StartsAtUtc: '2026-09-27T20:00:00Z',
          AwayTeamID: 'C',
          AwayTeamAbbr: 'C',
          HomeTeamID: 'D',
          HomeTeamAbbr: 'D',
          Status: 'Scheduled',
          Relevance: relevance,
          Impact: impact,
          FantasyTeams: [
            {
              FantasyTeamID: 1,
              FantasyMatchupID: 'm1',
              RosteredPlayerCount: 1,
              StarterCount: 1,
              RosteredPoints: 0,
              StarterPoints: 0,
              Players: [
                { PlayerID: 'p4', IsStarter: true, Points: null }
              ]
            }
          ]
        }
      ],
      FantasyMatchups: [
        {
          FantasyMatchupID: 'm1',
          TeamIDs: [1, 2],
          FinalScores: null,
          CounterfactualState: 'unavailable-not-final',
          Games: []
        }
      ],
      NonGameAssociations: [
        {
          FantasyTeamID: 2,
          FantasyMatchupID: 'm1',
          PlayerID: 'p5',
          NFLTeamID: null,
          IsStarter: true,
          Kind: 'no-game',
          Reason: 'No target-week NFL game'
        }
      ]
    };
  }

  function createPlayerWeekFantasy(): PlayerWeekFantasyReadModel {
    return {
      SchemaVersion: 1,
      CanonicalLeagueID: 'nfl-reise',
      Season: 2026,
      Week: 3,
      ScoringProfile: {
        ActiveSettingsCount: 41,
        FingerprintVersion: 1,
        Season: 2026,
        SettingsHash: 'sha256:test'
      },
      IdentityCoverage: {
        Provider: 'Sleeper',
        ResolvedRecordCount: 5,
        UnavailableRecordCount: 0
      },
      Display: { RangeLevel: 0.9, RangeAxis: { Min: -5, Max: 45 } },
      Records: [
        createPlayerWeekRecord('p1', 'available', 10),
        createPlayerWeekRecord('p2', 'available', 99),
        createPlayerWeekRecord('p3', 'available', 20),
        createPlayerWeekRecord('p4', 'available', 5),
        createPlayerWeekRecord('p5', 'no-game', null)
      ]
    };
  }

  function createMatchupProjections(): MatchupProjectionsReadModel {
    const team = (id: number, finalScore: number) => ({
      FantasyTeamID: id,
      State: 'available' as const,
      StarterCount: 2,
      ResolvedStarterCount: 2,
      FinalStarterCount: 0,
      ScoredPoints: 0,
      PregameProjectedScore: finalScore,
      ProjectedFinalScore: finalScore,
      StandardDeviation: 20,
      Ranges: [{ Level: 0.8, Lower: finalScore - 26, Upper: finalScore + 26 }],
      ByeStarterPlayerIDs: [],
      OutStarterPlayerIDs: [],
      UncertainStarterPlayerIDs: [],
      UnavailableStarterPlayerIDs: []
    });
    return {
      SchemaVersion: 1,
      CanonicalLeagueID: 'nfl-reise',
      Season: 2026,
      Week: 3,
      DisplayLevel: 0.8,
      Method: {
        Id: 'normal-independent-v1',
        Levels: [0.5, 0.8, 0.9],
        SigmaBasisLevel: 0.9,
        Assumption: 'starters score independently; player variances add',
        ParticipationCondition: 'conditional-on-participation'
      },
      Matchups: [
        {
          FantasyMatchupID: 'm1',
          Teams: [team(1, 180), team(2, 200)],
          Axis: { Min: 120, Max: 260, Step: 20 }
        }
      ]
    };
  }

  function createPlayerWeekRecord(
    playerID: string,
    status: PlayerWeekFantasyProjectionStatus,
    points: number | null
  ): PlayerWeekFantasyRecord {
    return {
      PlayerID: playerID,
      CanonicalPlayerID: `NFLP-${playerID}`,
      Projection: {
        AvailabilityAdjustmentApplied: false,
        HistoryGames: 8,
        IntervalModel: 'V4-C-PI1',
        ParticipationCondition: 'conditional-on-participation',
        PointModel: 'V4-C',
        Points: points,
        PredictionRange: status === 'available'
          ? { Level: 0.9, Lower: Math.max(-2, (points ?? 0) - 5), Upper: (points ?? 0) + 8 }
          : null,
        PredictionRanges: status === 'available'
          ? [{ Level: 0.9, Lower: Math.max(-2, (points ?? 0) - 5), Upper: (points ?? 0) + 8 }]
          : [],
        RangeQuality: status === 'available' ? 'player-volatility' : 'unavailable',
        Status: status
      },
      Actual: {
        Points: null,
        State: 'unavailable'
      }
    };
  }

  function createRawLeague(): RawLeague {
    return {
      LeagueID: 'league-1',
      Name: 'League',
      Avatar: '',
      Season: '2026',
      SeasonType: 'regular',
      Status: 'Off-Season',
      Phase: '',
      FinalScoredWeek: 0,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 15,
      TradeDeadlineWeek: 11,
      TradeReviewDays: 0,
      CutsAllowed: true,
      CutsMetaText: '',
      WaiversOpen: true,
      WaiversMetaText: '',
      TradesOpen: true,
      TradesMetaText: '',
      SalaryCap: 100,
      SalaryCapProjected: 100,
      CapDeadline: '2026-07-31',
      SalaryRelevantTeamSize: 0,
      Teams: [],
      Standings: []
    };
  }
});
