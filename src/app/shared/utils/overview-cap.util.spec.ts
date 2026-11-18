import type { FantasyTeam, Player } from '../../core/models/fantasy.models';
import { buildOverviewCapCheck, buildOverviewCapRows } from './overview-cap.util';

function player(id: string, salary: number): Player {
  return { ID: id, Name: id, NameShort: id, Salary: salary, SalaryProjected: salary } as unknown as Player;
}

function team(id: number, roster: Player[], usage?: number, projected?: number): FantasyTeam {
  return {
    TeamID: id,
    Roster: roster,
    CapOutlook: usage === undefined ? undefined : {
      Current: { Usage: usage, TopPlayerIDs: [], Cuts: [] },
      Projected: { Usage: projected ?? usage, TopPlayerIDs: [], Cuts: [] }
    }
  } as unknown as FantasyTeam;
}

const fmt = (amount: number) => `$${amount}`;

describe('overview cap utilities', () => {
  it('reads cap usage from the central outlook, not from the roster', () => {
    // Roster sum (60) deliberately differs from the central usage.
    const rows = buildOverviewCapRows([team(1, [player('a', 40), player('b', 20)], 55, 70)]);
    expect(rows[0].available).toBe(true);
    expect(rows[0].total).toBe(55);
    expect(rows[0].totalProjected).toBe(70);
    expect(rows[0].totalAll).toBe(60);
  });

  it('marks teams without a valid outlook unavailable and sorts them last', () => {
    const rows = buildOverviewCapRows([
      team(1, [player('a', 10)]),
      team(2, [player('b', 10)], 90),
      team(3, [player('c', 10)], 30)
    ]);
    expect(rows.map(r => r.team.TeamID)).toEqual([3, 2, 1]);
    expect(rows[2].available).toBe(false);
    expect(rows[2].total).toBeNull();
    expect(rows[2].totalProjected).toBeNull();
  });

  it('keeps tied usages stable and handles an empty roster', () => {
    const rows = buildOverviewCapRows([team(1, [], 0), team(2, [player('a', 5)], 0)]);
    expect(rows.map(r => r.team.TeamID)).toEqual([1, 2]);
    expect(rows[0].topPlayer).toBeNull();
    expect(rows[0].totalAll).toBe(0);
  });

  it('reports a passed cap check when all teams are under the cap', () => {
    const rows = buildOverviewCapRows([team(1, [], 80), team(2, [], 100)]);
    const check = buildOverviewCapCheck({ SalaryCap: 100 }, rows, fmt);
    expect(check.allCompliant).toBe(true);
    expect(check.detailText).toBe('2 of 2 teams compliant');
  });

  it('reports the largest overage of open cap checks', () => {
    const rows = buildOverviewCapRows([team(1, [], 80), team(2, [], 110), team(3, [], 125)]);
    const check = buildOverviewCapCheck({ SalaryCap: 100 }, rows, fmt);
    expect(check.allCompliant).toBe(false);
    expect(check.summaryText).toBe('2 teams still need to clear cap.');
    expect(check.detailText).toBe('1 compliant · largest overage $25');
  });

  it('shows the cap check as unavailable instead of guessing when any outlook is missing', () => {
    const rows = buildOverviewCapRows([team(1, [player('a', 500)]), team(2, [], 50)]);
    const check = buildOverviewCapCheck({ SalaryCap: 100 }, rows, fmt);
    expect(check.title).toContain('Unavailable');
    expect(check.allCompliant).toBe(false);
    expect(check.detailText).toBe('1 of 2 teams without current cap data');
  });
});
