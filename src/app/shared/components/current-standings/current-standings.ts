import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';
import type { SeasonStatisticsTeam } from '../../../core/models/season-statistics.models';
import { formatAllPlay, formatDecimal, formatExpectedRecord, formatSigned, signClass } from '../../utils/season-statistics-view.util';
import type { CurrentStandingRow } from '../../utils/league-standings-view.util';
import {
  standingCanonicalDelta,
  standingPlacementTrend,
  type StandingPlacementTrend,
  standingMovementLabel,
  standingMovementText,
  standingPerGame,
  standingPlayoffCutline,
  standingPointDifferential,
  recentStandingResults,
  recentStandingResultsLabel,
  type StandingRecentResult
} from './current-standings-display.util';

@Component({
  selector: 'app-current-standings',
  standalone: true,
  imports: [CommonModule, TeamIdentityComponent],
  templateUrl: './current-standings.html',
  styleUrl: './current-standings.scss'
})
export class CurrentStandingsComponent {
  @Input({ required: true }) standings: CurrentStandingRow[] | null | undefined;
  @Input() title = 'Current Standings';
  /** Keep the existing compact Overview presentation unchanged. */
  @Input() variant: 'compact' | 'detailed' = 'compact';
  @Input() playoffTeams: number | null = null;
  /** Generated season statistics by TeamID (Issue #506); absent while loading or unavailable. */
  @Input() statistics: ReadonlyMap<string, SeasonStatisticsTeam> | null = null;

  expandedTeamId: number | null = null;

  readonly mobileTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr', 'owner'];
  readonly desktopTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name', 'owner'];
  readonly detailedTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name'];

  formatRecord(row: CurrentStandingRow): string {
    const { Wins: wins, Losses: losses, Ties: ties } = row.team;
    return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
  }

  toggleDetails(teamId: number): void {
    this.expandedTeamId = this.expandedTeamId === teamId ? null : teamId;
  }

  isPlayoffCutline(row: CurrentStandingRow): boolean {
    return standingPlayoffCutline(row, this.playoffTeams, this.standings?.length ?? 0);
  }

  placeDelta(row: CurrentStandingRow): number | null {
    return standingCanonicalDelta(row);
  }

  movementText(row: CurrentStandingRow): string {
    return standingMovementText(row);
  }

  movementLabel(row: CurrentStandingRow): string {
    return standingMovementLabel(row);
  }

  recentResults(row: CurrentStandingRow): StandingRecentResult[] {
    return recentStandingResults(row);
  }

  recentResultsLabel(results: readonly StandingRecentResult[]): string {
    return recentStandingResultsLabel(results);
  }

  placementTrend(row: CurrentStandingRow, teamCount: number): StandingPlacementTrend | null {
    return standingPlacementTrend(row, teamCount);
  }

  pointDifferential(row: CurrentStandingRow): number {
    return standingPointDifferential(row);
  }

  pointsPerGame(row: CurrentStandingRow): number | null {
    return standingPerGame(row, row.team.Points);
  }

  pointsAgainstPerGame(row: CurrentStandingRow): number | null {
    return standingPerGame(row, row.team.PointsAgainst);
  }

  teamStatistics(row: CurrentStandingRow): SeasonStatisticsTeam | null {
    const stats = this.statistics?.get(String(row.team.TeamID)) ?? null;
    return stats && stats.Games > 0 ? stats : null;
  }

  readonly formatSigned = formatSigned;
  readonly formatDecimal = formatDecimal;
  readonly formatExpectedRecord = formatExpectedRecord;
  readonly formatAllPlay = formatAllPlay;
  readonly signClass = signClass;
}
