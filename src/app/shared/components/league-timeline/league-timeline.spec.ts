import { of, throwError } from 'rxjs';

import type { DecisionWindow, DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyTeam, League } from '../../../core/models/league.models';
import { DataService } from '../../../core/services/data.service';
import { LeagueTimelineComponent } from './league-timeline';

describe('LeagueTimelineComponent', () => {
  let component: LeagueTimelineComponent | null = null;

  beforeEach(() => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2026-09-04T10:00:30Z'));
  });

  afterEach(() => {
    component?.ngOnDestroy();
    component = null;
    jasmine.clock().uninstall();
  });

  it('loads Decision Windows only for active league phases', () => {
    const getDecisionWindows = jasmine.createSpy('getDecisionWindows').and.returnValue(of(createModel([])));
    const getDecisionWindowsTimestamp = jasmine.createSpy('getDecisionWindowsTimestamp').and.returnValue(of(undefined));
    component = new LeagueTimelineComponent({
      getDecisionWindows,
      getDecisionWindowsTimestamp
    } as unknown as DataService);
    component.league = createLeague({ Status: 'Pre-Season', SeasonKickoff: '2026-09-10T00:20:00Z' });

    component.ngOnInit();

    expect(getDecisionWindows).not.toHaveBeenCalled();
    expect(getDecisionWindowsTimestamp).not.toHaveBeenCalled();
    expect(component.timeline?.primary?.label).toBe('Season kickoff');
  });

  it('advances to the next Decision Window on the minute-aligned kickoff tick', () => {
    const first = createWindow('2026-09-04T10:01:00Z');
    const second = createWindow('2026-09-04T10:02:00Z');
    component = new LeagueTimelineComponent(createDataService(createModel([first, second])));
    component.league = createLeague({ NextWaiverRun: null });

    component.ngOnInit();
    expect(component.timeline?.operational[0].window?.DecisionWindowID).toBe(first.DecisionWindowID);

    jasmine.clock().tick(30_000);

    expect(component.now.toISOString()).toBe('2026-09-04T10:01:00.000Z');
    expect(component.timeline?.operational[0].window?.DecisionWindowID).toBe(second.DecisionWindowID);
  });

  it('isolates a DecisionWindows load failure from the rest of the timeline', () => {
    const dataService = {
      getDecisionWindows: () => throwError(() => new Error('DecisionWindows unavailable')),
      getDecisionWindowsTimestamp: () => throwError(() => new Error('timestamps unavailable'))
    } as unknown as DataService;
    component = new LeagueTimelineComponent(dataService);
    component.league = createLeague({
      NextWaiverRun: '2026-09-06T10:00:00Z',
      TradeDeadlineWeek: 8
    });

    component.ngOnInit();

    expect(component.decisionWindowsUnavailable).toBeTrue();
    expect(component.decisionWindowsUpdatedAt).toBeUndefined();
    expect(component.timeline?.operational.map(item => item.kind)).toEqual([
      'lineup-unavailable',
      'waiver'
    ]);
    expect(component.timeline?.milestones.map(item => item.label)).toEqual([
      'Trade deadline',
      'Playoffs'
    ]);
  });

  it('keeps a missing DecisionWindows timestamp non-fatal', () => {
    const dataService = {
      getDecisionWindows: () => of(createModel([createWindow('2026-09-04T12:00:00Z')])),
      getDecisionWindowsTimestamp: () => throwError(() => new Error('timestamp unavailable'))
    } as unknown as DataService;
    component = new LeagueTimelineComponent(dataService);
    component.league = createLeague();

    component.ngOnInit();

    expect(component.decisionWindowsUnavailable).toBeFalse();
    expect(component.decisionWindowsUpdatedAt).toBeUndefined();
    expect(component.timeline?.operational[0].kind).toBe('lineup');
  });
});

function createDataService(model: DecisionWindowsReadModel): DataService {
  return {
    getDecisionWindows: () => of(model),
    getDecisionWindowsTimestamp: () => of('2026-09-04T09:58:00Z')
  } as unknown as DataService;
}

function createLeague(overrides: Partial<League> = {}): League {
  return {
    Status: 'In-Season',
    Phase: '',
    Season: '2026',
    CurrentWeek: 1,
    FinalScoredWeek: 0,
    LastLeagueWeek: 17,
    PlayoffStartWeek: 14,
    TradeDeadlineWeek: 99,
    SeasonKickoff: null,
    CapDeadline: '',
    LeagueTimeZone: 'UTC',
    NextWaiverRun: null,
    Teams: [createTeam(1), createTeam(2)],
    ...overrides
  } as League;
}

function createModel(windows: DecisionWindow[]): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: windows,
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: [
      {
        FantasyTeamID: 1,
        State: 'ready',
        ExpectedStarterCount: 13,
        StarterCount: 13,
        OpenStarterSlots: 0,
        Issues: []
      },
      {
        FantasyTeamID: 2,
        State: 'ready',
        ExpectedStarterCount: 13,
        StarterCount: 13,
        OpenStarterSlots: 0,
        Issues: []
      }
    ]
  };
}

function createWindow(startsAtUtc: string): DecisionWindow {
  return {
    DecisionWindowID: startsAtUtc,
    Week: 1,
    StartsAtUtc: startsAtUtc,
    Games: [{
      GameID: `game-${startsAtUtc}`,
      Week: 1,
      AwayTeamID: 'NE',
      AwayTeamAbbr: 'NE',
      HomeTeamID: 'SEA',
      HomeTeamAbbr: 'SEA'
    }],
    ParticipatingNFLTeamIDs: ['NE', 'SEA'],
    FantasyContextState: 'available',
    AffectedFantasyTeams: []
  };
}

function createTeam(teamId: number): FantasyTeam {
  return {
    TeamID: teamId,
    Team: `Team ${teamId}`,
    Owner: `Owner ${teamId}`,
    OwnerAvatar: '',
    Avatar: ''
  } as FantasyTeam;
}
