import { CommonModule } from '@angular/common';
import { Component, Injector, Input, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';

import { GlyphComponent } from '../glyph/glyph';
import { DEFAULT_TEAM_AVATAR_SRC } from '../../utils/championship.util';
import type { HallOfFameHighlight, HallOfFamePlayerIdentity } from '../../utils/hall-of-fame-view.util';

@Component({
  selector: 'app-hall-of-fame',
  standalone: true,
  imports: [CommonModule, MatTooltipModule, GlyphComponent],
  templateUrl: './hall-of-fame.html',
  styleUrl: './hall-of-fame.scss'
})
export class HallOfFameComponent {
  @Input() heading = 'Hall of Fame';
  @Input() crest = '🏛️';
  @Input({ required: true }) highlights: readonly HallOfFameHighlight[] | null | undefined;

  private readonly dialog = inject(MatDialog);
  private readonly injector = inject(Injector);
  readonly defaultTeamAvatar = DEFAULT_TEAM_AVATAR_SRC;
  readonly previewCount = 2;
  trackHighlight = (_: number, item: HallOfFameHighlight): string => item.key;
  trackPlayer = (_: number, item: HallOfFamePlayerIdentity): string => item.id;

  openTeam(item: HallOfFameHighlight): void {
    if (!item.team || !item.teamInteractive) return;
    const teamId = item.team.TeamID;
    // Match the existing on-demand dialog pattern; keep the display component out
    // of the eager Team Detail / Matchups dependency graph.
    void import('../../services/team-detail-dialog.service').then(({ TeamDetailDialogService }) =>
      this.injector.get(TeamDetailDialogService).open(teamId));
  }

  openPlayer(identity: HallOfFamePlayerIdentity): void {
    const player = identity.player;
    if (!player) return;
    void import('../player-detail-dialog/player-detail-dialog').then(({ PlayerDetailDialogComponent }) =>
      this.dialog.open(PlayerDetailDialogComponent, {
        data: player, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog'
      }));
  }

  valueMain(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ')[0];
  }

  valueCaption(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ').slice(1).join(' ');
  }
}
