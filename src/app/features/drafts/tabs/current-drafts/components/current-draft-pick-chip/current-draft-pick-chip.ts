import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { PositionStylePipe } from '../../../../../../shared/pipes/position-style.pipe';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';
import { CurrentDraftPickPopoverComponent } from '../current-draft-pick-popover/current-draft-pick-popover';

@Component({
  selector: 'app-current-draft-pick-chip',
  standalone: true,
  imports: [CommonModule, MatMenuModule, PositionStylePipe, CurrentDraftPickPopoverComponent],
  templateUrl: './current-draft-pick-chip.html',
  styleUrl: './current-draft-pick-chip.scss'
})
export class CurrentDraftPickChipComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;
  @Input() usePickedPositionColor = false;
}
