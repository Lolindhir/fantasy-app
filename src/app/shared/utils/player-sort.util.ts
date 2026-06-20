import type { Player, SortField } from '../../core/models/player.models';

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
