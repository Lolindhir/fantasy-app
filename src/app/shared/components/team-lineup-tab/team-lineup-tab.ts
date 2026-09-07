import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import type {
  DecisionWindow,
  DecisionWindowGame,
  DecisionWindowsReadModel
} from '../../../core/models/decision-window.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import {
  formatDecisionWindowCountdown,
  formatDecisionWindowsUpdatedAt
} from '../../utils/decision-window-view.util';
import {
  buildLeagueTimelineMatchupContext,
  type LeagueTimelineMatchupContext
} from '../../utils/league-timeline-view.util';
import {
  buildTeamLineupHealthView,
  buildTeamLineupWeekSummary,
  buildTeamUpcomingLockViews,
  formatDecisionWindowCompactLocalDateTime,
  formatTeamAffectedCounts,
  getPendingTeamLookaheadMessage,
  type TeamDecisionWindowGameView,
  type TeamDecisionWindowNflTeamGroupView,
  type TeamLineupHealthView,
  type TeamLineupWeekSummaryView,
  type TeamUpcomingLockView
} from '../../utils/team-decision-window-view.util';
import { DecisionWindowMatchupContextComponent } from '../decision-window-matchup-context/decision-window-matchup-context';
import { PlayerListComponent, type PlayerListColumn } from '../player-list/player-list';

@Component({
  selector: 'app-team-lineup-tab',
  standalone: true,
  imports: [CommonModule, DecisionWindowMatchupContextComponent, PlayerListComponent],
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

  readonly playerColumns: PlayerListColumn[] = ['name', 'dynamicStat'];

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

  teamPlayers(group: TeamDecisionWindowNflTeamGroupView): Player[] {
    const playerById = new Map(this.players.map(player => [player.ID, player]));
    const starterById = new Map(group.affectedPlayers.map(player => [player.PlayerID, player.IsStarter]));

    return group.affectedPlayers
      .map(player => playerById.get(player.PlayerID))
      .filter((player): player is Player => !!player)
      .sort((a, b) => {
        const starterOrder = Number(starterById.get(b.ID) ?? false) - Number(starterById.get(a.ID) ?? false);
        if (starterOrder !== 0) return starterOrder;
        return a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' }) || a.ID.localeCompare(b.ID);
      });
  }

  unresolvedTeamPlayerCount(group: TeamDecisionWindowNflTeamGroupView): number {
    const knownIds = new Set(this.players.map(player => player.ID));
    return group.affectedPlayers.filter(player => !knownIds.has(player.PlayerID)).length;
  }

  teamLogo(group: TeamDecisionWindowNflTeamGroupView): string | null {
    if (!group.nflTeamId) return null;
    return this.nflTeams.find(team => team.ID === group.nflTeamId)?.Logo ?? null;
  }

  teamName(group: TeamDecisionWindowNflTeamGroupView): string {
    if (!group.nflTeamId) return group.teamAbbr;
    return this.nflTeams.find(team => team.ID === group.nflTeamId)?.Name || group.teamAbbr;
  }

  teamCounts(group: TeamDecisionWindowNflTeamGroupView): string {
    const players = `${group.affectedPlayers.length} ${group.affectedPlayers.length === 1 ? 'player' : 'players'}`;
    const starters = `${group.affectedStarterCount} ${group.affectedStarterCount === 1 ? 'starter' : 'starters'}`;
    return `${players} · ${starters}`;
  }

  getPlayerRole = (player: Player): string => {
    for (const window of this.upcomingWindows) {
      for (const game of window.games) {
        const affected = game.affectedPlayers.find(candidate => candidate.PlayerID === player.ID);
        if (affected) return affected.IsStarter ? 'Starter' : 'Roster';
      }
    }
    return 'Roster';
  };

  gameMatchupContext(window: DecisionWindow, game: DecisionWindowGame): LeagueTimelineMatchupContext | null {
    return buildLeagueTimelineMatchupContext({
      ...window,
      Games: [game],
      ParticipatingNFLTeamIDs: [game.AwayTeamID, game.HomeTeamID]
    }, this.nflTeams);
  }
}
