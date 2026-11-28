import { TestBed } from '@angular/core/testing';
import { defer, of, Subject, throwError } from 'rxjs';

import type { RawDraft } from '../../core/models/draft.models';
import type { PastSeasonsIndex } from '../../core/services/data-api.service';
import { DataService, type LeagueWithPlayers } from '../../core/services/data.service';
import { TeamSeasonService } from '../../shared/services/team-season.service';
import { DraftsPageComponent } from './drafts-page';
import { DraftsViewModelService } from './services/drafts-view-model.service';

describe('DraftsPageComponent archive loading', () => {
  const path = (season: string) => 'data/past_seasons/Drafts/Drafts_' + season + '.json';
  const draft = (season: string) => ({
    DraftKey: season + '-1', Season: season, DraftNo: 1, Picks: [], Status: 'Completed'
  } as RawDraft);
  const index: PastSeasonsIndex = {
    GeneratedAt: null,
    Seasons: ['2024', '2025', '2026', '2027'].map(Season => ({
      Season, Resources: { Drafts: { Exists: true, Path: path(Season) } }
    }))
  };
  const context = {
    league: { Season: '2026' }, drafts: [draft('2026'), draft('2027')],
    players: [], teams: [], nflTeams: []
  } as unknown as LeagueWithPlayers;

  function create() {
    let bundleSubscriptions = 0;
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayers', 'getPastSeasonsIndex', 'getPastDraftsRaw'
    ]);
    dataService.getLeagueWithPlayers.and.returnValue(defer(() => {
      bundleSubscriptions++;
      return of(context);
    }));
    dataService.getPastSeasonsIndex.and.returnValue(of(index));
    dataService.getPastDraftsRaw.and.callFake(source => of([draft(source.includes('2025') ? '2025' : '2024')]));
    const teamSeasons = jasmine.createSpyObj<TeamSeasonService>('TeamSeasonService', ['getLookup']);
    // Optional historical identity failure must not block published drafts.
    teamSeasons.getLookup.and.returnValue(throwError(() => new Error('identity unavailable')));
    TestBed.configureTestingModule({
      providers: [
        DraftsViewModelService,
        { provide: DataService, useValue: dataService },
        { provide: TeamSeasonService, useValue: teamSeasons }
      ]
    });
    const component = TestBed.runInInjectionContext(() => new DraftsPageComponent());
    return { component, dataService, teamSeasons, bundleSubscriptions: () => bundleSubscriptions };
  }

  it('renders current and future without any archive dependency, then loads only the selected past season', () => {
    const { component, dataService, teamSeasons, bundleSubscriptions } = create();
    const seen: Array<{ season: string | null; loading: boolean; drafts: string[] }> = [];
    const subscription = component.vm$.subscribe(vm => {
      expect(vm.currentSeasonDrafts.map(d => d.draft.Season)).toEqual(['2026']);
      expect(vm.futureDrafts.map(d => d.draft.Season)).toEqual(['2027']);
      seen.push({ season: vm.selectedPastSeason, loading: vm.pastLoading, drafts: vm.pastDrafts.map(d => d.draft.Season) });
    });
    component.selectTab('future');
    expect(dataService.getPastSeasonsIndex).not.toHaveBeenCalled();
    expect(dataService.getPastDraftsRaw).not.toHaveBeenCalled();
    expect(teamSeasons.getLookup).not.toHaveBeenCalled();

    component.selectTab('past');
    expect(dataService.getPastSeasonsIndex).toHaveBeenCalledTimes(1);
    expect(dataService.getPastDraftsRaw).toHaveBeenCalledOnceWith(path('2025'));
    expect(seen[seen.length - 1]).toEqual({ season: '2025', loading: false, drafts: ['2025'] });
    component.selectPastSeason('2024');
    expect(seen[seen.length - 1]).toEqual({ season: '2024', loading: false, drafts: ['2024'] });
    component.selectTab('current');
    component.selectTab('past');
    expect(dataService.getPastDraftsRaw.calls.allArgs()).toEqual([[path('2025')], [path('2024')], [path('2024')]]);
    expect(seen[seen.length - 1]).toEqual({ season: '2024', loading: false, drafts: ['2024'] });
    expect(bundleSubscriptions()).toBe(1);
    subscription.unsubscribe();
  });

  it('cancels stale season reads and pending archive work when leaving Past', () => {
    const { component, dataService } = create();
    const pending2025 = new Subject<RawDraft[]>();
    const pending2024 = new Subject<RawDraft[]>();
    dataService.getPastDraftsRaw.and.callFake(source => source === path('2025') ? pending2025 : pending2024);
    const seen: Array<[string | null, boolean, string[]]> = [];
    const subscription = component.vm$.subscribe(vm =>
      seen.push([vm.selectedPastSeason, vm.pastLoading, vm.pastDrafts.map(d => d.draft.Season)]));
    component.selectTab('past');
    expect(seen[seen.length - 1]).toEqual(['2025', true, []]);
    component.selectPastSeason('2024');
    expect(seen[seen.length - 1]).toEqual(['2024', true, []]);
    pending2025.next([draft('2025')]);
    expect(seen[seen.length - 1]).toEqual(['2024', true, []]);
    component.selectTab('future');
    pending2024.next([draft('2024')]);
    expect(seen[seen.length - 1]).toEqual([null, false, []]);
    subscription.unsubscribe();
  });

  it('keeps archive failures local and falls back to a valid season without showing stale drafts', () => {
    const { component, dataService } = create();
    dataService.getPastDraftsRaw.and.returnValue(throwError(() => new Error('archive unavailable')));
    const seen: Array<[string | null, boolean, number]> = [];
    const subscription = component.vm$.subscribe(vm => {
      expect(vm.currentSeasonDrafts.length).toBe(1);
      seen.push([vm.selectedPastSeason, vm.pastLoading, vm.pastDrafts.length]);
    });
    component.selectPastSeason('1999');
    component.selectTab('past');
    expect(seen[seen.length - 1]).toEqual(['2025', false, 0]);
    dataService.getPastDraftsRaw.and.returnValue(of([draft('2024')]));
    component.selectPastSeason('2024');
    expect(seen[seen.length - 1]).toEqual(['2024', false, 1]);
    subscription.unsubscribe();
  });
});
