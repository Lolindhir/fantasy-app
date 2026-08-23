import type { DraftPick, FantasyTeam, League, Player } from '../../core/models/fantasy.models';
import {
  buildTeamSalarySummary,
  getEarliestOpenPicks,
  getSalaryHealth,
  splitTeamRoster
} from './team-salary.util';

describe('team salary utilities', () => {
  it('classifies combined current/projected salary health', () => {
    expect(getSalaryHealth(90, 100, 95, 100)).toBe('healthy');
    expect(getSalaryHealth(90, 100, 105, 100)).toBe('watch');
    expect(getSalaryHealth(101, 100, 80, 100)).toBe('over');
  });

  it('removes Taxi and IR players from the normal roster count', () => {
    const active = makePlayer('active', 10, 11, 'WR');
    const taxi = makePlayer('taxi', 8, 9, 'RB');
    const ir = makePlayer('ir', 7, 7, 'TE');
    const split = splitTeamRoster(makeTeam({
      Roster: [active, taxi, ir],
      Taxi: [taxi],
      Reserve: [ir]
    }));

    expect(split.roster.map(player => player.ID)).toEqual(['active']);
    expect(split.taxi.map(player => player.ID)).toEqual(['taxi']);
    expect(split.ir.map(player => player.ID)).toEqual(['ir']);
  });

  it('uses the league salary-relevant team size for current and projected cap totals', () => {
    const first = makePlayer('first', 100, 70, 'QB');
    const second = makePlayer('second', 80, 120, 'WR');
    const third = makePlayer('third', 50, 40, 'RB');
    const summary = buildTeamSalarySummary(
      makeTeam({ Roster: [first, second, third] }),
      makeLeague({ SalaryRelevantTeamSize: 2, SalaryCap: 200, SalaryCapProjected: 220 })
    );

    expect(summary.current.salary).toBe(180);
    expect(summary.projected.salary).toBe(190);
    expect(summary.current.mostExpensive.map(player => player.ID)).toEqual(['first', 'second']);
    expect(summary.projected.mostExpensive.map(player => player.ID)).toEqual(['second', 'first']);
  });

  it('rolls open-pick summary forward to the earliest season with an available pick', () => {
    const picked2026 = makePick('2026-picked', '2026', 'Picked', 'player-1');
    const open2027A = makePick('2027-a', '2027', 'Open', null);
    const open2027B = makePick('2027-b', '2027', 'Open', null);
    const open2028 = makePick('2028-a', '2028', 'Open', null);

    const summary = getEarliestOpenPicks(
      makeTeam({ DraftPicks: [picked2026, open2028, open2027A, open2027B] }),
      2026
    );

    expect(summary?.season).toBe(2027);
    expect(summary?.count).toBe(2);
    expect(summary?.picks.map(pick => pick.PickKey)).toEqual(['2027-a', '2027-b']);
  });
});

function makePlayer(id: string, salary: number, projected: number, position: string): Player {
  return {
    ID: id,
    Name: id,
    Position: position,
    Salary: salary,
    SalaryProjected: projected
  } as unknown as Player;
}

function makePick(key: string, season: string, status: string, playerId: string | null): DraftPick {
  return {
    PickKey: key,
    Season: season,
    Status: status,
    PlayerID: playerId
  } as unknown as DraftPick;
}

function makeTeam(overrides: Partial<FantasyTeam> = {}): FantasyTeam {
  return {
    TeamID: 1,
    Roster: [],
    Taxi: [],
    Reserve: [],
    Starter: [],
    DraftPicks: [],
    ...overrides
  } as unknown as FantasyTeam;
}

function makeLeague(overrides: Partial<League> = {}): League {
  return {
    SalaryRelevantTeamSize: 20,
    SalaryCap: 100,
    SalaryCapProjected: 100,
    ...overrides
  } as unknown as League;
}
