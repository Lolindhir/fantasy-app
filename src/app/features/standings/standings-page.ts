import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import { DataService } from '../../core/services/data.service';
import { AllTimeOverviewComponent } from '../../shared/components/all-time-overview/all-time-overview';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { LeagueLegacySummaryComponent } from '../../shared/components/league-legacy-summary/league-legacy-summary';
import { SeasonArchiveComponent } from '../../shared/components/season-archive/season-archive';
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

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams }) => {
      const legacy = buildLeagueLegacy(league, teams);

      return {
        league,
        legacy,
        currentStandings: buildCurrentStandings(league, teams),
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
