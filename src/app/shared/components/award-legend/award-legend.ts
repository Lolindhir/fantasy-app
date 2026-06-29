import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { SharedMaterialImports } from '../../shared-material-imports';
import type { AwardLegendItem } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-award-legend',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './award-legend.html',
  styleUrl: './award-legend.scss'
})
export class AwardLegendComponent {
  @Input({ required: true }) awards: AwardLegendItem[] | null | undefined;
}
