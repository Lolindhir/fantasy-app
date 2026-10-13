import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { SeasonResultsViewModel } from '../../utils/league-standings-view.util';
import { FitTextDirective } from '../../directives/fit-text.directive';
import { AchievementBannerComponent } from '../achievement-banner/achievement-banner';
import { AchievementPlaqueComponent } from '../achievement-plaque/achievement-plaque';
import { StandingRankBadgeComponent } from '../standing-rank-badge/standing-rank-badge';

@Component({
  selector: 'app-season-results',
  standalone: true,
  imports: [CommonModule, FitTextDirective, AchievementBannerComponent, AchievementPlaqueComponent, StandingRankBadgeComponent],
  templateUrl: './season-results.html',
  styleUrl: './season-results.scss'
})
export class SeasonResultsComponent {
  @Input({ required: true }) results!: SeasonResultsViewModel | null | undefined;
  @Input() title = 'Season Results';
  @Input() showTitle = true;
  @Input() bannerSeason: string | number | null = null;
}
