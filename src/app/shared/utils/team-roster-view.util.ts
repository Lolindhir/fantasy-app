import type { Player } from '../../core/models/player.models';

export type RosterGroupMode = 'rosterStatus' | 'position' | 'rankingStatus' | 'none';
export type RosterSortMode = 'salary' | 'projected' | 'ranking' | 'age' | 'name';

export interface RosterPlayerGroup {
  key: string;
  label: string;
  players: Player[];
}

export const COMBINED_RANKING_MIN_FINAL_WEEK = 3;

const POSITION_ORDER = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF', 'DST'];
const POSITION_LABELS: Record<string, string> = {
  QB: 'Quarterbacks',
  RB: 'Running Backs',
  WR: 'Wide Receivers',
  TE: 'Tight Ends',
  K: 'Kickers',
  DEF: 'Defense',
  DST: 'Defense'
};

export function isCombinedRankingAvailable(finalScoredWeek: number | undefined): boolean {
  return (finalScoredWeek ?? 0) >= COMBINED_RANKING_MIN_FINAL_WEEK;
}

export function getCombinedRanking(player: Player): number | undefined {
  return getPositiveRanking(player, 'Combined');
}

export function getPreviousCombinedRanking(player: Player): number | undefined {
  return getPositiveRanking(player, 'Combined_Previous');
}

export function buildRosterPlayerGroups(
  players: Player[],
  groupMode: RosterGroupMode,
  sortMode: RosterSortMode
): RosterPlayerGroup[] {
  switch (groupMode) {
    case 'rosterStatus':
      return [
        buildGroup('roster', 'Roster', players.filter(player => !player.Reserve && !player.Taxi), sortMode),
        buildGroup('taxi', 'Taxi', players.filter(player => !player.Reserve && !!player.Taxi), sortMode),
        buildGroup('ir', 'IR', players.filter(player => !!player.Reserve), sortMode)
      ];

    case 'position': {
      const positions = [...new Set(players.map(player => player.Position).filter(Boolean))]
        .sort(comparePositions);

      return positions.map(position => buildGroup(
        `position-${position}`,
        POSITION_LABELS[position] ?? position,
        players.filter(player => player.Position === position),
        sortMode
      ));
    }

    case 'rankingStatus':
      return [
        buildGroup('ranked', 'Ranked', players.filter(player => getCombinedRanking(player) !== undefined), sortMode),
        buildGroup('unranked', 'Unranked', players.filter(player => getCombinedRanking(player) === undefined), sortMode)
      ];

    case 'none':
    default:
      return [buildGroup('all', 'All Players', players, sortMode)];
  }
}

export function sortRosterPlayers(players: Player[], sortMode: RosterSortMode): Player[] {
  return [...players].sort((a, b) => {
    const nameCompare = a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' });

    switch (sortMode) {
      case 'salary':
        return b.Salary - a.Salary || nameCompare || a.ID.localeCompare(b.ID);
      case 'projected':
        return b.SalaryProjected - a.SalaryProjected || nameCompare || a.ID.localeCompare(b.ID);
      case 'ranking':
        return compareCombinedRanking(a, b) || nameCompare || a.ID.localeCompare(b.ID);
      case 'age':
        return a.Age - b.Age || nameCompare || a.ID.localeCompare(b.ID);
      case 'name':
      default:
        return nameCompare || a.ID.localeCompare(b.ID);
    }
  });
}

function buildGroup(key: string, label: string, players: Player[], sortMode: RosterSortMode): RosterPlayerGroup {
  return {
    key,
    label,
    players: sortRosterPlayers(players, sortMode)
  };
}

function compareCombinedRanking(a: Player, b: Player): number {
  const currentA = getCombinedRanking(a);
  const currentB = getCombinedRanking(b);

  if (currentA !== undefined || currentB !== undefined) {
    if (currentA === undefined) return 1;
    if (currentB === undefined) return -1;
    if (currentA !== currentB) return currentA - currentB;
  }

  const previousA = getPreviousCombinedRanking(a);
  const previousB = getPreviousCombinedRanking(b);

  if (previousA !== undefined || previousB !== undefined) {
    if (previousA === undefined) return 1;
    if (previousB === undefined) return -1;
    if (previousA !== previousB) return previousA - previousB;
  }

  return b.Salary - a.Salary;
}

function getPositiveRanking(player: Player, type: 'Combined' | 'Combined_Previous'): number | undefined {
  const value = player.Stats?.Ranking?.find(entry => entry.Type === type)?.Value;
  return Number.isFinite(value) && (value ?? 0) > 0 ? value : undefined;
}

function comparePositions(a: string, b: string): number {
  const orderA = POSITION_ORDER.indexOf(a);
  const orderB = POSITION_ORDER.indexOf(b);
  const normalizedA = orderA === -1 ? Number.MAX_SAFE_INTEGER : orderA;
  const normalizedB = orderB === -1 ? Number.MAX_SAFE_INTEGER : orderB;
  return normalizedA - normalizedB || a.localeCompare(b);
}
