import { CommonModule } from '@angular/common';
import { Component, Inject, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import type {
  DecisionWindowsReadModel,
  FantasyRelevancePlayerState,
  FantasyRelevanceTeamState
} from '../../../core/models/decision-window.models';
import type {
  FantasyGameContextCounterfactualScore,
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextMatchupGame,
  FantasyGameContextPlayer,
  FantasyGameContextReadModel,
  FantasyGameContextTeam
} from '../../../core/models/fantasy-game-context.models';
import type { FantasyTeam, League } from '../../../core/models/league.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import {
  isFantasyGameImpactVisible,
  isFantasyMatchupFinalWindowGame
} from '../../utils/fantasy-game-context.util';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

interface FantasyGamePlayerDisplay {
  PlayerID: string;
  IsStarter: boolean;
  IsBenchCandidate: boolean;
  GameState: string | null;
  LineupSlotType: string | null;
  EligibleUnlockedSlotIDs: string[];
  Points: number | null;
}

export interface FantasyGameContextDialogData {
  mode: 'game' | 'matchup';
  context: FantasyGameContextReadModel;
  decisionWindows?: DecisionWindowsReadModel | null;
  nflTeams?: NFLTeam[];
  league: League;
  gameId?: string;
  fantasyMatchupId?: string;
}

