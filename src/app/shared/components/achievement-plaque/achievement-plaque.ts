import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { FitTextDirective } from '../../directives/fit-text.directive';

@Component({
  selector: 'app-achievement-plaque',
  standalone: true,
  imports: [CommonModule, FitTextDirective],
  templateUrl: './achievement-plaque.html',
  styleUrl: './achievement-plaque.scss'
})
export class AchievementPlaqueComponent {
  @Input({ required: true }) season!: string | number;
  @Input() achievementLabel = 'Regular Season Champion';
  @Input({ required: true }) subjectName!: string;
  @Input() subjectAvatar: string | null | undefined;
  @Input() secondaryAvatar: string | null | undefined;
  @Input() emblemSrc = 'assets/awards/ui/award-regular-season.png';
}
