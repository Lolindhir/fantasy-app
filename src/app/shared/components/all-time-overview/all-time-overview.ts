import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { AllTimeRegularSeasonStandingsComponent } from '../all-time-regular-season-standings/all-time-regular-season-standings';
import { AllTimeStandingsComponent } from '../all-time-standings/all-time-standings';
import type {
  AllTimeRegularSeasonStandingRow,
  AllTimeStandingRow
} from '../../utils/league-standings-view.util';

type AllTimeTab = 'overall' | 'regularSeason';

@Component({
  selector: 'app-all-time-overview',
  standalone: true,
  imports: [
    CommonModule,
    AllTimeStandingsComponent,
    AllTimeRegularSeasonStandingsComponent
  ],
  templateUrl: './all-time-overview.html',
  styleUrl: './all-time-overview.scss'
})
export class AllTimeOverviewComponent {
  @Input({ required: true }) overallStandings: AllTimeStandingRow[] | null | undefined;
  @Input({ required: true }) regularSeasonStandings: AllTimeRegularSeasonStandingRow[] | null | undefined;

  activeTab: AllTimeTab = 'overall';

  selectTab(tab: AllTimeTab): void {
    this.activeTab = tab;
  }
}
