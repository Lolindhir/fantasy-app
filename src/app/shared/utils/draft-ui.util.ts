export type DraftStatusClass = 'completed' | 'live' | 'upcoming' | 'unknown';

export function getDraftRoundColor(round: number | null | undefined, maxRound: number | null | undefined): string {
  const normalizedRound = Math.max(Number(round) || 1, 1);
  const normalizedMaxRound = Math.max(Number(maxRound) || 1, 1);
  const denominator = Math.max(normalizedMaxRound - 1, 1);
  const progress = Math.max(normalizedRound - 1, 0) / denominator;
  const hue = 25 + progress * 150;

  return `hsl(${hue}, 70%, 84%)`;
}

export function getDraftStatusClass(status: string | null | undefined): DraftStatusClass {
  const normalizedStatus = (status ?? '').toLowerCase();

  if (['complete', 'completed', 'closed'].includes(normalizedStatus)) return 'completed';
  if (['live', 'drafting'].includes(normalizedStatus)) return 'live';
  if (['pre_draft', 'upcoming'].includes(normalizedStatus)) return 'upcoming';
  return 'unknown';
}
