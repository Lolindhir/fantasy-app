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
  FantasyGameContextTeam,
  FantasyMatchupRemainingState
} from '../../../core/models/fantasy-game-context.models';
import type { FantasyTeam, League } from '../../../core/models/league.models';
import type { MatchupProjectionTeam } from '../../../core/models/matchup-projections.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import { MatchupRangeChartComponent } from '../projection-range/matchup-range-chart';
import { PlayerProjectionComponent } from '../projection-range/player-projection';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import {
  isFantasyGameImpactVisible,
  isFantasyMatchupFinalWindowGame
} from '../../utils/fantasy-game-context.util';
import { orderOverviewCurrentMatchups } from '../../utils/overview-weekly-dashboard.util';
import {
  axisPosition,
  formatProjectionPoints,
  playerProjectionView,
  rangeAtLevel,
  rangeBarGeometry,
  scoredSoFarNote,
  type MatchupRangeTeamView,
  type MatchupRangeView,
  type PlayerProjectionView
} from '../../utils/projection-range.util';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { MatchupPlayerStatusComponent } from '../matchup-player-status/matchup-player-status';
import {
  buildMatchupPlayerStatus,
  hasMatchupPlayerStatus,
  type MatchupPlayerStatusTeamView
} from '../matchup-player-status/matchup-player-status.util';
import { findNflTeam } from '../../utils/nfl-team-key.util';

interface FantasyGamePlayerDisplay {
  PlayerID: string;
  IsStarter: boolean;
  IsBenchCandidate: boolean;
  GameState: string | null;
  LineupSlotType: string | null;
  EligibleUnlockedSlotIDs: string[];
  Points: number | null;
  ProjectedPoints: number | null;
  ProjectedRange: { Lower: number; Upper: number } | null;
}

export function starterProjectedPoints(player: FantasyGameContextPlayer | null | undefined): number | null {
  const prediction = player?.Prediction;
  return prediction?.Status === 'available' && Number.isFinite(prediction.Points)
    ? prediction.Points
    : null;
}

export function starterProjectedRange(
  player: FantasyGameContextPlayer | null | undefined,
  level: number | null | undefined
): { Lower: number; Upper: number } | null {
  const range = rangeAtLevel(player?.Prediction?.PredictionRanges, level);
  return range ? { Lower: range.Lower, Upper: range.Upper } : null;
}

export function matchupProjectionTeam(
  matchup: FantasyGameContextMatchup,
  teamID: string | number
): MatchupProjectionTeam | null {
  return matchup.Projection?.Teams
    .find(team => String(team.FantasyTeamID) === String(teamID)) ?? null;
}

export function teamProjectedFinalScore(
  matchup: FantasyGameContextMatchup,
  teamID: string | number
): number | null {
  return matchupProjectionTeam(matchup, teamID)?.ProjectedFinalScore ?? null;
}

export type MatchupDisplaySide = 'left' | 'right';
export type MatchupDisplayTeamIDs = [string | number, string | number];

export function matchupSportsStateLabel(
  state: FantasyMatchupRemainingState,
  leftTeamName: string,
  rightTeamName: string
): string {
  switch (state) {
    case 'both-sides': return 'Both teams can still score';
    case 'left-only': return `Only ${leftTeamName} can still score`;
    case 'right-only': return `Only ${rightTeamName} can still score`;
    case 'none': return 'No more points can be scored';
  }
}

export function resolveMatchupDisplayTeamIDs(
  league: League,
  readModel: MatchupsReadModel | null | undefined,
  season: string,
  week: number,
  matchup: FantasyGameContextMatchup
): MatchupDisplayTeamIDs {
  const fallback = [matchup.TeamIDs[0], matchup.TeamIDs[1]] as MatchupDisplayTeamIDs;
  if (!readModel || readModel.Season !== season) return fallback;

  const weekModel = readModel.Weeks.find(candidate => candidate.Week === week);
  const officialMatchup = weekModel?.Matchups.find(
    candidate => candidate.FantasyMatchupID === matchup.FantasyMatchupID
  );
  if (!officialMatchup || officialMatchup.Participants.length !== 2) return fallback;

  const oriented = orderOverviewCurrentMatchups(league, [officialMatchup])[0];
  if (!oriented || oriented.Participants.length !== 2) return fallback;

  const candidate = [
    oriented.Participants[0].TeamID,
    oriented.Participants[1].TeamID
  ] as MatchupDisplayTeamIDs;
  const sourceTeamIDs = new Set(matchup.TeamIDs.map(teamID => String(teamID)));

  return candidate.every(teamID => sourceTeamIDs.has(String(teamID)))
    ? candidate
    : fallback;
}

