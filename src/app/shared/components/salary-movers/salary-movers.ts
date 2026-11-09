import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import type { Player } from '../../../core/models/fantasy.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import type { SalaryMover, SalaryMovers } from '../../utils/salary-movers.util';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

/** Largest projected-salary moves since the previous week; selection and change values come from the generator data. */
@Component({
  selector: 'app-salary-movers',
  standalone: true,
  imports: [CommonModule, PositionStylePipe],
  templateUrl: './salary-movers.html',
  styleUrl: './salary-movers.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SalaryMoversComponent {
  @Input({ required: true }) movers!: SalaryMovers;

  constructor(private readonly dialog: MatDialog) {}

  openPlayerDetail(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  formatChange(mover: SalaryMover): string {
    const absolute = Math.abs(mover.change);
    const text = absolute >= 1_000_000 ? `$${(absolute / 1_000_000).toFixed(1)}m` : `$${(absolute / 1_000).toFixed(0)}k`;
    return mover.change > 0 ? `+${text}` : `-${text}`;
  }

  formatSalary(value: number): string {
    return value >= 1_000_000 ? `$${(value / 1_000_000).toFixed(1)}m` : `$${(value / 1_000).toFixed(0)}k`;
  }
}
