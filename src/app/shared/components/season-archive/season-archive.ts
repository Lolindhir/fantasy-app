import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { SharedMaterialImports } from '../../shared-material-imports';
import type { SeasonHistoryViewModel } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-season-archive',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './season-archive.html',
  styleUrl: './season-archive.scss'
})
export class SeasonArchiveComponent {
  @Input({ required: true }) history: SeasonHistoryViewModel | null | undefined;
}
