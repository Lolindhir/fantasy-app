import { CommonModule } from '@angular/common';
import { Component, Injector, Input, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';
import { DataService } from '../../../core/services/data.service';

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

  private readonly dialog = inject(MatDialog);
  private readonly injector = inject(Injector);
  private readonly dataService = inject(DataService);
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
      // The detail dialog needs the fully enriched Player, never a partial display identity.
      const { players } = await firstValueFrom(this.dataService.getLeagueWithPlayers());
      const player = players.find(candidate => String(candidate.ID) === identity.id);
      if (!player) {
        this.playerOpenError = true;
        return;
      }
      const { PlayerDetailDialogComponent } = await import('../player-detail-dialog/player-detail-dialog');
      this.dialog.open(PlayerDetailDialogComponent, {
        data: player, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog'
      });
    } catch {
      this.playerOpenError = true;
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
