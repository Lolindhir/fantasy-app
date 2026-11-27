import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { catchError, map } from 'rxjs/operators';
import { forkJoin, of } from 'rxjs';

import { statisticsByTeam } from '../../shared/utils/season-statistics-view.util';
import { buildInjuryImpactByTeam } from '../../shared/utils/injury-impact-view.util';
import { DataService } from '../../core/services/data.service';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { PlayoffPictureComponent } from '../../shared/components/playoff-picture/playoff-picture';
import { resolvePlayoffOdds } from '../../shared/utils/schedule-outlook-view.util';
import { SeasonArchiveComponent } from '../../shared/components/season-archive/season-archive';
import {
  buildCurrentStandings,
  buildSeasonHistory,
  type SeasonHistoryViewModel
} from '../../shared/utils/league-standings-view.util';

@Component({
  selector: 'app-standings-page',
  standalone: true,
  imports: [
    CommonModule,
    CurrentStandingsComponent,
    PlayoffPictureComponent,
    SeasonArchiveComponent
  ],
  templateUrl: './standings-page.html',
  styleUrl: './standings-page.scss'
})
export class StandingsPageComponent {
  private dataService = inject(DataService);

  vm$ = forkJoin({ league: this.dataService.getLeagueSummary(), outlook: this.dataService.getScheduleOutlook().pipe(catchError(() => of(null))), stats: this.dataService.getSeasonStatistics().pipe(catchError(() => of(null))), injury: this.dataService.getInjuryImpact() }).pipe(
    map(({ league, outlook, stats, injury }) => {
      const teams = league.Teams;
      const configuredPlayoffTeams = league.Settings?.['playoff_teams'];
      const playoffTeams = typeof configuredPlayoffTeams === 'number'
        && Number.isInteger(configuredPlayoffTeams)
        && configuredPlayoffTeams > 0
        && configuredPlayoffTeams < teams.length
        ? configuredPlayoffTeams
        : null;

      return {
        league,
        teams,
        currentStatistics: stats && String(stats.Season) === String(league.Season) ? statisticsByTeam(stats.Teams) : null,
        currentInjuryImpact: buildInjuryImpactByTeam((injury?.Seasons ?? []).find(item => String(item.Season) === String(league.Season))),
        currentStandings: buildCurrentStandings(league, teams),
        playoffTeams,
        playoffOdds: resolvePlayoffOdds(outlook, league.Season),
        seasonHistory: filterArchivedSeasons(buildSeasonHistory(league), String(league.Season))
      };
    })
  );
}

function filterArchivedSeasons(
  history: SeasonHistoryViewModel,
  currentSeason: string
): SeasonHistoryViewModel {
  return {
    seasons: history.seasons.filter(season =>
      season.season !== currentSeason
      && /^\d{4}$/.test(season.season)
      && !!season.champion
    )
  };
}
