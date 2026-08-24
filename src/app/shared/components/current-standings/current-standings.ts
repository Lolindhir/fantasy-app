import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';

import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
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

  private teamDetailDialog = inject(TeamDetailDialogService);

  openTeam(teamId: number): void {
    this.teamDetailDialog.open(teamId);
  }
}
