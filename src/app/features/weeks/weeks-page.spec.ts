import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';

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

  async function create(query: Record<string, string> = {}, view: 'week' | 'overview' = 'week'): Promise<HTMLElement> {
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
    const host = fixture.nativeElement as HTMLElement;
    if (view === 'week') {
      const weekTab = Array.from(host.querySelectorAll('.activity-tab'))
        .find(tab => tab.textContent?.trim() === 'Week') as HTMLElement | undefined;
      weekTab?.click();
      fixture.detectChanges();
    }
    return host;
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
      'getFantasyGameContextBase',
      'getFantasyGameContextWithProjections',
      'getPastFantasyGameContextRaw',
      'getFantasyGameContextHistory',
      'getTeamSeasons'
    ]);
    dataService.getTeamSeasons.and.returnValue(of({
      SchemaVersion: 1, Product: 'league-teams', CanonicalLeagueID: 'test', CurrentSeason: '2026', Seasons: []
    }));
    dataService.getLeagueWithPlayers.and.returnValue(of({
      league: { Season: '2026' },
      teams: [team(1), team(2)],
      nflTeams: []
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
    dataService.getFantasyGameContextBase.and.returnValue(throwError(() => new Error('missing')));
    dataService.getFantasyGameContextWithProjections.and.callFake(context => of(context));
    dataService.getFantasyGameContextHistory.and.returnValue(throwError(() => new Error('missing')));
    dataService.getPastFantasyGameContextRaw.and.returnValue(throwError(() => new Error('missing')));
  });


  it('starts on the league schedule overview and shows every future week in order', async () => {
    dataService.getMatchups.and.returnValue(of(matchups('2026', [
      { week: 1, stage: 'regular-season', state: 'final' },
      { week: 2, stage: 'regular-season', state: 'final' },
      { week: 3, stage: 'regular-season', state: 'open' },
      { week: 4, stage: 'regular-season', state: 'open' }
    ])));
    const host = await create({}, 'overview');

    expect(host.querySelectorAll('.schedule-upcoming .schedule-week').length).toBe(2);
    expect(Array.from(host.querySelectorAll('.schedule-upcoming .schedule-week-link'))
      .map(node => node.textContent?.trim())).toEqual(['Week 3', 'Week 4']);
    expect(host.querySelectorAll('.schedule-upcoming .week-matchup').length).toBe(2);
    expect(host.querySelector('.week-title')).toBeNull();
    expect(host.querySelector('.schedule-played')).toBeNull();

    (host.querySelector('.schedule-played-toggle') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(host.querySelectorAll('.schedule-played .schedule-week').length).toBe(2);
    expect(Array.from(host.querySelectorAll('.schedule-played .schedule-week-link'))
      .map(node => node.textContent?.trim())).toEqual(['Week 2', 'Week 1']);
    expect(host.querySelector('.schedule-played .week-matchup-side:not(.week-matchup-side--right) .week-matchup-score')?.textContent).toContain('102');
  });

  it('reuses the Week card renderer as separate cards in the Overview, including open state', async () => {
    const host = await create({}, 'overview');
    const row = host.querySelector('.schedule-upcoming .week-matchup') as HTMLButtonElement;
    expect(row).not.toBeNull();
    expect(row.classList.contains('week-matchup--schedule')).toBeTrue();
    expect(row.querySelectorAll('app-team-identity').length).toBe(4); // desktop/mobile identities
    expect(row.querySelector('.week-matchup-state--open')?.textContent).toContain('Open');
    expect(row.querySelector('.week-matchup-score')?.textContent?.trim()).toBe('–');
    expect(host.querySelectorAll('.schedule-upcoming .schedule-scoreboards > .week-matchup').length).toBe(1);
    expect(host.querySelector('.schedule-upcoming .schedule-scoreboards')).not.toBeNull();
  });

  it('preserves final scores in played rows and detailed Week cards', async () => {
    const host = await create({}, 'overview');
    (host.querySelector('.schedule-played-toggle') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(host.querySelector('.schedule-played .week-matchup-side:not(.week-matchup-side--right) .week-matchup-score')?.textContent).toContain('102');
    expect(host.querySelector('.schedule-played .week-matchup-side--right .week-matchup-score')?.textContent).toContain('90');

    (Array.from(host.querySelectorAll('.activity-tab')).find(tab => tab.textContent?.trim() === 'Week') as HTMLElement).click();
    fixture.detectChanges();
    expect(host.querySelector('.week-matchup')).not.toBeNull();
    expect(host.querySelector('.week-matchup-score')?.textContent).toContain('102');
  });


  it('shows the team identity of the selected past season, not the current one', async () => {
    const season = matchups('2025', [{ week: 1, stage: 'regular-season', state: 'final' }]);
    season.Weeks[0].Matchups[0].Result = { Type: 'win', WinnerTeamID: 1 };
    dataService.getPastMatchupsRaw.and.returnValue(of(season));
    dataService.getTeamSeasons.and.returnValue(of({
      SchemaVersion: 1, Product: 'league-teams', CanonicalLeagueID: 'test', CurrentSeason: '2026',
      Seasons: [{ Season: '2025', Teams: [{
        TeamID: 1, CanonicalLeagueRosterID: 'r1', CanonicalLeagueMemberID: 'm1', OwnerID: 'u1', Owner: 'Old Owner', OwnerAvatar: null,
        TeamName: 'Old Name', TeamNameSource: 'provider', TeamAbbr: 'OLD', TeamAvatar: null
      }] }]
    }));

    const host = await create({ season: '2025' }, 'overview');
    const row = host.querySelector('.schedule-played .week-matchup') as HTMLButtonElement;
    expect(row.getAttribute('aria-label')).toContain('winner OLD');
    expect(row.getAttribute('aria-label')).not.toContain('winner T1');
  });

  it('tints only the authoritative winner side and associates each score with its team', async () => {
    const season = matchups('2025', [
      { week: 1, stage: 'regular-season', state: 'final' },
      { week: 2, stage: 'regular-season', state: 'final' }
    ]);
    season.Weeks[0].Matchups[0].Result = { Type: 'win', WinnerTeamID: 2 };
    season.Weeks[1].Matchups[0].Result = { Type: 'win', WinnerTeamID: 1 };
    dataService.getPastMatchupsRaw.and.returnValue(of(season));

    const host = await create({ season: '2025' }, 'overview');
    const rows = Array.from(host.querySelectorAll('.schedule-played .week-matchup')) as HTMLButtonElement[];
    expect(rows.length).toBe(2);

    const leftWinner = rows[0]; // Week 2 (reverse chronological)
    expect(leftWinner.querySelector('.week-matchup-side:not(.week-matchup-side--right).week-matchup-side--winner')).not.toBeNull();
    expect(leftWinner.querySelector('.week-matchup-side--right.week-matchup-side--winner')).toBeNull();
    expect(leftWinner.querySelector('.week-matchup-side:not(.week-matchup-side--right) .week-matchup-score')?.textContent?.trim()).toBe('102');
    expect(leftWinner.querySelector('.week-matchup-side--right .week-matchup-score')?.textContent?.trim()).toBe('90');
    expect(leftWinner.getAttribute('aria-label')).toContain('winner T1');

    const rightWinner = rows[1]; // Week 1
    expect(rightWinner.querySelector('.week-matchup-side:not(.week-matchup-side--right).week-matchup-side--winner')).toBeNull();
    expect(rightWinner.querySelector('.week-matchup-side--right.week-matchup-side--winner')).not.toBeNull();
    expect(rightWinner.querySelector('.week-matchup-side--right .week-matchup-score')?.textContent?.trim()).toBe('90');
    expect(rightWinner.getAttribute('aria-label')).toContain('winner T2');
  });

  it('does not invent a winner for a final tie, unknown state or open live scores', async () => {
    const season = matchups('2026', [
      { week: 1, stage: 'regular-season', state: 'final' },
      { week: 2, stage: 'regular-season', state: 'open' },
      { week: 3, stage: 'regular-season', state: 'open' }
    ]);
    season.Weeks[0].Matchups[0].Result = { Type: 'tie', WinnerTeamID: null };
    season.Weeks[0].Matchups[0].Participants[1].Points = 101;
    season.Weeks[1].Matchups[0].Participants[0].Points = 23.5;
    season.Weeks[1].Matchups[0].Participants[1].Points = 14.2;
    season.Weeks[2].CompletionState = 'unknown';
    season.Weeks[2].Matchups[0].CompletionState = 'unknown';
    dataService.getMatchups.and.returnValue(of(season));

    const host = await create({}, 'overview');
    const upcoming = Array.from(host.querySelectorAll('.schedule-upcoming .week-matchup')) as HTMLButtonElement[];
    expect(upcoming.length).toBe(2);
    expect(upcoming[0].querySelector('.week-matchup-score')?.textContent?.trim()).toBe('23.5');
    expect(upcoming[0].querySelectorAll('.week-matchup-side--winner').length).toBe(0);
    expect(upcoming[1].querySelector('.week-matchup-state--unknown')?.textContent).toContain('Unconfirmed');
    expect(upcoming[1].querySelectorAll('.week-matchup-side--winner').length).toBe(0);

    (host.querySelector('.schedule-played-toggle') as HTMLButtonElement).click();
    fixture.detectChanges();
    const tie = host.querySelector('.schedule-played .week-matchup') as HTMLButtonElement;
    expect(tie.querySelectorAll('.week-matchup-side--winner').length).toBe(0);
    expect(tie.querySelectorAll('.week-matchup-score').length).toBe(2);
    expect(tie.getAttribute('aria-label')).toContain('tie');
  });

  it('opens the original Week detail from a schedule group header', async () => {
    const host = await create({}, 'overview');
    (host.querySelector('.schedule-upcoming .schedule-week-link') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(host.querySelector('.week-title')?.textContent).toContain('Week 3');
    expect(host.querySelector('.week-recap .weekly-recap-empty')).not.toBeNull();
  });

  it('shows verified playoff fixture labels above each card and in accessible names', async () => {
    const season = matchups('2025', [
      { week: 14, stage: 'playoffs', state: 'final' },
      { week: 15, stage: 'playoffs', state: 'final' },
      { week: 16, stage: 'playoffs', state: 'final' },
      { week: 17, stage: 'playoffs', state: 'final' }
    ]);
    for (const week of season.Weeks) {
      const fixture = week.Matchups[0];
      fixture.Bracket = 'championship';
      fixture.PlayoffRound = week.Week <= 15 ? 1 : 2;
      fixture.PlayoffRoundCount = 2;
      fixture.PlayoffPlacement = week.Week <= 15 ? null : 1;
      fixture.PlayoffRoundWeek = week.Week % 2 === 0 ? 1 : 2;
      fixture.PlayoffRoundWeeks = 2;
    }
    dataService.getPastMatchupsRaw.and.returnValue(of(season));
    const host = await create({ season: '2025' }, 'overview');
    const labels = Array.from(host.querySelectorAll('.schedule-played .week-matchup-playoff-label'))
      .map(node => node.textContent?.trim());
    expect(labels).toEqual(['Final · 2/2', 'Final · 1/2', 'Semifinal · 2/2', 'Semifinal · 1/2']);
    expect((host.querySelector('.schedule-played .week-matchup') as HTMLButtonElement).getAttribute('aria-label'))
      .toContain('Final · 2/2');
    expect(host.querySelectorAll('.schedule-played .week-matchup-side--winner').length).toBe(4);
    expect(host.querySelectorAll('.schedule-played .week-matchup--schedule').length).toBe(4);
    expect(host.querySelector('.schedule-played .week-matchup-playoff-label')?.parentElement?.classList.contains('week-matchup')).toBeTrue();

    (Array.from(host.querySelectorAll('.activity-tab')).find(tab => tab.textContent?.trim() === 'Week') as HTMLElement).click();
    fixture.detectChanges();
    const weekLabel = host.querySelector('.week-section .week-matchup-playoff-label')?.textContent?.trim();
    expect(weekLabel).toBe('Final · 2/2');
  });

  it('keeps Semifinal I and II stable across two legs in Overview and Week despite shuffled fixture order', async () => {
    const season = matchups('2025', [
      { week: 14, stage: 'playoffs', state: 'final' },
      { week: 15, stage: 'playoffs', state: 'final' }
    ]);
    for (const [index, week] of season.Weeks.entries()) {
      const first = week.Matchups[0];
      Object.assign(first, {
        Bracket: 'championship', PlayoffRound: 1, PlayoffRoundCount: 2, PlayoffPlacement: null,
        PlayoffRoundWeek: index + 1, PlayoffRoundWeeks: 2
      });
      const second = {
        ...first,
        FantasyMatchupID: `other-${week.Week}`,
        Participants: [
          { TeamID: 3, Points: 150, ScoreKind: 'standard' as const },
          { TeamID: 4, Points: 140, ScoreKind: 'standard' as const }
        ],
        Result: { Type: 'win' as const, WinnerTeamID: 3 }
      };
      week.Matchups = index === 0 ? [first, second] : [second, first];
    }
    dataService.getPastMatchupsRaw.and.returnValue(of(season));
    const host = await create({ season: '2025' }, 'overview');
    const weeks = Array.from(host.querySelectorAll('.schedule-played .schedule-week'));
    expect(weeks.map(node => Array.from(node.querySelectorAll('.week-matchup-playoff-label'))
      .map(label => label.textContent?.trim()))).toEqual([
      ['Semifinal II · 2/2', 'Semifinal I · 2/2'],
      ['Semifinal I · 1/2', 'Semifinal II · 1/2']
    ]);
    expect(weeks[0].querySelectorAll('.week-matchup').length).toBe(2);

    (weeks[0].querySelector('.schedule-week-link') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(Array.from(host.querySelectorAll('.week-section .week-matchup-playoff-label'))
      .map(node => node.textContent?.trim())).toEqual(['Semifinal II · 2/2', 'Semifinal I · 2/2']);
  });

  it('does not display an exact playoff label for legacy or unclassified evidence', async () => {
    const season = matchups('2025', [
      { week: 14, stage: 'playoffs', state: 'final' },
      { week: 15, stage: 'playoffs', state: 'final' }
    ]);
    season.Weeks[0].Matchups[0].Bracket = 'unclassified';
    season.Weeks[1].Matchups[0].Bracket = 'championship'; // legacy label without exact round facts
    dataService.getPastMatchupsRaw.and.returnValue(of(season));
    const host = await create({ season: '2025' }, 'overview');
    expect(host.querySelectorAll('.week-matchup-playoff-label').length).toBe(0);
    expect(host.querySelectorAll('.schedule-played .week-matchup').length).toBe(2);
  });

  it('shows all known archived weeks without hiding playoffs or inventing unavailable results', async () => {
    const host = await create({ season: '2025' }, 'overview');
    expect(host.querySelector('.schedule-upcoming')).toBeNull();
    expect(host.querySelector('.schedule-played-toggle')).toBeNull();
    expect(host.querySelectorAll('.schedule-played .schedule-week').length).toBe(2);
    expect(host.querySelector('.schedule-played .week-stage')?.textContent).toContain('Playoffs');
  });

  it('uses the old ?week= deep link to open the detailed Week tab', async () => {
    const host = await create({ week: '3' }, 'overview');
    expect(host.querySelector('.week-title')?.textContent).toContain('Week 3');
    expect(host.querySelector('.schedule-upcoming')).toBeNull();
  });

  it('opens schedule matchups only when that particular week has context', async () => {
    const context = (week: number) => ({
      Season: '2026', Week: week, FantasyMatchups: [{ FantasyMatchupID: `2026-${week}` }]
    }) as unknown as FantasyGameContextReadModel;
    dataService.getFantasyGameContextBase.and.returnValue(of(context(3)));
    dataService.getFantasyGameContextHistory.and.returnValue(of({ Weeks: [context(2)] } as unknown as HistoricalFantasyGameContextSeason));
    const host = await create({}, 'overview');

    expect((host.querySelector('.schedule-upcoming .week-matchup') as HTMLButtonElement).disabled).toBeFalse();
    expect(dataService.getFantasyGameContext).not.toHaveBeenCalled();
    expect(dataService.getFantasyGameContextWithProjections).not.toHaveBeenCalled();
    expect(dataService.getNflTeams).not.toHaveBeenCalled();
    (host.querySelector('.schedule-played-toggle') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect((host.querySelector('.schedule-played .week-matchup') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('enriches only the active context on explicit detail opening, without reloading membership', async () => {
    const active = { Season: '2026', Week: 3, FantasyMatchups: [{ FantasyMatchupID: '2026-3' }] } as unknown as FantasyGameContextReadModel;
    const finished = { Season: '2026', Week: 2, FantasyMatchups: [{ FantasyMatchupID: '2026-2' }] } as unknown as FantasyGameContextReadModel;
    dataService.getFantasyGameContextBase.and.returnValue(of(active));
    dataService.getFantasyGameContextHistory.and.returnValue(of({ Weeks: [finished] } as unknown as HistoricalFantasyGameContextSeason));
    const enriched = { ...active };
    dataService.getFantasyGameContextWithProjections.and.returnValue(of(enriched));
    await create({}, 'overview');
    const open = spyOn(fixture.debugElement.injector.get(MatDialog), 'open').and.stub();
    await fixture.componentInstance.openWeekMatchup(3, 'missing');
    expect(open).not.toHaveBeenCalled();
    await fixture.componentInstance.openWeekMatchup(2, '2026-2');
    expect(dataService.getFantasyGameContextWithProjections).not.toHaveBeenCalled();
    expect(open).toHaveBeenCalledTimes(1);
    expect(open.calls.mostRecent()?.args[1]?.data.context).toBe(finished);
    expect(fixture.componentInstance.matchupOpenError()).toBeFalse();
    await fixture.componentInstance.openWeekMatchup(3, '2026-3');
    expect(dataService.getFantasyGameContextWithProjections).toHaveBeenCalledOnceWith(active);
    expect(open).toHaveBeenCalledTimes(2);
    expect(open.calls.mostRecent()?.args[1]?.data.context).toBe(enriched);
    expect(fixture.componentInstance.matchupOpenError()).toBeFalse();
    expect(dataService.getFantasyGameContextBase).toHaveBeenCalledTimes(1);
  });

  it('does not open a stale active matchup after changing seasons during projection loading', async () => {
    const active = { Season: '2026', Week: 3, FantasyMatchups: [{ FantasyMatchupID: '2026-3' }] } as unknown as FantasyGameContextReadModel;
    dataService.getFantasyGameContextBase.and.returnValue(of(active));
    const pending = new Subject<FantasyGameContextReadModel>();
    dataService.getFantasyGameContextWithProjections.and.returnValue(pending);
    await create({}, 'overview');
    const open = spyOn(fixture.debugElement.injector.get(MatDialog), 'open').and.stub();
    const component = fixture.componentInstance;
    const request = component.openWeekMatchup(3, '2026-3');
    await component.openWeekMatchup(3, '2026-3');
    expect(dataService.getFantasyGameContextWithProjections).toHaveBeenCalledTimes(1);
    component.selectSeason('2025');
    fixture.detectChanges();
    await fixture.whenStable();
    pending.next(active);
    pending.complete();
    await request;
    expect(open).not.toHaveBeenCalled();
    expect(component.openingMatchup()).toBeNull();
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
    dataService.getFantasyGameContextBase.and.returnValue(of(context(3)));
    dataService.getFantasyGameContextHistory.and.returnValue(of({ Weeks: [context(2)] } as unknown as HistoricalFantasyGameContextSeason));
    const host = await create();

    // Default week is the last settled week (2), which only the history file covers.
    expect((host.querySelector('.week-matchup') as HTMLButtonElement).disabled).toBeFalse();
    // One tap target: the team identities inside the row are not separate buttons.
    expect(host.querySelectorAll('.week-matchup app-team-identity button').length).toBe(0);
    expect(host.querySelector('.week-matchup-chevron')).not.toBeNull();
  });

  it('does not offer a Season tab or the season grid anymore', async () => {
    const host = await create({ season: '2025' }, 'overview');

    const labels = Array.from(host.querySelectorAll('.activity-tab')).map(tab => tab.textContent?.trim());
    expect(labels).toEqual(['Overview', 'Week']);
    expect(host.querySelector('.season-grid')).toBeNull();
  });

  it('shows the biggest underdog win in the recap when the generator marked an underdog win', async () => {
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

    expect(host.querySelector('.weekly-recap-underdog')?.textContent).toContain('Biggest Underdog Win');
    expect(host.querySelector('.weekly-recap-underdog')?.textContent).toContain('Upset');
    expect(host.querySelector('.weekly-recap-underdog')?.textContent).toContain('28');
  });

  it('does not show pregame chances or upsets in the week list', async () => {
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
  });
});
