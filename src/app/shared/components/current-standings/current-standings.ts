import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { CurrentStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-current-standings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './current-standings.html',
  styleUrl: './current-standings.scss'
})
export class CurrentStandingsComponent {
  @Input({ required: true }) standings: CurrentStandingRow[] | null | undefined;
  @Input() title = 'Current Standings';
}
