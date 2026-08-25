import { Component, Input } from '@angular/core';

import { DraftPickContextTriggerComponent } from '../../../../shared/components/draft-pick-context/draft-pick-context-trigger';
import type { DraftPickContext } from '../../../../shared/components/draft-pick-context/draft-pick-context.models';
import type {
  CompactRoundPickViewModel,
  DraftPickViewModel,
  DraftViewModel,
  TeamDisplayViewModel
} from '../../models/drafts-view.models';

export type DraftPickTriggerVariant = 'chip' | 'round-pill';

@Component({
  selector: 'app-draft-pick-trigger',
  standalone: true,
  imports: [DraftPickContextTriggerComponent],
  templateUrl: './draft-pick-trigger.html',
  styleUrl: './draft-pick-trigger.scss'
})
export class DraftPickTriggerComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input() item?: DraftPickViewModel;
  @Input() compactPick?: CompactRoundPickViewModel;
  @Input() currentOwner?: TeamDisplayViewModel;
  @Input() variant: DraftPickTriggerVariant = 'chip';
  @Input() usePickedPositionColor = false;

  get context(): DraftPickContext {
    return {
      draft: this.draftVm.draft,
      pick: this.item?.pick,
      label: this.item?.pick.DisplayPick ?? this.compactPick?.label ?? 'Pick',
      currentOwner: this.item?.currentOwner ?? this.currentOwner,
      originalOwner: this.item?.originalOwner ?? this.compactPick?.originalOwner,
      selectedPlayer: this.item?.selectedPlayer,
      selectedPlayerName: this.item?.selectedPlayerName ?? this.item?.pick.PlayerName ?? undefined,
      isTradedPick: this.item?.isCurrentlyTraded ?? this.compactPick?.isCurrentlyTraded ?? false,
      roundColor: this.item?.roundColor ?? this.compactPick?.color
    };
  }
}
