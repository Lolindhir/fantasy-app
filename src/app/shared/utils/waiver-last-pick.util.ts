import type { Transaction } from '../../core/models/transaction.models';

/**
 * Presentation-only summary of completed acquisitions through waivers.
 * EffectiveAt is the actual processing time; CreatedAt only tracks claim submission.
 * The caller supplies the displayed season because current Transactions are season-scoped.
 */
export function buildLastWaiverPickByTeam(
  transactions: readonly Transaction[],
  season: string
): Record<number, number> {
  const latestByTeam: Record<number, number> = {};

  for (const transaction of transactions) {
    if (
      transaction.Season !== season
      || transaction.Type.toLowerCase() !== 'waiver'
      || transaction.Status.toLowerCase() !== 'complete'
      || !Number.isFinite(transaction.EffectiveAt)
      || transaction.EffectiveAt <= 0
    ) {
      continue;
    }

    for (const participant of transaction.Participants) {
      if (participant.AddedPlayers.length === 0 || !Number.isFinite(participant.RosterID)) {
        continue;
      }

      latestByTeam[participant.RosterID] = Math.max(
        latestByTeam[participant.RosterID] ?? 0,
        transaction.EffectiveAt
      );
    }
  }

  return latestByTeam;
}
