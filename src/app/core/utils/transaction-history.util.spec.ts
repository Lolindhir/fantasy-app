import type { RawTransaction } from '../models/transaction.models';
import { mergeRawTransactions } from './transaction-history.util';

describe('transaction-history.util', () => {
  it('deduplicates the same transaction within one season', () => {
    const transaction = createTransaction('duplicate-1', '2025');

    expect(mergeRawTransactions([[transaction], [transaction]])).toEqual([transaction]);
  });

  it('keeps equal transaction ids from different seasons', () => {
    const current = createTransaction('shared-id', '2026');
    const historical = createTransaction('shared-id', '2025');

    expect(mergeRawTransactions([[current], [historical]])).toEqual([
      current,
      historical
    ]);
  });

  function createTransaction(
    transactionID: string,
    season: string
  ): RawTransaction {
    return {
      Source: 'Sleeper',
      TransactionID: transactionID,
      Type: 'waiver',
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
