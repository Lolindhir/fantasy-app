import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import type {
  DecisionWindow,
  DecisionWindowsReadModel
} from '../../../core/models/decision-window.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import {
  formatDecisionWindowCountdown,
  formatDecisionWindowsUpdatedAt
} from '../../utils/decision-window-view.util';
import {
  buildTeamLineupHealthView,
  buildTeamLineupWeekSummary,
  buildTeamUpcomingLockViews,
  formatDecisionWindowCompactLocalDateTime,
  formatTeamAffectedCounts,
  getPendingTeamLookaheadMessage,
  type TeamDecisionWindowGameView,
  type TeamLineupHealthView,
  type TeamLineupWeekSummaryView,
  type TeamUpcomingLockView
} from '../../utils/team-decision-window-view.util';
import { TeamLineupMatchupComponent } from '../team-lineup-matchup/team-lineup-matchup';
import {
  getTeamLineupPlayerStatuses,
  TeamLineupPlayerListComponent,
  type TeamLineupPlayerRow
} from '../team-lineup-player-list/team-lineup-player-list';

@Component({
  selector: 'app-team-lineup-tab',
  standalone: true,
  imports: [CommonModule, TeamLineupMatchupComponent, TeamLineupPlayerListComponent],
  templateUrl: './team-lineup-tab.html',
  styleUrl: './team-lineup-tab.scss'
})
export class TeamLineupTabComponent {
  @Input() model: DecisionWindowsReadModel | null = null;
  @Input({ required: true }) fantasyTeamId!: number;
  @Input() players: Player[] = [];
  @Input() nflTeams: NFLTeam[] = [];
  @Input() updatedAt: string | null | undefined;
  @Input() now = new Date();
  @Input() loading = false;
  @Input() unavailable = false;
  @Output() openWindow = new EventEmitter<DecisionWindow>();

  get upcomingWindows(): TeamUpcomingLockView[] {
    if (!this.model) return [];
    return buildTeamUpcomingLockViews(this.model, this.fantasyTeamId, this.now);
  }

  get weekSummary(): TeamLineupWeekSummaryView {
    return buildTeamLineupWeekSummary(this.upcomingWindows);
  }

  get lineupHealth(): TeamLineupHealthView | null {
    if (!this.model) return null;
    return buildTeamLineupHealthView(this.model, this.fantasyTeamId);
  }

  get pendingLookaheadMessage(): string | null {
    if (!this.model) return null;
    return getPendingTeamLookaheadMessage(this.model, this.upcomingWindows, this.now);
  }

  get updatedLabel(): string | null {
    return formatDecisionWindowsUpdatedAt(this.updatedAt, this.now);
  }

  get nextDecisionCountdown(): string | null {
    const nextWindow = this.weekSummary.nextWindow;
    return nextWindow ? formatDecisionWindowCountdown(nextWindow.window, this.now) : null;
  }

  get weekSummaryCounts(): string {
    const summary = this.weekSummary;
    const windows = `${summary.windowCount} ${summary.windowCount === 1 ? 'window' : 'windows'}`;
    const games = `${summary.gameCount} ${summary.gameCount === 1 ? 'game' : 'games'}`;
    const players = `${summary.affectedRosteredPlayerCount} ${summary.affectedRosteredPlayerCount === 1 ? 'player' : 'players'}`;
    const starters = `${summary.affectedStarterCount} ${summary.affectedStarterCount === 1 ? 'starter' : 'starters'}`;
    return `${windows} · ${games} · ${players} · ${starters}`;
  }

  affectedCounts(window: TeamUpcomingLockView): string {
    return formatTeamAffectedCounts(window);
  }

  windowGameCount(window: TeamUpcomingLockView): string {
    return `${window.games.length} ${window.games.length === 1 ? 'game' : 'games'}`;
  }

  windowDateTimeLabel(window: DecisionWindow): string {
    return formatDecisionWindowCompactLocalDateTime(window);
  }

  gamePlayerRows(game: TeamDecisionWindowGameView): TeamLineupPlayerRow[] {
    const playerById = new Map(this.players.map(player => [player.ID, player]));

    return game.teamGroups.flatMap(group => {
      const affectedById = new Map(
        group.affectedPlayers.map(player => [player.PlayerID, player])
      );

      return group.affectedPlayers
        .map(player => playerById.get(player.PlayerID))
        .filter((player): player is Player => !!player)
        .sort((a, b) => {
          const starterOrder = Number(affectedById.get(b.ID)?.IsStarter ?? false)
            - Number(affectedById.get(a.ID)?.IsStarter ?? false);
          if (starterOrder !== 0) return starterOrder;
          return a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' }) || a.ID.localeCompare(b.ID);
        })
        .map<TeamLineupPlayerRow>(player => {
          const isStarter = affectedById.get(player.ID)?.IsStarter ?? false;
          return {
            player,
            statuses: getTeamLineupPlayerStatuses(player, isStarter)
          };
        });
    });
  }

  unresolvedGamePlayerCount(game: TeamDecisionWindowGameView): number {
    const knownIds = new Set(this.players.map(player => player.ID));
    return game.affectedPlayers.filter(player => !knownIds.has(player.PlayerID)).length;
  }
}
