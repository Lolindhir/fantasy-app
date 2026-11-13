import type { FantasyTeam, League, Player } from '../../core/models/fantasy.models';

/** Overview cap row. Cap usage comes only from the verified central TeamCapOutlook (ADR-079). */
export interface OverviewCapRow {
  team: FantasyTeam;
  /** False when the central outlook is missing, stale or invalid for this team. */
  available: boolean;
  /** Central Current.Usage, or null when unavailable (never a locally computed fallback). */
  total: number | null;
  /** Central Projected.Usage, or null when unavailable. */
  totalProjected: number | null;
  /** Display-only roster aggregates, not cap values. */
  totalAll: number;
  totalTop5: number;
  topPlayer: Player | null;
}

export interface OverviewCapCheck {
  title: string;
  summaryText: string;
  detailText: string;
  allCompliant: boolean;
}

export function buildOverviewCapRows(teams: FantasyTeam[]): OverviewCapRow[] {
  return teams
    .map(team => {
      const bySalary = [...team.Roster].sort((a, b) =>
        (b.Salary ?? 0) - (a.Salary ?? 0) || (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0));
      return {
        team,
        available: !!team.CapOutlook,
        total: team.CapOutlook?.Current.Usage ?? null,
        totalProjected: team.CapOutlook?.Projected.Usage ?? null,
        totalAll: bySalary.reduce((sum, p) => sum + p.Salary, 0),
        totalTop5: bySalary.slice(0, 5).reduce((sum, p) => sum + p.Salary, 0),
        topPlayer: bySalary[0] ?? null
      };
    })
    // Teams without a valid outlook sort last.
    .sort((a, b) => {
      if (a.total === null || b.total === null) {
        return a.total === b.total ? 0 : a.total === null ? 1 : -1;
      }
      return a.total - b.total;
    });
}

export function buildOverviewCapCheck(
  league: Pick<League, 'SalaryCap'>,
  rows: OverviewCapRow[],
  formatDollars: (amount: number) => string
): OverviewCapCheck {
  const unavailable = rows.filter(row => !row.available);
  if (unavailable.length > 0) {
    return {
      title: '⚠️ Cap Check Unavailable',
      summaryText: 'Cap data is currently unavailable.',
      detailText: `${unavailable.length} of ${rows.length} teams without current cap data`,
      allCompliant: false
    };
  }

  const overCapTeams = rows.filter(row => (row.total as number) > league.SalaryCap);
  const compliantTeams = rows.length - overCapTeams.length;

  if (overCapTeams.length === 0) {
    return {
      title: '✅ Cap Check Passed',
      summaryText: 'All teams are under the salary cap.',
      detailText: `${compliantTeams} of ${rows.length} teams compliant`,
      allCompliant: true
    };
  }

  const worstOverage = Math.max(...overCapTeams.map(row => (row.total as number) - league.SalaryCap));
  const teamLabel = overCapTeams.length === 1 ? 'team still needs' : 'teams still need';

  return {
    title: '🚨 Cap Check Open',
    summaryText: `${overCapTeams.length} ${teamLabel} to clear cap.`,
    detailText: `${compliantTeams} compliant · largest overage ${formatDollars(worstOverage)}`,
    allCompliant: false
  };
}
