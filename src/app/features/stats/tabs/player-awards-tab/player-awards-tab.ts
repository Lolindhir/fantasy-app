import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatDialog } from '@angular/material/dialog';
import { catchError, forkJoin, map, of } from 'rxjs';

import type { Player } from '../../../../core/models/player.models';
import { DataService } from '../../../../core/services/data.service';
import { PlayerDetailDialogComponent } from '../../../../shared/components/player-detail-dialog/player-detail-dialog';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import { ALL_TIME, AWARD_COLUMNS, buildPlayerAwardsView, type PlayerAwardRow } from './player-awards-view.util';

const INITIAL_ROWS = 15;

/** Stats > Player Awards: weekly player awards per player, all-time or per season (Issue #1621). Display only; the generator ranks and counts. */
@Component({
  selector: 'app-stats-player-awards-tab',
  standalone: true,
  imports: [CommonModule, PositionStylePipe],
  templateUrl: './player-awards-tab.html',
  styleUrl: './player-awards-tab.scss'
})
export class PlayerAwardsTabComponent {
  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);

  readonly allTime = ALL_TIME;
  readonly columns = AWARD_COLUMNS;
  readonly selected = signal<string>(ALL_TIME);
  readonly expanded = signal(false);

  /** undefined while loading, null when the award file is unavailable. */
  private readonly base = toSignal(
    forkJoin({
      data: this.dataService.getLeagueWithPlayers(),
      history: this.dataService.getPlayerAwardHistory()
    }).pipe(
      map(({ data, history }) => ({ view: history ? buildPlayerAwardsView(history, data.players) : null })),
      catchError(() => of(null))
    ),
    { initialValue: undefined }
  );

  readonly ready = computed(() => this.base());
  readonly seasons = computed(() => this.base()?.view?.seasons ?? []);

  readonly rows = computed<PlayerAwardRow[]>(() => this.base()?.view?.rows(this.selected()) ?? []);
  readonly visibleRows = computed(() => (this.expanded() ? this.rows() : this.rows().slice(0, INITIAL_ROWS)));
  readonly hiddenCount = computed(() => Math.max(0, this.rows().length - INITIAL_ROWS));

  selectSeason(value: string): void {
    this.selected.set(value);
    this.expanded.set(false);
  }

  toggleExpanded(): void {
    this.expanded.update(value => !value);
  }

  openPlayer(player: Player | null): void {
    if (!player) return;
    this.dialog.open(PlayerDetailDialogComponent, { data: player, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog' });
  }

  trackRow = (_: number, row: PlayerAwardRow): string => row.playerId;
}
