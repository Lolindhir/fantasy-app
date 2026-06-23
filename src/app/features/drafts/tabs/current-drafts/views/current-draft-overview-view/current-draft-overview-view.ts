import { CommonModule } from '@angular/common';
import { AfterViewChecked, Component, ElementRef, Input, Renderer2, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
import type { Player } from '../../../../../../core/models/fantasy.models';
import { PlayerDetailDialogComponent } from '../../../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionColorPipe } from '../../../../../../shared/pipes/position-color.pipe';
import type { DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-overview-view',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatMenuModule, PositionColorPipe],
  templateUrl: './current-draft-overview-view.html',
  styleUrl: './current-draft-overview-view.scss'
})
export class CurrentDraftOverviewViewComponent implements AfterViewChecked {
  private dialog = inject(MatDialog);
  private hostElement = inject<ElementRef<HTMLElement>>(ElementRef);
  private renderer = inject(Renderer2);

  @Input({ required: true }) draftVm!: DraftViewModel;

  get columnCount(): number {
    return Math.max(...this.draftVm.rounds.map(round => round.picks.length), 1);
  }

  ngAfterViewChecked(): void {
    this.renderTileTeamNames();
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

  private renderTileTeamNames(): void {
    const pickItems = this.draftVm.rounds.flatMap(round => round.picks);
    const pickTiles = Array.from(
      this.hostElement.nativeElement.querySelectorAll<HTMLElement>('.draft-pick-tile')
    );

    pickTiles.forEach((tile, index) => {
      const pickItem = pickItems[index];
      const teamLabel = pickItem?.selectedPlayer
        ? pickItem.selectedPlayer.NameShort || pickItem.selectedPlayer.Name || pickItem.pick.PlayerName
        : (pickItem?.currentOwner as { abbr?: string } | undefined)?.abbr;
      if (!teamLabel) return;

      const existingTeamNameElement = tile.querySelector<HTMLElement>('.tile-team-name');
      const teamNameElement = existingTeamNameElement ?? this.renderer.createElement('span') as HTMLElement;

      if (!existingTeamNameElement) {
        this.renderer.addClass(teamNameElement, 'tile-team-name');
        this.renderer.appendChild(tile, teamNameElement);
      }

      if (teamNameElement.textContent !== teamLabel) {
        this.renderer.setProperty(teamNameElement, 'textContent', teamLabel);
      }
    });
  }
}
