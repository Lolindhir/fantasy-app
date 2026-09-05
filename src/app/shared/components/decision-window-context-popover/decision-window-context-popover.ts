import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';

import type {
  DecisionWindow,
  DecisionWindowGame,
  DecisionWindowsReadModel
} from '../../../core/models/decision-window.models';
import type { FantasyTeam } from '../../../core/models/league.models';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import {
  buildDecisionWindowTeamRows,
  formatDecisionWindowCountdown,
  formatDecisionWindowGame,
  formatDecisionWindowLocalDateTime,
  formatDecisionWindowsUpdatedAt,
  type DecisionWindowTeamRowView
} from '../../utils/decision-window-view.util';

@Component({
  selector: 'app-decision-window-context-popover',
  standalone: true,
  imports: [CommonModule, MatMenuModule],
  templateUrl: './decision-window-context-popover.html',
  styleUrl: './decision-window-context-popover.scss'
})
export class DecisionWindowContextPopoverComponent {
  @Input({ required: true }) model!: DecisionWindowsReadModel;
  @Input({ required: true }) window!: DecisionWindow;
  @Input() teams: FantasyTeam[] = [];
  @Input() updatedAt: string | null | undefined;
  @Input() now = new Date();

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
