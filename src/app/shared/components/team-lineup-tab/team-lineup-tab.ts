import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import type {
  DecisionWindow,
  DecisionWindowGame,
  DecisionWindowsReadModel
} from '../../../core/models/decision-window.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import { formatDecisionWindowsUpdatedAt } from '../../utils/decision-window-view.util';
import {
  buildLeagueTimelineMatchupContext,
  type LeagueTimelineMatchupContext
} from '../../utils/league-timeline-view.util';
import {
  buildTeamLineupHealthView,
  buildTeamUpcomingLockViews,
  formatTeamAffectedCounts,
  getPendingTeamLookaheadMessage,
  type TeamDecisionWindowGameView,
  type TeamLineupHealthView,
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

  affectedCounts(window: TeamUpcomingLockView): string {
    return formatTeamAffectedCounts(window);
  }

  gamePlayers(game: TeamDecisionWindowGameView): Player[] {
    const playerById = new Map(this.players.map(player => [player.ID, player]));
    const starterById = new Map(game.affectedPlayers.map(player => [player.PlayerID, player.IsStarter]));

    return game.affectedPlayers
      .map(player => playerById.get(player.PlayerID))
      .filter((player): player is Player => !!player)
      .sort((a, b) => {
        const starterOrder = Number(starterById.get(b.ID) ?? false) - Number(starterById.get(a.ID) ?? false);
        if (starterOrder !== 0) return starterOrder;
        return a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' }) || a.ID.localeCompare(b.ID);
      });
  }

  unresolvedGamePlayerCount(game: TeamDecisionWindowGameView): number {
    const knownIds = new Set(this.players.map(player => player.ID));
    return game.affectedPlayers.filter(player => !knownIds.has(player.PlayerID)).length;
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
