import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { SeasonHistoryRegularSeasonRow } from '../../utils/league-standings-view.util';
import { TeamIdentityComponent, type TeamIdentityElement, type TeamIdentitySubject } from '../team-identity/team-identity';

/**
 * Regular-season table of an archived season; reuses the Current Standings look.
 * Display only: every value comes from the league-standings product, nothing is derived here.
 */
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

  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'name'];

  /** Season-specific identity (name, owner, logo of that season), never the current team. */
  identity(row: SeasonHistoryRegularSeasonRow): TeamIdentitySubject {
    return {
      TeamID: Number(row.teamId),
      Team: row.teamName ?? '',
      Owner: row.owner,
      Avatar: row.teamAvatar || 'assets/default-team-avatar.png'
    };
  }
}
