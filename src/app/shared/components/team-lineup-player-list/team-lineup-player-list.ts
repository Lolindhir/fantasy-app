import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/player.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export type TeamLineupPlayerRole = 'Starter' | 'Roster';

export interface TeamLineupPlayerRow {
  player: Player;
  role: TeamLineupPlayerRole;
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
