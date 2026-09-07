import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/player.models';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { TeamLineupPlayerListComponent } from './team-lineup-player-list';

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

  it('renders team logo, player picture, full player name, position and role in one row', () => {
    const player = {
      ID: 'loveland',
      Name: 'Colston Loveland',
      NameShort: 'C. Loveland',
      Position: 'TE',
      Picture: 'player-picture',
      TeamNFL: {
        ID: '6',
        Name: 'Bears',
        Abv: 'CHI',
        Logo: 'team-logo'
      }
    } as Player;

    fixture.componentRef.setInput('rows', [{ player, role: 'Starter' }]);
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;
    expect(element.textContent).toContain('Colston Loveland');
    expect(element.textContent).toContain('TE');
    expect(element.textContent).toContain('Starter');
    expect(element.querySelector('.team-lineup-player-team-logo img')).not.toBeNull();
    expect(element.querySelector('.team-lineup-player-picture img')).not.toBeNull();
  });

  it('keeps Player Detail interaction on the dedicated lineup row', () => {
    const player = {
      ID: 'brooks',
      Name: 'Jonathon Brooks',
      NameShort: 'J. Brooks',
      Position: 'RB',
      Picture: 'player-picture',
      TeamNFL: {
        ID: '5',
        Name: 'Panthers',
        Abv: 'CAR',
        Logo: 'team-logo'
      }
    } as Player;

    fixture.componentRef.setInput('rows', [{ player, role: 'Roster' }]);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('.team-lineup-player-row') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalledWith(
      PlayerDetailDialogComponent,
      jasmine.objectContaining({ data: player })
    );
  });
});
