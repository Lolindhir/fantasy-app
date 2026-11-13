import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import type { FantasyTeam } from '../../core/models/league.models';
import type { FantasyGameContextReadModel, HistoricalFantasyGameContextSeason } from '../../core/models/fantasy-game-context.models';
import type { MatchupsReadModel } from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import { DataService, type LeagueWithPlayers } from '../../core/services/data.service';
import type { PastSeasonsIndex } from '../../core/services/data-api.service';
import { TeamDetailDialogService } from '../../shared/services/team-detail-dialog.service';
import { WeeksPageComponent } from './weeks-page';

function team(id: number): FantasyTeam {
  return {
    TeamID: id,
    Team: `Team ${id}`,
    TeamAbbr: `T${id}`,
    Owner: `Owner ${id}`,
    Avatar: '',
    OwnerAvatar: '',
    Roster: []
  } as unknown as FantasyTeam;
}

function matchups(season: string, weeks: Array<{ week: number; stage: 'regular-season' | 'playoffs'; state: 'final' | 'open' }>): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: season,
    Summary: { LastCompletedWeek: null, ActiveOrNextWeek: null },
    Weeks: weeks.map(({ week, stage, state }) => ({
      Week: week,
      Stage: stage,
      FirstKickoffUtc: null,
      CompletionState: state,
      Matchups: [{
        FantasyMatchupID: `${season}-${week}`,
        CompletionState: state,
        Participants: [
          { TeamID: 1, Points: state === 'final' ? 100 + week : null, ScoreKind: 'standard' as const },
          { TeamID: 2, Points: state === 'final' ? 90 : null, ScoreKind: 'standard' as const }
        ],
        Result: state === 'final' ? { Type: 'win' as const, WinnerTeamID: 1 } : null
      }]
    }))
  };
}

function recaps(season: string, weeks: number[]): WeeklyRecapsReadModel {
  return {
    SchemaVersion: 1,
    Season: season,
    Weeks: weeks.map(week => ({
      Week: week,
      KeyGames: [],
      KeyPlayers: [{ PlayerID: 'missing-player', FantasyTeamID: 1, NFLTeamID: 'BUF', Position: 'QB', Points: 30.5 }]
    }))
  };
}

const index = {
  GeneratedAt: null,
  Seasons: [{
    Season: '2025',
    Resources: {
      Matchups: { Path: 'data/past_seasons/Matchups/Matchups_2025.json', Exists: true },
      WeeklyRecaps: { Path: 'data/past_seasons/WeeklyRecaps/WeeklyRecaps_2025.json', Exists: true }
    }
  }]
} as unknown as PastSeasonsIndex;

