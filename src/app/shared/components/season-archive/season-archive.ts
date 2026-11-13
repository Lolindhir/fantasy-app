import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../../core/models/season-statistics.models';
import { formatDecimal, formatSigned, signClass } from '../../utils/season-statistics-view.util';
import { RegularSeasonStandingsListComponent } from '../regular-season-standings-list/regular-season-standings-list';
import { SeasonAwardsComponent } from '../season-awards/season-awards';
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
    RouterLink,
    SharedMaterialImports,
    SeasonResultsComponent,
    SeasonAwardsComponent,
    RegularSeasonStandingsListComponent
  ],
  templateUrl: './season-archive.html',
  styleUrl: './season-archive.scss'
})
export class SeasonArchiveComponent {
  @Input({ required: true }) history: SeasonHistoryViewModel | null | undefined;

  /** Archived season statistics keyed by season (Issue #506). */
  @Input() statistics: ReadonlyMap<string, SeasonStatisticsReadModel> | null | undefined;

  readonly formatSigned = formatSigned;
  readonly formatDecimal = formatDecimal;
  readonly signClass = signClass;

  /** Teams of the season statistics ordered by luck (presentation sort only). */
  statisticsTeams(season: SeasonHistorySeasonViewModel): SeasonStatisticsTeam[] {
    const teams = this.statistics?.get(season.season)?.Teams ?? [];
    return teams
      .filter(team => team.Games > 0)
      .sort((a, b) => (b.Luck ?? Number.NEGATIVE_INFINITY) - (a.Luck ?? Number.NEGATIVE_INFINITY));
  }

  formatRecord(team: SeasonStatisticsTeam): string {
    return team.Ties > 0 ? `${team.Wins}-${team.Losses}-${team.Ties}` : `${team.Wins}-${team.Losses}`;
  }

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
