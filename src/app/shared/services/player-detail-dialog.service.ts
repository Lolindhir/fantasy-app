import { Injectable, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';

import { DataService } from '../../core/services/data.service';

/** On-demand detail opening for lightweight identity consumers; no cross-page cache. */
@Injectable({ providedIn: 'root' })
export class PlayerDetailDialogService {
  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);

  async open(playerId: string, isActive: () => boolean): Promise<boolean> {
    const { players } = await firstValueFrom(this.dataService.getLeagueWithPlayers());
    const player = players.find(candidate => String(candidate.ID) === playerId);
    if (!player || !isActive()) return false;
    const { PlayerDetailDialogComponent } = await import('../components/player-detail-dialog/player-detail-dialog');
    if (!isActive()) return false;
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog'
    });
    return true;
  }
}
