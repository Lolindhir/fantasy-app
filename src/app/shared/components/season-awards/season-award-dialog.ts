import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import type { SeasonHistoryAwardItem } from '../../utils/league-standings-view.util';

/** Detail dialog for one dynamic Season Award. Purely presentational, data-driven. */
@Component({
  selector: 'app-season-award-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './season-award-dialog.html',
  styleUrl: './season-award-dialog.scss'
})
export class SeasonAwardDialogComponent {
  readonly award = inject<SeasonHistoryAwardItem>(MAT_DIALOG_DATA);

  /** The generated stat text separates its facts with " | "; show one fact per line. */
  readonly statLines: string[] = (this.award.statDisplay ?? '')
    .split('|')
    .map(part => part.trim())
    .filter(part => part.length > 0);
}
