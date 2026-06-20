import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftPickViewModel, DraftViewModel } from '../../../../models/drafts-view.models';

@Component({
  selector: 'app-current-draft-list-view',
  standalone: true,
  imports: [CommonModule, CurrentDraftPickChipComponent],
  templateUrl: './current-draft-list-view.html',
  styleUrl: './current-draft-list-view.scss'
})
export class CurrentDraftListViewComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;

  get orderedPicks(): DraftPickViewModel[] {
    return this.draftVm.rounds
      .flatMap(round => round.picks)
      .sort((a, b) => this.comparePicksByDraftOrder(a, b));
  }

  getPickStatusLabel(item: DraftPickViewModel): string {
    return item.pick.PlayerName || item.pick.Status === 'Picked' ? 'Picked' : 'Open';
  }

  private comparePicksByDraftOrder(a: DraftPickViewModel, b: DraftPickViewModel): number {
    const roundDiff = (a.pick.Round ?? 999) - (b.pick.Round ?? 999);
    if (roundDiff !== 0) return roundDiff;

    const positionDiff = (a.pick.PositionInRound ?? 999) - (b.pick.PositionInRound ?? 999);
    if (positionDiff !== 0) return positionDiff;

    return (a.pick.OverallPick ?? 9999) - (b.pick.OverallPick ?? 9999);
  }
}
