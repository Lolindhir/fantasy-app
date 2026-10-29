import type { NFLTeam } from '../../core/models/player.models';

type NflTeamKeySource = Pick<NFLTeam, 'ID' | 'LegacyIDs'>;

function normalizeKey(value: string | number | null | undefined): string {
  return String(value ?? '').trim().toUpperCase();
}

/**
 * Finds an NFL team by its current ID or any LegacyIDs entry (#347 F3b). Generated data may carry
 * either key form while producers switch to the canonical abbreviation one at a time, so every
 * lookup of an NFL team by a generated team reference must go through this function.
 */
export function findNflTeam<T extends NflTeamKeySource>(
  nflTeams: readonly T[],
  key: string | number | null | undefined
): T | null {
  const wanted = normalizeKey(key);
  if (!wanted) return null;

  return nflTeams.find(team => normalizeKey(team.ID) === wanted)
    ?? nflTeams.find(team => (team.LegacyIDs ?? []).some(legacyId => normalizeKey(legacyId) === wanted))
    ?? null;
}

/** Canonical team ID for a reference; unresolvable references are returned trimmed and unchanged. */
export function canonicalNflTeamKey(
  nflTeams: readonly NflTeamKeySource[],
  key: string | number | null | undefined
): string {
  return findNflTeam(nflTeams, key)?.ID ?? String(key ?? '').trim();
}

/** True when both references denote the same NFL team, whatever key form each one uses. */
export function nflTeamKeysMatch(
  nflTeams: readonly NflTeamKeySource[],
  left: string | number | null | undefined,
  right: string | number | null | undefined
): boolean {
  const leftKey = canonicalNflTeamKey(nflTeams, left);
  const rightKey = canonicalNflTeamKey(nflTeams, right);
  return leftKey !== '' && normalizeKey(leftKey) === normalizeKey(rightKey);
}
