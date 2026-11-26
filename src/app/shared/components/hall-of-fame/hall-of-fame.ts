import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';

import { GlyphComponent } from '../glyph/glyph';
import { TeamIdentityComponent } from '../team-identity/team-identity';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import type { HallOfFameHighlight, HallOfFamePlayerIdentity } from '../../utils/hall-of-fame-view.util';

@Component({
  selector: 'app-hall-of-fame',
  standalone: true,
  imports: [CommonModule, MatTooltipModule, GlyphComponent, TeamIdentityComponent],
  templateUrl: './hall-of-fame.html',
  styleUrl: './hall-of-fame.scss'
})
export class HallOfFameComponent {
  @Input() heading = 'Hall of Fame';
  @Input() crest = '🏛️';
  @Input({ required: true }) highlights: readonly HallOfFameHighlight[] | null | undefined;

  private readonly dialog = inject(MatDialog);
  private readonly teamDetails = inject(TeamDetailDialogService);
  readonly previewCount = 2;
  trackHighlight = (_: number, item: HallOfFameHighlight): string => item.key;
  trackPlayer = (_: number, item: HallOfFamePlayerIdentity): string => item.id;

  openTeam(item: HallOfFameHighlight): void {
    if (item.team && item.teamInteractive) this.teamDetails.open(item.team.TeamID);
  }

  openPlayer(identity: HallOfFamePlayerIdentity): void {
    if (identity.player) this.dialog.open(PlayerDetailDialogComponent, {
      data: identity.player, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog'
    });
  }

  valueMain(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ')[0];
  }

  valueCaption(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ').slice(1).join(' ');
  }
}
