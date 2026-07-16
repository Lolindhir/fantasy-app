import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import type {
  TransactionParticipant,
  TransactionPlayerAsset
} from '../../core/models/transaction.models';
import { DataService } from '../../core/services/data.service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import {
  buildMovesViewModel,
  getDraftPickLabel,
  getMoveTypeIcon,
  getMoveTypeLabel
} from './moves-view-model.util';

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports
  ],
  templateUrl: './league-activity.html',
  styleUrl: './league-activity.scss'
})
export class LeagueActivityComponent {
  private dataService = inject(DataService);

  loadFailed = false;

  readonly moveTypeLabel = getMoveTypeLabel;
  readonly moveTypeIcon = getMoveTypeIcon;
  readonly draftPickLabel = getDraftPickLabel;

  readonly timestamp$ = this.dataService.getTransactionsTimestamp().pipe(
    catchError(() => of(undefined))
  );

  readonly vm$ = this.dataService.getTransactions().pipe(
    map(transactions => buildMovesViewModel(transactions)),
    catchError(() => {
      this.loadFailed = true;
      return of(buildMovesViewModel([]));
    }),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  getTeamName(participant: TransactionParticipant): string {
    return participant.Team?.Team
      || participant.Team?.Owner
      || `Team ${participant.RosterID}`;
  }

  getPlayerName(asset: TransactionPlayerAsset): string {
    return asset.Player?.Name || `Player ${asset.PlayerID}`;
  }

  hasIncomingAssets(participant: TransactionParticipant): boolean {
    return participant.AddedPlayers.length > 0 || participant.AcquiredDraftPicks.length > 0;
  }

  hasOutgoingAssets(participant: TransactionParticipant): boolean {
    return participant.DroppedPlayers.length > 0 || participant.SentDraftPicks.length > 0;
  }
}
