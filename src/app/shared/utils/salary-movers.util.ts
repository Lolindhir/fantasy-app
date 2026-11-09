import type { Player } from '../../core/models/fantasy.models';

export interface SalaryMover {
  player: Player;
  /** Generator-owned SalaryProjected change since the previous week; never computed here. */
  change: number;
}

export interface SalaryMovers {
  up: SalaryMover[];
  down: SalaryMover[];
}

export const SALARY_MOVERS_LIMIT = 5;

/**
 * Selects the largest SalaryProjected movers since the previous week from the generator-owned
 * `SalaryProjectedChange.SinceLastWeek`. Only sorting and filtering happens here (no calculation):
 * players without a known or without a non-zero change are left out, and `include` narrows the pool
 * (the Overview shows rostered players only).
 */
export function buildSalaryMovers(
  players: readonly Player[],
  include: (player: Player) => boolean = () => true,
  limit: number = SALARY_MOVERS_LIMIT
): SalaryMovers {
  const movers: SalaryMover[] = [];
  for (const player of players) {
    const change = player.SalaryProjectedChange?.SinceLastWeek;
    if (change == null || change === 0 || !include(player)) continue;
    movers.push({ player, change });
  }
  const byName = (a: SalaryMover, b: SalaryMover) => a.player.Name.localeCompare(b.player.Name) || a.player.ID.localeCompare(b.player.ID);
  const up = movers.filter(m => m.change > 0).sort((a, b) => b.change - a.change || byName(a, b)).slice(0, limit);
  const down = movers.filter(m => m.change < 0).sort((a, b) => a.change - b.change || byName(a, b)).slice(0, limit);
  return { up, down };
}
