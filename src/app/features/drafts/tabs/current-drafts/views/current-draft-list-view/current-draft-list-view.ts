import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionColorPipe } from '../../../../../../shared/pipes/position-color.pipe';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-list-view',
  standalone: true,
  imports: [CommonModule, MatDialogModule, CurrentDraftPickChipComponent, PositionColorPipe],
  templateUrl: './current-draft-list-view.html',
  styleUrl: './current-draft-list-view.scss'
})
export class CurrentDraftListViewComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) draftVm!: DraftViewModel;

  get orderedPicks(): DraftPickViewModel[] {
    return this.draftVm.rounds
      .flatMap(round => round.picks)
      .sort((a, b) => this.comparePicksByDraftOrder(a, b));
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

  private comparePicksByDraftOrder(a: DraftPickViewModel, b: DraftPickViewModel): number {
    const roundDiff = (a.pick.Round ?? 999) - (b.pick.Round ?? 999);
    if (roundDiff !== 0) return roundDiff;

    const positionDiff = (a.pick.PositionInRound ?? 999) - (b.pick.PositionInRound ?? 999);
    if (positionDiff !== 0) return positionDiff;

    return (a.pick.OverallPick ?? 9999) - (b.pick.OverallPick ?? 9999);
  }
}
