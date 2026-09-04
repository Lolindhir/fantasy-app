import { ChangeDetectionStrategy, Component, Input, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';

import type { FantasyTeam, Player } from '../../../core/models/fantasy.models';
import { SharedMaterialImports } from '../../shared-material-imports';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { getPlayerDepthChartLabel } from '../../utils/player-sort.util';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export type PlayerListColumn =
  | 'rank'
  | 'picture'
  | 'name'
  | 'position'
  | 'team'
  | 'depth'
  | 'salary'
  | 'salaryProjected'
  | 'fantasyTeam'
  | 'marketStatus'
  | 'dynamicStat'
  | 'exclude';

@Component({
  selector: 'app-player-list',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports,
    PositionStylePipe
  ],
  templateUrl: './player-list.html',
  styleUrls: ['./player-list.scss'],
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PlayerListComponent {

  @Input() players: Player[] = [];

  @Input() columns: PlayerListColumn[] = [
    'rank',
    'picture',
    'name',
    'position',
    'team',
    'salary',
    'salaryProjected',
    'fantasyTeam'
  ];

  @Input() dynamicColumnHeader = '';
  @Input() dynamicColumnValueFn?: (player: Player) => string;

  @Input() compact = false;
  @Input() lineNumber: number | null = null;
  @Input() team: FantasyTeam | null = null;

  @Input() projectedAbr = 'Proj.';
  @Input() showProjectedMarket = false;
  @Input() showDepth = false;

  // Optional für TeamList-Exclude-Use-Case
  @Input() isExcludedFn?: (teamId: string, playerId: string) => boolean;
  @Input() isPlayerExcludableFn?: (player: Player, team: FantasyTeam | null) => boolean;
  @Input() toggleExcludeFn?: (teamId: string, playerId: string) => void;

  constructor(private dialog: MatDialog) {}

  get displayedColumns(): PlayerListColumn[] {
    if (!this.showDepth || this.columns.includes('depth')) {
      return this.columns;
    }

    const firstMetricIndex = this.columns.findIndex(column =>
      column === 'salary'
      || column === 'salaryProjected'
      || column === 'dynamicStat'
      || column === 'fantasyTeam'
      || column === 'marketStatus'
      || column === 'exclude'
    );

    if (firstMetricIndex === -1) {
      return [...this.columns, 'depth'];
    }

    return [
      ...this.columns.slice(0, firstMetricIndex),
      'depth',
      ...this.columns.slice(firstMetricIndex)
    ];
  }

  trackByPlayerId(index: number, player: Player): string {
    return player.ID;
  }

  openPlayerDetail(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  isExcluded(player: Player): boolean {
    if (!this.team || !this.isExcludedFn) {
      return false;
    }

    return this.isExcludedFn(String(this.team.TeamID), player.ID);
  }

  toggleExclude(player: Player): void {
    if (!this.team || !this.toggleExcludeFn) {
      return;
    }

    this.toggleExcludeFn(String(this.team.TeamID), player.ID);
  }

  isPlayerExcludable(player: Player): boolean {
    if (!this.isPlayerExcludableFn) {
      return true;
    }

    return this.isPlayerExcludableFn(player, this.team);
  }

  getDepthChartLabel(player: Player): string {
    return getPlayerDepthChartLabel(player) ?? '—';
  }

  getMarketText(player: Player): string {
    const info = this.showProjectedMarket
      ? player.FreeAgentMarketInfoProjected
      : player.FreeAgentMarketInfo;

    switch (info?.Status) {
      case 'FreeAgent':
        return 'FA';
      case 'ProjectedCapCut':
        return 'Cap Cut';
      case 'PossibleCapCut':
        return 'Possible';
      case 'Rostered':
      default:
        return 'Rostered';
    }
  }

  getMarketTooltip(player: Player): string {
    const info = this.showProjectedMarket
      ? player.FreeAgentMarketInfoProjected
      : player.FreeAgentMarketInfo;

    return info?.Reason ?? '';
  }

  formatSalaryDollars(amount: number, plus: boolean, afterPoint: number): string {
    if (amount >= 0) {
      return (plus ? '+ ' : '') + '$' + (amount / 1_000_000).toFixed(afterPoint) + ' Mio.';
    }

    return '- $' + (-amount / 1_000_000).toFixed(afterPoint) + ' Mio.';
  }

  getDynamicColumnValue(player: Player): string {
    if (!this.dynamicColumnValueFn) {
      return '';
    }

    return this.dynamicColumnValueFn(player);
  }
}
