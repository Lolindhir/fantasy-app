import { TestBed } from '@angular/core/testing';

import { PlayoffPlaceBarsComponent } from './playoff-place-bars';

describe('PlayoffPlaceBarsComponent', () => {
  it('labels an exact 0 as 0% and an exact 1 as 100%', () => {
    const fixture = TestBed.createComponent(PlayoffPlaceBarsComponent);
    Object.assign(fixture.componentInstance, { places: [0, 0.004, 0.5, 0.996, 1], playoffTeams: 2 });
    fixture.detectChanges();

    const labels = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('.place-value'))
      .map(el => el.textContent?.trim());
    expect(labels).toEqual(['0%', '<1%', '50%', '>99%', '100%']);
  });
});
