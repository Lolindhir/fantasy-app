import { Component, Input } from '@angular/core';

import type { PlayerRangeBarView } from '../../utils/projection-range.util';

@Component({
  selector: 'app-range-whisker',
  standalone: true,
  templateUrl: './range-whisker.html',
  styleUrl: './range-whisker.scss'
})
export class RangeWhiskerComponent {
  @Input({ required: true }) bar!: PlayerRangeBarView;
}
