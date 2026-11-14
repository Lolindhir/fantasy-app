import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import type { FantasyTeam } from '../../../core/models/league.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import type {
  WeeklyRecapKeyGame,
  WeeklyPlayerAwardKey,
  WeeklyRecapKeyPlayer,
  WeeklyRecapPlayerAwardEntry,
  WeeklyRecapPlayerAwards,
  WeeklyRecapTeamAwards
} from '../../../core/models/weekly-recap.models';
import { findNflTeam } from '../../utils/nfl-team-key.util';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

/** The recap content of one week: games, players and awards (the data of OverviewRecapSelection). */
export interface WeekRecapContent {
  games: readonly WeeklyRecapKeyGame[];
  players: readonly WeeklyRecapKeyPlayer[];
  awards: WeeklyRecapTeamAwards | null;
  /** Weekly player awards (generator values); null when unavailable or absent. */
  playerAwards?: WeeklyRecapPlayerAwards | null;
  /** The biggest underdog win of the week (lowest pregame chance of a winner, generator marks); null when none. */
  underdog?: WeekRecapUpset | null;
  /** True when pregame chances are known for the week and no underdog won. */
  allFavoritesWon?: boolean;
}

/** One matchup the underdog won: the mark and the pregame chance of the winner come from the generator. */
export interface WeekRecapUpset {
  matchupID: string;
  level: 'upset' | 'underdog';
  winnerTeamID: string | number;
  loserTeamID: string | number | null;
  winnerChance: number | null;
}

/**
 * Presentational recap body shared by the Overview and the Weeks page. The surrounding shell and heading
 * stay with the host. Players that no longer resolve against the current rosters fall back to their ID.
 */
@Component({
  selector: 'app-week-recap-content',
  standalone: true,
  imports: [CommonModule, MatIconModule, PositionStylePipe],
  templateUrl: './week-recap-content.html'
})
export class WeekRecapContentComponent {
  @Input() recap: WeekRecapContent | null = null;
  @Input() teams: readonly FantasyTeam[] = [];
  @Input() nflTeams: readonly NFLTeam[] = [];
  @Input() emptyMessage = 'Completed-week recap data is not available yet.';

  private readonly dialog = inject(MatDialog);
  private readonly teamDialog = inject(TeamDetailDialogService);

