import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionStylePipe } from '../../../../../../shared/pipes/position-style.pipe';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-pick-popover',
  standalone: true,
  imports: [CommonModule, MatDialogModule, PositionStylePipe],
  templateUrl: './current-draft-pick-popover.html',
  styleUrl: './current-draft-pick-popover.scss'
})
export class CurrentDraftPickPopoverComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;

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
