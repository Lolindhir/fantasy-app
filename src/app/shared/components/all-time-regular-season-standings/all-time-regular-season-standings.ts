import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { AllTimeRegularSeasonStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-all-time-regular-season-standings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './all-time-regular-season-standings.html',
  styleUrl: './all-time-regular-season-standings.scss'
})
export class AllTimeRegularSeasonStandingsComponent {
  @Input({ required: true }) standings: AllTimeRegularSeasonStandingRow[] | null | undefined;
  @Input() title = 'All-Time Regular Season';
}