@Component({
  selector: 'app-fantasy-game-context-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, PositionStylePipe],
  templateUrl: './fantasy-game-context-dialog.html',
  styleUrls: ['./fantasy-game-context-dialog.scss', './fantasy-game-context-dialog-refinements.scss']
})
export class FantasyGameContextDialogComponent {
  private readonly dialog = inject(MatDialog);
  private readonly teamDialog = inject(TeamDetailDialogService);
  private readonly fantasyScoreFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
  private readonly nflScoreFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

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
    const team = this.teamForID(teamID);
    return team?.Team || team?.Owner || `Team ${teamID}`;
  }

  teamShortName(teamID: string | number): string {
    const team = this.teamForID(teamID);
    return team?.TeamAbbr?.trim() || team?.Team?.trim() || team?.Owner || `Team ${teamID}`;
  }

  teamAvatar(teamID: string | number): string | null {
    return this.teamForID(teamID)?.Avatar || null;
  }

  nflLogo(teamID: string | number): string | null {
    return (this.data.nflTeams ?? []).find(team => String(team.ID) === String(teamID))?.Logo || null;
  }

  playerName(playerID: string): string {
    return this.findPlayer(playerID)?.Name ?? playerID;
  }

  playerPicture(playerID: string): string | null {
    return this.findPlayer(playerID)?.Picture || null;
  }

  playerPosition(playerID: string): string | null {
    return this.findPlayer(playerID)?.Position || null;
  }

  playerNflLogo(playerID: string): string | null {
    return this.findPlayer(playerID)?.TeamNFL?.Logo || null;
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

  hasNflScore(game: FantasyGameContextGame): boolean {
    return /^Final/i.test(game.Status ?? '')
      && game.AwayScore !== null
      && game.AwayScore !== undefined
      && game.HomeScore !== null
      && game.HomeScore !== undefined;
  }

  formatFantasyPoints(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.fantasyScoreFormatter.format(Number(value));
  }

  formatNflScore(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.nflScoreFormatter.format(Number(value));
  }

  fantasyMatchupScore(matchup: FantasyGameContextMatchup): FantasyGameContextCounterfactualScore | null {
    const snapshot = this.data.league.Matchups;
    if (snapshot && snapshot.Season === this.data.context.Season && snapshot.Week === this.data.context.Week) {
      const teamIDs = matchup.TeamIDs.map(teamID => String(teamID));
      const leagueMatchup = snapshot.Matchups.find(candidate => {
        const participantIDs = candidate.Participants.map(participant => String(participant.TeamID));
        return participantIDs.length === 2 && teamIDs.every(teamID => participantIDs.includes(teamID));
      });
      if (leagueMatchup) {
        const left = leagueMatchup.Participants.find(participant => String(participant.TeamID) === teamIDs[0]);
        const right = leagueMatchup.Participants.find(participant => String(participant.TeamID) === teamIDs[1]);
        if (left && right) {
          const leftPoints = Number(left.Points ?? 0);
          const rightPoints = Number(right.Points ?? 0);
          if (Number.isFinite(leftPoints) && Number.isFinite(rightPoints)
              && (leftPoints !== 0 || rightPoints !== 0 || !!matchup.FinalScores)) {
            return { Left: leftPoints, Right: rightPoints };
          }
        }
      }
    }
    return matchup.FinalScores;
  }

  showCounterfactual(matchup: FantasyGameContextMatchup): boolean {
    return matchup.CounterfactualState === 'available' || this.data.context.ScoringState === 'final';
  }

  affectedStarterTeamIDs(game: FantasyGameContextGame): Array<string | number> {
    const generated = game.RemainingRelevance?.DirectStarterFantasyTeamIDs ?? [];
    if (generated.length > 0) return this.uniqueTeamIDs(generated);

    return this.uniqueTeamIDs(
      game.FantasyTeams
        .filter(team => team.StarterCount > 0)
        .map(team => team.FantasyTeamID)
    );
  }

  relevantFantasyTeamsForGame(game: FantasyGameContextGame): FantasyGameContextTeam[] {
    const relevanceAvailable = this.hasDecisionRelevance();
    return game.FantasyTeams
      .filter(team => relevanceAvailable
        ? this.gamePlayersForTeam(game, team).length > 0
        : team.StarterCount > 0)
      .sort((left, right) => {
        const leftPlayers = this.gamePlayersForTeam(game, left);
        const rightPlayers = this.gamePlayersForTeam(game, right);
        const leftStarterCount = leftPlayers.filter(player => player.IsStarter).length;
        const rightStarterCount = rightPlayers.filter(player => player.IsStarter).length;
        return rightStarterCount - leftStarterCount
          || rightPlayers.length - leftPlayers.length
          || this.teamName(left.FantasyTeamID).localeCompare(this.teamName(right.FantasyTeamID));
      });
  }

  gamePlayersForTeam(game: FantasyGameContextGame, team: FantasyGameContextTeam): FantasyGamePlayerDisplay[] {
    const legacyByID = new Map(team.Players.map(player => [String(player.PlayerID), player]));
    const teamState = this.decisionTeamState(team.FantasyTeamID);

    if (teamState) {
      const states = teamState.Players
        .filter(player => player.GameID === game.GameID)
        .filter(player =>
          player.HasDirectScoringPath
          || player.HasAlternativePath
          || (player.Placement === 'starter' && player.GameState === 'completed')
        );

      if (states.length > 0) {
        return states
          .map(state => this.toPlayerDisplay(state, legacyByID.get(String(state.PlayerID)) ?? null))
          .sort((left, right) => Number(right.IsStarter) - Number(left.IsStarter)
            || Number(right.GameState === 'locked-active') - Number(left.GameState === 'locked-active')
            || Number(right.IsBenchCandidate) - Number(left.IsBenchCandidate)
            || this.playerName(left.PlayerID).localeCompare(this.playerName(right.PlayerID)));
      }
    }

    return [...team.Players]
      .filter(player => player.IsStarter)
      .sort((left, right) => this.playerName(left.PlayerID).localeCompare(this.playerName(right.PlayerID)))
      .map(player => ({
        PlayerID: player.PlayerID,
        IsStarter: player.IsStarter,
        IsBenchCandidate: false,
        GameState: null,
        LineupSlotType: null,
        EligibleUnlockedSlotIDs: [],
        Points: player.Points
      }));
  }

  matchupTimelineRows(matchup: FantasyGameContextMatchup): FantasyGameContextMatchupGame[] {
    const relevantGameIDs = new Set<string>();
    if (this.hasDecisionRelevance()) {
      for (const teamID of matchup.TeamIDs) {
        const teamState = this.decisionTeamState(teamID);
        for (const player of teamState?.Players ?? []) {
          if (!player.GameID) continue;
          if (player.HasDirectScoringPath
              || player.HasAlternativePath
              || (player.Placement === 'starter' && player.GameState === 'completed')) {
            relevantGameIDs.add(player.GameID);
          }
        }
      }
    }

    return [...matchup.Games]
      .filter(row => relevantGameIDs.size > 0
        ? relevantGameIDs.has(row.GameID) || row.OutcomeChangedWithoutGame === true
        : row.LeftStarterCount + row.RightStarterCount > 0 || row.OutcomeChangedWithoutGame === true)
      .sort((left, right) => Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc) || left.GameID.localeCompare(right.GameID));
  }

  matchupGameTeamPlayers(
    matchup: FantasyGameContextMatchup,
    row: FantasyGameContextMatchupGame,
    teamID: string | number
  ): FantasyGamePlayerDisplay[] {
    const game = this.gameForMatchupRow(row);
    if (!game) return [];
    const legacyTeam = game.FantasyTeams.find(team => String(team.FantasyTeamID) === String(teamID));
    if (legacyTeam) return this.gamePlayersForTeam(game, legacyTeam);

    const state = this.decisionTeamState(teamID);
    return (state?.Players ?? [])
      .filter(player => player.GameID === row.GameID)
      .filter(player => player.HasDirectScoringPath || player.HasAlternativePath || (player.Placement === 'starter' && player.GameState === 'completed'))
      .map(player => this.toPlayerDisplay(player, null));
  }

  matchupStateLabel(matchup: FantasyGameContextMatchup): string {
    const remaining = matchup.RemainingRelevance;
    if (!remaining) return 'Current starter exposure';

    switch (remaining.State) {
      case 'both-sides': return 'Both teams can still score';
      case 'left-only': return `Only ${this.teamShortName(matchup.TeamIDs[0])} can still score`;
      case 'right-only': return `Only ${this.teamShortName(matchup.TeamIDs[1])} can still score`;
      case 'none': return 'No scoring paths remaining';
    }
  }

  remainingPathCount(matchup: FantasyGameContextMatchup, side: 'left' | 'right'): number | null {
    const remaining = matchup.RemainingRelevance;
    if (!remaining) return null;
    return side === 'left' ? remaining.LeftRemainingPathCount : remaining.RightRemainingPathCount;
  }

  isFinalWindow(matchup: FantasyGameContextMatchup, gameID: string): boolean {
    return isFantasyMatchupFinalWindowGame(matchup, gameID);
  }

  gameStageLabel(game: FantasyGameContextGame | null): string {
    if (!game) return 'NFL game';
    if (/^Final/i.test(game.Status ?? '')) return 'Final';
    if ((game.RemainingRelevance?.LockedActiveStarterCount ?? 0) > 0) return 'Live';
    return 'Upcoming';
  }

  playerStateLabel(player: FantasyGamePlayerDisplay): string {
    if (player.IsBenchCandidate) return 'Option';
    if (player.GameState === 'locked-active') return 'Locked';
    if (player.GameState === 'completed') return 'Final';
    if (player.IsStarter) return 'Starter';
    return 'Player';
  }

  playerSecondarySlot(player: FantasyGamePlayerDisplay): string | null {
    const naturalPosition = (this.playerPosition(player.PlayerID) ?? '').trim().toUpperCase();

    if (player.IsBenchCandidate) {
      const alternatives = player.EligibleUnlockedSlotIDs
        .map(slot => slot.replace(/-\d+$/, '').toUpperCase())
        .filter((slot, index, all) => slot !== naturalPosition && all.indexOf(slot) === index);
      return alternatives.length > 0 ? alternatives.join(' / ') : null;
    }

    const lineupSlot = player.LineupSlotType?.trim().toUpperCase() ?? '';
    return lineupSlot && lineupSlot !== naturalPosition ? lineupSlot : null;
  }

  playerRoleLabel(player: FantasyGamePlayerDisplay): string {
    const slot = this.playerSecondarySlot(player);
    return slot ? `${slot} · ${this.playerStateLabel(player).toLowerCase()}` : this.playerStateLabel(player);
  }

  playerAlternativeSlots(player: FantasyGamePlayerDisplay): string {
    return player.EligibleUnlockedSlotIDs
      .map(slot => slot.replace(/-\d+$/, ''))
      .filter((slot, index, all) => all.indexOf(slot) === index)
      .join(' / ');
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
      width: 'calc(100vw - 16px)',
      maxWidth: '800px',
      maxHeight: 'calc(100dvh - 16px)',
      panelClass: 'player-dialog'
    });
  }

  openGame(gameID: string): void {
    if (!this.gameForID(gameID)) return;
    this.dialog.open(FantasyGameContextDialogComponent, {
      data: {
        mode: 'game',
        context: this.data.context,
        decisionWindows: this.data.decisionWindows,
        nflTeams: this.data.nflTeams,
        league: this.data.league,
        gameId: gameID
      } satisfies FantasyGameContextDialogData,
      width: 'calc(100vw - 16px)',
      maxWidth: '760px',
      maxHeight: 'calc(100dvh - 16px)',
      autoFocus: false,
      restoreFocus: true,
      panelClass: 'fantasy-context-dialog-panel'
    });
  }

  private hasDecisionRelevance(): boolean {
    const decision = this.data.decisionWindows;
    return !!decision
      && decision.Season === this.data.context.Season
      && decision.LineupWeek === this.data.context.Week
      && !!decision.FantasyRelevance;
  }

  private decisionTeamState(teamID: string | number): FantasyRelevanceTeamState | null {
    if (!this.hasDecisionRelevance()) return null;
    return this.data.decisionWindows?.FantasyRelevance?.Teams
      .find(team => String(team.FantasyTeamID) === String(teamID)) ?? null;
  }

  private toPlayerDisplay(
    state: FantasyRelevancePlayerState,
    legacy: FantasyGameContextPlayer | null
  ): FantasyGamePlayerDisplay {
    return {
      PlayerID: state.PlayerID,
      IsStarter: state.Placement === 'starter',
      IsBenchCandidate: state.IsBenchCandidate,
      GameState: state.GameState,
      LineupSlotType: state.LineupSlotType,
      EligibleUnlockedSlotIDs: [...state.EligibleUnlockedSlotIDs],
      Points: legacy?.Points ?? null
    };
  }

  private gameForID(gameID: string): FantasyGameContextGame | null {
    return this.data.context.Games.find(game => game.GameID === gameID) ?? null;
  }

  private teamForID(teamID: string | number): FantasyTeam | null {
    return this.data.league.Teams.find(candidate => String(candidate.TeamID) === String(teamID)) ?? null;
  }

  private findPlayer(playerID: string): Player | null {
    for (const team of this.data.league.Teams) {
      const player = team.Roster.find(candidate => String(candidate.ID) === String(playerID));
      if (player) return player;
    }
    return null;
  }

  private uniqueTeamIDs(teamIDs: Array<string | number>): Array<string | number> {
    const seen = new Set<string>();
    return teamIDs.filter(teamID => {
      const key = String(teamID);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}