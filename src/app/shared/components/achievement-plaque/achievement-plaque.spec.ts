import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AchievementPlaqueComponent } from './achievement-plaque';

describe('AchievementPlaqueComponent avatar fallback', () => {
  let fixture: ComponentFixture<AchievementPlaqueComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AchievementPlaqueComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AchievementPlaqueComponent);
    fixture.componentInstance.season = '2024';
    fixture.componentInstance.subjectName = 'ND - Fighting Childish';
  });

  it('uses the shared team avatar when a historical snapshot has no team avatar', () => {
    fixture.componentInstance.subjectAvatar = null;
    fixture.detectChanges();

    const primaryAvatar = fixture.nativeElement.querySelector(
      '.achievement-plaque__primary-avatar img'
    ) as HTMLImageElement | null;

    expect(primaryAvatar).not.toBeNull();
    expect(primaryAvatar?.getAttribute('src')).toBe('assets/default-team-avatar.png');
    expect(fixture.nativeElement.querySelector('.achievement-plaque__primary-avatar span')).toBeNull();
  });

  it('keeps the mobile plaque internals compact without shrinking avatars or emblems', () => {
    // Exercise the <=480px container-query style regardless of the CI browser viewport.
    (fixture.nativeElement as HTMLElement).style.width = '320px';
    fixture.detectChanges();

    const plaque = fixture.nativeElement.querySelector('.achievement-plaque') as HTMLElement;
    const metal = fixture.nativeElement.querySelector('.achievement-plaque__metal') as HTMLElement;
    const body = fixture.nativeElement.querySelector('.achievement-plaque__body') as HTMLElement;
    const emblem = fixture.nativeElement.querySelector('.achievement-plaque__emblem img') as HTMLElement;

    expect(getComputedStyle(plaque).paddingTop).toBe('6px');
    expect(getComputedStyle(metal).paddingLeft).toBe('8px');
    expect(getComputedStyle(metal).paddingTop).toBe('7px');
    expect(getComputedStyle(body).columnGap).toBe('7px');
    expect(getComputedStyle(emblem).width).toBe('46px');
  });

  it('uses a smaller year and a single compact stats row with accessible record/points labels', () => {
    (fixture.nativeElement as HTMLElement).style.width = '300px';
    fixture.componentInstance.record = '11-3';
    fixture.componentInstance.points = 2468.78;
    fixture.detectChanges();

    const year = fixture.nativeElement.querySelector('.achievement-plaque__year') as HTMLElement;
    const record = fixture.nativeElement.querySelector('.achievement-plaque__record') as HTMLElement;
    const points = fixture.nativeElement.querySelector('.achievement-plaque__points') as HTMLElement;
    const stats = fixture.nativeElement.querySelector('.achievement-plaque__stats') as HTMLElement;
    const body = fixture.nativeElement.querySelector('.achievement-plaque__body') as HTMLElement;

    expect(getComputedStyle(year).fontSize).toBe('16px');
    expect(getComputedStyle(body).columnGap).toBe('4px');
    expect(Number.parseFloat(getComputedStyle(record).fontSize)).toBeCloseTo(16.8, 1);
    expect(Number.parseFloat(getComputedStyle(points).fontSize)).toBeLessThan(
      Number.parseFloat(getComputedStyle(record).fontSize)
    );
    expect(stats.querySelectorAll('.achievement-plaque__stat-label').length).toBe(0);
    expect(record.textContent).toContain('Record:');
    expect(record.textContent).toContain('11-3');
    expect(points.textContent).toContain('Points:');
    expect(points.textContent).toContain('2,468.78');
    expect(points.textContent).toContain('pts');
  });

  it('keeps the real team avatar when a snapshot provides one', () => {
    fixture.componentInstance.subjectAvatar = 'assets/test-team-avatar.png';
    fixture.detectChanges();

    const primaryAvatar = fixture.nativeElement.querySelector(
      '.achievement-plaque__primary-avatar img'
    ) as HTMLImageElement | null;

    expect(primaryAvatar?.getAttribute('src')).toBe('assets/test-team-avatar.png');
  });
});
