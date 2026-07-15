import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of } from 'rxjs';

import type { RawLeague } from '../models/league.models';
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
      'getTimestamps'
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
