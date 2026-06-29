import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { SharedMaterialImports } from '../../shared-material-imports';
import type { LeagueLegacyHighlight } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-league-legacy-summary',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './league-legacy-summary.html',
  styleUrl: './league-legacy-summary.scss'
})
export class LeagueLegacySummaryComponent {
  @Input({ required: true }) highlights: LeagueLegacyHighlight[] | null | undefined;
}
