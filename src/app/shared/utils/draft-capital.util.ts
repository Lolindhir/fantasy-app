import type { DraftPick } from '../../core/models/fantasy.models';

export interface DraftPickStrength {
  roundCounts: number[];
  totalPickCount: number;
  bestPick: DraftPick | null;
}

export function compareDraftPicksByDraftOrder(a: DraftPick, b: DraftPick): number {
  const roundDiff = sortNumber(a.Round, 999) - sortNumber(b.Round, 999);
  if (roundDiff !== 0) return roundDiff;

  const positionDiff = sortNumber(a.PositionInRound, 999) - sortNumber(b.PositionInRound, 999);
  if (positionDiff !== 0) return positionDiff;

  return sortNumber(a.OverallPick, 9999) - sortNumber(b.OverallPick, 9999);
}

export function compareDraftPicksByDraftThenOrder(a: DraftPick, b: DraftPick): number {
  const draftNoDiff = sortNumber(a.Draft?.DraftNo, 999) - sortNumber(b.Draft?.DraftNo, 999);
  if (draftNoDiff !== 0) return draftNoDiff;

  return compareDraftPicksByDraftOrder(a, b);
}

export function getDraftPickStrength(picks: DraftPick[], maxRound?: number | null): DraftPickStrength {
  const effectiveMaxRound = getEffectiveMaxRound(picks, maxRound);

  return {
    roundCounts: getDraftPickRoundCounts(picks, effectiveMaxRound),
    totalPickCount: picks.length,
    bestPick: getBestDraftPick(picks)
  };
}

export function getDraftPickRoundCounts(picks: DraftPick[], maxRound?: number | null): number[] {
  const effectiveMaxRound = getEffectiveMaxRound(picks, maxRound);
  const roundCounts = Array.from({ length: effectiveMaxRound }, () => 0);

  picks.forEach(pick => {
    const roundIndex = sortNumber(pick.Round, 0) - 1;
    if (roundIndex >= 0 && roundIndex < effectiveMaxRound) roundCounts[roundIndex] += 1;
  });

  return roundCounts;
}

export function getBestDraftPick(picks: DraftPick[]): DraftPick | null {
  return [...picks].sort(compareDraftPicksByDraftThenOrder)[0] ?? null;
}

export function compareDraftPickStrength(a: DraftPickStrength, b: DraftPickStrength): number {
  const maxRound = Math.max(a.roundCounts.length, b.roundCounts.length);

  for (let index = 0; index < maxRound; index++) {
    const diff = (b.roundCounts[index] ?? 0) - (a.roundCounts[index] ?? 0);
    if (diff !== 0) return diff;
  }

  const totalPickDiff = b.totalPickCount - a.totalPickCount;
  if (totalPickDiff !== 0) return totalPickDiff;

  return compareNullableDraftPicks(a.bestPick, b.bestPick);
}

export function compareDraftPickCollectionsByStrength(
  a: DraftPick[],
  b: DraftPick[],
  maxRound?: number | null
): number {
  const effectiveMaxRound = maxRound ?? Math.max(getMaxDraftPickRound(a), getMaxDraftPickRound(b), 1);

  return compareDraftPickStrength(
    getDraftPickStrength(a, effectiveMaxRound),
    getDraftPickStrength(b, effectiveMaxRound)
  );
}

export function getMaxDraftPickRound(picks: DraftPick[]): number {
  return Math.max(...picks.map(pick => sortNumber(pick.Round, 0)), 1);
}

function compareNullableDraftPicks(a: DraftPick | null, b: DraftPick | null): number {
  if (a && !b) return -1;
  if (!a && b) return 1;
  if (!a || !b) return 0;

  return compareDraftPicksByDraftThenOrder(a, b);
}

function getEffectiveMaxRound(picks: DraftPick[], maxRound?: number | null): number {
  return Math.max(sortNumber(maxRound, 0), getMaxDraftPickRound(picks), 1);
}

function sortNumber(value: number | null | undefined, fallback: number): number {
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : fallback;
}
