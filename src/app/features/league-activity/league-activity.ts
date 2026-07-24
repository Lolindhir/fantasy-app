import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, of } from 'rxjs';
import { catchError, map, shareReplay, switchMap, tap } from 'rxjs/operators';

import type {
  TransactionParticipant,
  TransactionPlayerAsset
} from '../../core/models/transaction.models';
import { DataService } from '../../core/services/data.service';
import type {
  PastSeasonIndexEntry,
  PastSeasonsIndex
} from '../../core/services/data-api.service';
import { PositionStylePipe } from '../../shared/pipes/position-style.pipe';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import {
  buildMovesViewModel,
  getDraftPickAssetLabel,
  getDraftPickOriginalOwnerLabel,
  getDraftPickTrackKey,
  getIncomingAssetIcon,
  getIncomingAssetLabel,
  getMoveCategory,
  getMoveTypeIcon,
  getMoveTypeLabel,
  getOutgoingAssetIcon,
  getOutgoingAssetLabel,
  type MovesFilter
} from './moves-view-model.util';

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
}

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    CommonModule,
    PositionStylePipe,
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
  readonly moveTypeLabel = getMoveTypeLabel;
  readonly moveTypeIcon = getMoveTypeIcon;
  readonly incomingAssetLabel = getIncomingAssetLabel;
  readonly outgoingAssetLabel = getOutgoingAssetLabel;
  readonly incomingAssetIcon = getIncomingAssetIcon;
  readonly outgoingAssetIcon = getOutgoingAssetIcon;
  readonly draftPickAssetLabel = getDraftPickAssetLabel;
  readonly draftPickOriginalOwnerLabel = getDraftPickOriginalOwnerLabel;
  readonly draftPickTrackKey = getDraftPickTrackKey;

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

  readonly vm$ = combineLatest([
    this.transactions$,
    this.selectedFilter$,
    this.selectionContext$
  ]).pipe(
    map(([transactions, selectedFilter, context]) => ({
      ...buildMovesViewModel(transactions, selectedFilter),
      SeasonLabel: context.SeasonLabel,
      SeasonOptions: context.SeasonOptions,
      SelectedSeason: context.SelectedSeason
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

  getTeamName(participant: TransactionParticipant): string {
    return participant.Team?.Team
      || participant.Team?.Owner
      || `Team ${participant.RosterID}`;
  }

  getTeamInitials(participant: TransactionParticipant): string {
    return this.getTeamName(participant)
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0]?.toUpperCase())
      .join('');
  }

  getPlayerName(asset: TransactionPlayerAsset): string {
    return asset.Player?.Name || `Player ${asset.PlayerID}`;
  }

  getPlayerTeamLabel(asset: TransactionPlayerAsset): string {
    return asset.Player?.TeamNFL?.Abv || 'NFL';
  }

  hasIncomingAssets(participant: TransactionParticipant): boolean {
    return participant.AddedPlayers.length > 0 || participant.AcquiredDraftPicks.length > 0;
  }

  hasOutgoingAssets(participant: TransactionParticipant): boolean {
    return participant.DroppedPlayers.length > 0 || participant.SentDraftPicks.length > 0;
  }

  getIncomingAssetCount(participant: TransactionParticipant): number {
    return participant.AddedPlayers.length + participant.AcquiredDraftPicks.length;
  }

  getOutgoingAssetCount(participant: TransactionParticipant): number {
    return participant.DroppedPlayers.length + participant.SentDraftPicks.length;
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
          .filter((path): path is string => !!path)
      };
    }

    if (selectedSeason === currentSeason) {
      return {
        SeasonOptions: seasonOptions,
        SelectedSeason: selectedSeason,
        SeasonLabel: currentSeason,
        IncludeCurrent: true,
        HistoricalPaths: []
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
        : []
    };
  }
}
