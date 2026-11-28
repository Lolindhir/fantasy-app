import { CommonModule } from '@angular/common';
import { Component, DestroyRef, Injector, Input, inject } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PlayerDetailDialogService } from '../../services/player-detail-dialog.service';

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
  @Input() compact = false;
  @Input({ required: true }) highlights: readonly HallOfFameHighlight[] | null | undefined;

  private readonly injector = inject(Injector);
  private readonly playerDetail = inject(PlayerDetailDialogService);
  private readonly destroyRef = inject(DestroyRef);
  openingPlayerId: string | null = null;
  playerOpenError = false;
  readonly defaultTeamAvatar = DEFAULT_TEAM_AVATAR_SRC;
  readonly directWinnerLimit = 2;
  trackHighlight = (_: number, item: HallOfFameHighlight): string => item.key;
  trackPlayer = (_: number, item: HallOfFamePlayerIdentity): string => item.id;

  openTeam(item: HallOfFameHighlight): void {
    if (!item.team || !item.teamInteractive) return;
    this.openTeamId(item.team.TeamID);
  }

  openTeamId(teamId: number): void {
    // Match the existing on-demand dialog pattern; keep the display component out
    // of the eager Team Detail / Matchups dependency graph.
    void import('../../services/team-detail-dialog.service').then(({ TeamDetailDialogService }) =>
      this.injector.get(TeamDetailDialogService).open(teamId));
  }

  async openPlayer(identity: HallOfFamePlayerIdentity): Promise<void> {
    if (!identity.interactive || this.openingPlayerId !== null) return;
    this.openingPlayerId = identity.id;
    this.playerOpenError = false;
    try {
      const opened = await this.playerDetail.open(identity.id, () => !this.destroyRef.destroyed);
      if (!opened && !this.destroyRef.destroyed) this.playerOpenError = true;
    } catch {
      if (!this.destroyRef.destroyed) this.playerOpenError = true;
    } finally {
      this.openingPlayerId = null;
    }
  }

  valueMain(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ')[0];
  }

  valueCaption(item: HallOfFameHighlight): string {
    return item.valueDisplay.split(' ').slice(1).join(' ');
  }
}
