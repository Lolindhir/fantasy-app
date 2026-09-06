import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type {
  DecisionWindow,
  DecisionWindowAffectedFantasyTeam,
  DecisionWindowGame,
  DecisionWindowsReadModel
} from '../../../core/models/decision-window.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import {
  buildDecisionWindowTeamRows,
  formatDecisionWindowCountdown,
  formatDecisionWindowGame,
  formatDecisionWindowLocalDateTime,
  formatDecisionWindowsUpdatedAt,
  type DecisionWindowTeamRowView
} from '../../utils/decision-window-view.util';
import {
  buildLeagueTimelineMatchupContext,
  type LeagueTimelineMatchupContext
} from '../../utils/league-timeline-view.util';
import { DecisionWindowMatchupContextComponent } from '../decision-window-matchup-context/decision-window-matchup-context';
import { PlayerListComponent, type PlayerListColumn } from '../player-list/player-list';

@Component({
  selector: 'app-decision-window-context-popover',
  standalone: true,
  imports: [CommonModule, DecisionWindowMatchupContextComponent, PlayerListComponent],
  templateUrl: './decision-window-context-popover.html',
  styleUrl: './decision-window-context-popover.scss'
})
export class DecisionWindowContextPopoverComponent {
  @Input({ required: true }) model!: DecisionWindowsReadModel;
  @Input({ required: true }) window!: DecisionWindow;
  @Input() teams: FantasyTeam[] = [];
  @Input() players: Player[] = [];
  @Input() nflTeams: NFLTeam[] = [];
  @Input() teamId: number | null = null;
  @Input() updatedAt: string | null | undefined;
  @Input() now = new Date();

  readonly teamPlayerColumns: PlayerListColumn[] = ['name', 'dynamicStat'];

  constructor(private teamDetailDialogService: TeamDetailDialogService) {}

  get teamRows(): DecisionWindowTeamRowView[] {
    return buildDecisionWindowTeamRows(this.model, this.window, this.teams);
  }

  get localDateTime(): string {
    return formatDecisionWindowLocalDateTime(this.window);
  }

  get countdown(): string {
    return formatDecisionWindowCountdown(this.window, this.now);
  }

  get updatedLabel(): string | null {
    return formatDecisionWindowsUpdatedAt(this.updatedAt, this.now);
  }

  get showGameCount(): boolean {
    return this.window.Games.length > 1;
  }

  get matchupContext(): LeagueTimelineMatchupContext | null {
    return buildLeagueTimelineMatchupContext(this.window, this.nflTeams);
  }

  get isTeamScope(): boolean {
    return this.teamId !== null;
  }

  get teamAffectedContext(): DecisionWindowAffectedFantasyTeam | undefined {
    if (this.teamId === null) return undefined;
    return this.window.AffectedFantasyTeams.find(affected => affected.FantasyTeamID === this.teamId);
  }

  get teamAffectedPlayers(): Player[] {
    const affected = this.teamAffectedContext;
    if (!affected) return [];

    const playerById = new Map(this.players.map(player => [player.ID, player]));
    const starterById = new Map(affected.Players.map(player => [player.PlayerID, player.IsStarter]));

    return affected.Players
      .map(player => playerById.get(player.PlayerID))
      .filter((player): player is Player => !!player)
      .sort((a, b) => {
        const starterOrder = Number(starterById.get(b.ID) ?? false) - Number(starterById.get(a.ID) ?? false);
        if (starterOrder !== 0) return starterOrder;
        return a.Name.localeCompare(b.Name, 'en', { sensitivity: 'base' }) || a.ID.localeCompare(b.ID);
      });
  }

  get unresolvedTeamPlayerCount(): number {
    const affected = this.teamAffectedContext;
    if (!affected) return 0;
    const knownIds = new Set(this.players.map(player => player.ID));
    return affected.Players.filter(player => !knownIds.has(player.PlayerID)).length;
  }

  get teamScopeSummary(): string {
    const affected = this.teamAffectedContext;
    if (!affected) return 'No affected players for this team.';
    const playerLabel = affected.AffectedRosteredPlayerCount === 1 ? 'player' : 'players';
    const starterLabel = affected.AffectedStarterCount === 1 ? 'starter' : 'starters';
    return `${affected.AffectedRosteredPlayerCount} ${playerLabel} · ${affected.AffectedStarterCount} ${starterLabel}`;
  }

  getTeamPlayerRole = (player: Player): string => {
    const affected = this.teamAffectedContext?.Players.find(candidate => candidate.PlayerID === player.ID);
    return affected?.IsStarter ? 'Starter' : 'Roster';
  };

  gameLabel(game: DecisionWindowGame): string {
    return formatDecisionWindowGame(game);
  }

  openTeam(teamId: number): void {
    this.teamDetailDialogService.open(teamId);
  }

  trackTeam(_index: number, row: DecisionWindowTeamRowView): number {
    return row.teamId;
  }

  trackGame(_index: number, game: DecisionWindowGame): string {
    return game.GameID;
  }
}
