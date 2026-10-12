import { ComponentFixture, TestBed } from '@angular/core/testing';

import {
  AchievementBannerAccent,
  AchievementBannerComponent
} from './achievement-banner';

describe('AchievementBannerComponent textile treatment', () => {
  let fixture: ComponentFixture<AchievementBannerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AchievementBannerComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AchievementBannerComponent);
    fixture.componentInstance.season = '2025';
    fixture.componentInstance.achievementLabel = 'Champion';
    fixture.componentInstance.subjectName = 'Mighty Giants';
    fixture.componentInstance.emblemSrc = 'assets/awards/ui/award-championship-ring.png';
  });

  it('preserves the angled banner shape and embroidered stitch outlines', () => {
    fixture.detectChanges();
    const banner = fixture.nativeElement.querySelector('.achievement-banner') as HTMLElement;

    expect(getComputedStyle(banner).clipPath).toContain('polygon(');
    expect(banner.querySelectorAll('.achievement-banner__threadwork path').length).toBe(2);
    expect(banner.querySelector('.achievement-banner__name')?.textContent).toContain('Mighty Giants');
    expect(banner.querySelector('.achievement-banner__season')?.textContent).toContain('2025');
  });

  it('uses a common textile background while changing only metallic threading', () => {
    const styles = (['silver', 'gold', 'bronze'] as AchievementBannerAccent[]).map(accent => {
      fixture.componentInstance.accent = accent;
      fixture.detectChanges();
      const banner = fixture.nativeElement.querySelector('.achievement-banner') as HTMLElement;
      const computed = getComputedStyle(banner);
      return {
        fabricTop: computed.getPropertyValue('--banner-top').trim(),
        fabricBottom: computed.getPropertyValue('--banner-bottom').trim(),
        thread: computed.getPropertyValue('--banner-thread').trim()
      };
    });

    expect(new Set(styles.map(style => style.fabricTop)).size).toBe(1);
    expect(new Set(styles.map(style => style.fabricBottom)).size).toBe(1);
    expect(new Set(styles.map(style => style.thread)).size).toBe(3);
  });
});
