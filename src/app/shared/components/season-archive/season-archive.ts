import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

import type { FantasyTeam } from '../../../core/models/league.models';
import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../../core/models/season-statistics.models';
import { statisticsByTeam } from '../../utils/season-statistics-view.util';
import { SeasonStandingsTableComponent } from '../season-standings-table/season-standings-table';
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
    SeasonStandingsTableComponent
  ],
  templateUrl: './season-archive.html',
  styleUrl: './season-archive.scss'
})
export class SeasonArchiveComponent {
  @Input({ required: true }) history: SeasonHistoryViewModel | null | undefined;

  /** Current teams for logo and abbreviation, joined by TeamID. */
  @Input() teams: readonly FantasyTeam[] | null | undefined;

  /** Archived season statistics keyed by season (Issue #506). */
  @Input() statistics: ReadonlyMap<string, SeasonStatisticsReadModel> | null | undefined;

  private statisticsCache = new Map<SeasonStatisticsReadModel, ReadonlyMap<string, SeasonStatisticsTeam>>();

  /** Stable per-season index so the child input does not change on every check. */
  statisticsByTeam(season: SeasonHistorySeasonViewModel): ReadonlyMap<string, SeasonStatisticsTeam> | null {
    const doc = this.statistics?.get(season.season);
    if (!doc) return null;
    let index = this.statisticsCache.get(doc);
    if (!index) {
      index = statisticsByTeam(doc.Teams);
      this.statisticsCache.set(doc, index);
    }
    return index;
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
