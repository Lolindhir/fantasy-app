import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { DraftPickPopoverComponent } from '../../../../components/draft-pick-popover/draft-pick-popover';
import { PositionStylePipe } from '../../../../../../shared/pipes/position-style.pipe';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-pick-chip',
  standalone: true,
  imports: [CommonModule, MatMenuModule, PositionStylePipe, DraftPickPopoverComponent],
  templateUrl: './current-draft-pick-chip.html',
  styleUrl: './current-draft-pick-chip.scss'
})
export class CurrentDraftPickChipComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;
  @Input() usePickedPositionColor = false;
}
