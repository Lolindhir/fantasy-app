import type { DraftPick, FantasyTeam, League, Player } from '../../core/models/fantasy.models';
import type { RawLeague } from '../../core/models/league.models';
import type { RawPlayer } from '../../core/models/player.models';
import { verifyTeamCapOutlook, type TeamCapOutlookReadModel } from '../../core/models/team-cap-outlook.models';
import { calculateTopPlayersSalary } from './trade-calculator.util';
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

  it('removes Taxi and IR players from the Active Roster count', () => {
    const active = makePlayer('active', 10, 11, 'WR');
    const taxi = makePlayer('taxi', 8, 9, 'RB');
    const ir = makePlayer('ir', 7, 7, 'TE');
    const split = splitTeamRoster(makeTeam({
      Roster: [active, taxi, ir],
      Taxi: [taxi],
      Reserve: [ir]
    }));

    expect(split.activeRoster.map(player => player.ID)).toEqual(['active']);
    expect(split.taxi.map(player => player.ID)).toEqual(['taxi']);
    expect(split.ir.map(player => player.ID)).toEqual(['ir']);
  });

  it('uses the league salary-relevant team size for current and projected cap totals', () => {
    const first = makePlayer('first', 100, 70, 'QB');
    const second = makePlayer('second', 80, 120, 'WR');
    const third = makePlayer('third', 50, 40, 'RB');
    const summary = buildTeamSalarySummary(
      makeTeam({ Roster: [first, second, third], CapOutlook: {
        TeamID: 1, Status: 'ready', InputRoster: [],
        Current: { Usage: 180, TopPlayerIDs: ['first', 'second'], Cuts: [] },
        Projected: { Usage: 190, TopPlayerIDs: ['second', 'first'], Cuts: [] }
      } }),
      makeLeague({ SalaryRelevantTeamSize: 2, SalaryCap: 200, SalaryCapProjected: 220 })
    );

    expect(summary.available).toBeTrue();
    expect(summary.current.salary).toBe(180);
    expect(summary.projected.salary).toBe(190);
    expect(summary.current.mostExpensive.map(player => player.ID)).toEqual(['first', 'second']);
    expect(summary.projected.mostExpensive.map(player => player.ID)).toEqual(['second', 'first']);
  });

  it('does not invent real salary usage when central data is missing', () => {
    const summary = buildTeamSalarySummary(
      makeTeam({ Roster: [makePlayer('a', 99, 99, 'QB')] }), makeLeague());
    expect(summary.available).toBeFalse();
    expect(summary.health).toBe('unavailable');
  });

  it('pins Variant A hypothetical calculations against roster-cap-v1 examples', () => {
    const roster = [70, 60, 50, 40, 30, 20, 10]
      .map((salary, index) => makePlayer(String(index + 1), salary, salary + 10, 'WR'));
    expect(calculateTopPlayersSalary(roster, 6, p => p.Salary).cap).toBe(270);
    expect(calculateTopPlayersSalary(roster, 6, p => p.SalaryProjected).cap).toBe(330);
  });

  it('rejects stale salary, wrong league and missing roster witnesses without recalculation', () => {
    const players = [makePlayer('a', 100, 110, 'QB'), makePlayer('b', 80, 90, 'WR')];
    const league = {
      LeagueID: '123456', Season: '2026', FinalScoredWeek: 7,
      SalaryRelevantTeamSize: 2, SalaryCap: 200, SalaryCapProjected: 220,
      Teams: [{ TeamID: 1, Roster: ['a', 'b'] }]
    } as unknown as RawLeague;
    const outlook: TeamCapOutlookReadModel = {
      ContractVersion: 1, CanonicalLeagueID: 'example', ProviderLeagueID: '123456',
      Season: 2026, AsOfFinalScoredWeek: 7,
      Models: { RosterCap: 'roster-cap-v1', AutoCut: 'auto-cut-v1' },
      SalaryRelevantTeamSize: 2, SalaryCap: 200, SalaryCapProjected: 220,
      Teams: [{
        TeamID: 1, Status: 'ready',
        InputRoster: [
          { PlayerID: 'a', Salary: 100, SalaryProjected: 110 },
          { PlayerID: 'b', Salary: 80, SalaryProjected: 90 }
        ],
        Current: { Usage: 180, TopPlayerIDs: ['a', 'b'], Cuts: [] },
        Projected: { Usage: 200, TopPlayerIDs: ['a', 'b'], Cuts: [] }
      }]
    };
    expect(verifyTeamCapOutlook(outlook, league, players as unknown as RawPlayer[]).size).toBe(1);
    expect(verifyTeamCapOutlook({ ...outlook, Models: { RosterCap: 'roster-cap-v2', AutoCut: 'auto-cut-v3' } }, league, players as unknown as RawPlayer[]).size).toBe(1);
    expect(verifyTeamCapOutlook({ ...outlook, Models: { RosterCap: '', AutoCut: 'auto-cut-v1' } }, league, players as unknown as RawPlayer[]).size).toBe(0);
    expect(verifyTeamCapOutlook(outlook, league, [makePlayer('a', 101, 110, 'QB'), players[1]] as unknown as RawPlayer[]).size).toBe(0);
    expect(verifyTeamCapOutlook({ ...outlook, ProviderLeagueID: 'other' }, league, players as unknown as RawPlayer[]).size).toBe(0);
    expect(verifyTeamCapOutlook({ ...outlook, AsOfFinalScoredWeek: 6 }, league, players as unknown as RawPlayer[]).size).toBe(0);
    expect(verifyTeamCapOutlook(null, league, players as unknown as RawPlayer[]).size).toBe(0);
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