describe('WeeksPageComponent', () => {
  let fixture: ComponentFixture<WeeksPageComponent>;
  let dataService: jasmine.SpyObj<DataService>;

  async function create(query: Record<string, string> = {}): Promise<HTMLElement> {
    await TestBed.configureTestingModule({
      imports: [WeeksPageComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: DataService, useValue: dataService },
        { provide: TeamDetailDialogService, useValue: jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']) },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(WeeksPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayers',
      'getPastSeasonsIndex',
      'getNflTeams',
      'getMatchups',
      'getWeeklyRecaps',
      'getPastMatchupsRaw',
      'getPastWeeklyRecapsRaw',
      'getFantasyGameContext',
      'getPastFantasyGameContextRaw',
      'getFantasyGameContextHistory'
    ]);
    dataService.getLeagueWithPlayers.and.returnValue(of({
      league: { Season: '2026' },
      teams: [team(1), team(2)]
    } as unknown as LeagueWithPlayers));
    dataService.getPastSeasonsIndex.and.returnValue(of(index));
    dataService.getNflTeams.and.returnValue(of([]));
    dataService.getMatchups.and.returnValue(of(matchups('2026', [
      { week: 1, stage: 'regular-season', state: 'final' },
      { week: 2, stage: 'regular-season', state: 'final' },
      { week: 3, stage: 'regular-season', state: 'open' }
    ])));
    dataService.getWeeklyRecaps.and.returnValue(of(recaps('2026', [1, 2])));
    dataService.getPastMatchupsRaw.and.returnValue(of(matchups('2025', [
      { week: 1, stage: 'regular-season', state: 'final' },
      { week: 2, stage: 'playoffs', state: 'final' }
    ])));
    dataService.getPastWeeklyRecapsRaw.and.returnValue(of(recaps('2025', [1])));
    dataService.getFantasyGameContext.and.returnValue(throwError(() => new Error('missing')));
    dataService.getFantasyGameContextHistory.and.returnValue(throwError(() => new Error('missing')));
    dataService.getPastFantasyGameContextRaw.and.returnValue(throwError(() => new Error('missing')));
  });

  it('opens the last completed week of the current season with scores and a recap', async () => {
    const host = await create();

    expect(host.querySelector('.week-title')?.textContent).toContain('Week 2');
    expect(host.querySelectorAll('.week-chip').length).toBe(3);
    expect(host.querySelector('.week-chip--active')?.textContent?.trim()).toBe('2');
    expect(host.querySelector('.week-matchup-score')?.textContent?.trim()).toBe('102');
    expect(host.querySelector('.weekly-recap-shell')).not.toBeNull();
    expect(dataService.getMatchups).toHaveBeenCalled();
  });

  it('shows a visible fallback instead of a name when a recap player no longer resolves', async () => {
    const host = await create();

    expect(host.querySelector('.weekly-recap-player-copy strong')?.textContent).toContain('Player missing-player');
    expect((host.querySelector('.weekly-recap-player') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows the pending hint instead of a recap for an open week', async () => {
    const host = await create();

    (Array.from(host.querySelectorAll('.week-chip')).find(chip => chip.textContent?.trim() === '3') as HTMLElement).click();
    fixture.detectChanges();

    expect(host.querySelector('.week-recap .weekly-recap-empty')?.textContent)
      .toContain('Recap available after the week is final.');
    expect(host.querySelector('.week-matchup-state--open')).not.toBeNull();
  });

  it('shows a missing-recap message for a final week without recap data', async () => {
    dataService.getWeeklyRecaps.and.returnValue(of(recaps('2026', [1])));
    const host = await create();

    expect(host.querySelector('.week-recap .weekly-recap-empty')?.textContent)
      .toContain('No recap is available for this week.');
  });

  it('loads a requested archived season and week and marks its playoff weeks', async () => {
    const host = await create({ season: '2025', week: '1' });

    expect(dataService.getPastMatchupsRaw).toHaveBeenCalledWith('data/past_seasons/Matchups/Matchups_2025.json');
    expect(dataService.getPastWeeklyRecapsRaw).toHaveBeenCalledWith('data/past_seasons/WeeklyRecaps/WeeklyRecaps_2025.json');
    expect(host.querySelector('.week-title')?.textContent).toContain('Week 1');
    expect(host.querySelectorAll('.week-chip--playoff').length).toBe(1);
  });

  it('falls back to the current season for an unknown requested season', async () => {
    await create({ season: '1999' });

    expect(dataService.getMatchups).toHaveBeenCalled();
    expect(dataService.getPastMatchupsRaw).not.toHaveBeenCalled();
  });

  it('keeps the page usable when recap or matchup files fail to load', async () => {
    dataService.getWeeklyRecaps.and.returnValue(throwError(() => new Error('missing')));
    const host = await create();

    expect(host.querySelector('.week-matchup')).not.toBeNull();
    expect(host.querySelector('.week-recap .weekly-recap-empty')?.textContent)
      .toContain('No recap is available for this week.');

    dataService.getMatchups.and.returnValue(throwError(() => new Error('missing')));
    fixture = TestBed.createComponent(WeeksPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No matchup data is available for 2026.');
  });

  it('keeps the compact matchup row inert while no matchup detail is available', async () => {
    const host = await create();

    const row = host.querySelector('.week-matchup') as HTMLButtonElement;
    expect(row.disabled).toBeTrue();
    expect(host.querySelector('.week-matchup-chevron')).toBeNull();
  });

  it('enables the matchup detail for a finished week of the running season from the history file', async () => {
    const context = (week: number) => ({
      Season: '2026',
      Week: week,
      FantasyMatchups: [{ FantasyMatchupID: `2026-${week}` }]
    }) as unknown as FantasyGameContextReadModel;
    dataService.getFantasyGameContext.and.returnValue(of(context(3)));
    dataService.getFantasyGameContextHistory.and.returnValue(of({ Weeks: [context(2)] } as unknown as HistoricalFantasyGameContextSeason));
    const host = await create();

    // Default week is the last settled week (2), which only the history file covers.
    expect((host.querySelector('.week-matchup') as HTMLButtonElement).disabled).toBeFalse();
    // One tap target: the team identities inside the row are not separate buttons.
    expect(host.querySelectorAll('.week-matchup app-team-identity button').length).toBe(0);
    expect(host.querySelector('.week-matchup-chevron')).not.toBeNull();
  });

  it('shows the season grid with a playoff group and opens a week from its header', async () => {
    const host = await create({ season: '2025' });

    (Array.from(host.querySelectorAll('.activity-tab')).find(tab => tab.textContent?.trim() === 'Season') as HTMLElement).click();
    fixture.detectChanges();

    // Teams are columns, weeks are rows: two weeks plus the playoff divider row.
    expect(host.querySelectorAll('.season-grid tbody tr').length).toBe(3);
    expect(host.querySelectorAll('.season-grid-team-head').length).toBe(2);
    expect(host.querySelector('.season-grid-divider')?.textContent).toContain('Playoffs');
    expect(host.querySelectorAll('.season-grid-cell--high').length).toBeGreaterThan(0);

    (host.querySelectorAll('.season-grid-week-button')[1] as HTMLElement).click();
    fixture.detectChanges();

    expect(host.querySelector('.week-title')?.textContent).toContain('Week 2');
  });
  it('shows an Upset card in the recap when the generator marked an underdog win', async () => {
    const marked = recaps('2026', [1, 2]);
    marked.Weeks[1].WinProbabilities = [{
      FantasyMatchupID: '2026-2',
      Teams: [{ FantasyTeamID: 1, PregameWinProbability: 28 }, { FantasyTeamID: 2, PregameWinProbability: 72 }],
      Upset: true,
      UpsetWinnerFantasyTeamID: 1,
      UpsetLevel: 'upset',
      UnderdogWinnerFantasyTeamID: 1
    }];
    dataService.getWeeklyRecaps.and.returnValue(of(marked));
    const host = await create();

    expect(host.querySelector('.weekly-recap-upset')?.textContent).toContain('Upset');
    expect(host.querySelector('.weekly-recap-upset')?.textContent).toContain('28');
  });

  it('does not show pregame chances or upsets in the week list and the season grid', async () => {
    const withChance = recaps('2026', [1, 2]);
    withChance.Weeks[1].WinProbabilities = [{
      FantasyMatchupID: '2026-2',
      Teams: [{ FantasyTeamID: 1, PregameWinProbability: 28 }, { FantasyTeamID: 2, PregameWinProbability: 72 }],
      Upset: true,
      UpsetWinnerFantasyTeamID: 1
    }];
    withChance.UpsetCounts = [{ FantasyTeamID: 1, Upsets: 1, Weeks: 1 }, { FantasyTeamID: 2, Upsets: 0, Weeks: 1 }];
    dataService.getWeeklyRecaps.and.returnValue(of(withChance));
    const host = await create();

    expect(host.querySelector('app-win-chance-bar')).toBeNull();
    expect(host.textContent).not.toContain('Upset');

    (Array.from(host.querySelectorAll('.activity-tab')).find(tab => tab.textContent?.trim() === 'Season') as HTMLElement).click();
    fixture.detectChanges();
    expect(host.querySelector('.season-grid tfoot')).toBeNull();
  });
});
