import { CommonModule } from '@angular/common';
import { Component, Inject, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextMatchupGame,
  FantasyGameContextPlayer,
  FantasyGameContextReadModel,
  FantasyGameContextTeam
} from '../../../core/models/fantasy-game-context.models';
import type { League, Player } from '../../../core/models/fantasy.models';
import { isFantasyGameImpactVisible } from '../../utils/fantasy-game-context.util';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

export interface FantasyGameContextDialogData {
  mode: 'game' | 'matchup';
  context: FantasyGameContextReadModel;
  league: League;
  gameId?: string;
  fantasyMatchupId?: string;
}

@Component({
  selector: 'app-fantasy-game-context-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './fantasy-game-context-dialog.html',
  styleUrl: './fantasy-game-context-dialog.scss'
})
export class FantasyGameContextDialogComponent {
  private readonly dialog = inject(MatDialog);
  private readonly teamDialog = inject(TeamDetailDialogService);

  readonly game: FantasyGameContextGame | null;
  readonly matchup: FantasyGameContextMatchup | null;

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: FantasyGameContextDialogData) {
    this.game = data.gameId
      ? data.context.Games.find(game => game.GameID === data.gameId) ?? null
      : null;
    this.matchup = data.fantasyMatchupId
      ? data.context.FantasyMatchups.find(matchup => matchup.FantasyMatchupID === data.fantasyMatchupId) ?? null
      : null;
  }

  teamName(teamID: string | number): string {
    const team = this.data.league.Teams.find(candidate => String(candidate.TeamID) === String(teamID));
    return team?.Team || team?.Owner || `Team ${teamID}`;
  }

  teamShortName(teamID: string | number): string {
    const team = this.data.league.Teams.find(candidate => String(candidate.TeamID) === String(teamID));
    return team?.TeamAbbr?.trim() || team?.Team?.trim() || team?.Owner || `Team ${teamID}`;
  }

  playerName(playerID: string): string {
    return this.findPlayer(playerID)?.Name ?? playerID;
  }

  gameLabel(gameID: string): string {
    const game = this.gameForID(gameID);
    if (!game) return gameID;
    return `${game.AwayTeamAbbr || game.AwayTeamID} @ ${game.HomeTeamAbbr || game.HomeTeamID}`;
  }

  gameForMatchupRow(row: FantasyGameContextMatchupGame): FantasyGameContextGame | null {
    return this.gameForID(row.GameID);
  }

  hasGameScoring(game: FantasyGameContextGame): boolean {
    return isFantasyGameImpactVisible(game);
  }

  hasMatchupGameScoring(row: FantasyGameContextMatchupGame): boolean {
    const game = this.gameForMatchupRow(row);
    return !!game && isFantasyGameImpactVisible(game);
  }

  showCounterfactual(matchup: FantasyGameContextMatchup): boolean {
    return matchup.CounterfactualState === 'available' || this.data.context.ScoringState === 'final';
  }

  playersForTeam(team: FantasyGameContextTeam): FantasyGameContextPlayer[] {
    return [...team.Players].sort((left, right) =>
      Number(right.IsStarter) - Number(left.IsStarter)
      || this.playerName(left.PlayerID).localeCompare(this.playerName(right.PlayerID))
    );
  }

  openTeam(teamID: string | number): void {
    const numericID = Number(teamID);
    if (Number.isFinite(numericID)) this.teamDialog.open(numericID);
  }

  openPlayer(playerID: string): void {
    const player = this.findPlayer(playerID);
    if (!player) return;
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  private gameForID(gameID: string): FantasyGameContextGame | null {
    return this.data.context.Games.find(game => game.GameID === gameID) ?? null;
  }

  private findPlayer(playerID: string): Player | null {
    for (const team of this.data.league.Teams) {
      const player = team.Roster.find(candidate => String(candidate.ID) === String(playerID));
      if (player) return player;
    }
    return null;
  }
}
