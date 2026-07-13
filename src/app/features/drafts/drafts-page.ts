import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, of } from 'rxjs';
import { catchError, map, shareReplay, switchMap, tap } from 'rxjs/operators';
import { DataService } from '../../core/services/data.service';
import type { PastSeasonIndexEntry } from '../../core/services/data-api.service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { DraftsViewModelService } from './services/drafts-view-model.service';
import { CurrentDraftsTabComponent } from './tabs/current-drafts/current-drafts-tab';
import { FutureDraftsTabComponent } from './tabs/future-drafts/future-drafts-tab';


type DraftsTab = 'current' | 'future' | 'past';

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
  private selectedPastSeasonSubject = new BehaviorSubject<string | null>(null);

  activeTab: DraftsTab = 'current';

  private leagueData$ = this.dataService.getLeagueWithPlayers().pipe(
    shareReplay(1)
  );

  private pastSeasons$ = combineLatest([
    this.dataService.getPastSeasonsIndex(),
    this.leagueData$
  ]).pipe(
    map(([index, leagueData]) => this.getPastDraftSeasons(index.Seasons ?? [], leagueData.league.Season)),
    tap(seasons => {
      const selectedSeason = this.selectedPastSeasonSubject.value;
      const fallbackSeason = seasons[0]?.Season ?? null;
      const selectionIsAvailable = !!selectedSeason && seasons.some(entry => entry.Season === selectedSeason);

      if (!selectionIsAvailable && selectedSeason !== fallbackSeason) {
        this.selectedPastSeasonSubject.next(fallbackSeason);
      }
    }),
    catchError(() => of([] as PastSeasonIndexEntry[])),
    shareReplay(1)
  );

  private pastDrafts$ = combineLatest([
    this.leagueData$,
    this.pastSeasons$,
    this.selectedPastSeasonSubject
  ]).pipe(
    switchMap(([leagueData, pastSeasons, selectedSeason]) => {
      const season = selectedSeason ?? pastSeasons[0]?.Season ?? null;
      const selectedEntry = season ? pastSeasons.find(entry => entry.Season === season) : undefined;
      const draftsPath = selectedEntry?.Resources?.Drafts?.Path;
      const draftsExist = selectedEntry?.Resources?.Drafts?.Exists === true;

      if (!draftsPath || !draftsExist) {
        return of([]);
      }

      return this.dataService.getPastDraftsRaw(draftsPath).pipe(
        map(drafts => this.draftsViewModelService.createDraftViewModels(drafts, leagueData.teams, leagueData.players)),
        catchError(() => of([]))
      );
    }),
    shareReplay(1)
  );

  vm$ = combineLatest([
    this.leagueData$,
    this.pastSeasons$,
    this.selectedPastSeasonSubject,
    this.pastDrafts$
  ]).pipe(
    map(([leagueData, pastSeasons, selectedSeason, pastDrafts]) => {
      const draftVm = this.draftsViewModelService.createDraftsViewModel(
        leagueData.league,
        leagueData.drafts,
        leagueData.teams,
        leagueData.players
      );
      const resolvedPastSeason = selectedSeason ?? pastSeasons[0]?.Season ?? null;

      return {
        currentSeason: draftVm.currentSeason,
        currentSeasonDrafts: draftVm.currentSeasonDrafts,
        futureDrafts: draftVm.futureDrafts,
        draftCount: draftVm.draftCount,
        tradedPickCount: draftVm.tradedPickCount,
        pickCount: draftVm.pickCount,
        pickedCount: draftVm.pickedCount,
        pastSeasons,
        selectedPastSeason: resolvedPastSeason,
        pastDrafts
      };
    })
  );

  selectTab(tab: DraftsTab): void {
    this.activeTab = tab;
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
