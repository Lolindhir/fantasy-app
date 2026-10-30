import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { RegularSeasonStandingsListComponent } from '../regular-season-standings-list/regular-season-standings-list';
import { SeasonResultsComponent } from '../season-results/season-results';
import { SharedMaterialImports } from '../../shared-material-imports';
import type {
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
    const winner = season.champion ? season.regularSeasonWinner : undefined;
    const teams = season.playoffResults
      .map(row => ({
        team: { Owner: row.owner },
        teamId: row.teamId,
        teamName: row.teamName,
        place: row.place,
        isRegularSeasonChampion: !!winner && String(row.teamId) === String(winner.teamId),
        ownerAvatar: row.ownerAvatar,
        teamAvatar: row.teamAvatar
      }))
      .sort((a, b) => a.place - b.place);

    return {
      teams,
      champion: teams.find(row => row.place === 1),
      runnerUp: teams.find(row => row.place === 2),
      thirdPlace: teams.find(row => row.place === 3),
      remainingTeams: teams.filter(row => row.place > 3),
      regularSeasonChampion: winner ? {
        teamId: winner.teamId,
        owner: winner.owner,
        teamName: winner.teamName,
        teamAvatar: winner.teamAvatar,
        ownerAvatar: winner.ownerAvatar,
        record: winner.record,
        points: winner.points
      } : undefined
    };
  }

}
