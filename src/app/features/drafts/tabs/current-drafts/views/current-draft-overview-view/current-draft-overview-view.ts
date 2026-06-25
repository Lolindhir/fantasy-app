import { CommonModule } from '@angular/common';
import { AfterViewChecked, Component, ElementRef, Input, Renderer2, inject } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { PositionStylePipe } from '../../../../../../shared/pipes/position-style.pipe';
import { CurrentDraftPickPopoverComponent } from '../../components/current-draft-pick-popover/current-draft-pick-popover';
import type { DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-overview-view',
  standalone: true,
  imports: [CommonModule, MatMenuModule, PositionStylePipe, CurrentDraftPickPopoverComponent],
  templateUrl: './current-draft-overview-view.html',
  styleUrl: './current-draft-overview-view.scss'
})
export class CurrentDraftOverviewViewComponent implements AfterViewChecked {
  private hostElement = inject<ElementRef<HTMLElement>>(ElementRef);
  private renderer = inject(Renderer2);

  @Input({ required: true }) draftVm!: DraftViewModel;

  get columnCount(): number {
    return Math.max(...this.draftVm.rounds.map(round => round.picks.length), 1);
  }

  ngAfterViewChecked(): void {
    this.renderTileTeamNames();
  }

  private renderTileTeamNames(): void {
    const pickItems = this.draftVm.rounds.flatMap(round => round.picks);
    const pickTiles = Array.from(
      this.hostElement.nativeElement.querySelectorAll<HTMLElement>('.draft-pick-tile')
    );

    pickTiles.forEach((tile, index) => {
      const pickItem = pickItems[index];
      const teamLabel = pickItem?.selectedPlayer
        ? pickItem.selectedPlayer.NameLast || pickItem.selectedPlayer.NameShort || pickItem.selectedPlayer.Name || pickItem.pick.PlayerName
        : pickItem?.currentOwner.abbr;
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
