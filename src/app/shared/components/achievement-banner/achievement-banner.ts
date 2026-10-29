import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { FitTextDirective } from '../../directives/fit-text.directive';

export type AchievementBannerAccent = 'gold' | 'silver' | 'bronze';

@Component({
  selector: 'app-achievement-banner',
  standalone: true,
  imports: [CommonModule, FitTextDirective],
  templateUrl: './achievement-banner.html',
  styleUrl: './achievement-banner.scss'
})
export class AchievementBannerComponent {
  @Input() season: string | number | null = null;
  @Input({ required: true }) achievementLabel!: string;
  @Input({ required: true }) subjectName!: string;
  @Input() subjectAvatar: string | null | undefined;
  @Input() secondaryAvatar: string | null | undefined;
  @Input({ required: true }) emblemSrc!: string;
  @Input() accent: AchievementBannerAccent = 'silver';
  @Input() achievementBadgeSrc: string | null = null;
}
