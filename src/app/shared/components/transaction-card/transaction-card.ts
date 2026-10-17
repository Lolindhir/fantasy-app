import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import type { Transaction, TransactionParticipant } from '../../../core/models/transaction.models';
import type { RawDraft } from '../../../core/models/draft.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import { MatMenuModule } from '@angular/material/menu';
import { DraftPickContextPopoverComponent } from '../draft-pick-context/draft-pick-context-popover';
import type { DraftPickContext } from '../draft-pick-context/draft-pick-context.models';
import type { Player } from '../../../core/models/player.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { TeamIdentityComponent } from '../team-identity/team-identity';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import {
  buildTransactionPickContext,
  getTransactionCardAssets,
  getTransactionPreviewLimit,
  type TransactionAssetDirection,
  type TransactionCardAsset,
  type TransactionDisplayCategory,
  type TransactionDisplayDensity
} from './transaction-card.presenter';

@Component({
  selector: 'app-transaction-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatMenuModule, PositionStylePipe, TeamIdentityComponent, DraftPickContextPopoverComponent],
  templateUrl: './transaction-card.html',
  styleUrl: './transaction-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TransactionCardComponent {
  @Input({ required: true }) transaction!: Transaction;
  @Input({ required: true }) category!: TransactionDisplayCategory;
  @Input() density: TransactionDisplayDensity = 'compact';
  @Input() drafts: readonly RawDraft[] = [];
  @Input() teams: readonly FantasyTeam[] = [];

  private readonly dialog = inject(MatDialog);
  private readonly cache = new WeakMap<TransactionParticipant, {
    incoming: TransactionCardAsset[];
    outgoing: TransactionCardAsset[];
  }>();

  expanded = false;

  get icon(): string {
    switch (this.category) {
      case 'trade': return 'swap_horiz';
      case 'add': return 'person_add';
      case 'cut': return 'person_remove';
      default: return 'sync_alt';
    }
  }

  get label(): string {
    switch (this.category) {
      case 'trade': return 'Trade';
      case 'add': return 'Add';
      case 'cut': return 'Cut';
      default: return this.transaction.Type === 'commissioner' ? 'Commissioner move' : 'Move';
    }
  }

  get previewLimit(): number {
    return getTransactionPreviewLimit(this.category, this.density, this.expanded);
  }

  getAssets(participant: TransactionParticipant, direction: TransactionAssetDirection): TransactionCardAsset[] {
    let assets = this.cache.get(participant);
    if (!assets) {
      assets = {
        incoming: getTransactionCardAssets(participant, 'incoming'),
        outgoing: getTransactionCardAssets(participant, 'outgoing')
      };
      this.cache.set(participant, assets);
    }
    return assets[direction];
  }

  visibleAssets(participant: TransactionParticipant, direction: TransactionAssetDirection): TransactionCardAsset[] {
    return this.getAssets(participant, direction).slice(0, this.previewLimit);
  }

  hiddenAssets(participant: TransactionParticipant, direction: TransactionAssetDirection): number {
    return Math.max(0, this.getAssets(participant, direction).length - this.previewLimit);
  }

  pickContext(asset: TransactionCardAsset): DraftPickContext | null {
    return buildTransactionPickContext(asset, this.drafts, this.teams);
  }

  toggleExpanded(): void {
    this.expanded = !this.expanded;
  }

  openPlayer(player: Player | undefined): void {
    if (!player) return;
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
