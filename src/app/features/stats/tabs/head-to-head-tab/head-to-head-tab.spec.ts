import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import type { FantasyTeam } from '../../../../core/models/league.models';
import type { RawRivalryGame, RawRivalryRecord, RivalryReadModel } from '../../../../core/models/rivalry.models';
import { DataService, type LeagueWithPlayers } from '../../../../core/services/data.service';
import { RivalryLookup, TeamRivalryService } from '../../../../shared/services/team-rivalry.service';
import { TeamDetailDialogService } from '../../../../shared/services/team-detail-dialog.service';
import { HeadToHeadTabComponent } from './head-to-head-tab';

function team(id: number): FantasyTeam {
  return { TeamID: id, Team: `Team ${id}`, TeamAbbr: `T${id}`, Owner: `Owner ${id}`, Avatar: '', OwnerAvatar: '', Roster: [] } as unknown as FantasyTeam;
}

const game = (id: string, outcome: 'win' | 'loss'): RawRivalryGame => ({
  Season: '2025', Week: 1, FantasyMatchupID: id, Stage: 'regular-season', Bracket: null, Outcome: outcome,
  TeamPoints: 100, OpponentPoints: 90, Margin: 10
});

const record = (teamId: number, opponentId: number, filter: RawRivalryRecord['Filter'], wins: number, losses: number): RawRivalryRecord => ({
  TeamID: teamId, OpponentID: opponentId, Filter: filter, Wins: wins, Losses: losses, Ties: 0, PointsFor: 1, PointsAgainst: 1,
  BiggestWinMatchupID: null, ClosestLossMatchupID: null, Games: [game(`${teamId}-${opponentId}-${filter}`, 'win')]
});

const model: RivalryReadModel = {
  SchemaVersion: 1, Product: 'league-rivalry', CanonicalLeagueID: 'test',
  Seasons: [{ Season: '2024' }, { Season: '2025' }],
  Records: [
    record(1, 2, 'all', 3, 1), record(2, 1, 'all', 1, 3),
    record(1, 2, 'playoffs', 0, 1)
  ]
};

describe('HeadToHeadTabComponent', () => {
  function create(): { fixture: ComponentFixture<HeadToHeadTabComponent>; root: HTMLElement; open: jasmine.Spy } {
    const dataService = jasmine.createSpyObj<DataService>('DataService', ['getLeagueWithPlayers']);
    dataService.getLeagueWithPlayers.and.returnValue(of({ league: { Season: '2025' }, teams: [team(1), team(2)] } as unknown as LeagueWithPlayers));
    const open = jasmine.createSpy('open');
    TestBed.configureTestingModule({
      imports: [HeadToHeadTabComponent],
      providers: [
        { provide: DataService, useValue: dataService },
        { provide: TeamRivalryService, useValue: { getLookup: () => of(new RivalryLookup(model)) } },
        { provide: TeamDetailDialogService, useValue: { open } }
      ]
    });
    const fixture = TestBed.createComponent(HeadToHeadTabComponent);
    fixture.detectChanges();
    return { fixture, root: fixture.nativeElement as HTMLElement, open };
  }

  const records = (root: HTMLElement) => Array.from(root.querySelectorAll('.h2h-record')).map(node => node.textContent?.trim());

  it('shows the generated record per team pair and leaves the diagonal empty', () => {
    const { root } = create();
    expect(root.querySelectorAll('.h2h-self').length).toBe(2);
    expect(records(root)).toEqual(['3-1', '1-3']);
  });

  it('switches the filter to the generated playoff records', () => {
    const { fixture, root } = create();
    (Array.from(root.querySelectorAll('.stats-chip')).find(node => node.textContent?.trim() === 'Playoffs') as HTMLElement).click();
    fixture.detectChanges();
    expect(records(root)).toEqual(['0-1', '–']);
  });

  it('opens the rivals tab of the row team', () => {
    const { root, open } = create();
    (root.querySelector('.h2h-record') as HTMLElement).click();
    expect(open).toHaveBeenCalledOnceWith(1, { initialTab: 'rivals' });
  });
});
