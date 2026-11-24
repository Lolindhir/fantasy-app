import { NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { AchievementBannerComponent } from '../../shared/components/achievement-banner/achievement-banner';
import type { HallOfFameChampion } from '../../shared/utils/hall-of-fame-view.util';

export interface HallOfFameChampionDialogData {
  champion: HallOfFameChampion;
  emblemSrc: string;
  ringSrc: string;
}

/** Detail of one past league champion: banner, ring, season logo, team name and owner. Display only. */
@Component({
  selector: 'app-hall-of-fame-champion-dialog',
  standalone: true,
  imports: [NgIf, MatDialogModule, MatButtonModule, MatIconModule, AchievementBannerComponent],
  template: `
    <div class="champ-dialog">
      <button mat-icon-button mat-dialog-close cdkFocusInitial class="champ-dialog__close" aria-label="Close">
        <mat-icon>close</mat-icon>
      </button>
      <app-achievement-banner
        class="champ-dialog__banner"
        [season]="data.champion.season"
        achievementLabel="Champion"
        accent="gold"
        [subjectName]="data.champion.teamName"
        [subjectAvatar]="data.champion.teamAvatar"
        [secondaryAvatar]="data.champion.ownerAvatar"
        [emblemSrc]="data.emblemSrc"
        [achievementBadgeSrc]="data.champion.isRegularSeasonChampion ? 'assets/awards/ui/award-regular-season.png' : null"
      ></app-achievement-banner>
      <img class="champ-dialog__ring" [src]="data.ringSrc" [alt]="data.champion.season + ' championship ring'" />
      <span class="champ-dialog__owner">
        <img *ngIf="data.champion.ownerAvatar" class="champ-dialog__owner-avatar" [src]="data.champion.ownerAvatar" alt="" />
        {{ data.champion.owner }}
      </span>
    </div>
  `,
  styles: [`
    .champ-dialog { position: relative; display: grid; justify-items: center; gap: 10px; padding: 20px 20px 18px; max-height: 90vh; overflow-y: auto; }
    .champ-dialog__ring { width: 225px; height: 225px; object-fit: contain; }
    .champ-dialog__banner { width: 110px; }
    .champ-dialog__owner { display: inline-flex; align-items: center; gap: 8px; font-size: 1.05rem; font-weight: 600; color: #000; }
    .champ-dialog__owner-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
    .champ-dialog__close { position: absolute; top: 4px; right: 4px; }
  `]
})
export class HallOfFameChampionDialogComponent {
  readonly data = inject<HallOfFameChampionDialogData>(MAT_DIALOG_DATA);
}
