import { ComponentFixture, TestBed } from '@angular/core/testing';

import type { AchievementBannerAccent } from './achievement-banner';
import { AchievementBannerComponent } from './achievement-banner';

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

  it('makes the regular-season achievement badge 25% larger without resizing the team avatar', () => {
    fixture.componentInstance.achievementBadgeSrc = 'assets/awards/ui/award-regular-season.png';
    fixture.detectChanges();

    const badge = fixture.nativeElement.querySelector('.achievement-banner__corner-badge') as HTMLElement;
    const badgeImage = badge.querySelector('img') as HTMLImageElement;
    const avatar = fixture.nativeElement.querySelector('.achievement-banner__primary-avatar') as HTMLElement;

    expect(getComputedStyle(badge).width).toBe('32px');
    expect(getComputedStyle(badgeImage).width).toBe('27px');
    expect(Number.parseFloat(getComputedStyle(badge).right)).toBeCloseTo(-10.72, 1);
    expect(getComputedStyle(avatar).width).toBe('52px');
  });

  it('reserves 3px of safety space on each side of the team name', () => {
    fixture.componentInstance.subjectName = 'ND - Fighting Childish';
    fixture.detectChanges();

    const name = fixture.nativeElement.querySelector('.achievement-banner__name') as HTMLElement;
    const style = getComputedStyle(name);

    expect(style.boxSizing).toBe('border-box');
    expect(style.paddingLeft).toBe('3px');
    expect(style.paddingRight).toBe('3px');
  });

  it('colors both avatar outlines with the gold, silver or bronze thread', () => {
    fixture.componentInstance.secondaryAvatar = 'assets/owner-avatar.png';

    const expected = [
      { accent: 'silver', color: 'rgb(225, 229, 234)' },
      { accent: 'gold', color: 'rgb(240, 206, 131)' },
      { accent: 'bronze', color: 'rgb(232, 178, 142)' }
    ] as const;

    for (const tier of expected) {
      fixture.componentInstance.accent = tier.accent;
      fixture.detectChanges();

      const primary = fixture.nativeElement.querySelector('.achievement-banner__primary-avatar') as HTMLElement;
      const secondary = fixture.nativeElement.querySelector('.achievement-banner__secondary-avatar') as HTMLElement;

      expect(getComputedStyle(primary).borderTopColor).toBe(tier.color);
      expect(getComputedStyle(secondary).borderTopColor).toBe(tier.color);
    }
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
