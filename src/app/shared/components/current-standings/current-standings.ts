import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PlayoffOddsPillComponent } from '../playoff-odds-pill/playoff-odds-pill';
import { PlayoffPlaceBarsComponent } from '../playoff-place-bars/playoff-place-bars';
import type { PlayoffOddsTeamView, PlayoffOddsView } from '../../utils/schedule-outlook-view.util';
import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';
import type { CurrentStandingRow } from '../../utils/league-standings-view.util';
import {
  standingCanonicalDelta,
  standingPlacementTrend,
  type StandingPlacementTrend,
  standingMovementLabel,
  standingMovementText,
  standingPlayoffCutline,
  recentStandingResults,
  recentStandingResultsLabel,
  type StandingRecentResult
} from './current-standings-display.util';

@Component({
  selector: 'app-current-standings',
  standalone: true,
  imports: [CommonModule, RouterLink, TeamIdentityComponent, PlayoffOddsPillComponent, PlayoffPlaceBarsComponent],
  templateUrl: './current-standings.html',
  styleUrl: './current-standings.scss'
})
export class CurrentStandingsComponent {
  @Input({ required: true }) standings: CurrentStandingRow[] | null | undefined;
  @Input() title = 'Current Standings';
  /** Keep the existing compact Overview presentation unchanged. */
  @Input() variant: 'compact' | 'detailed' = 'compact';
  @Input() playoffTeams: number | null = null;
  /** Generated playoff status per TeamID (Issue #1588); null while unavailable or after the regular season. */
  @Input() playoffOdds: PlayoffOddsView | null = null;

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

  playoffTeamOdds(row: CurrentStandingRow): PlayoffOddsTeamView | null {
    return this.playoffOdds?.teams.get(Number(row.team.TeamID)) ?? null;
  }

}
