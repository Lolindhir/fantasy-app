import { Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import { DataService } from '../../core/services/data.service';
import { TeamDetailDialogComponent } from '../components/team-detail-dialog/team-detail-dialog';

@Injectable({ providedIn: 'root' })
export class TeamDetailDialogService {
  constructor(
    private dataService: DataService,
    private dialog: MatDialog
  ) {}

  open(teamId: number): void {
    this.dataService.getLeagueWithPlayers(['Salary']).subscribe(({ league, players, teams, drafts }) => {
      const team = teams.find(candidate => candidate.TeamID === teamId);
      if (!team) return;

      this.dialog.open(TeamDetailDialogComponent, {
        data: { team, league, players, drafts },
        width: '95vw',
        maxWidth: '1000px',
        maxHeight: '90vh',
        panelClass: 'team-detail-dialog-panel',
        autoFocus: false
      });
    });
  }
}
