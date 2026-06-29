import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { SeasonResultsComponent } from '../season-results/season-results';
import { SharedMaterialImports } from '../../shared-material-imports';
import type {
  SeasonHistoryAwardItem,
  SeasonHistoryPlayoffRow,
  SeasonHistorySeasonViewModel,
  SeasonHistoryViewModel,
  SeasonResultsViewModel
} from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-season-archive',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports, SeasonResultsComponent],
  templateUrl: './season-archive.html',
  styleUrl: './season-archive.scss'
})
export class SeasonArchiveComponent {
  @Input({ required: true }) history: SeasonHistoryViewModel | null | undefined;

  playoffResultsViewModel(season: SeasonHistorySeasonViewModel): SeasonResultsViewModel {
    const teams = season.playoffResults
      .map(row => ({
        team: { Owner: row.owner },
        place: row.place,
        awardsDisplay: ''
      }))
      .sort((a, b) => a.place - b.place);

    return {
      teams,
      champion: teams[0],
      runnerUp: teams[1],
      thirdPlace: teams[2],
      remainingTeams: teams.slice(3)
    };
  }

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
