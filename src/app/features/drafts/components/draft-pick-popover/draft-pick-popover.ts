import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import type { Player } from '../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import type {
  CompactRoundPickViewModel,
  DraftPickViewModel,
  DraftViewModel,
  TeamDisplayViewModel
} from '../../models/drafts-view.models';

@Component({
  selector: 'app-draft-pick-popover',
  standalone: true,
  imports: [CommonModule, MatDialogModule, PositionStylePipe],
  templateUrl: './draft-pick-popover.html',
  styleUrl: './draft-pick-popover.scss'
})
export class DraftPickPopoverComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input() item?: DraftPickViewModel;
  @Input() compactPick?: CompactRoundPickViewModel;
  @Input() currentOwner?: TeamDisplayViewModel;

  get displayPick(): string {
    return this.item?.pick.DisplayPick ?? this.compactPick?.label.replace('R', 'Round ') ?? 'Pick';
  }

  get overallPick(): number | null {
    return this.item?.pick.OverallPick ?? null;
  }

  get selectedPlayer(): Player | undefined {
    return this.item?.selectedPlayer;
  }

  get showOpenPickLabel(): boolean {
    return !!this.item && !this.selectedPlayer;
  }

  get currentOwnerDisplay(): TeamDisplayViewModel | undefined {
    return this.item?.currentOwner ?? this.currentOwner;
  }

  get originalOwnerDisplay(): TeamDisplayViewModel | undefined {
    return this.item?.originalOwner ?? this.compactPick?.originalOwner;
  }

  get showOriginalOwner(): boolean {
    const currentOwner = this.currentOwnerDisplay;
    const originalOwner = this.originalOwnerDisplay;

    return !!currentOwner && !!originalOwner && currentOwner.id !== originalOwner.id;
  }

  get isTradedPick(): boolean {
    return this.item?.isCurrentlyTraded ?? this.compactPick?.isCurrentlyTraded ?? false;
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
