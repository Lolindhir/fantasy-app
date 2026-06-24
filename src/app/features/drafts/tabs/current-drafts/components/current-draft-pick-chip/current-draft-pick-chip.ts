import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionColorPipe } from '../../../../../../shared/pipes/position-color.pipe';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-pick-chip',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatMenuModule, PositionColorPipe],
  templateUrl: './current-draft-pick-chip.html',
  styleUrl: './current-draft-pick-chip.scss'
})
export class CurrentDraftPickChipComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;
  @Input() usePickedPositionColor = false;

  get statusLabel(): string {
    return this.item.pick.PlayerName || this.item.pick.Status === 'Picked' ? 'Picked' : 'Open Pick';
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
