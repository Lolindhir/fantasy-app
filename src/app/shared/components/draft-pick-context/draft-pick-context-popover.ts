import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import type { Player } from '../../../core/models/fantasy.models';
import { PlayerPicturePipe } from '../../pipes/player-picture.pipe';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import type { DraftPickContext } from './draft-pick-context.models';

@Component({
  selector: 'app-draft-pick-context-popover',
  standalone: true,
  imports: [CommonModule, MatDialogModule, PositionStylePipe, PlayerPicturePipe],
  templateUrl: './draft-pick-context-popover.html',
  styleUrl: './draft-pick-context-popover.scss'
})
export class DraftPickContextPopoverComponent {
  private readonly dialog = inject(MatDialog);

  @Input({ required: true }) context!: DraftPickContext;

  get displayPick(): string {
    if (this.context.pick?.DisplayPick) return this.context.pick.DisplayPick;
    const roundMatch = /^R(\d+)$/.exec(this.context.label);
    return roundMatch ? `Round ${roundMatch[1]}` : this.context.label;
  }

  get overallPick(): number | null {
    return this.context.pick?.OverallPick ?? null;
  }

  get selectedPlayer(): Player | undefined {
    // A current Player dialog cannot stand in for an archived draft identity.
    return this.context.pick?.PlayerRef?.Name ? undefined : this.context.selectedPlayer;
  }

  get selectedPlayerRef() {
    return this.context.pick?.PlayerRef;
  }

  get selectedPlayerName(): string | undefined {
    return this.selectedPlayerRef?.Name || this.context.selectedPlayerName || this.context.pick?.PlayerName || undefined;
  }

  get showOpenPickLabel(): boolean {
    return !this.selectedPlayer && !this.selectedPlayerName;
  }

  get currentOwnerDisplay() {
    return this.context.currentOwner;
  }

  get originalOwnerDisplay() {
    return this.context.originalOwner;
  }

  get showOriginalOwner(): boolean {
    const currentOwner = this.currentOwnerDisplay;
    const originalOwner = this.originalOwnerDisplay;
    return !!currentOwner && !!originalOwner && currentOwner.id !== originalOwner.id;
  }

  openPlayerDetail(player: Player, event?: Event): void {
    event?.stopPropagation();

    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
