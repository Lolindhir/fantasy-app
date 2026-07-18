import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import type {
  TransactionParticipant,
  TransactionPlayerAsset
} from '../../core/models/transaction.models';
import { DataService } from '../../core/services/data.service';
import { PositionStylePipe } from '../../shared/pipes/position-style.pipe';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import {
  buildMovesViewModel,
  getDraftPickAssetLabel,
  getDraftPickLabel,
  getDraftPickOriginalOwnerLabel,
  getDraftPickTrackKey,
  getIncomingAssetIcon,
  getIncomingAssetLabel,
  getMoveTypeIcon,
  getMoveTypeLabel,
  getOutgoingAssetIcon,
  getOutgoingAssetLabel,
  type MovesFilter
} from './moves-view-model.util';

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    CommonModule,
    PositionStylePipe,
    SharedMaterialImports
  ],
  templateUrl: './league-activity.html',
  styleUrl: './league-activity.scss'
})
export class LeagueActivityComponent {
  private readonly dataService = inject(DataService);
  private readonly selectedFilter$ = new BehaviorSubject<MovesFilter>('all');

  loadFailed = false;
  selectedFilter: MovesFilter = 'all';

  readonly moveTypeLabel = getMoveTypeLabel;
  readonly moveTypeIcon = getMoveTypeIcon;
  readonly incomingAssetLabel = getIncomingAssetLabel;
  readonly outgoingAssetLabel = getOutgoingAssetLabel;
  readonly incomingAssetIcon = getIncomingAssetIcon;
  readonly outgoingAssetIcon = getOutgoingAssetIcon;
  readonly draftPickLabel = getDraftPickLabel;
  readonly draftPickAssetLabel = getDraftPickAssetLabel;
  readonly draftPickOriginalOwnerLabel = getDraftPickOriginalOwnerLabel;
  readonly draftPickTrackKey = getDraftPickTrackKey;

  private readonly transactions$ = this.dataService.getTransactions().pipe(
    catchError(() => {
      this.loadFailed = true;
      return of([]);
    }),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly vm$ = combineLatest([
    this.transactions$,
    this.selectedFilter$
  ]).pipe(
    map(([transactions, selectedFilter]) => buildMovesViewModel(transactions, selectedFilter)),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  setFilter(filter: MovesFilter): void {
    if (this.selectedFilter === filter) {
      return;
    }

    this.selectedFilter = filter;
    this.selectedFilter$.next(filter);
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
}
