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
    expect(getComputedStyle(metal).paddingLeft).toBe('6px');
    expect(getComputedStyle(metal).paddingTop).toBe('5px');
    expect(getComputedStyle(body).columnGap).toBe('4px');
    expect(getComputedStyle(emblem).width).toBe('46px');
  });

  it('displays a 280px-sized trophy without record or points, keeping identity intact', () => {
    (fixture.nativeElement as HTMLElement).style.width = '280px';
    fixture.componentInstance.subjectAvatar = 'assets/2024-team.png';
    fixture.componentInstance.secondaryAvatar = 'assets/2024-owner.png';
    fixture.detectChanges();

    const plaque = fixture.nativeElement.querySelector('.achievement-plaque') as HTMLElement;
    const year = fixture.nativeElement.querySelector('.achievement-plaque__year') as HTMLElement;
    const emblem = fixture.nativeElement.querySelector('.achievement-plaque__emblem img') as HTMLElement;
    const avatar = fixture.nativeElement.querySelector('.achievement-plaque__primary-avatar') as HTMLElement;

    expect(getComputedStyle(year).fontSize).toBe('16px');
    expect(getComputedStyle(emblem).width).toBe('46px');
    expect(getComputedStyle(avatar).width).toBe('50px');
    expect(getComputedStyle(plaque).width).toBe('280px');
    expect(fixture.nativeElement.querySelector('.achievement-plaque__stats')).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Record');
    expect(fixture.nativeElement.textContent).not.toContain('Points');
    expect(fixture.nativeElement.textContent).toContain('ND - Fighting Childish');
    expect(fixture.nativeElement.textContent).toContain('Regular Season Champion');
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
