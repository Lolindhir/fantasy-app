import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { SharedMaterialImports } from '../../../../../shared/shared-material-imports';
import type { DraftPickViewModel, DraftViewModel } from '../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-overview-view',
  standalone: true,
  imports: [CommonModule, MatMenuModule, SharedMaterialImports],
  templateUrl: './current-draft-overview-view.html',
  styleUrl: './current-draft-overview-view.scss'
})
export class CurrentDraftOverviewViewComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;

  getPickStatusLabel(item: DraftPickViewModel): string {
    return item.pick.PlayerName || item.pick.Status === 'Picked' ? 'Picked' : 'Open Pick';
  }
}
