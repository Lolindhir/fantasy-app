import type { Player } from '../../core/models/fantasy.models';

export interface SalaryMover {
  player: Player;
  /** Generator-owned SalaryProjected minus current Salary; never computed here. */
  delta: number;
}

export interface SalaryMovers {
  up: SalaryMover[];
  down: SalaryMover[];
}

export const SALARY_MOVERS_LIMIT = 5;

/**
 * Selects the players whose projected salary differs most from the current salary, using the generator-owned
 * `SalaryProjectedDelta`. Only sorting and filtering happens here (no calculation): players without a known or
 * with a zero delta are left out, and `include` narrows the pool (for example rostered players only).
 */
export function buildSalaryMovers(
  players: readonly Player[],
  include: (player: Player) => boolean = () => true,
  limit: number = SALARY_MOVERS_LIMIT
): SalaryMovers {
  const movers: SalaryMover[] = [];
  for (const player of players) {
    const delta = player.SalaryProjectedDelta;
    if (delta == null || delta === 0 || !include(player)) continue;
    movers.push({ player, delta });
  }
  const byName = (a: SalaryMover, b: SalaryMover) => a.player.Name.localeCompare(b.player.Name) || a.player.ID.localeCompare(b.player.ID);
  const up = movers.filter(m => m.delta > 0).sort((a, b) => b.delta - a.delta || byName(a, b)).slice(0, limit);
  const down = movers.filter(m => m.delta < 0).sort((a, b) => a.delta - b.delta || byName(a, b)).slice(0, limit);
  return { up, down };
}
