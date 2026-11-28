import { CommonModule } from '@angular/common';
import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, map, of, switchMap } from 'rxjs';
import { DataService } from '../../../../core/services/data.service';
import { PlayerDetailDialogService } from '../../../../shared/services/player-detail-dialog.service';
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
  private readonly playerDetail = inject(PlayerDetailDialogService);
  private readonly destroyRef = inject(DestroyRef);
  readonly openingPlayerId = signal<string | null>(null);
  readonly playerOpenError = signal(false);

  readonly allTime = ALL_TIME;
  readonly columns = AWARD_COLUMNS;
  readonly selected = signal<string>(ALL_TIME);
  readonly expanded = signal(false);

  /** undefined while loading, null when the award file is unavailable. */
  private readonly base = toSignal(
    this.dataService.getPlayerAwardHistory().pipe(
      switchMap(history => {
        if (!history) return of({ view: null });
        const ids = [...new Set([
          ...history.Players.filter(player => player.Total > 0).map(player => player.PlayerID),
          ...history.Seasons.flatMap(season => (season.Players ?? []).map(player => player.PlayerID))
        ])];
        return this.dataService.getPlayerIdentitySummaries(ids).pipe(
          catchError(() => of([])),
          map(players => ({ view: buildPlayerAwardsView(history, players) }))
        );
      }),
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

  async openPlayer(row: PlayerAwardRow): Promise<void> {
    if (!row.interactive || this.openingPlayerId() !== null) return;
    this.openingPlayerId.set(row.playerId);
    this.playerOpenError.set(false);
    try {
      const opened = await this.playerDetail.open(row.playerId, () => !this.destroyRef.destroyed);
      if (!opened && !this.destroyRef.destroyed) this.playerOpenError.set(true);
    } catch {
      if (!this.destroyRef.destroyed) this.playerOpenError.set(true);
    } finally {
      this.openingPlayerId.set(null);
    }
  }

  trackRow = (_: number, row: PlayerAwardRow): string => row.playerId;
}
