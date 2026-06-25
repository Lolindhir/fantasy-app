import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { PositionStylePipe } from '../../../shared/pipes/position-style.pipe';
import { CurrentDraftPickPopoverComponent } from '../../drafts/tabs/current-drafts/components/current-draft-pick-popover/current-draft-pick-popover';
import type { DraftPickViewModel, DraftViewModel } from '../../drafts/models/drafts-view.models';

@Component({
  selector: 'app-draft-pick-card',
  standalone: true,
  imports: [CommonModule, MatMenuModule, PositionStylePipe, CurrentDraftPickPopoverComponent],
  templateUrl: './draft-pick-card.html',
  styleUrl: './draft-pick-card.scss'
})
export class DraftPickCardComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;

  get hasSelectedPlayer(): boolean {
    return !!this.item.selectedPlayer;
  }

  get tileContextLabel(): string {
    if (this.item.selectedPlayer) {
      return this.item.selectedPlayer.NameLast
        || this.item.selectedPlayer.NameShort
        || this.item.selectedPlayer.Name
        || this.item.pick.PlayerName
        || '';
    }

    return this.item.currentOwner.abbr;
  }
}
