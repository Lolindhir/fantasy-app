import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-team-view',
  standalone: true,
  imports: [CommonModule, CurrentDraftPickChipComponent],
  templateUrl: './current-draft-team-view.html',
  styleUrl: './current-draft-team-view.scss'
})
export class CurrentDraftTeamViewComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
}
