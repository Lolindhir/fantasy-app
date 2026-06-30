import { Component, Input } from '@angular/core';

import {
  RegularSeasonStandingsListComponent,
  type RegularSeasonStandingListRow
} from '../regular-season-standings-list/regular-season-standings-list';
import type { AllTimeRegularSeasonStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-all-time-regular-season-standings',
  standalone: true,
  imports: [RegularSeasonStandingsListComponent],
  templateUrl: './all-time-regular-season-standings.html',
  styleUrl: './all-time-regular-season-standings.scss'
})
export class AllTimeRegularSeasonStandingsComponent {
  @Input({ required: true }) standings: AllTimeRegularSeasonStandingRow[] | null | undefined;
  @Input() title = 'All-Time Regular Season';
  @Input() showTitle = true;

  regularSeasonRows(): RegularSeasonStandingListRow[] | null | undefined {
    return this.standings?.map(row => ({
      place: row.place,
      owner: row.owner,
      record: row.record,
      points: row.points,
      pointsAgainst: row.pointsAgainst,
      winPercentageDisplay: row.winPercentageDisplay,
      winPercentage: row.team.Placements.AllTime.Regular.WinPercentage
    }));
  }
}
