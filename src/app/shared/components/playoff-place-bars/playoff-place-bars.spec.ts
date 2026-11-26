import { TestBed } from '@angular/core/testing';

import { PlayoffPlaceBarsComponent } from './playoff-place-bars';

describe('PlayoffPlaceBarsComponent', () => {
  it('labels place shares with one decimal', () => {
    const fixture = TestBed.createComponent(PlayoffPlaceBarsComponent);
    Object.assign(fixture.componentInstance, { places: [0, 0.004, 0.5, 0.996, 1], playoffTeams: 2 });
    fixture.detectChanges();

    const labels = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('.place-value'))
      .map(el => el.textContent?.trim());
    expect(labels).toEqual(['0.0%', '0.4%', '50.0%', '99.6%', '100.0%']);
  });
  it('uses the same joint rounding and exact tail labels for bars and accessible description', () => {
    const fixture = TestBed.createComponent(PlayoffPlaceBarsComponent);
    Object.assign(fixture.componentInstance, {
      places: [1, 1e-30, 0], placeLabels: ['>99.99%', '<0.01%', '0.0%'],
      model: 'playoff-odds-v4', playoffTeams: 1
    });
    fixture.detectChanges();
    const labels = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('.place-value'))
      .map(el => el.textContent?.trim());
    expect(labels).toEqual(['>99.99%', '<0.01%', '0.0%']);
    expect(fixture.componentInstance.bars[1].heightPercent).toBeGreaterThan(0);
    expect(fixture.componentInstance.bars[2].heightPercent).toBe(0);
    expect(fixture.componentInstance.description).toContain('1% tie probability');
    expect(fixture.componentInstance.description).toContain('place 2 <0.01%');
  });
});
