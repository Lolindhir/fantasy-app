import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { FantasyTeam } from '../../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../../../core/models/weekly-recap.models';
import { DataService, type LeagueWithPlayers } from '../../../../core/services/data.service';
import type { PastSeasonsIndex } from '../../../../core/services/data-api.service';
import { WeeklyTabComponent } from './weekly-tab';

function team(id: number): FantasyTeam {
  return { TeamID: id, Team: `Team ${id}`, TeamAbbr: `T${id}`, Owner: `Owner ${id}`, Avatar: '', OwnerAvatar: '', Roster: [] } as unknown as FantasyTeam;
}

function matchups(season: string, weeks: Array<{ week: number; stage: 'regular-season' | 'playoffs' }>): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: season,
    Summary: { LastCompletedWeek: null, ActiveOrNextWeek: null },
    Weeks: weeks.map(({ week, stage }) => ({
      Week: week,
      Stage: stage,
      FirstKickoffUtc: null,
      CompletionState: 'final' as const,
      Matchups: [{
        FantasyMatchupID: `${season}-${week}`,
        CompletionState: 'final' as const,
        Participants: [
          { TeamID: 1, Points: 100 + week, ScoreKind: 'standard' as const },
          { TeamID: 2, Points: 90, ScoreKind: 'standard' as const }
        ],
        Result: { Type: 'win' as const, WinnerTeamID: 1 }
      }]
    }))
  };
}

const index = {
  GeneratedAt: null,
  Seasons: [{
    Season: '2025',
    Resources: { Matchups: { Path: 'data/past_seasons/Matchups/Matchups_2025.json', Exists: true } }
  }]
} as unknown as PastSeasonsIndex;

describe('WeeklyTabComponent', () => {
  async function create(query: Record<string, string> = {}): Promise<HTMLElement> {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayers', 'getPastSeasonsIndex', 'getMatchups', 'getWeeklyRecaps', 'getPastMatchupsRaw', 'getPastWeeklyRecapsRaw'
    ]);
    dataService.getLeagueWithPlayers.and.returnValue(of({ league: { Season: '2026' }, teams: [team(1), team(2)] } as unknown as LeagueWithPlayers));
    dataService.getPastSeasonsIndex.and.returnValue(of(index));
    dataService.getMatchups.and.returnValue(of(matchups('2026', [{ week: 1, stage: 'regular-season' }])));
    dataService.getWeeklyRecaps.and.returnValue(of({ SchemaVersion: 1, Season: '2026', Weeks: [] } as unknown as WeeklyRecapsReadModel));
    dataService.getPastMatchupsRaw.and.returnValue(of(matchups('2025', [
      { week: 1, stage: 'regular-season' },
      { week: 2, stage: 'playoffs' }
    ])));
    dataService.getPastWeeklyRecapsRaw.and.returnValue(of({ SchemaVersion: 1, Season: '2025', Weeks: [] } as unknown as WeeklyRecapsReadModel));

    await TestBed.configureTestingModule({
      imports: [WeeklyTabComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(WeeklyTabComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('shows the grid of the requested season with a playoff divider and no efficiency toggle without values', async () => {
    const host = await create({ season: '2025' });

    expect(host.querySelectorAll('.season-grid tbody tr').length).toBe(3);
    expect(host.querySelectorAll('.season-grid-team-head').length).toBe(2);
    expect(host.querySelector('.season-grid-divider')?.textContent).toContain('Playoffs');
    expect(host.querySelectorAll('.season-grid-cell--high').length).toBeGreaterThan(0);
    expect(host.querySelector('.weekly-modes')).toBeNull();
  });

  it('links each week number to the Week view of the Schedule', async () => {
    const host = await create({ season: '2025' });

    const link = host.querySelectorAll('.season-grid-week-button')[1] as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('/schedule');
    expect(link.getAttribute('href')).toContain('week=2');
    expect(link.getAttribute('href')).toContain('season=2025');
  });
});
