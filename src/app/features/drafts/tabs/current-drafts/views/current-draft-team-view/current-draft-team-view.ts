import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { CurrentDraftPickChipComponent } from '../../components/current-draft-pick-chip/current-draft-pick-chip';
import type { DraftPickViewModel, DraftViewModel, TeamDisplayViewModel } from '../../../../models/drafts-view.models';

type CurrentOwnerPickGroup = {
  owner: TeamDisplayViewModel;
  picks: DraftPickViewModel[];
  pickCount: number;
};

@Component({
  selector: 'app-current-draft-team-view',
  standalone: true,
  imports: [CommonModule, CurrentDraftPickChipComponent],
  templateUrl: './current-draft-team-view.html',
  styleUrl: './current-draft-team-view.scss'
})
export class CurrentDraftTeamViewComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;

  get ownerPickGroups(): CurrentOwnerPickGroup[] {
    const groups = new Map<number, DraftPickViewModel[]>();

    this.orderedPicks.forEach(pick => {
      const ownerId = pick.currentOwner.id;
      if (!groups.has(ownerId)) groups.set(ownerId, []);
      groups.get(ownerId)!.push(pick);
    });

    return [...groups.values()]
      .map(picks => ({
        owner: picks[0].currentOwner,
        picks,
        pickCount: picks.length
      }))
      .sort((a, b) => this.compareOwnerPickGroupsByStrength(a, b));
  }

  private get orderedPicks(): DraftPickViewModel[] {
    return this.draftVm.rounds
      .flatMap(round => round.picks)
      .sort((a, b) => this.comparePicksByStrength(a, b));
  }

  private compareOwnerPickGroupsByStrength(a: CurrentOwnerPickGroup, b: CurrentOwnerPickGroup): number {
    const maxPickCount = Math.max(a.picks.length, b.picks.length);

    for (let index = 0; index < maxPickCount; index++) {
      const aPick = a.picks[index];
      const bPick = b.picks[index];

      if (!aPick && bPick) return 1;
      if (aPick && !bPick) return -1;
      if (!aPick || !bPick) continue;

      const pickDiff = this.comparePicksByStrength(aPick, bPick);
      if (pickDiff !== 0) return pickDiff;
    }

    return a.owner.name.localeCompare(b.owner.name, 'en', { sensitivity: 'base' });
  }

  private comparePicksByStrength(a: DraftPickViewModel, b: DraftPickViewModel): number {
    const roundDiff = (a.pick.Round ?? 999) - (b.pick.Round ?? 999);
    if (roundDiff !== 0) return roundDiff;

    const positionDiff = (a.pick.PositionInRound ?? 999) - (b.pick.PositionInRound ?? 999);
    if (positionDiff !== 0) return positionDiff;

    return (a.pick.OverallPick ?? 9999) - (b.pick.OverallPick ?? 9999);
  }
}
