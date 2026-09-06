import type { DecisionWindow, DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import type { Player } from '../../../core/models/player.models';
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

  it('keeps commissioner scope exposing every current League team', () => {
    const component = createComponent();

    expect(component.isTeamScope).toBeFalse();
    expect(component.teamRows.map(row => row.teamId)).toEqual([1, 2, 3]);
  });

  it('team scope exposes only affected players for the selected fantasy team', () => {
    const component = createComponent();
    component.teamId = 2;
    component.players = [
      makePlayer('starter', 'Starter Player'),
      makePlayer('bench', 'Bench Player'),
      makePlayer('other', 'Other Player')
    ];
    component.window = {
      ...component.window,
      AffectedFantasyTeams: [{
        FantasyTeamID: 2,
        AffectedRosteredPlayerCount: 2,
        AffectedStarterCount: 1,
        Players: [
          { PlayerID: 'bench', NFLTeamID: 'SEA', GameID: 'g1', IsStarter: false },
          { PlayerID: 'starter', NFLTeamID: 'NE', GameID: 'g1', IsStarter: true }
        ]
      }]
    };

    expect(component.isTeamScope).toBeTrue();
    expect(component.teamAffectedPlayers.map(player => player.ID)).toEqual(['starter', 'bench']);
    expect(component.getTeamPlayerRole(component.teamAffectedPlayers[0])).toBe('Starter');
    expect(component.getTeamPlayerRole(component.teamAffectedPlayers[1])).toBe('Roster');
    expect(component.teamAffectedPlayers.some(player => player.ID === 'other')).toBeFalse();
  });

  it('team scope reports unresolved affected player ids without falling back to league-wide context', () => {
    const component = createComponent();
    component.teamId = 2;
    component.players = [makePlayer('known', 'Known')];
    component.window = {
      ...component.window,
      AffectedFantasyTeams: [{
        FantasyTeamID: 2,
        AffectedRosteredPlayerCount: 2,
        AffectedStarterCount: 1,
        Players: [
          { PlayerID: 'known', NFLTeamID: 'NE', GameID: 'g1', IsStarter: true },
          { PlayerID: 'missing', NFLTeamID: 'SEA', GameID: 'g1', IsStarter: false }
        ]
      }]
    };

    expect(component.teamAffectedPlayers.map(player => player.ID)).toEqual(['known']);
    expect(component.unresolvedTeamPlayerCount).toBe(1);
    expect(component.teamScopeSummary).toBe('2 players · 1 starter');
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

function makePlayer(id: string, name: string): Player {
  return { ID: id, Name: name, NameShort: name } as Player;
}
