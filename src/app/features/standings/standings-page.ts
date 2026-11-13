import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { catchError, map, switchMap } from 'rxjs/operators';
import { forkJoin, of, type Observable } from 'rxjs';

import type { SeasonStatisticsReadModel } from '../../core/models/season-statistics.models';
import { DataService } from '../../core/services/data.service';
import { AllTimeOverviewComponent } from '../../shared/components/all-time-overview/all-time-overview';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { LeagueLegacySummaryComponent } from '../../shared/components/league-legacy-summary/league-legacy-summary';
import { SeasonArchiveComponent } from '../../shared/components/season-archive/season-archive';
import { buildBiggestUpsetHighlight, statisticsByTeam } from '../../shared/utils/season-statistics-view.util';
import {
  buildCurrentStandings,
  buildLeagueLegacy,
  buildSeasonHistory,
  type SeasonHistoryViewModel
} from '../../shared/utils/league-standings-view.util';

@Component({
  selector: 'app-standings-page',
  standalone: true,
  imports: [
    CommonModule,
    LeagueLegacySummaryComponent,
    AllTimeOverviewComponent,
    CurrentStandingsComponent,
    SeasonArchiveComponent
  ],
  templateUrl: './standings-page.html',
  styleUrl: './standings-page.scss'
})
export class StandingsPageComponent {
  private dataService = inject(DataService);

  /** Current and archived season statistics; unavailable files never block the page. */
  private readonly statistics$: Observable<{ current: SeasonStatisticsReadModel | null; bySeason: Map<string, SeasonStatisticsReadModel> }> = forkJoin({
    current: this.dataService.getSeasonStatistics().pipe(catchError(() => of(null))),
    index: this.dataService.getPastSeasonsIndex().pipe(catchError(() => of(null)))
  }).pipe(
    switchMap(({ current, index }) => {
      const entries = (index?.Seasons ?? [])
        .map(entry => ({ season: String(entry.Season), path: entry.Resources?.SeasonStatistics }))
        .filter(item => item.path?.Exists && item.path.Path);
      if (entries.length === 0) return of({ current, bySeason: new Map<string, SeasonStatisticsReadModel>() });
      return forkJoin(entries.map(item =>
        this.dataService.getPastSeasonStatisticsRaw(item.path!.Path as string).pipe(
          map(doc => [item.season, doc] as const),
          catchError(() => of(null))
        )
      )).pipe(map(results => ({
        current,
        bySeason: new Map(results.filter((r): r is readonly [string, SeasonStatisticsReadModel] => r !== null))
      })));
    })
  );

  vm$ = forkJoin({ data: this.dataService.getLeagueWithPlayers(), stats: this.statistics$ }).pipe(
    map(({ data: { league, teams }, stats }) => {
      const legacy = buildLeagueLegacy(league, teams);
      const configuredPlayoffTeams = league.Settings?.['playoff_teams'];
      const playoffTeams = typeof configuredPlayoffTeams === 'number'
        && Number.isInteger(configuredPlayoffTeams)
        && configuredPlayoffTeams > 0
        && configuredPlayoffTeams < teams.length
        ? configuredPlayoffTeams
        : null;

      return {
        league,
        legacy,
        highlights: [
          ...legacy.highlights,
          ...(buildBiggestUpsetHighlight(stats.current, stats.bySeason) ? [buildBiggestUpsetHighlight(stats.current, stats.bySeason)!] : [])
        ],
        currentStatistics: stats.current && String(stats.current.Season) === String(league.Season) ? statisticsByTeam(stats.current.Teams) : null,
        seasonStatistics: stats.bySeason,
        teams,
        currentStandings: buildCurrentStandings(league, teams),
        playoffTeams,
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
