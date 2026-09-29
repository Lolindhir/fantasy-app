import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of, throwError } from 'rxjs';

import type { FantasyGameContextReadModel } from '../models/fantasy-game-context.models';
import type { RawLeague } from '../models/league.models';
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
      'getPlayerWeekFantasyRaw'
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


  it('joins PlayerWeekFantasy into FantasyGameContext and aggregates complete team predictions', async () => {
    const context = createFantasyGameContext();
    dataApiService.getFantasyGameContextRaw.and.returnValue(of(context));
    dataApiService.getPlayerWeekFantasyRaw.and.returnValue(of(createPlayerWeekFantasy()));

    const result = await firstValueFrom(service.getFantasyGameContext());
    const matchup = result.FantasyMatchups[0];
    const team1 = matchup.TeamPredictions?.find(team => String(team.FantasyTeamID) === '1');
    const team2 = matchup.TeamPredictions?.find(team => String(team.FantasyTeamID) === '2');

    expect(result.Games[0].FantasyTeams[0].Players[0].Prediction?.Points).toBe(10);
    expect(result.Games[0].FantasyTeams[0].Players[1].Prediction?.Points).toBe(99);

    expect(team1).toEqual(jasmine.objectContaining({
      State: 'available',
      StarterCount: 2,
      ProjectedStarterCount: 2,
      ProjectedStarterPoints: 15,
      PredictedEndScore: 15,
      UnavailableStarterPlayerIDs: []
    }));

    expect(team2).toEqual(jasmine.objectContaining({
      State: 'partial',
      StarterCount: 2,
      ProjectedStarterCount: 1,
      ProjectedStarterPoints: 20,
      PredictedEndScore: null,
      UnavailableStarterPlayerIDs: ['p5']
    }));
  });

  it('keeps raw FantasyGameContext when the prediction snapshot targets another week', async () => {
    const context = createFantasyGameContext();
    const playerWeekFantasy = createPlayerWeekFantasy();
    playerWeekFantasy.Week = 4;
    dataApiService.getFantasyGameContextRaw.and.returnValue(of(context));
    dataApiService.getPlayerWeekFantasyRaw.and.returnValue(of(playerWeekFantasy));

    const result = await firstValueFrom(service.getFantasyGameContext());

    expect(result).toBe(context);
    expect(result.FantasyMatchups[0].TeamPredictions).toBeUndefined();
  });

  it('keeps raw FantasyGameContext when PlayerWeekFantasy cannot be loaded', async () => {
    const context = createFantasyGameContext();
    dataApiService.getFantasyGameContextRaw.and.returnValue(of(context));
    dataApiService.getPlayerWeekFantasyRaw.and.returnValue(
      throwError(() => new Error('prediction publication unavailable'))
    );

    const result = await firstValueFrom(service.getFantasyGameContext());

    expect(result).toBe(context);
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
      Records: [
        createPlayerWeekRecord('p1', 'available', 10),
        createPlayerWeekRecord('p2', 'available', 99),
        createPlayerWeekRecord('p3', 'available', 20),
        createPlayerWeekRecord('p4', 'available', 5),
        createPlayerWeekRecord('p5', 'no-game', null)
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
