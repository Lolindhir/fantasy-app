import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { SeasonAwardDialogComponent } from './season-award-dialog';
import type { SeasonHistoryAwardItem } from '../../utils/league-standings-view.util';

/**
 * Uniform, purely data-driven cards for dynamic Season Awards.
 * Renders whatever awards it receives; it never branches on an award name or type.
 * Placement achievements (podium, Regular Season Champion plaque) are separate components.
 */
@Component({
  selector: 'app-season-awards',
  standalone: true,
  imports: [CommonModule, MatDialogModule],
  templateUrl: './season-awards.html',
  styleUrl: './season-awards.scss'
})
export class SeasonAwardsComponent {
  @Input() awards: SeasonHistoryAwardItem[] | null | undefined;
  @Input() title = 'Season Awards';

  private readonly dialog = inject(MatDialog);

  open(award: SeasonHistoryAwardItem): void {
    this.dialog.open(SeasonAwardDialogComponent, {
      data: award,
      width: '90vw',
      maxWidth: '360px',
      autoFocus: false
    });
  }

  trackAward(index: number, award: SeasonHistoryAwardItem): string {
    return `${award.key}:${award.owner}:${index}`;
  }
}
