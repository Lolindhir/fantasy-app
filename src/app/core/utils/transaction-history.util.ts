import type { RawTransaction } from '../models/transaction.models';

export function mergeRawTransactions(
  transactionLists: RawTransaction[][]
): RawTransaction[] {
  const transactionsByKey = new Map<string, RawTransaction>();

  for (const transactionList of transactionLists ?? []) {
    for (const transaction of transactionList ?? []) {
      const key = `${transaction.Season}:${transaction.TransactionID}`;

      if (!transactionsByKey.has(key)) {
        transactionsByKey.set(key, transaction);
      }
    }
  }

  return Array.from(transactionsByKey.values());
}