export function matchupDisplaySideSourceIndex(
  matchup: FantasyGameContextMatchup,
  displayTeamIDs: MatchupDisplayTeamIDs,
  side: MatchupDisplaySide
): 0 | 1 {
  const displayIndex = side === 'left' ? 0 : 1;
  const sourceIndex = matchup.TeamIDs.findIndex(
    teamID => String(teamID) === String(displayTeamIDs[displayIndex])
  );
  return sourceIndex === 0 || sourceIndex === 1 ? sourceIndex : displayIndex;
}

export function matchupDisplaySideValue<T>(
  matchup: FantasyGameContextMatchup,
  displayTeamIDs: MatchupDisplayTeamIDs,
  side: MatchupDisplaySide,
  leftValue: T,
  rightValue: T
): T {
  return matchupDisplaySideSourceIndex(matchup, displayTeamIDs, side) === 0
    ? leftValue
    : rightValue;
}

export function orientMatchupScore(
  matchup: FantasyGameContextMatchup,
  displayTeamIDs: MatchupDisplayTeamIDs,
  score: FantasyGameContextCounterfactualScore | null
): FantasyGameContextCounterfactualScore | null {
  if (!score) return null;

  return {
    Left: matchupDisplaySideValue(matchup, displayTeamIDs, 'left', score.Left, score.Right),
    Right: matchupDisplaySideValue(matchup, displayTeamIDs, 'right', score.Left, score.Right)
  };
}

export interface FantasyGameContextDialogData {
  mode: 'game' | 'matchup';
  context: FantasyGameContextReadModel;
  decisionWindows?: DecisionWindowsReadModel | null;
  matchups?: MatchupsReadModel | null;
  nflTeams?: NFLTeam[];
  league: League;
  gameId?: string;
  fantasyMatchupId?: string;
}

