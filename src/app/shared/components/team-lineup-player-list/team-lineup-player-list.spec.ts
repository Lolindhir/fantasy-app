import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/player.models';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import {
  getTeamLineupPlayerStatuses,
  TeamLineupPlayerListComponent
} from './team-lineup-player-list';

describe('TeamLineupPlayerListComponent', () => {
  let fixture: ComponentFixture<TeamLineupPlayerListComponent>;
  let dialog: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [TeamLineupPlayerListComponent],
      providers: [{ provide: MatDialog, useValue: dialog }]
    }).compileComponents();

    fixture = TestBed.createComponent(TeamLineupPlayerListComponent);
  });

  it('renders a compact player row without a table header and shows status chips', () => {
    const player = buildPlayer('loveland', 'Colston Loveland', 'TE');

    fixture.componentRef.setInput('rows', [{ player, statuses: ['Starter', 'IR'] }]);
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('.team-lineup-player-list__header')).toBeNull();
    expect(element.textContent).toContain('Colston Loveland');
    expect(element.textContent).toContain('TE');
    expect(element.textContent).toContain('Starter');
    expect(element.textContent).toContain('IR');
    expect(element.querySelectorAll('.team-lineup-player-status').length).toBe(2);
    expect(element.querySelector('.team-lineup-player-team-logo img')).not.toBeNull();
    expect(element.querySelector('.team-lineup-player-picture img')).not.toBeNull();
  });

  it('resolves game-week lineup placement into Starter, Bench, Taxi and IR chips without hiding contradictory starter state', () => {
    const benchPlayer = buildPlayer('bench', 'Bench Player', 'WR');
    assignFantasyPlacement(benchPlayer, 'activeRoster');
    expect(getTeamLineupPlayerStatuses(benchPlayer, false)).toEqual(['Bench']);
    expect(getTeamLineupPlayerStatuses(benchPlayer, true)).toEqual(['Starter']);

    const taxiPlayer = buildPlayer('taxi', 'Taxi Player', 'RB');
    assignFantasyPlacement(taxiPlayer, 'taxi');
    expect(getTeamLineupPlayerStatuses(taxiPlayer, false)).toEqual(['Taxi']);
    expect(getTeamLineupPlayerStatuses(taxiPlayer, true)).toEqual(['Starter', 'Taxi']);

    const irPlayer = buildPlayer('ir', 'IR Player', 'TE');
    assignFantasyPlacement(irPlayer, 'ir');
    expect(getTeamLineupPlayerStatuses(irPlayer, false)).toEqual(['IR']);
    expect(getTeamLineupPlayerStatuses(irPlayer, true)).toEqual(['Starter', 'IR']);
  });

  it('shows reported injury separately from fantasy placement for starters and reserve players', () => {
    const starter = buildPlayer('starter', 'Starter Player', 'WR');
    starter.InjuryDetails = { Designation: 'Out' } as Player['InjuryDetails'];
    const reserve = buildPlayer('reserve', 'Reserve Player', 'WR');
    reserve.InjuryDetails = { Designation: ' questionable ' } as Player['InjuryDetails'];
    assignFantasyPlacement(reserve, 'ir');
    fixture.componentRef.setInput('rows', [
      { player: starter, statuses: getTeamLineupPlayerStatuses(starter, true) },
      { player: reserve, statuses: getTeamLineupPlayerStatuses(reserve, false) }
    ]);
    fixture.detectChanges();

    const rows = (fixture.nativeElement as HTMLElement).querySelectorAll('.team-lineup-player-row');
    expect(rows[0].querySelector('.team-lineup-player-injury--out')?.textContent).toContain('Injury: Out');
    expect(rows[0].querySelector('.team-lineup-player-status')?.textContent?.trim()).toBe('Starter');
    expect(rows[0].getAttribute('aria-label')).toContain('Injury: Out');
    expect(rows[1].querySelector('.team-lineup-player-injury--questionable')?.textContent).toContain('Injury: Questionable');
    expect(rows[1].querySelector('.team-lineup-player-status')?.textContent?.trim()).toBe('IR');
  });

  it('omits missing and blank injury designations, but preserves unrecognized provider text', () => {
    const missing = buildPlayer('missing', 'Missing', 'WR');
    const blank = buildPlayer('blank', 'Blank', 'WR');
    blank.InjuryDetails = { Designation: '  ' } as Player['InjuryDetails'];
    const unfamiliar = buildPlayer('unfamiliar', 'Unfamiliar', 'WR');
    unfamiliar.InjuryDetails = { Designation: 'Suspended' } as Player['InjuryDetails'];
    const reportedIr = buildPlayer('reported-ir', 'Reported IR', 'WR');
    reportedIr.InjuryDetails = { Designation: 'IR' } as Player['InjuryDetails'];
    fixture.componentRef.setInput('rows', [
      { player: missing, statuses: ['IR'] },
      { player: blank, statuses: ['Bench'] },
      { player: unfamiliar, statuses: ['Bench'] },
      { player: reportedIr, statuses: ['Bench'] }
    ]);
    fixture.detectChanges();

    const rows = (fixture.nativeElement as HTMLElement).querySelectorAll('.team-lineup-player-row');
    expect(rows[0].querySelector('.team-lineup-player-injury')).toBeNull();
    expect(rows[1].querySelector('.team-lineup-player-injury')).toBeNull();
    expect(rows[2].querySelector('.team-lineup-player-injury--unknown')?.textContent).toContain('Injury: Suspended');
    expect(rows[3].querySelector('.team-lineup-player-injury--ir')?.textContent).toContain('Injury: IR');
    expect(rows[3].querySelector('.team-lineup-player-status')?.textContent?.trim()).toBe('Bench');
  });

  it('keeps Player Detail interaction on the dedicated lineup row', () => {
    const player = buildPlayer('brooks', 'Jonathon Brooks', 'RB');

    fixture.componentRef.setInput('rows', [{ player, statuses: ['Bench'] }]);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('.team-lineup-player-row') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalledWith(
      PlayerDetailDialogComponent,
      jasmine.objectContaining({ data: player })
    );
  });
});

function buildPlayer(id: string, name: string, position: string): Player {
  return {
    ID: id,
    Name: name,
    NameShort: name,
    Position: position,
    Picture: 'player-picture',
    TeamNFL: {
      ID: '6',
      Name: 'Bears',
      Abv: 'CHI',
      Logo: 'team-logo'
    }
  } as Player;
}

function assignFantasyPlacement(player: Player, placement: 'activeRoster' | 'taxi' | 'ir'): void {
  const team = {
    TeamID: 1,
    Roster: [player],
    Taxi: placement === 'taxi' ? [player] : [],
    Reserve: placement === 'ir' ? [player] : [],
    Starter: []
  } as unknown as Player['TeamFantasy'];

  player.TeamFantasy = team;
}
