import { ChangeDetectionStrategy, Component, Input, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';

import { FantasyTeam, Player } from '../services/data-service';
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export type PlayerListColumn =
  | 'rank'
  | 'picture'
  | 'name'
  | 'position'
  | 'team'
  | 'salary'
  | 'salaryProjected'
  | 'fantasyTeam'
  | 'marketStatus'
  | 'exclude';

@Component({
  selector: 'app-player-list',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports
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

  @Input() compact = false;
  @Input() lineNumber: number | null = null;
  @Input() team: FantasyTeam | null = null;

  @Input() projectedAbr = 'Proj.';
  @Input() showProjectedMarket = false;

  // Optional für TeamList-Exclude-Use-Case
  @Input() isExcludedFn?: (teamId: string, playerId: string) => boolean;
  @Input() isPlayerExcludableFn?: (player: Player, team: FantasyTeam | null) => boolean;
  @Input() toggleExcludeFn?: (teamId: string, playerId: string) => void;

  constructor(private dialog: MatDialog) {}

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
      return `${plus ? '+ ' : ''}$${(amount / 1_000_000).toFixed(afterPoint)} Mio.`;
    }

    return `- $${(-amount / 1_000_000).toFixed(afterPoint)} Mio.`;
  }

  getPositionColor(position: string): string {
    switch (position) {
      case 'WR': return '#337ccaff';
      case 'QB': return '#e24a4dff';
      case 'TE': return '#f28e2c';
      case 'K': return '#ab46bbff';
      case 'RB': return '#27998fff';
      case 'DEF': return '#999999';
      default: return '#555555';
    }
  }
}