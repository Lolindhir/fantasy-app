import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-pick-chip',
  standalone: true,
  imports: [CommonModule, MatMenuModule],
  templateUrl: './current-draft-pick-chip.html',
  styleUrl: './current-draft-pick-chip.scss'
})
export class CurrentDraftPickChipComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input({ required: true }) item!: DraftPickViewModel;

  get statusLabel(): string {
    return this.item.pick.PlayerName || this.item.pick.Status === 'Picked' ? 'Picked' : 'Open Pick';
  }
}
