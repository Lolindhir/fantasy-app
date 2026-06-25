import { Component, Input } from '@angular/core';
import { DraftPickTriggerComponent } from '../../../../components/draft-pick-trigger/draft-pick-trigger';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-pick-chip',
  standalone: true,
  imports: [DraftPickTriggerComponent],
  templateUrl: './current-draft-pick-chip.html',
  styleUrl: './current-draft-pick-chip.scss'
})
export class CurrentDraftPickChipComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;
  @Input() usePickedPositionColor = false;
}
