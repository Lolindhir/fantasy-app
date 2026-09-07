import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/player.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export type TeamLineupPlayerStatus = 'Starter' | 'Roster' | 'Taxi' | 'IR';

export interface TeamLineupPlayerRow {
  player: Player;
  statuses: TeamLineupPlayerStatus[];
}

export function getTeamLineupPlayerStatuses(
  player: Player,
  isStarter: boolean
): TeamLineupPlayerStatus[] {
  const fantasyTeam = player.TeamFantasy;
  const isTaxi = fantasyTeam?.Taxi.some(candidate => candidate.ID === player.ID) ?? false;
  const isIr = fantasyTeam?.Reserve.some(candidate => candidate.ID === player.ID) ?? false;
  const statuses: TeamLineupPlayerStatus[] = [];

  if (isStarter) statuses.push('Starter');
  if (isTaxi) statuses.push('Taxi');
  if (isIr) statuses.push('IR');
  if (!isStarter && !isTaxi && !isIr) statuses.push('Roster');

  return statuses;
}

@Component({
  selector: 'app-team-lineup-player-list',
  standalone: true,
  imports: [CommonModule, PositionStylePipe],
  templateUrl: './team-lineup-player-list.html',
  styleUrl: './team-lineup-player-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TeamLineupPlayerListComponent {
  @Input() rows: TeamLineupPlayerRow[] = [];

  constructor(private dialog: MatDialog) {}

  openPlayerDetail(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
