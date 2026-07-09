import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { DraftPickPlayerCardComponent } from '../../../../../../shared/components/draft-pick-player-card/draft-pick-player-card';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-list-view',
  standalone: true,
  imports: [CommonModule, CurrentDraftPickChipComponent, DraftPickPlayerCardComponent],
  templateUrl: './current-draft-list-view.html',
  styleUrl: './current-draft-list-view.scss'
})
export class CurrentDraftListViewComponent {
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
}
