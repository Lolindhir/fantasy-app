import type { DecisionWindow, DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { DecisionWindowContextPopoverComponent } from './decision-window-context-popover';

describe('DecisionWindowContextPopoverComponent', () => {
  it('drills into the existing Team Detail service with the stable TeamID', () => {
    const service = { open: jasmine.createSpy('open') } as unknown as TeamDetailDialogService;
    const component = new DecisionWindowContextPopoverComponent(service);

    component.openTeam(42);

    expect(service.open).toHaveBeenCalledOnceWith(42);
  });

  it('uses Updated freshness semantics and tolerates a missing timestamp', () => {
    const component = createComponent();
    component.now = new Date('2026-09-05T10:00:00Z');
    component.updatedAt = '2026-09-05T09:48:00Z';

    expect(component.updatedLabel).toBe('Updated 12 min ago');

    component.updatedAt = undefined;
    expect(component.updatedLabel).toBeNull();
  });

  it('exposes every current League team through the popover rows', () => {
    const component = createComponent();

    expect(component.teamRows.map(row => row.teamId)).toEqual([1, 2, 3]);
  });
});

function createComponent(): DecisionWindowContextPopoverComponent {
  const component = new DecisionWindowContextPopoverComponent({
    open: jasmine.createSpy('open')
  } as unknown as TeamDetailDialogService);
  component.window = createWindow();
  component.model = createModel(component.window);
  component.teams = [createTeam(1), createTeam(2), createTeam(3)];
  return component;
}

function createWindow(): DecisionWindow {
  return {
    DecisionWindowID: '2026-09-06T17:00:00Z',
    Week: 1,
    StartsAtUtc: '2026-09-06T17:00:00Z',
    Games: [{
      GameID: 'g1',
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

function createModel(window: DecisionWindow): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: [window],
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: [1, 2, 3].map(teamId => ({
      FantasyTeamID: teamId,
      State: 'ready' as const,
      ExpectedStarterCount: 13,
      StarterCount: 13,
      OpenStarterSlots: 0,
      Issues: []
    }))
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
