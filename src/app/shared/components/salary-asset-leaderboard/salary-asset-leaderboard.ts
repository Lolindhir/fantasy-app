import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/fantasy.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export type SalaryAssetLens = 'current' | 'projected';

@Component({
  selector: 'app-salary-asset-leaderboard',
  standalone: true,
  imports: [CommonModule, PositionStylePipe],
  templateUrl: './salary-asset-leaderboard.html',
  styleUrl: './salary-asset-leaderboard.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SalaryAssetLeaderboardComponent {
  @Input() players: Player[] = [];
  @Input() lens: SalaryAssetLens = 'current';
  @Input() cap = 0;

  constructor(private readonly dialog: MatDialog) {}

  openPlayerDetail(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  primarySalary(player: Player): number {
    return this.lens === 'current' ? player.Salary : player.SalaryProjected;
  }

  comparisonSalary(player: Player): number {
    return this.lens === 'current' ? player.SalaryProjected : player.Salary;
  }

  comparisonLabel(): string {
    return this.lens === 'current' ? 'Projected' : 'Current';
  }

  projectedDelta(player: Player): number {
    return player.SalaryProjected - player.Salary;
  }

  capShare(player: Player): string {
    if (this.cap <= 0) return '—';
    return `${((this.primarySalary(player) / this.cap) * 100).toFixed(1)}% of cap`;
  }

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    const prefix = value < 0 ? '-' : '';
    if (absolute >= 1_000_000) return `${prefix}$${(absolute / 1_000_000).toFixed(1)}m`;
    if (absolute >= 1_000) return `${prefix}$${(absolute / 1_000).toFixed(1)}k`;
    return `${prefix}$${absolute.toFixed(0)}`;
  }

  formatDelta(value: number): string {
    if (value > 0) return `+${this.formatMoney(value)}`;
    return this.formatMoney(value);
  }
}
