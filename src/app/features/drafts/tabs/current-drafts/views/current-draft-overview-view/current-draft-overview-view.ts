import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { DraftPickCardComponent } from '../../../../components/draft-pick-card/draft-pick-card';
import type { DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-overview-view',
  standalone: true,
  imports: [CommonModule, DraftPickCardComponent],
  templateUrl: './current-draft-overview-view.html',
  styleUrl: './current-draft-overview-view.scss'
})
export class CurrentDraftOverviewViewComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;

  get columnCount(): number {
    return Math.max(...this.draftVm.rounds.map(round => round.picks.length), 1);
  }
}
