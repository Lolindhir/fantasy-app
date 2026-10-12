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

  it('keeps the real team avatar when a snapshot provides one', () => {
    fixture.componentInstance.subjectAvatar = 'assets/test-team-avatar.png';
    fixture.detectChanges();

    const primaryAvatar = fixture.nativeElement.querySelector(
      '.achievement-plaque__primary-avatar img'
    ) as HTMLImageElement | null;

    expect(primaryAvatar?.getAttribute('src')).toBe('assets/test-team-avatar.png');
  });
});
