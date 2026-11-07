import { CommonModule } from '@angular/common';
import { Component, Input, TemplateRef, ViewChild, inject } from '@angular/core';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';

import type { FantasyTeam, League } from '../../../core/models/fantasy.models';
import {
  GENERIC_CHAMPIONSHIP_RING_SRC,
  buildTrophyRoom,
  type TrophyRoomRing,
  type TrophyRoomViewModel
} from '../../utils/championship.util';
import { AchievementBannerComponent } from '../achievement-banner/achievement-banner';
import { AchievementPlaqueComponent } from '../achievement-plaque/achievement-plaque';

/**
 * Trophy Room of one franchise (#662): rings = titles won (legacy), banners =
 * podium seasons (commemoration), plaques = Regular Season titles. Seasonal
 * identity (team name, avatars) is taken from that season's standings row.
 */
@Component({
  selector: 'app-trophy-room',
  standalone: true,
  imports: [CommonModule, MatDialogModule, AchievementBannerComponent, AchievementPlaqueComponent],
  templateUrl: './trophy-room.html',
  styleUrl: './trophy-room.scss'
})
export class TrophyRoomComponent {
  @Input({ required: true }) league!: Pick<League, 'Standings' | 'Season' | 'IsFinished'>;
  @Input({ required: true }) team!: Pick<FantasyTeam, 'TeamID'>;

  @ViewChild('ringDetail') private ringDetail?: TemplateRef<unknown>;

  private readonly dialog = inject(MatDialog);
  private dialogRef?: MatDialogRef<unknown>;
  private readonly failedRingSeasons = new Set<string>();

  selectedRing: TrophyRoomRing | null = null;

  get room(): TrophyRoomViewModel {
    return buildTrophyRoom(this.league, this.team);
  }

  get isEmpty(): boolean {
    const room = this.room;
    return !room.rings.length && !room.banners.length && !room.plaques.length;
  }

  ringSrc(ring: TrophyRoomRing): string {
    return this.failedRingSeasons.has(ring.season) ? GENERIC_CHAMPIONSHIP_RING_SRC : ring.ringSrc;
  }

  /** F15: a missing season-specific file falls back to the generic ring. */
  onRingError(ring: TrophyRoomRing): void {
    this.failedRingSeasons.add(ring.season);
  }

  openRing(ring: TrophyRoomRing): void {
    if (!this.ringDetail) return;
    this.selectedRing = ring;
    this.dialogRef = this.dialog.open(this.ringDetail, { panelClass: 'trophy-ring-dialog-panel', maxWidth: '92vw' });
  }

  closeRing(): void {
    this.dialogRef?.close();
  }
}
