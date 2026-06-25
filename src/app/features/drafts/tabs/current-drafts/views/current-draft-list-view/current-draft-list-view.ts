import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionStylePipe } from '../../../../../../shared/pipes/position-style.pipe';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-list-view',
  standalone: true,
  imports: [CommonModule, MatDialogModule, CurrentDraftPickChipComponent, PositionStylePipe],
  templateUrl: './current-draft-list-view.html',
  styleUrl: './current-draft-list-view.scss'
})
export class CurrentDraftListViewComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;

  get isCompletedDraft(): boolean {
    const draft = this.draftVm?.draft;
    return draft?.Status === 'Complete'
      || draft?.DisplayStatus === 'Completed'
      || draft?.SleeperStatus === 'complete';
  }

  getPickStatusLabel(item: DraftPickViewModel): string {
    return item.pick.PlayerName || item.pick.Status === 'Picked' ? 'Picked' : 'Open';
  }

  openPlayerDetail(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
