import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input, OnChanges, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import type { FantasyTeam, Player } from '../../../core/models/fantasy.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { PlayerPicturePipe } from '../../pipes/player-picture.pipe';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { SharedMaterialImports } from '../../shared-material-imports';
import {
  buildTeamInjuryReport,
  type InjuryReportMode,
  type InjuryKind,
  type InjuryReportRow
} from '../../utils/team-injury-report.util';
import type { RosterNextLockContext } from '../../utils/team-roster-view.util';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

interface InjurySummaryChip {
  kind: InjuryKind;
  label: string;
  count: number;
}

/** Collapsible injury overview of one fantasy team: presentation of Players.json injury data only. */
@Component({
  selector: 'app-team-injury-report',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports, PlayerPicturePipe, PositionStylePipe],
  templateUrl: './team-injury-report.html',
  styleUrl: './team-injury-report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TeamInjuryReportComponent implements OnChanges {
  private readonly dialog = inject(MatDialog);

  @Input({ required: true }) team!: FantasyTeam;
  /** roster: whole roster by designation; lineup: starters of the current week only. */
  @Input() mode: InjuryReportMode = 'roster';
  /** Starters of the current lineup week; only passed while the lineup phase is active. */
  @Input() starterIds: ReadonlySet<string> | null = null;
  @Input() lockContext?: RosterNextLockContext;

  expanded = false;

  rows: InjuryReportRow[] = [];
  summary: InjurySummaryChip[] = [];

  ngOnChanges(): void {
    this.rows = buildTeamInjuryReport(this.team, { mode: this.mode, starterIds: this.starterIds, lockContext: this.lockContext });
    const counts = new Map<InjuryKind, InjurySummaryChip>();
    for (const row of this.rows) {
      const chip = counts.get(row.kind) ?? { kind: row.kind, label: row.label, count: 0 };
      chip.count += 1;
      counts.set(row.kind, chip);
    }
    this.summary = [...counts.values()];
  }

  toggle(): void {
    this.expanded = !this.expanded;
  }

  placementLabel(row: InjuryReportRow): string | null {
    switch (row.placement) {
      case 'ir': return 'IR slot';
      case 'taxi': return 'Taxi';
      default: return null;
    }
  }

  /** Free agents without an NFL team have no logo. */
  nflLogo(player: Player): string | null {
    return (player.TeamNFL as NFLTeam | undefined)?.Logo || null;
  }

  trackRow(_: number, row: InjuryReportRow): string {
    return row.player.ID;
  }

  openPlayer(player: Player): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
