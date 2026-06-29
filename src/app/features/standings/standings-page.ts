import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import { DataService } from '../../core/services/data.service';
import { AllTimeRegularSeasonStandingsComponent } from '../../shared/components/all-time-regular-season-standings/all-time-regular-season-standings';
import { AllTimeStandingsComponent } from '../../shared/components/all-time-standings/all-time-standings';
import { AwardLegendComponent } from '../../shared/components/award-legend/award-legend';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { LeagueLegacySummaryComponent } from '../../shared/components/league-legacy-summary/league-legacy-summary';
import { SeasonArchiveComponent } from '../../shared/components/season-archive/season-archive';
import { buildDetailedAwardLegend } from '../../shared/utils/award-legend-view.util';
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
    AllTimeStandingsComponent,
    AllTimeRegularSeasonStandingsComponent,
    AwardLegendComponent,
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
      const legacy = {
        ...buildLeagueLegacy(league, teams),
        awardLegend: buildDetailedAwardLegend(league)
      };

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
