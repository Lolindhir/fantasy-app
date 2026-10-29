import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, forkJoin, of } from 'rxjs';
import { catchError, map, shareReplay, switchMap, tap } from 'rxjs/operators';

import { DataService } from '../../core/services/data.service';
import type { RawDraft } from '../../core/models/draft.models';
import type {
  PastSeasonIndexEntry,
  PastSeasonsIndex
} from '../../core/services/data-api.service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { TransactionCardComponent } from '../../shared/components/transaction-card/transaction-card';
import { buildMovesViewModel, getMoveCategory, type MovesFilter } from './moves-view-model.util';

const ALL_SEASONS_ID = 'all';

interface MovesSeasonOption {
  Id: string;
  Label: string;
  TransactionPath: string | null;
}

interface MovesSelectionContext {
  SeasonOptions: MovesSeasonOption[];
  SelectedSeason: string;
  SeasonLabel: string;
  IncludeCurrent: boolean;
  HistoricalPaths: string[];
  HistoricalDraftPaths: string[];
}

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    CommonModule,
    TransactionCardComponent,
    SharedMaterialImports
  ],
  templateUrl: './league-activity.html',
  styleUrls: [
    './league-activity.scss',
    './league-activity-hero.scss',
    './league-activity-trades.scss'
  ]
})
export class LeagueActivityComponent {
  private readonly dataService = inject(DataService);
  private readonly selectedFilter$ = new BehaviorSubject<MovesFilter>('all');
  private readonly selectedSeason$ = new BehaviorSubject<string | null>(null);

  loadFailed = false;
  selectedFilter: MovesFilter = 'all';

  readonly moveCategory = getMoveCategory;

  private readonly leagueData$ = this.dataService.getLeagueWithPlayers().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly pastSeasonsIndex$ = this.dataService.getPastSeasonsIndex().pipe(
    catchError(() => of({ GeneratedAt: null, Seasons: [] } as PastSeasonsIndex)),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly historicalSeasons$ = combineLatest([
    this.leagueData$,
    this.pastSeasonsIndex$
  ]).pipe(
    map(([leagueData, index]) => this.getHistoricalTransactionSeasons(
      index.Seasons ?? [],
      leagueData.league.Season
    )),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly selectionContext$ = combineLatest([
    this.leagueData$,
    this.historicalSeasons$,
    this.selectedSeason$
  ]).pipe(
    map(([leagueData, historicalSeasons, selectedSeason]) => this.buildSelectionContext(
      leagueData.league.Season,
      historicalSeasons,
      selectedSeason
    )),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly transactions$ = this.selectionContext$.pipe(
    tap(() => {
      this.loadFailed = false;
    }),
    switchMap(context => this.dataService.getTransactionsForSources(
      context.IncludeCurrent,
      context.HistoricalPaths
    ).pipe(
      catchError(() => {
        this.loadFailed = true;
        return of([]);
      })
    )),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly drafts$ = combineLatest([
    this.selectionContext$,
    this.leagueData$
  ]).pipe(
    switchMap(([context, leagueData]) => {
      const historicDrafts$ = context.HistoricalDraftPaths.map(path =>
        this.dataService.getPastDraftsRaw(path).pipe(catchError(() => of([] as RawDraft[])))
      );
      return (historicDrafts$.length ? forkJoin(historicDrafts$) : of([] as RawDraft[][])).pipe(
        map(drafts => [
          ...(context.IncludeCurrent ? leagueData.drafts : []),
          ...drafts.flat()
        ])
      );
    }),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly vm$ = combineLatest([
    this.transactions$,
    this.selectedFilter$,
    this.selectionContext$,
    this.drafts$,
    this.leagueData$
  ]).pipe(
    map(([transactions, selectedFilter, context, drafts, leagueData]) => ({
      ...buildMovesViewModel(transactions, selectedFilter),
      SeasonLabel: context.SeasonLabel,
      SeasonOptions: context.SeasonOptions,
      SelectedSeason: context.SelectedSeason,
      Drafts: drafts,
      Teams: leagueData.teams
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  setFilter(filter: MovesFilter): void {
    if (this.selectedFilter === filter) {
      return;
    }

    this.selectedFilter = filter;
    this.selectedFilter$.next(filter);
  }

  selectSeason(season: string): void {
    this.selectedSeason$.next(season);
  }

  private getHistoricalTransactionSeasons(
    seasons: PastSeasonIndexEntry[],
    currentSeason: string
  ): PastSeasonIndexEntry[] {
    return seasons
      .filter(entry =>
        entry.Resources?.Transactions?.Exists === true
        && !!entry.Resources?.Transactions?.Path
        && Number(entry.Season) < Number(currentSeason)
      )
      .sort((left, right) => Number(right.Season) - Number(left.Season));
  }

  private buildSelectionContext(
    currentSeason: string,
    historicalSeasons: PastSeasonIndexEntry[],
    requestedSeason: string | null
  ): MovesSelectionContext {
    const historicalOptions = historicalSeasons.map(entry => ({
      Id: entry.Season,
      Label: entry.Season,
      TransactionPath: entry.Resources.Transactions?.Path ?? null
    }));
    const seasonOptions: MovesSeasonOption[] = [
      {
        Id: currentSeason,
        Label: `${currentSeason} (current)`,
        TransactionPath: null
      },
      {
        Id: ALL_SEASONS_ID,
        Label: 'All seasons',
        TransactionPath: null
      },
      ...historicalOptions
    ];
    const selectedSeason = requestedSeason
      && seasonOptions.some(option => option.Id === requestedSeason)
      ? requestedSeason
      : currentSeason;

    if (selectedSeason === ALL_SEASONS_ID) {
      return {
        SeasonOptions: seasonOptions,
        SelectedSeason: selectedSeason,
        SeasonLabel: 'All seasons',
        IncludeCurrent: true,
        HistoricalPaths: historicalOptions
          .map(option => option.TransactionPath)
          .filter((path): path is string => !!path),
        HistoricalDraftPaths: historicalSeasons
          .map(entry => entry.Resources.Drafts?.Exists ? entry.Resources.Drafts.Path : null)
          .filter((path): path is string => !!path)
      };
    }

    if (selectedSeason === currentSeason) {
      return {
        SeasonOptions: seasonOptions,
        SelectedSeason: selectedSeason,
        SeasonLabel: currentSeason,
        IncludeCurrent: true,
        HistoricalPaths: [],
        HistoricalDraftPaths: []
      };
    }

    const selectedHistoricalSeason = historicalOptions.find(option => option.Id === selectedSeason);

    return {
      SeasonOptions: seasonOptions,
      SelectedSeason: selectedSeason,
      SeasonLabel: selectedSeason,
      IncludeCurrent: false,
      HistoricalPaths: selectedHistoricalSeason?.TransactionPath
        ? [selectedHistoricalSeason.TransactionPath]
        : [],
      HistoricalDraftPaths: historicalSeasons
        .filter(entry => entry.Season === selectedSeason && entry.Resources.Drafts?.Exists)
        .map(entry => entry.Resources.Drafts?.Path)
        .filter((path): path is string => !!path)
    };
  }
}
