import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';
import type { CurrentStandingRow } from '../../utils/league-standings-view.util';

export interface StandingRecentResult {
  week: number;
  result: 'W' | 'L' | 'T';
}

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

  expandedTeamId: number | null = null;

  readonly mobileTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr', 'owner'];
  readonly desktopTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name', 'owner'];
  readonly detailedTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name', 'owner'];

  formatRecord(row: CurrentStandingRow): string {
    const { Wins: wins, Losses: losses, Ties: ties } = row.team;
    return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
  }

  toggleDetails(teamId: number): void {
    this.expandedTeamId = this.expandedTeamId === teamId ? null : teamId;
  }

  isPlayoffCutline(row: CurrentStandingRow): boolean {
    return this.playoffTeams !== null
      && Number.isInteger(this.playoffTeams)
      && this.playoffTeams > 0
      && this.playoffTeams < (this.standings?.length ?? 0)
      && row.displayPlace === this.playoffTeams + 1;
  }

  /** Never reconstruct the official ranking. Only display matching canonical movement. */
  placeDelta(row: CurrentStandingRow): number | null {
    const regular = row.team.Placements?.Current?.Regular;
    if (!regular || regular.Place !== row.displayPlace) return null;
    const delta = regular.PlaceDelta;
    return typeof delta === 'number' && Number.isFinite(delta) ? delta : null;
  }

  movementText(row: CurrentStandingRow): string {
    const delta = this.placeDelta(row);
    if (delta === null || delta === 0) return '—';
    return delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`;
  }

  movementLabel(row: CurrentStandingRow): string {
    const delta = this.placeDelta(row);
    if (delta === null) return 'No previous week available';
    if (delta === 0) return 'No change since last week';
    const magnitude = Math.abs(delta);
    return `Moved ${delta > 0 ? 'up' : 'down'} ${magnitude} ${magnitude === 1 ? 'place' : 'places'} since last week`;
  }

  /**
   * Current-season generator Record contains one W/L/T character per completed
   * regular-season game, ordered oldest to newest. The length/summary guard
   * avoids presenting stale or partial data as trustworthy results.
   */
  recentResults(row: CurrentStandingRow): StandingRecentResult[] {
    const regular = row.team.Placements?.Current?.Regular;
    if (!regular || typeof regular.Record !== 'string') return [];
    const record = regular.Record;
    const expected = regular.Wins + regular.Losses + regular.Ties;
    if (!/^[WLT]*$/.test(record) || !Number.isInteger(expected) || record.length !== expected) return [];

    const start = Math.max(0, record.length - 5);
    return [...record.slice(start)].map((result, index) => ({
      week: start + index + 1,
      result: result as StandingRecentResult['result']
    }));
  }

  recentResultsLabel(results: readonly StandingRecentResult[]): string {
    const descriptions = { W: 'win', L: 'loss', T: 'tie' };
    return `Last ${results.length} completed games: ${results.map(item =>
      `week ${item.week} ${descriptions[item.result]}`
    ).join(', ')}`;
  }

  pointDifferential(row: CurrentStandingRow): number {
    return row.team.Points - row.team.PointsAgainst;
  }

  pointsPerGame(row: CurrentStandingRow): number | null {
    return this.perGame(row, row.team.Points);
  }

  pointsAgainstPerGame(row: CurrentStandingRow): number | null {
    return this.perGame(row, row.team.PointsAgainst);
  }

  private perGame(row: CurrentStandingRow, points: number): number | null {
    const games = row.team.Wins + row.team.Losses + row.team.Ties;
    return games > 0 && Number.isFinite(points) ? points / games : null;
  }
}
