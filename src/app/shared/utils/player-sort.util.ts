import type { Player, SortField } from '../../core/models/player.models';

const PLAYER_POSITION_ORDER = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF', 'DST'];

export function getPlayerDepthChartOrder(player: Player): number | undefined {
  const value = Number(player.SleeperDepthChartOrder);
  return Number.isFinite(value) && value > 0 ? value : undefined;
}

export function getPlayerDepthChartLabel(player: Player): string | undefined {
  const depth = getPlayerDepthChartOrder(player);
  return depth === undefined ? undefined : `${player.Position} #${depth}`;
}

export function formatPlayerPositionDepth(player: Player): string {
  return getPlayerDepthChartLabel(player) ?? player.Position;
}

export function comparePlayersByDepthChart(a: Player, b: Player): number {
  const depthA = getPlayerDepthChartOrder(a);
  const depthB = getPlayerDepthChartOrder(b);

  if (depthA !== undefined || depthB !== undefined) {
    if (depthA === undefined) return 1;
    if (depthB === undefined) return -1;
    if (depthA !== depthB) return depthA - depthB;
  }

  return comparePlayerPositions(a.Position, b.Position)
    || (b.Salary ?? 0) - (a.Salary ?? 0)
    || comparePlayerNames(a, b)
    || a.ID.localeCompare(b.ID);
}

export function sortPlayers(roster: Player[], sortFields: SortField[]): Player[] {
  return roster.sort((a, b) => {
    for (const field of sortFields) {
      if (field === 'Salary' || field === 'SalaryProjected' || field === 'Age' || field === 'Year') {
        const diff = (b[field] as number) - (a[field] as number);
        if (diff !== 0) return diff;
      } else {
        const cmp = String(a[field]).localeCompare(String(b[field]), 'en', { sensitivity: 'base' });
        if (cmp !== 0) return cmp;
      }
    }

    return a.ID.localeCompare(b.ID);
  });
}

function comparePlayerPositions(a: string, b: string): number {
  const orderA = PLAYER_POSITION_ORDER.indexOf(a);
  const orderB = PLAYER_POSITION_ORDER.indexOf(b);
  const normalizedA = orderA === -1 ? Number.MAX_SAFE_INTEGER : orderA;
  const normalizedB = orderB === -1 ? Number.MAX_SAFE_INTEGER : orderB;
  return normalizedA - normalizedB || a.localeCompare(b);
}

function comparePlayerNames(a: Player, b: Player): number {
  return a.NameLast.localeCompare(b.NameLast, 'en', { sensitivity: 'base' })
    || a.NameFirst.localeCompare(b.NameFirst, 'en', { sensitivity: 'base' });
}
