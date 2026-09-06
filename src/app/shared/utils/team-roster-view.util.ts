import type { DecisionWindowPlayerLockFact } from '../../core/models/decision-window.models';
import type { Player } from '../../core/models/player.models';
import { comparePlayersByDepthChart } from './player-sort.util';

export type RosterGroupMode = 'rosterStatus' | 'position' | 'rankingStatus' | 'none';
export type RosterSortMode = 'salary' | 'projected' | 'ranking' | 'depth' | 'ageAsc' | 'ageDesc' | 'name' | 'nextLock';

export interface RosterPlayerGroup {
  key: string;
  label: string;
  players: Player[];
}

export interface RosterStatusPlayerGroups {
  roster: Player[];
  taxi: Player[];
  ir: Player[];
}

export interface RosterNextLockContext {
  fantasyTeamId: number;
  playerLockFacts: DecisionWindowPlayerLockFact[];
  now: Date;
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
  sortMode: RosterSortMode,
  rosterStatusGroups?: RosterStatusPlayerGroups,
  nextLockContext?: RosterNextLockContext
): RosterPlayerGroup[] {
  switch (groupMode) {
    case 'rosterStatus': {
      const statusGroups = rosterStatusGroups ?? { roster: players, taxi: [], ir: [] };
      return [
        buildGroup('roster', 'Roster', statusGroups.roster, sortMode, nextLockContext),
        buildGroup('taxi', 'Taxi', statusGroups.taxi, sortMode, nextLockContext),
        buildGroup('ir', 'IR', statusGroups.ir, sortMode, nextLockContext)
      ];
    }

    case 'position': {
      const positions = [...new Set(players.map(player => player.Position).filter(Boolean))]
        .sort(comparePositions);

      return positions.map(position => buildGroup(
        `position-${position}`,
        POSITION_LABELS[position] ?? position,
        players.filter(player => player.Position === position),
        sortMode,
        nextLockContext
      ));
    }

    case 'rankingStatus':
      return [
        buildGroup(
          'ranked',
          'Ranked',
          players.filter(player => getCombinedRanking(player) !== undefined),
          sortMode,
          nextLockContext
        ),
        buildGroup(
          'unranked',
          'Unranked',
          players.filter(player => getCombinedRanking(player) === undefined),
          sortMode,
          nextLockContext
        )
      ];

    case 'none':
    default:
      return [buildGroup('all', 'All Players', players, sortMode, nextLockContext)];
  }
}

export function sortRosterPlayers(
  players: Player[],
  sortMode: RosterSortMode,
  nextLockContext?: RosterNextLockContext
): Player[] {
  const lockFactByPlayer = sortMode === 'nextLock'
    ? buildTeamLockFactMap(nextLockContext)
    : null;

  return [...players].sort((a, b) => {
    const nameCompare = comparePlayerIdentity(a, b);

    switch (sortMode) {
      case 'salary':
        return b.Salary - a.Salary || nameCompare;
      case 'projected':
        return b.SalaryProjected - a.SalaryProjected || nameCompare;
      case 'ranking':
        return compareCombinedRanking(a, b) || nameCompare;
      case 'depth':
        return comparePlayersByDepthChart(a, b);
      case 'ageAsc':
        return a.Age - b.Age || nameCompare;
      case 'ageDesc':
        return b.Age - a.Age || nameCompare;
      case 'nextLock':
        return compareNextLockPlayers(
          a,
          b,
          lockFactByPlayer ?? new Map<string, DecisionWindowPlayerLockFact>(),
          nextLockContext?.now ?? new Date(0)
        );
      case 'name':
      default:
        return nameCompare;
    }
  });
}

export function formatRosterNextLockValue(
  player: Player,
  context: RosterNextLockContext
): string {
  const fact = buildTeamLockFactMap(context).get(player.ID);
  if (!fact) return 'Unknown';

  switch (fact.Kind) {
    case 'bye':
      return 'Bye';
    case 'no-team':
      return 'No team';
    case 'unknown':
      return 'Unknown';
    case 'scheduled': {
      const startsAt = parseTimestamp(fact.StartsAtUtc);
      if (!startsAt) return 'Unknown';
      if (startsAt.getTime() <= context.now.getTime()) return 'Locked';
      return new Intl.DateTimeFormat(undefined, {
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }).format(startsAt).replace(',', '');
    }
  }
}

function buildGroup(
  key: string,
  label: string,
  players: Player[],
  sortMode: RosterSortMode,
  nextLockContext?: RosterNextLockContext
): RosterPlayerGroup {
  return {
    key,
    label,
    players: sortRosterPlayers(players, sortMode, nextLockContext)
  };
}

function compareNextLockPlayers(
  a: Player,
  b: Player,
  factByPlayer: Map<string, DecisionWindowPlayerLockFact>,
  now: Date
): number {
  const aState = getNextLockSortState(factByPlayer.get(a.ID), now);
  const bState = getNextLockSortState(factByPlayer.get(b.ID), now);

  if (aState.bucket !== bState.bucket) return aState.bucket - bState.bucket;

  if ((aState.bucket === 0 || aState.bucket === 4) && aState.startsAtMs !== bState.startsAtMs) {
    return aState.startsAtMs - bState.startsAtMs;
  }

  return comparePlayerIdentity(a, b);
}

function getNextLockSortState(
  fact: DecisionWindowPlayerLockFact | undefined,
  now: Date
): { bucket: number; startsAtMs: number } {
  if (!fact || fact.Kind === 'unknown') return { bucket: 1, startsAtMs: Number.MAX_SAFE_INTEGER };
  if (fact.Kind === 'no-team') return { bucket: 2, startsAtMs: Number.MAX_SAFE_INTEGER };
  if (fact.Kind === 'bye') return { bucket: 3, startsAtMs: Number.MAX_SAFE_INTEGER };

  const startsAt = parseTimestamp(fact.StartsAtUtc);
  if (!startsAt) return { bucket: 1, startsAtMs: Number.MAX_SAFE_INTEGER };
  if (startsAt.getTime() > now.getTime()) return { bucket: 0, startsAtMs: startsAt.getTime() };
  return { bucket: 4, startsAtMs: startsAt.getTime() };
}

function buildTeamLockFactMap(
  context: RosterNextLockContext | undefined
): Map<string, DecisionWindowPlayerLockFact> {
  if (!context) return new Map();
  return new Map(
    context.playerLockFacts
      .filter(fact => fact.FantasyTeamID === context.fantasyTeamId)
      .map(fact => [fact.PlayerID, fact])
  );
}

function comparePlayerIdentity(a: Player, b: Player): number {
  return a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' }) || a.ID.localeCompare(b.ID);
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

function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
