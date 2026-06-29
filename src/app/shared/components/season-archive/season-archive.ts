import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { SharedMaterialImports } from '../../shared-material-imports';
import type {
  SeasonHistoryAwardItem,
  SeasonHistoryPlayoffRow,
  SeasonHistorySeasonViewModel,
  SeasonHistoryViewModel
} from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-season-archive',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './season-archive.html',
  styleUrl: './season-archive.scss'
})
export class SeasonArchiveComponent {
  @Input({ required: true }) history: SeasonHistoryViewModel | null | undefined;

  champion(season: SeasonHistorySeasonViewModel): SeasonHistoryPlayoffRow | undefined {
    return season.playoffResults[0];
  }

  runnerUp(season: SeasonHistorySeasonViewModel): SeasonHistoryPlayoffRow | undefined {
    return season.playoffResults[1];
  }

  thirdPlace(season: SeasonHistorySeasonViewModel): SeasonHistoryPlayoffRow | undefined {
    return season.playoffResults[2];
  }

  remainingPlayoffResults(season: SeasonHistorySeasonViewModel): SeasonHistoryPlayoffRow[] {
    return season.playoffResults.slice(3);
  }

  awardsForOwner(
    season: SeasonHistorySeasonViewModel,
    owner: string
  ): SeasonHistoryAwardItem[] {
    return season.awards.filter(award => award.owner === owner);
  }

  placeEmoji(place: number): string {
    switch (place) {
      case 4:
        return '4️⃣';
      case 5:
        return '5️⃣';
      case 6:
        return '6️⃣';
      case 7:
        return '7️⃣';
      case 8:
        return '8️⃣';
      case 9:
        return '9️⃣';
      case 10:
        return '🔟';
      default:
        return `${place}.`;
    }
  }
}
