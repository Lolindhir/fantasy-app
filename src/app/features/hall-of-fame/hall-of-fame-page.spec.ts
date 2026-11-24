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

  it('shows the champion of a season with its banner and ring, even when the team identity file is unavailable', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.hof-champion').length).toBe(1);
    expect(el.querySelector('.hof-champion app-achievement-banner')?.textContent).toContain('Aces');
    expect(el.querySelector('.hof-champion__ring img')?.getAttribute('src')).toBe('assets/awards/rings/2025.png');
  });

  it('falls back to the generic ring when a season has no ring artwork', () => {
    const img = fixture.nativeElement.querySelector('.hof-champion__ring img') as HTMLImageElement;
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
