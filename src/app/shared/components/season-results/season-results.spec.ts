import { ComponentFixture, TestBed } from '@angular/core/testing';

import type { SeasonResultsViewModel } from '../../utils/league-standings-view.util';
import { SeasonResultsComponent } from './season-results';

describe('SeasonResultsComponent remaining playoff placements', () => {
  let fixture: ComponentFixture<SeasonResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SeasonResultsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(SeasonResultsComponent);
    fixture.componentInstance.results = {
      champion: null,
      runnerUp: null,
      thirdPlace: null,
      regularSeasonChampion: null,
      remainingTeams: [4, 9, 10, 11, 12].map(place => ({
        place,
        teamName: `Team ${place}`,
        team: { Owner: `Owner ${place}` },
        teamAvatar: null,
        ownerAvatar: null,
        isRegularSeasonChampion: place === 4
      }))
    } as unknown as SeasonResultsViewModel;
    fixture.detectChanges();
  });

  it('uses the shared numeric shield while preserving team and achievement markup', () => {
    const rows = Array.from(fixture.nativeElement.querySelectorAll('.team-row')) as HTMLElement[];
    expect(rows.length).toBe(5);

    rows.forEach((row, index) => {
      const place = [4, 9, 10, 11, 12][index];
      const badge = row.querySelector('app-standing-rank-badge .standing-rank-badge');
      expect(badge?.getAttribute('aria-label')).toBe(`Playoff place ${place}`);
      expect(badge?.textContent?.trim()).toBe(String(place));
      expect(row.querySelector('.team-row__primary-avatar')).not.toBeNull();
      expect(row.querySelector('.team-row__name')?.textContent?.trim()).toBe(`Team ${place}`);
      expect(getComputedStyle(row).height).toBe('58px');
    });

    expect(rows[0].querySelector('.team-row__achievement-badge')).not.toBeNull();
    expect(rows[1].querySelector('.team-row__achievement-badge')).toBeNull();
  });

  it('fits two-digit badges into a narrow 272px row without moving the identity column', () => {
    const rest = fixture.nativeElement.querySelector('.rest') as HTMLElement;
    rest.style.width = '272px';

    const rows = Array.from(rest.querySelectorAll('.team-row')) as HTMLElement[];
    const identityStarts = rows.map(row =>
      (row.querySelector('.team-row__identity') as HTMLElement).getBoundingClientRect().left
    );

    expect(Math.max(...identityStarts) - Math.min(...identityStarts)).toBeLessThan(1);

    for (const row of rows) {
      const rankColumn = row.querySelector('.place') as HTMLElement;
      const badge = rankColumn.querySelector('.standing-rank-badge') as HTMLElement;
      const badgeBox = badge.getBoundingClientRect();
      const columnBox = rankColumn.getBoundingClientRect();

      expect(badgeBox.width).toBeLessThanOrEqual(columnBox.width);
      expect(badgeBox.left).toBeGreaterThanOrEqual(columnBox.left - 1);
      expect(badgeBox.right).toBeLessThanOrEqual(columnBox.right + 1);
      expect(row.scrollWidth).toBeLessThanOrEqual(row.clientWidth);
    }
  });
});
