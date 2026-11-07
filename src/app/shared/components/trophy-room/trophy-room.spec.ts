import { ComponentFixture, TestBed } from '@angular/core/testing';

import type { Standing } from '../../../core/models/fantasy.models';
import { TrophyRoomComponent } from './trophy-room';

describe('TrophyRoomComponent ring asset fallback', () => {
  let fixture: ComponentFixture<TrophyRoomComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [TrophyRoomComponent] }).compileComponents();
    const standings = [{
      Season: '2025',
      Playoffs: [{ Place: 1, PlaceOrdinal: '1st', TeamID: 3, Owner: 'O', TeamName: 'Just Bill', TeamAvatar: 'a.png' }],
      RegularSeason: []
    }] as Standing[];
    fixture = TestBed.createComponent(TrophyRoomComponent);
    fixture.componentInstance.league = { Standings: standings, Season: '2026', IsFinished: false };
    fixture.componentInstance.team = { TeamID: 3 };
    fixture.detectChanges();
  });

  it('shows the season ring path first and falls back to the generic ring when the file is missing', () => {
    const img = () => fixture.nativeElement.querySelector('.trophy-ring img') as HTMLImageElement;
    expect(img().getAttribute('src')).toBe('assets/awards/rings/2025.png');

    img().dispatchEvent(new Event('error'));
    fixture.detectChanges();

    expect(img().getAttribute('src')).toBe('assets/awards/ui/award-championship-ring.png');
  });

  it('shows an empty state for a team without titles', () => {
    fixture.componentInstance.team = { TeamID: 99 };
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.empty-state')?.textContent).toContain('No titles');
  });
});
