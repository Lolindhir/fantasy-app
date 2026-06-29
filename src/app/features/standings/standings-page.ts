import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import { DataService } from '../../core/services/data.service';
import { AllTimeStandingsComponent } from '../../shared/components/all-time-standings/all-time-standings';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { SeasonResultsComponent } from '../../shared/components/season-results/season-results';
import {
  buildAllTimeStandings,
  buildCurrentStandings,
  buildSeasonResults
} from '../../shared/utils/league-standings-view.util';

@Component({
  selector: 'app-standings-page',
  standalone: true,
  imports: [
    CommonModule,
    CurrentStandingsComponent,
    SeasonResultsComponent,
    AllTimeStandingsComponent
  ],
  templateUrl: './standings-page.html',
  styleUrl: './standings-page.scss'
})
export class StandingsPageComponent {
  private dataService = inject(DataService);

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams }) => ({
      league,
      currentStandings: buildCurrentStandings(league, teams),
      seasonResults: buildSeasonResults(teams),
      allTimeStandings: buildAllTimeStandings(teams)
    }))
  );
}
