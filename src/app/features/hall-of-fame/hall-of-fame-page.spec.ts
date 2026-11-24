import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { DataService } from '../../core/services/data.service';
import { HallOfFamePageComponent } from './hall-of-fame-page';

const league = {
  Season: '2026',
  IsFinished: false,
  Standings: [
    {
      Season: '2025',
      Playoffs: [{ TeamID: 1, Place: 1, PlaceOrdinal: '1.', Owner: 'Ada', TeamName: 'Aces', OwnerAvatar: null, TeamAvatar: 'aces.png' }],
      RegularSeason: [{ TeamID: 1, Place: 1, PlaceOrdinal: '1.', Owner: 'Ada', TeamName: 'Aces', Wins: 10, Losses: 4, Ties: 0, Points: 1, PointsAgainst: 1, WinPercentageDisplay: '' }],
      Awards: []
    },
    { Season: 'AllTime', RegularSeason: [], LegacyHighlights: [{ Key: 'ChampOfChamps', TeamID: 1 }] }
  ]
};

describe('HallOfFamePageComponent', () => {
  let fixture: ComponentFixture<HallOfFamePageComponent>;

  beforeEach(async () => {
    const dataService = {
      getLeagueWithPlayers: () => of({ league, teams: [{ TeamID: 1, Owner: 'Ada', Team: 'Aces', Placements: { AllTime: { Playoffs: { Place: 1, Championships: 1, RunnerUps: 0, Thirds: 0, PlaceAverage: 1 }, Regular: { Place: 1, Wins: 10, Losses: 4, Ties: 0, Points: 1, PointsAgainst: 1, RegularSeasonWins: 1 } } } }], players: [] }),
      getAllSeasonStatistics: () => of({ current: null, bySeason: new Map() }),
      getPlayerAwardHistory: () => of(null),
      getTeamSeasons: () => throwError(() => new Error('unavailable'))
    };
    await TestBed.configureTestingModule({
      imports: [HallOfFamePageComponent],
      providers: [provideRouter([]), { provide: DataService, useValue: dataService }]
    }).compileComponents();
    fixture = TestBed.createComponent(HallOfFamePageComponent);
    fixture.detectChanges();
  });

  it('shows the newest champion large with banner and ring, even when the team identity file is unavailable', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.hof-featured').length).toBe(1);
    expect(el.querySelector('.hof-featured app-achievement-banner')?.textContent).toContain('Aces');
    expect(el.querySelector('.hof-featured__ring img')?.getAttribute('src')).toBe('assets/awards/rings/2025.png');
    expect(el.querySelector('.hof-champions__grid')).toBeNull();
  });

  it('falls back to the generic ring when a season has no ring artwork', () => {
    const img = fixture.nativeElement.querySelector('.hof-featured__ring img') as HTMLImageElement;
    img.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(img.getAttribute('src')).toBe('assets/awards/ui/award-championship-ring.png');
  });

  it('renders the legacy tiles and the all-time standings; empty record groups are not shown', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('app-hall-of-fame[heading="League Legacy"] .hof__card')?.textContent).toContain('Champ of Champs');
    expect(el.querySelector('app-hall-of-fame[heading="All-Time Bests"] .hof')).toBeNull();
    expect(el.querySelector('app-all-time-overview')).not.toBeNull();
  });
});

describe('HallOfFamePageComponent with several champions', () => {
  function season(year: string, teamName: string) {
    return {
      Season: year,
      Playoffs: [{ TeamID: 1, Place: 1, PlaceOrdinal: '1.', Owner: 'Ada', TeamName: teamName, OwnerAvatar: null, TeamAvatar: 'logo.png' }],
      RegularSeason: [{ TeamID: 1, Place: 1, PlaceOrdinal: '1.', Owner: 'Ada', TeamName: teamName, Wins: 10, Losses: 4, Ties: 0, Points: 1, PointsAgainst: 1, WinPercentageDisplay: '' }],
      Awards: []
    };
  }

  let fixture: ComponentFixture<HallOfFamePageComponent>;

  beforeEach(async () => {
    const multi = { Season: '2026', IsFinished: false, Standings: [season('2025', 'Aces'), season('2024', 'Kings'), { Season: 'AllTime', RegularSeason: [] }] };
    const dataService = {
      getLeagueWithPlayers: () => of({ league: multi, teams: [], players: [] }),
      getAllSeasonStatistics: () => of({ current: null, bySeason: new Map() }),
      getPlayerAwardHistory: () => of(null),
      getTeamSeasons: () => throwError(() => new Error('unavailable'))
    };
    await TestBed.configureTestingModule({
      imports: [HallOfFamePageComponent],
      providers: [provideRouter([]), { provide: DataService, useValue: dataService }]
    }).compileComponents();
    fixture = TestBed.createComponent(HallOfFamePageComponent);
    fixture.detectChanges();
  });

  afterEach(() => document.querySelectorAll('.cdk-overlay-container').forEach(c => (c.innerHTML = '')));

  it('keeps the newest champion featured and lists earlier ones as compact tiles without banner', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.hof-featured')?.textContent).toContain('Aces');
    const tiles = el.querySelectorAll('.hof-champion');
    expect(tiles.length).toBe(1);
    expect(tiles[0].querySelector('app-achievement-banner')).toBeNull();
    expect(tiles[0].textContent).toContain('Kings');
    expect(tiles[0].textContent).toContain('2024');
  });

  it('opens the champion detail dialog from a tile', () => {
    (fixture.nativeElement.querySelector('.hof-champion') as HTMLButtonElement).click();
    fixture.detectChanges();
    const dialog = document.querySelector('app-hall-of-fame-champion-dialog');
    expect(dialog?.textContent).toContain('Kings');
    expect(dialog?.querySelector('app-achievement-banner')).not.toBeNull();
    expect(dialog?.querySelector('.champ-dialog__close')).not.toBeNull();
  });
});