@Component({
  selector: 'app-fantasy-game-context-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    PositionStylePipe,
    MatchupRangeChartComponent,
    MatchupPlayerStatusComponent,
    PlayerProjectionComponent
  ],
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
  readonly matchupTeamIDs: MatchupDisplayTeamIDs | null;
  readonly playerStatusTeams: readonly MatchupPlayerStatusTeamView[];

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: FantasyGameContextDialogData) {
    this.game = data.gameId
      ? data.context.Games.find(game => game.GameID === data.gameId) ?? null
      : null;
    this.matchup = data.fantasyMatchupId
      ? data.context.FantasyMatchups.find(matchup => matchup.FantasyMatchupID === data.fantasyMatchupId) ?? null
      : null;
    this.matchupTeamIDs = this.matchup
      ? resolveMatchupDisplayTeamIDs(
          data.league,
          data.matchups,
          data.context.Season,
          data.context.Week,
          this.matchup
        )
      : null;
    this.playerStatusTeams = this.matchup && this.matchupTeamIDs
      ? this.buildPlayerStatus(this.matchup, this.matchupTeamIDs)
      : [];
  }

  get hasPlayerStatus(): boolean {
    return hasMatchupPlayerStatus(this.playerStatusTeams);
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
    return findNflTeam(this.data.nflTeams ?? [], teamID)?.Logo || null;
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
    const displayTeamIDs = this.displayTeamIDsFor(matchup);
    const readModel = this.data.matchups;
    if (readModel && readModel.Season === this.data.context.Season) {
      const week = readModel.Weeks.find(candidate => candidate.Week === this.data.context.Week);
      const officialMatchup = week?.Matchups.find(candidate => candidate.FantasyMatchupID === matchup.FantasyMatchupID);
      if (officialMatchup) {
        const left = officialMatchup.Participants.find(
          participant => String(participant.TeamID) === String(displayTeamIDs[0])
        );
        const right = officialMatchup.Participants.find(
          participant => String(participant.TeamID) === String(displayTeamIDs[1])
        );
        if (left?.Points !== null && left?.Points !== undefined && right?.Points !== null && right?.Points !== undefined) {
          const leftPoints = Number(left.Points);
          const rightPoints = Number(right.Points);
          if (Number.isFinite(leftPoints) && Number.isFinite(rightPoints)) {
            return { Left: leftPoints, Right: rightPoints };
          }
        }
      }
    }
    return orientMatchupScore(matchup, displayTeamIDs, matchup.FinalScores);
  }

  matchupTeamID(matchup: FantasyGameContextMatchup, side: MatchupDisplaySide): string | number {
    const teamIDs = this.displayTeamIDsFor(matchup);
    return teamIDs[side === 'left' ? 0 : 1];
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
        Points: player.Points,
        ProjectedPoints: starterProjectedPoints(player),
        ProjectedRange: starterProjectedRange(player, this.data.context.ProjectionDisplay?.PlayerRangeLevel)
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

  matchupProjection(matchup: FantasyGameContextMatchup): { left: string; right: string } | null {
    if (matchup.CounterfactualState !== 'unavailable-not-final') return null;
    const left = teamProjectedFinalScore(matchup, this.matchupTeamID(matchup, 'left'));
    const right = teamProjectedFinalScore(matchup, this.matchupTeamID(matchup, 'right'));
    if (left === null && right === null) return null;
    return { left: formatProjectionPoints(left), right: formatProjectionPoints(right) };
  }

  matchupRange(matchup: FantasyGameContextMatchup): MatchupRangeView | null {
    if (matchup.CounterfactualState !== 'unavailable-not-final') return null;
    const axis = matchup.Projection?.Axis;
    const level = this.data.context.ProjectionDisplay?.TeamRangeLevel;
    if (!axis || level === null || level === undefined) return null;

    const sides: MatchupDisplaySide[] = ['left', 'right'];
    const teams: MatchupRangeTeamView[] = [];
    const scored: number[] = [];
    for (const side of sides) {
      const teamID = this.matchupTeamID(matchup, side);
      const team = matchupProjectionTeam(matchup, teamID);
      const range = rangeAtLevel(team?.Ranges, level);
      if (!team || !range || team.ProjectedFinalScore === null) return null;
      const projected = formatProjectionPoints(team.ProjectedFinalScore);
      teams.push({
        label: this.teamShortName(teamID),
        avatar: this.teamAvatar(teamID),
        bar: rangeBarGeometry(range, axis),
        marker: axisPosition(team.ProjectedFinalScore, axis),
        projected,
        lower: String(Math.round(range.Lower)),
        upper: String(Math.round(range.Upper)),
        ariaLabel: `${this.teamName(teamID)} projected ${projected}, ${Math.round(level * 100)}% range ${Math.round(range.Lower)} to ${Math.round(range.Upper)}`
      });
      scored.push(team.ScoredPoints);
    }

    const ticks: Array<{ value: number; position: number }> = [];
    for (let value = axis.Min; value <= axis.Max; value += axis.Step) {
      ticks.push({ value, position: axisPosition(value, axis) });
    }
    return {
      levelLabel: `${Math.round(level * 100)}% range`,
      teams,
      ticks,
      scoredNote: scoredSoFarNote(scored[0], scored[1])
    };
  }

  playerProjection(row: FantasyGameContextMatchupGame, player: FantasyGamePlayerDisplay): PlayerProjectionView | null {
    if (player.ProjectedPoints === null || !this.showPlayerProjection(row, player)) return null;
    return playerProjectionView({
      projected: player.ProjectedPoints,
      range: player.ProjectedRange,
      axis: this.data.context.ProjectionDisplay?.PlayerRangeAxis ?? null
    });
  }

  showPlayerProjection(row: FantasyGameContextMatchupGame, player: FantasyGamePlayerDisplay): boolean {
    return player.IsStarter
      && player.ProjectedPoints !== null
      && !(this.hasMatchupGameScoring(row) && player.Points != null);
  }

  matchupStateLabel(matchup: FantasyGameContextMatchup): string {
    const remaining = matchup.RemainingRelevance;
    if (!remaining) return 'Current starter exposure';

    return matchupSportsStateLabel(
      remaining.State,
      this.teamShortName(matchup.TeamIDs[0]),
      this.teamShortName(matchup.TeamIDs[1])
    );
  }

  matchupGameStarterPoints(
    matchup: FantasyGameContextMatchup,
    row: FantasyGameContextMatchupGame,
    side: MatchupDisplaySide
  ): number {
    return matchupDisplaySideValue(
      matchup,
      this.displayTeamIDsFor(matchup),
      side,
      row.LeftStarterPoints,
      row.RightStarterPoints
    );
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
        matchups: this.data.matchups,
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

  private buildPlayerStatus(
    matchup: FantasyGameContextMatchup,
    displayTeamIDs: MatchupDisplayTeamIDs
  ): MatchupPlayerStatusTeamView[] {
    return buildMatchupPlayerStatus(matchup, displayTeamIDs, this.data.context, {
      teamName: teamID => this.teamName(teamID),
      teamAvatar: teamID => this.teamAvatar(teamID),
      player: playerID => ({
        name: this.playerName(playerID),
        picture: this.playerPicture(playerID),
        nflLogo: this.playerNflLogo(playerID)
      })
    });
  }

  private displayTeamIDsFor(matchup: FantasyGameContextMatchup): MatchupDisplayTeamIDs {
    if (this.matchup?.FantasyMatchupID === matchup.FantasyMatchupID && this.matchupTeamIDs) {
      return this.matchupTeamIDs;
    }

    return resolveMatchupDisplayTeamIDs(
      this.data.league,
      this.data.matchups,
      this.data.context.Season,
      this.data.context.Week,
      matchup
    );
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
      Points: legacy?.Points ?? null,
      ProjectedPoints: starterProjectedPoints(legacy),
      ProjectedRange: starterProjectedRange(legacy, this.data.context.ProjectionDisplay?.PlayerRangeLevel)
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
