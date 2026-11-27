import { of } from 'rxjs';
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

  it('loads one combined league context and preserves published cap values', () => {
    const timestamp = '2026-11-27T00:00:00Z';
    const getLeagueWithPlayers = jasmine.createSpy('getLeagueWithPlayers').and.returnValue(of({
      league: { SalaryRelevantTeamSize: 2, SalaryCap: 300, SalaryCapProjected: 320, SeasonAsNumber: 2026, IsFinished: false },
      players,
      teams: [team()],
      drafts: []
    }));
    const getLatestTimestamp = jasmine.createSpy('getLatestTimestamp').and.returnValue(of(timestamp));
    const data = { getLeagueWithPlayers, getLatestTimestamp } as unknown as DataService;
    const view = new TeamListComponent(data, {} as MatDialog);

    view.ngOnInit();

    expect(getLeagueWithPlayers).toHaveBeenCalledOnceWith(['Salary']);
    expect(getLatestTimestamp).toHaveBeenCalledTimes(1);
    expect(view.salaryCap).toBe(300);
    expect(view.salaryCapProjected).toBe(320);
    expect(view.fantasyTeams[0].Salary).toBe(180);
    expect(view.fantasyTeams[0].SalaryProjected).toBe(200);
    expect(view.allPlayers.length).toBe(3);
    expect(view.timestamp).toBe(timestamp);
  });

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
