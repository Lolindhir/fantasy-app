import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import { DataService } from '../../core/services/data.service';
import { AllTimeRegularSeasonStandingsComponent } from '../../shared/components/all-time-regular-season-standings/all-time-regular-season-standings';
import { AllTimeStandingsComponent } from '../../shared/components/all-time-standings/all-time-standings';
import { AwardLegendComponent } from '../../shared/components/award-legend/award-legend';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { LeagueLegacySummaryComponent } from '../../shared/components/league-legacy-summary/league-legacy-summary';
import { SeasonResultsComponent } from '../../shared/components/season-results/season-results';
import {
  buildCurrentStandings,
  buildLeagueLegacy,
  buildSeasonResults
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
    SeasonResultsComponent
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
        seasonResults: buildSeasonResults(teams)
      };
    })
  );
}
