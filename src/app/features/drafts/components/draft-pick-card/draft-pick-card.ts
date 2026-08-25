import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';

import { DraftPickContextPopoverComponent } from '../../../../shared/components/draft-pick-context/draft-pick-context-popover';
import type { DraftPickContext } from '../../../../shared/components/draft-pick-context/draft-pick-context.models';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import type { DraftPickViewModel, DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-draft-pick-card',
  standalone: true,
  imports: [CommonModule, MatMenuModule, PositionStylePipe, DraftPickContextPopoverComponent],
  templateUrl: './draft-pick-card.html',
  styleUrl: './draft-pick-card.scss'
})
export class DraftPickCardComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;

  get context(): DraftPickContext {
    return {
      draft: this.draftVm.draft,
      pick: this.item.pick,
      label: this.item.pick.DisplayPick,
      currentOwner: this.item.currentOwner,
      originalOwner: this.item.originalOwner,
      selectedPlayer: this.item.selectedPlayer,
      selectedPlayerName: this.item.selectedPlayerName ?? this.item.pick.PlayerName ?? undefined,
      isTradedPick: this.item.isCurrentlyTraded,
      roundColor: this.item.roundColor
    };
  }

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