  private readonly fantasyPointsFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
  private readonly efficiencyFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  });
  private readonly nflScoreFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

  readonly playerAwardDefs: ReadonlyArray<{ key: WeeklyPlayerAwardKey; label: string; icon: string; hint: string }> = [
    { key: 'MVP', label: 'Week MVP', icon: 'emoji_events', hint: 'Highest-scoring player of the week' },
    { key: 'MatchupHero', label: 'Matchup Hero', icon: 'bolt', hint: 'Decided a win that would otherwise have been lost' },
    { key: 'Heartbreaker', label: 'Heartbreaker', icon: 'heart_broken', hint: 'Big week, but the team still lost' },
    { key: 'UnsungHero', label: 'Unsung Hero', icon: 'chair', hint: 'Bench player who would have flipped a lost matchup' }
  ];

  /** Award chips with at least one winner, in fixed award order; awards without a winner are not shown. */
  playerAwardChips(): Array<{ key: WeeklyPlayerAwardKey; label: string; icon: string; hint: string; entries: readonly WeeklyRecapPlayerAwardEntry[] }> {
    const awards = this.recap?.playerAwards;
    if (!awards) return [];
    return this.playerAwardDefs
      .map(def => ({ ...def, entries: awards[def.key] ?? [] }))
      .filter(chip => chip.entries.length > 0);
  }

  awardPlayer(entry: WeeklyRecapPlayerAwardEntry): Player | null {
    if (entry.PlayerID === null) return null;
    for (const team of this.teams) {
      const resolved = team.Roster.find(candidate => String(candidate.ID) === String(entry.PlayerID));
      if (resolved) return resolved;
    }
    return null;
  }

  awardPlayerName(entry: WeeklyRecapPlayerAwardEntry): string {
    const resolved = this.awardPlayer(entry);
    return resolved?.NameShort || resolved?.Name || `Player ${entry.PlayerID ?? ''}`.trim();
  }

  /** NFL team logo of the resolved award player (same source as the common player rows); null when unresolved. */
  awardPlayerNflLogo(entry: WeeklyRecapPlayerAwardEntry): string | null {
    return (this.awardPlayer(entry)?.TeamNFL as NFLTeam | undefined)?.Logo || null;
  }

  awardPlayerPicture(entry: WeeklyRecapPlayerAwardEntry): string | null {
    return this.awardPlayer(entry)?.Picture || null;
  }

  openAwardPlayerDetail(entry: WeeklyRecapPlayerAwardEntry): void {
    const resolved = this.awardPlayer(entry);
    if (!resolved) return;
    this.dialog.open(PlayerDetailDialogComponent, { data: resolved, width: '800px', maxHeight: '90vh', panelClass: 'player-dialog' });
  }

  /** The Week MVP is also the number one of the key players; the badge only marks that player. */
  isWeekMvp(player: WeeklyRecapKeyPlayer): boolean {
    return (this.recap?.playerAwards?.MVP ?? []).some(entry => entry.PlayerID !== null && String(entry.PlayerID) === String(player.PlayerID));
  }

  nflLogo(teamID: string | number): string | null {
    return findNflTeam(this.nflTeams, teamID)?.Logo || null;
  }

  nflAbbr(teamID: string | number): string {
    return findNflTeam(this.nflTeams, teamID)?.Abv || String(teamID);
  }

  /** Awards describe the Owner, not the franchise logo or mixed team Avatar. */
  awardOwnerName(teamID: string | number): string {
    return this.teamForID(teamID)?.Owner?.trim() || `Team ${teamID}`;
  }

  awardOwnerAvatar(teamID: string | number): string | null {
    return this.teamForID(teamID)?.OwnerAvatar?.trim() || null;
  }

  /** Team name (not the manager) for the underdog row. */
  teamLabel(teamID: string | number): string {
    const team = this.teamForID(teamID);
    return team?.Team?.trim() || team?.TeamAbbr?.trim() || `Team ${teamID}`;
  }

  /** Short fantasy team label for compact player rows (TeamAbbr, then the team name). */
  teamAbbr(teamID: string | number): string {
    const team = this.teamForID(teamID);
    return team?.TeamAbbr?.trim() || team?.Team?.trim() || `T${teamID}`;
  }

  teamLogo(teamID: string | number): string | null {
    return this.teamForID(teamID)?.Avatar?.trim() || null;
  }

  awardTeamName(teamID: string | number): string | null {
    return this.teamForID(teamID)?.Team?.trim() || null;
  }

  awardTeamExists(teamID: string | number): boolean {
    return this.teamForID(teamID) !== null;
  }

  openAwardTeamDetails(teamID: string | number): void {
    const team = this.teamForID(teamID);
    if (team) this.teamDialog.open(team.TeamID);
  }


  upsetAriaLabel(upset: WeekRecapUpset): string {
    const winner = this.teamLabel(upset.winnerTeamID);
    const loser = upset.loserTeamID === null ? 'the favorite' : this.teamLabel(upset.loserTeamID);
    const chance = upset.winnerChance === null ? '' : ` with a ${upset.winnerChance} percent pregame chance`;
    return `Biggest underdog win${upset.level === 'upset' ? ' (upset)' : ''}: ${winner} beat ${loser}${chance}`;
  }

  formatAwardEfficiency(value: number): string {
    return Number.isFinite(value) ? this.efficiencyFormatter.format(value) : '–';
  }

  formatFantasyPoints(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.fantasyPointsFormatter.format(Number(value));
  }

  formatNflScore(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.nflScoreFormatter.format(Number(value));
  }

  recapGameAriaLabel(game: WeeklyRecapKeyGame): string {
    return `${this.nflAbbr(game.AwayNFLTeamID)} at ${this.nflAbbr(game.HomeNFLTeamID)}, ${this.formatNflScore(game.AwayScore)} to ${this.formatNflScore(game.HomeScore)}`;
  }

  recapPlayer(player: WeeklyRecapKeyPlayer): Player | null {
    for (const team of this.teams) {
      const resolved = team.Roster.find(candidate => String(candidate.ID) === String(player.PlayerID));
      if (resolved) return resolved;
    }
    return null;
  }

  recapPlayerName(player: WeeklyRecapKeyPlayer): string {
    const resolved = this.recapPlayer(player);
    return resolved?.NameShort || resolved?.Name || `Player ${player.PlayerID}`;
  }

  recapPlayerPicture(player: WeeklyRecapKeyPlayer): string | null {
    return this.recapPlayer(player)?.Picture || null;
  }

  recapPlayerDetailAvailable(player: WeeklyRecapKeyPlayer): boolean {
    return this.recapPlayer(player) !== null;
  }

  openRecapPlayerDetail(player: WeeklyRecapKeyPlayer): void {
    const resolved = this.recapPlayer(player);
    if (!resolved) return;

    this.dialog.open(PlayerDetailDialogComponent, {
      data: resolved,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  private teamForID(teamID: string | number): FantasyTeam | null {
    return this.teams.find(team => String(team.TeamID) === String(teamID)) ?? null;
  }
}
