import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { FantasyTeam } from '../../../core/models/league.models';
import type { SeasonStatisticsTeam } from '../../../core/models/season-statistics.models';
import { formatAllPlay, formatDecimal, formatExpectedRecord, formatSigned, signClass } from '../../utils/season-statistics-view.util';
import type { SeasonHistoryRegularSeasonRow } from '../../utils/league-standings-view.util';
import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';

/** Expandable regular-season table of an archived season; reuses the Current Standings look (Issue #506). */
@Component({
  selector: 'app-season-standings-table',
  standalone: true,
  imports: [CommonModule, TeamIdentityComponent],
  templateUrl: './season-standings-table.html',
  styleUrls: ['../current-standings/current-standings.scss', './season-standings-table.scss']
})
export class SeasonStandingsTableComponent {
  @Input({ required: true }) standings: readonly SeasonHistoryRegularSeasonRow[] | null | undefined;
  @Input() title = 'Regular Season Standings';
  /** Current teams for logo and name, joined by TeamID. */
  @Input() teams: readonly FantasyTeam[] | null | undefined;
  /** Season statistics by TeamID; absent when the season has none. */
  @Input() statistics: ReadonlyMap<string, SeasonStatisticsTeam> | null | undefined;
  @Input() idPrefix = 'season';

  expandedTeamId: string | null = null;

  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'name'];
  readonly formatSigned = formatSigned;
  readonly formatDecimal = formatDecimal;
  readonly formatExpectedRecord = formatExpectedRecord;
  readonly formatAllPlay = formatAllPlay;
  readonly signClass = signClass;

  team(row: SeasonHistoryRegularSeasonRow): FantasyTeam | undefined {
    return this.teams?.find(team => String(team.TeamID) === String(row.teamId));
  }

  stats(row: SeasonHistoryRegularSeasonRow): SeasonStatisticsTeam | null {
    const stats = this.statistics?.get(String(row.teamId)) ?? null;
    return stats && stats.Games > 0 ? stats : null;
  }

  toggle(row: SeasonHistoryRegularSeasonRow): void {
    const id = String(row.teamId);
    this.expandedTeamId = this.expandedTeamId === id ? null : id;
  }

  isExpanded(row: SeasonHistoryRegularSeasonRow): boolean {
    return this.expandedTeamId === String(row.teamId);
  }

  pointDifferential(row: SeasonHistoryRegularSeasonRow): number | null {
    return row.points === null || row.pointsAgainst === null ? null : row.points - row.pointsAgainst;
  }

  perGame(row: SeasonHistoryRegularSeasonRow, value: number | null): number | null {
    const games = this.stats(row)?.Games;
    return value === null || !games ? null : value / games;
  }
}
