import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { SeasonResultsViewModel } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-season-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './season-results.html',
  styleUrl: './season-results.scss'
})
export class SeasonResultsComponent {
  @Input({ required: true }) results!: SeasonResultsViewModel | null | undefined;
  @Input() title = 'Season Results';
  @Input() showTitle = true;

  placeEmoji(place: number): string {
    switch (place) {
      case 1: return '🏆';
      case 2: return '🥈';
      case 3: return '🥉';
      case 4: return '4️⃣';
      case 5: return '5️⃣';
      case 6: return '6️⃣';
      case 7: return '7️⃣';
      case 8: return '8️⃣';
      case 9: return '9️⃣';
      case 10: return '🔟';
      default:
        return place.toString();
    }
  }
}
