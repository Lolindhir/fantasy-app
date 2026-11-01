import type { Player } from '../../../core/models/fantasy.models';
import type { DataService } from '../../../core/services/data.service';
import type { MatDialog } from '@angular/material/dialog';
import { TeamListComponent } from './team-list';

describe('legacy team salary view L10', () => {
  function component() {
    const calculate = jasmine.createSpy('calculateTopPlayersSalary').and.callFake(
      (roster: Player[], topN: number, selector: (player: Player) => number) => {
        const topPlayers = [...roster].sort((a, b) => selector(b) - selector(a)).slice(0, topN);
        return { cap: topPlayers.reduce((sum, player) => sum + selector(player), 0), topPlayers };
      }
    );
    const data = { calculateTopPlayersSalary: calculate } as unknown as DataService;
    const view = new TeamListComponent(data, {} as MatDialog);
    view.salaryRelevantTeamSize = 2;
    return { view, calculate };
  }
  const players = [
    { ID: 'a', Salary: 100, SalaryProjected: 110 },
    { ID: 'b', Salary: 80, SalaryProjected: 90 },
    { ID: 'c', Salary: 30, SalaryProjected: 40 }
  ] as unknown as Player[];

  function team(withOutlook = true) {
    return {
      TeamID: 1, Roster: players,
      CapOutlook: withOutlook ? { Current: { Usage: 180 }, Projected: { Usage: 200 } } : undefined
    };
  }

  it('uses published central cap for an unchanged real roster', () => {
    const { view, calculate } = component();
    const result = (view as any).processTeam(team());
    expect(result.Salary).toBe(180);
    expect(result.SalaryProjected).toBe(200);
    expect(result.IsSalaryAvailable).toBeTrue();
    expect(result.IsWhatIf).toBeFalse();
    expect(calculate).not.toHaveBeenCalled();
  });

  it('uses the local calculator only after the user explicitly excludes a player', () => {
    const { view, calculate } = component();
    view.excludedPlayersByTeam[1] = new Set(['a']);
    const result = (view as any).processTeam(team());
    expect(result.Salary).toBe(110);
    expect(result.SalaryProjected).toBe(130);
    expect(result.IsWhatIf).toBeTrue();
    expect(calculate).toHaveBeenCalledTimes(2);
  });

  it('does not invent team cap values when published central data is missing', () => {
    const { view, calculate } = component();
    view.excludedPlayersByTeam[1] = new Set(['a']);
    const result = (view as any).processTeam(team(false));
    expect(result.IsSalaryAvailable).toBeFalse();
    expect(result.Salary).toBeNull();
    expect(result.SalaryProjected).toBeNull();
    expect(calculate).not.toHaveBeenCalled();
  });
});
