import type {
  PlayerAwardHistoryEntry,
  PlayerAwardHistoryPlayer,
  PlayerAwardHistoryReadModel,
  PlayerAwardKey
} from '../../core/models/player-award-history.models';

/** Display metadata of the weekly player awards (Issue #499); same wording as the Weeks page. */
export const PLAYER_AWARD_DISPLAY: ReadonlyArray<{ key: PlayerAwardKey; label: string; plural: string; icon: string; hint: string }> = [
  { key: 'MVP', label: 'Week MVP', plural: 'Week MVPs', icon: '🏆', hint: 'Highest-scoring player of the week' },
  { key: 'MatchupHero', label: 'Matchup Hero', plural: 'Matchup Heroes', icon: '⚡', hint: 'Decided a win that would otherwise have been lost' },
  { key: 'Heartbreaker', label: 'Heartbreaker', plural: 'Heartbreakers', icon: '💔', hint: 'Big week, but the team still lost' },
  { key: 'UnsungHero', label: 'Unsung Hero', plural: 'Unsung Heroes', icon: '🪑', hint: 'Bench player who would have flipped a lost matchup' }
];

export interface PlayerAwardHighlight {
  key: string;
  icon: string;
  title: string;
  owner: string;
  valueDisplay: string;
  reason: string;
}

/** Hall of Fame tiles from the published leaders; awards without a leader are skipped, ties are listed together. */
export function buildPlayerAwardHighlights(history: PlayerAwardHistoryReadModel | null | undefined): PlayerAwardHighlight[] {
  const leaders = history?.Leaders;
  if (!leaders) return [];
  const result: PlayerAwardHighlight[] = [];
  for (const def of PLAYER_AWARD_DISPLAY) {
    const list = leaders[def.key] ?? [];
    if (list.length === 0) continue;
    const count = list[0].Count;
    result.push({
      key: `player-award-${def.key}`,
      icon: def.icon,
      title: `Most ${def.plural}`,
      owner: list.length <= 2 ? list.map(l => l.Name).join(', ') : `${list.length} players tied`,
      valueDisplay: `${count}×`,
      reason: `${def.hint}. ${list.map(l => l.Name).join(', ')} ${list.length > 1 ? 'share' : 'holds'} the record with ${count}.`
    });
  }
  return result;
}

export interface PlayerAwardSeasonGroup {
  season: number;
  entries: Array<{ week: number; award: PlayerAwardKey; label: string; icon: string; points: number | null }>;
}

export function findPlayerAwards(
  history: PlayerAwardHistoryReadModel | null | undefined,
  sleeperPlayerId: string | number
): PlayerAwardHistoryPlayer | null {
  return history?.Players.find(p => String(p.PlayerID) === String(sleeperPlayerId) && p.Total > 0) ?? null;
}

/** Entries grouped by season (newest first) and week (newest first). */
export function groupPlayerAwardEntries(entries: readonly PlayerAwardHistoryEntry[]): PlayerAwardSeasonGroup[] {
  const defs = new Map(PLAYER_AWARD_DISPLAY.map(d => [d.key, d]));
  const bySeason = new Map<number, PlayerAwardSeasonGroup>();
  for (const e of entries) {
    const def = defs.get(e.Award);
    if (!def) continue;
    const group = bySeason.get(e.Season) ?? { season: e.Season, entries: [] };
    group.entries.push({ week: e.Week, award: e.Award, label: def.label, icon: def.icon, points: e.Points ?? null });
    bySeason.set(e.Season, group);
  }
  const order = (k: PlayerAwardKey) => PLAYER_AWARD_DISPLAY.findIndex(d => d.key === k);
  return [...bySeason.values()]
    .sort((a, b) => b.season - a.season)
    .map(g => ({ ...g, entries: g.entries.sort((a, b) => b.week - a.week || order(a.award) - order(b.award)) }));
}
