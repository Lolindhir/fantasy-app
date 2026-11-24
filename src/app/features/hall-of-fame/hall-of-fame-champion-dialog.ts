import { NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';

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
  imports: [NgIf, MatDialogModule, AchievementBannerComponent],
  template: `
    <div class="champ-dialog" mat-dialog-content>
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
    <div mat-dialog-actions align="end">
      <button type="button" class="champ-dialog__close" mat-dialog-close cdkFocusInitial>Close</button>
    </div>
  `,
  styles: [`
    .champ-dialog { display: grid; justify-items: center; gap: 12px; padding-top: 12px; }
    .champ-dialog__ring { width: 180px; height: 180px; object-fit: contain; }
    .champ-dialog__banner { width: 110px; }
    .champ-dialog__owner { display: inline-flex; align-items: center; gap: 8px; font-size: 1.05rem; font-weight: 600; color: #000; }
    .champ-dialog__owner-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
    .champ-dialog__close { padding: 6px 14px; border: 1px solid rgba(148,163,184,.5); border-radius: 8px; background: #fff; cursor: pointer; font: inherit; }
  `]
})
export class HallOfFameChampionDialogComponent {
  readonly data = inject<HallOfFameChampionDialogData>(MAT_DIALOG_DATA);
}
