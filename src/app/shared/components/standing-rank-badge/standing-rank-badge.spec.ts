import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StandingRankBadgeComponent } from './standing-rank-badge';

describe('StandingRankBadgeComponent', () => {
  let fixture: ComponentFixture<StandingRankBadgeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StandingRankBadgeComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(StandingRankBadgeComponent);
  });

  for (const rank of [4, 9, 10, 11, 12, 32]) {
    it(`renders rank ${rank} as accessible numeric text instead of an emoji`, () => {
      fixture.componentInstance.rank = rank;
      fixture.detectChanges();

      const badge = fixture.nativeElement.querySelector('.standing-rank-badge') as HTMLElement;
      const number = badge.querySelector('.standing-rank-badge__number') as HTMLElement;

      expect(number.textContent?.trim()).toBe(String(rank));
      expect(number.getAttribute('aria-hidden')).toBe('true');
      expect(badge.getAttribute('role')).toBe('img');
      expect(badge.getAttribute('aria-label')).toBe(`Playoff place ${rank}`);
      expect(badge.textContent?.trim()).toBe(String(rank));
    });
  }

  it('retains the 30px shield height and numeral size while growing for two digits', () => {
    const measure = (rank: number) => {
      fixture.componentInstance.rank = rank;
      fixture.detectChanges();
      const badge = fixture.nativeElement.querySelector('.standing-rank-badge') as HTMLElement;
      const number = badge.querySelector('.standing-rank-badge__number') as HTMLElement;
      return {
        width: badge.getBoundingClientRect().width,
        height: badge.getBoundingClientRect().height,
        fontSize: getComputedStyle(number).fontSize,
        numericVariant: getComputedStyle(number).fontVariantNumeric,
        clipPath: getComputedStyle(badge).clipPath
      };
    };

    const single = measure(9);
    expect(single.height).toBe(30);
    expect(single.width).toBeGreaterThanOrEqual(32);
    expect(single.numericVariant).toContain('tabular-nums');
    expect(single.clipPath).toContain('polygon(');

    for (const rank of [10, 11, 12, 32]) {
      const double = measure(rank);
      expect(double.height).toBe(single.height);
      expect(double.width).toBeGreaterThan(single.width);
      expect(double.fontSize).toBe(single.fontSize);
      expect(double.clipPath).toBe(single.clipPath);
    }
  });
});
