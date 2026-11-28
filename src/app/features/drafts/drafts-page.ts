import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, defer, of } from 'rxjs';
import { catchError, distinctUntilChanged, map, shareReplay, startWith, switchMap } from 'rxjs/operators';
import { DataService } from '../../core/services/data.service';
import type { PastSeasonIndexEntry } from '../../core/services/data-api.service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { TeamSeasonService, teamsWithSeasonIdentity } from '../../shared/services/team-season.service';
import { DraftsViewModelService } from './services/drafts-view-model.service';
import type { DraftViewModel } from './models/drafts-view.models';
import { CurrentDraftsTabComponent } from './tabs/current-drafts/current-drafts-tab';
import { FutureDraftsTabComponent } from './tabs/future-drafts/future-drafts-tab';


type DraftsTab = 'current' | 'future' | 'past';

interface PastDraftsState {
  pastSeasons: PastSeasonIndexEntry[];
  selectedPastSeason: string | null;
  pastDrafts: DraftViewModel[];
  pastLoading: boolean;
}

const EMPTY_PAST: PastDraftsState = {
  pastSeasons: [], selectedPastSeason: null, pastDrafts: [], pastLoading: false
};

@Component({
  selector: 'app-drafts-page',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports,
    CurrentDraftsTabComponent,
    FutureDraftsTabComponent
  ],
  templateUrl: './drafts-page.html',
  styleUrl: './drafts.scss'
})
export class DraftsPageComponent {
  private dataService = inject(DataService);
  private draftsViewModelService = inject(DraftsViewModelService);
  private teamSeasons = inject(TeamSeasonService);
  private readonly selectedPastSeasonSubject = new BehaviorSubject<string | null>(null);
  private readonly activeTabSubject = new BehaviorSubject<DraftsTab>('current');

  get activeTab(): DraftsTab {
    return this.activeTabSubject.value;
  }

  private readonly leagueData$ = this.dataService.getLeagueWithPlayers().pipe(
    shareReplay(1)
  );

  // The index and historical identities are not prerequisites for Current or Future.
  private readonly pastSeasons$ = combineLatest([
    defer(() => this.dataService.getPastSeasonsIndex()),
    this.leagueData$
  ]).pipe(
    map(([index, leagueData]) => this.getPastDraftSeasons(index.Seasons ?? [], leagueData.league.Season)),
    catchError(() => of([] as PastSeasonIndexEntry[])),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly pastDrafts$ = combineLatest([
    this.leagueData$,
    this.pastSeasons$,
    this.selectedPastSeasonSubject.pipe(distinctUntilChanged()),
    defer(() => this.teamSeasons.getLookup()).pipe(catchError(() => of(null)))
  ]).pipe(
    switchMap(([leagueData, pastSeasons, selectedSeason, teamSeasonLookup]) => {
      const selectedEntry = pastSeasons.find(entry => entry.Season === selectedSeason) ?? pastSeasons[0];
      const season = selectedEntry?.Season ?? null;
      const selection = { pastSeasons, selectedPastSeason: season };
      const draftsPath = selectedEntry?.Resources?.Drafts?.Path;
      if (!draftsPath || selectedEntry?.Resources?.Drafts?.Exists !== true) {
        return of({ ...selection, pastDrafts: [], pastLoading: false } satisfies PastDraftsState);
      }

      return this.dataService.getPastDraftsRaw(draftsPath).pipe(
        // Historical identity and PlayerRef precedence remain owned by the existing mapper.
        map(drafts => this.draftsViewModelService.createDraftViewModels(
          drafts, teamsWithSeasonIdentity(leagueData.teams, teamSeasonLookup, season), leagueData.players)),
        catchError(() => of([] as DraftViewModel[])),
        map(pastDrafts => ({ ...selection, pastDrafts, pastLoading: false })),
        startWith({ ...selection, pastDrafts: [], pastLoading: true })
      );
    }),
    startWith({ ...EMPTY_PAST, pastLoading: true })
  );

  private readonly currentDrafts$ = this.leagueData$.pipe(
    map(leagueData => this.draftsViewModelService.createDraftsViewModel(
      leagueData.league, leagueData.drafts, leagueData.teams, leagueData.players))
  );

  // A single subscription owns the current tab. Leaving Past cancels any in-flight archive read.
  readonly vm$ = combineLatest([
    this.currentDrafts$,
    this.activeTabSubject.pipe(
      distinctUntilChanged(),
      switchMap(tab => tab === 'past' ? this.pastDrafts$ : of(EMPTY_PAST))
    )
  ]).pipe(map(([draftVm, past]) => ({ ...draftVm, ...past })));

  selectTab(tab: DraftsTab): void {
    this.activeTabSubject.next(tab);
  }

  selectPastSeason(season: string): void {
    this.selectedPastSeasonSubject.next(season);
  }

  private getPastDraftSeasons(
    seasons: PastSeasonIndexEntry[],
    currentSeason: string
  ): PastSeasonIndexEntry[] {
    return seasons
      .filter(entry =>
        entry.Resources?.Drafts?.Exists === true
        && !!entry.Resources?.Drafts?.Path
        && Number(entry.Season) < Number(currentSeason)
      )
      .sort((a, b) => Number(b.Season) - Number(a.Season));
  }
}
