import type { RawTransaction } from '../models/transaction.models';
import { mergeCompletedRawTransactions } from './transaction-history.util';

describe('transaction-history.util', () => {
  it('keeps only completed transactions', () => {
    const complete = createTransaction('complete-1', '2025', 'complete');
    const failed = createTransaction('failed-1', '2025', 'failed');

    expect(mergeCompletedRawTransactions([[complete, failed]])).toEqual([complete]);
  });

  it('deduplicates the same transaction within one season', () => {
    const transaction = createTransaction('duplicate-1', '2025');

    expect(mergeCompletedRawTransactions([[transaction], [transaction]])).toEqual([transaction]);
  });

  it('keeps equal transaction ids from different seasons', () => {
    const current = createTransaction('shared-id', '2026');
    const historical = createTransaction('shared-id', '2025');

    expect(mergeCompletedRawTransactions([[current], [historical]])).toEqual([
      current,
      historical
    ]);
  });

  function createTransaction(
    transactionID: string,
    season: string,
    status = 'complete'
  ): RawTransaction {
    return {
      Source: 'Sleeper',
      TransactionID: transactionID,
      Type: 'waiver',
      Status: status,
      Season: season,
      Week: 1,
      CreatedAt: 1,
      CreatedDate: `${season}-01-01`,
      RosterIDs: [1],
      Adds: {},
      Drops: {},
      DraftPicks: [],
      Notes: null
    };
  }
});
