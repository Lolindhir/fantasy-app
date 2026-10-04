import { Component, Input } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';

import type { MatchupRangeView } from '../../utils/projection-range.util';

@Component({
  selector: 'app-matchup-range-chart',
  standalone: true,
  imports: [NgFor, NgIf],
  templateUrl: './matchup-range-chart.html',
  styleUrl: './matchup-range-chart.scss'
})
export class MatchupRangeChartComponent {
  @Input({ required: true }) view!: MatchupRangeView;
}
