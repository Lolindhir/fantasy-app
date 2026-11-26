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
      getPlayerAwardHistory: () => of({
        Leaders: { MVP: [
          { PlayerID: 'a', Name: 'First Long Player Name', Count: 4 },
          { PlayerID: 'b', Name: 'Second Player', Count: 4 },
          { PlayerID: 'c', Name: 'Third Player', Count: 4 },
          { PlayerID: 'd', Name: 'Fourth Player', Count: 4 },
          { PlayerID: 'e', Name: 'Fifth Player', Count: 4 },
          { PlayerID: 'f', Name: 'Sixth Player', Count: 4 },
          { PlayerID: 'g', Name: 'Seventh Player', Count: 4 },
          { PlayerID: 'h', Name: 'Eighth Player', Count: 4 }
        ],
        MatchupHero: [
          { PlayerID: 'a', Name: 'First Long Player Name', Count: 2 },
          { PlayerID: 'b', Name: 'Second Player', Count: 2 }
        ],
        Heartbreaker: [{ PlayerID: 'c', Name: 'Third Player', Count: 1 }] },
        Players: [{ PlayerID: 'a', Picture: 'first.png' }]
      }),
      getTeamSeasons: () => throwError(() => new Error('unavailable'))
    };
    await TestBed.configureTestingModule({
      imports: [HallOfFamePageComponent],
      providers: [provideRouter([]), { provide: DataService, useValue: dataService }]
    }).compileComponents();
    fixture = TestBed.createComponent(HallOfFamePageComponent);
    fixture.detectChanges();
  });

  it('shows a single champion as a normal tile with ring, without banner, even when the team identity file is unavailable', () => {
    const el = fixture.nativeElement as HTMLElement;
    const tiles = el.querySelectorAll('.hof-champion');
    expect(tiles.length).toBe(1);
    expect(tiles[0].querySelector('app-achievement-banner')).toBeNull();
    expect(tiles[0].textContent).toContain('Aces');
    expect(el.querySelector('.hof-champion__ring')?.getAttribute('src')).toBe('assets/awards/rings/2025.png');
  });

  it('falls back to the generic ring when a season has no ring artwork', () => {
    const img = fixture.nativeElement.querySelector('.hof-champion__ring') as HTMLImageElement;
    img.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(img.getAttribute('src')).toBe('assets/awards/ui/award-championship-ring.png');
  });

  it('shows every tied player as an equal avatar and reveals all names only on expansion', () => {
    const el = fixture.nativeElement as HTMLElement;
    const card = el.querySelector('app-hall-of-fame[heading="Player Legends"] .hof__card')!;
    const details = card.querySelector('details') as HTMLDetailsElement;
    const summary = details.querySelector('summary')!;
    expect(summary.querySelectorAll('.hof__portrait').length).toBe(8);
    expect(summary.querySelector('.hof__photo')?.getAttribute('src')).toBe('first.png');
    expect(summary.textContent).toContain('8 players tied');
    expect(summary.textContent).not.toContain('First Long Player Name');
    expect(card.querySelector('.hof__winners > .hof__identity')).toBeNull();
    expect(details.open).toBe(false);
    details.open = true;
    fixture.detectChanges();
    expect(details.querySelectorAll('.hof__extra .hof__identity').length).toBe(8);
    expect(details.querySelector('.hof__extra')?.textContent).toContain('First Long Player Name');
    expect(details.querySelector('.hof__extra')?.textContent).toContain('Eighth Player');
    expect(card.querySelector('.hof__value')?.textContent).toContain('4×');
  });

  it('renders one or two co-leaders directly without arbitrary hiding', () => {
    const el = fixture.nativeElement as HTMLElement;
    const cards = el.querySelectorAll('app-hall-of-fame[heading="Player Legends"] .hof__card');
    expect(cards[1].querySelectorAll('.hof__identity').length).toBe(2);
    expect(cards[1].textContent).toContain('First Long Player Name');
    expect(cards[1].textContent).toContain('Second Player');
    expect(cards[1].querySelector('details')).toBeNull();
    expect(cards[2].querySelectorAll('.hof__identity').length).toBe(1);
    expect(cards[2].textContent).toContain('Third Player');
    expect(cards[2].querySelector('details')).toBeNull();
  });

  it('uses the compact grid for team records only and gives champions the matching heading and gold border', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.hof-champions__head h2')?.textContent).toBe('League Champions');
    expect(el.querySelector('.hof-champions__crest')?.textContent).toBe('🏆');
    expect(getComputedStyle(el.querySelector('.hof-champion')!).borderTopColor).toBe('rgb(200, 170, 114)');
    expect(el.querySelector('app-hall-of-fame[heading="League Legacy"] .hof__grid--compact')).not.toBeNull();
    expect(el.querySelector('app-hall-of-fame[heading="Player Legends"] .hof__grid--compact')).toBeNull();
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

  it('lists every champion, newest first, as the same compact tile without banner', () => {
    const el = fixture.nativeElement as HTMLElement;
    const tiles = el.querySelectorAll('.hof-champion');
    expect(tiles.length).toBe(2);
    expect(el.querySelector('.hof-featured')).toBeNull();
    expect(tiles[0].textContent).toContain('Aces');
    expect(tiles[1].textContent).toContain('Kings');
    expect(tiles[1].textContent).toContain('2024');
    tiles.forEach(t => expect(t.querySelector('app-achievement-banner')).toBeNull());
  });

  it('opens the champion detail dialog from a tile', () => {
    (fixture.nativeElement.querySelectorAll('.hof-champion')[1] as HTMLButtonElement).click();
    fixture.detectChanges();
    const dialog = document.querySelector('app-hall-of-fame-champion-dialog');
    expect(dialog?.textContent).toContain('Kings');
    expect(dialog?.querySelector('app-achievement-banner')).not.toBeNull();
    expect(dialog?.querySelector('.champ-dialog__close')).not.toBeNull();
  });
});
