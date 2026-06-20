import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import type { DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-overview-view',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatMenuModule],
  templateUrl: './current-draft-overview-view.html',
  styleUrl: './current-draft-overview-view.scss'
})
export class CurrentDraftOverviewViewComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;

  get columnCount(): number {
    return Math.max(...this.draftVm.rounds.map(round => round.picks.length), 1);
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
