import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { RegularSeasonStandingsListComponent } from '../regular-season-standings-list/regular-season-standings-list';
import { SeasonResultsComponent } from '../season-results/season-results';
import { SharedMaterialImports } from '../../shared-material-imports';
import type {
  SeasonHistoryAwardItem,
  SeasonHistorySeasonViewModel,
  SeasonHistoryViewModel,
  SeasonResultsViewModel
} from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-season-archive',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports,
    SeasonResultsComponent,
    RegularSeasonStandingsListComponent
  ],
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
        awardsDisplay: this.awardsForOwner(season, row.owner)
          .map(award => award.icon)
          .join('')
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

  awardsForOwner(
    season: SeasonHistorySeasonViewModel,
    owner: string
  ): SeasonHistoryAwardItem[] {
    return season.awards.filter(award => award.owner === owner);
  }
}
