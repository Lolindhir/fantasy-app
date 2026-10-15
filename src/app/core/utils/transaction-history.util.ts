import type { RawTransaction } from '../models/transaction.models';

export function mergeCompletedRawTransactions(
  transactionLists: RawTransaction[][]
): RawTransaction[] {
  const transactionsByKey = new Map<string, RawTransaction>();

  for (const transactionList of transactionLists ?? []) {
    for (const transaction of transactionList ?? []) {
      if (transaction.Status?.toLowerCase() !== 'complete') {
        continue;
      }

      const key = `${transaction.Season}:${transaction.TransactionID}`;

      if (!transactionsByKey.has(key)) {
        transactionsByKey.set(key, transaction);
      }
    }
  }

  return Array.from(transactionsByKey.values());
}
