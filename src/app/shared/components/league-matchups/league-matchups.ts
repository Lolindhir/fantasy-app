import { CommonModule } from '@angular/common';
import { Component, inject, Input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { catchError, combineLatest, map, of, shareReplay, tap, timer } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';
import type {
  FantasyTeam,
  League,
  PlacementRegularSeason
} from '../../../core/models/league.models';
import type {
  MatchupCompletionState,
  MatchupParticipant,
  MatchupsReadModel
} from '../../../core/models/matchup.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import type {
  WeeklyRecapKeyGame,
  WeeklyRecapKeyPlayer,
  WeeklyRecapsReadModel
} from '../../../core/models/weekly-recap.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import {
  getMustWatchGames,
  isFantasyGameContextForLeagueWeek
} from '../../utils/fantasy-game-context.util';
import {
  buildMatchupScoringWindow,
  buildMatchupScoreboardState,
  buildMatchupStarterProgress,
  findFantasyRelevanceTeam,
  type MatchupScoringWindowView,
  type MatchupScoreboardState,
  type MatchupStarterProgressView
} from '../../utils/matchups-overview-view.util';
import {
  buildOverviewTopContext,
  orderOverviewCurrentMatchups,
  resolveOverviewWeeklyPhase,
  selectOverviewRecap,
  type OverviewRecapSelection,
  type OverviewTopContext,
  type OverviewWeeklyPhase
} from '../../utils/overview-weekly-dashboard.util';
import {
  FantasyGameContextDialogComponent,
  type FantasyGameContextDialogData
} from '../fantasy-game-context-dialog/fantasy-game-context-dialog';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';

type LeagueMatchupContextMode = 'current' | 'previous';

interface LeagueMatchupTeamContextView {
  mode: LeagueMatchupContextMode;
  seasonLabel: string | null;
  standing: number | null;
  overallStanding: number | null;
  regularStanding: number | null;
  record: string | null;
  streak: string | null;
  pointsFor: number | null;
  pointsForDisplay: string | null;
}

interface LeagueMatchupTeamView {
  team: FantasyTeam;
  points: number | null;
  pointsDisplay: string;
  context: LeagueMatchupTeamContextView | null;
}

interface LeagueMatchupView {
  matchupID: string;
  completionState: MatchupCompletionState;
  left: LeagueMatchupTeamView;
  right: LeagueMatchupTeamView;
}

interface FantasyContextState {
  context: FantasyGameContextReadModel | null;
  decisionWindows: DecisionWindowsReadModel | null;
  matchups: MatchupsReadModel | null;
  nflTeams: NFLTeam[];
}

@Component({
  selector: 'app-league-matchups',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    TeamIdentityComponent
  ],
  templateUrl: './league-matchups.html',
  styleUrls: [
    './league-matchups.scss',
    './league-matchups-refinements.scss',
    './league-weekly-dashboard.scss'
  ]
})
export class LeagueMatchupsComponent {
  @Input({ required: true }) league!: League;

  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);
  private readonly teamDialog = inject(TeamDetailDialogService);
  private latestFantasyContextState: FantasyContextState | null = null;

  private readonly matchups$ = this.dataService.getMatchups().pipe(
    catchError(() => of(null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly matchupsReadModelSignal = toSignal(this.matchups$, { initialValue: null });

  private readonly weeklyRecaps$ = (this.dataService.getWeeklyRecaps?.() ?? of(null)).pipe(
    catchError(() => of(null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly weeklyRecapsSignal = toSignal<WeeklyRecapsReadModel | null>(this.weeklyRecaps$, { initialValue: null });

  private readonly nflTeams$ = this.dataService.getNflTeams().pipe(
    catchError(() => of([] as NFLTeam[])),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly nflTeamsSignal = toSignal(this.nflTeams$, { initialValue: [] as NFLTeam[] });

  private readonly nowSignal = toSignal(
    timer(0, 30_000).pipe(map(() => new Date())),
    { initialValue: new Date() }
  );

  readonly mobileTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly desktopTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name'];

  readonly fantasyContextState$ = combineLatest({
    context: this.dataService.getFantasyGameContext().pipe(catchError(() => of(null))),
    decisionWindows: this.dataService.getDecisionWindows().pipe(catchError(() => of(null))),
    matchups: this.matchups$,
    nflTeams: this.nflTeams$
  }).pipe(
    map(state => state satisfies FantasyContextState),
    tap(state => this.latestFantasyContextState = state),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly pointsForFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  });

  private readonly matchupScoreFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });

  private readonly nflScoreFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

  get weeklyDashboardEnabled(): boolean {
    return !this.league?.Status || ['Pre-Season', 'In-Season', 'Playoffs'].includes(this.league.Status);
  }

  get hasOverviewContextData(): boolean {
    return Array.isArray(this.league?.Standings)
      && Array.isArray(this.league?.Teams)
      && this.league.Teams.every(team => !!team.Placements);
  }

  get week(): number | null {
    return this.currentMatchupsReadModel()?.Summary.ActiveOrNextWeek ?? null;
  }

  get overviewPhase(): OverviewWeeklyPhase {
    return resolveOverviewWeeklyPhase(this.currentMatchupsReadModel(), this.nowSignal());
  }

  get topContext(): OverviewTopContext | null {
    if (!this.hasOverviewContextData) return null;
    return buildOverviewTopContext(this.league, this.currentMatchupsReadModel());
  }

  get weeklyRecap(): OverviewRecapSelection | null {
    const lastCompletedWeek = this.topContext?.lastCompletedWeek ?? null;
    return selectOverviewRecap(
      this.weeklyRecapsSignal(),
      this.league.Season,
      lastCompletedWeek,
      this.overviewPhase
    );
  }

  get matchups(): LeagueMatchupView[] {
    const readModel = this.currentMatchupsReadModel();
    const week = this.week;
    if (!readModel || week === null) return [];

    const weekModel = readModel.Weeks.find(candidate => candidate.Week === week);
    if (!weekModel) return [];

    const teamByID = new Map(this.league.Teams.map(team => [team.TeamID, team]));
    const ordered = orderOverviewCurrentMatchups(this.league, weekModel.Matchups);

    return ordered
      .filter(matchup => matchup.Participants.length === 2)
      .map(matchup => {
        const participants = matchup.Participants
          .map(participant => this.mapParticipant(participant, teamByID))
          .filter((participant): participant is LeagueMatchupTeamView => !!participant);

        if (participants.length !== 2) return null;

        return {
          matchupID: matchup.FantasyMatchupID,
          completionState: matchup.CompletionState,
          left: participants[0],
          right: participants[1]
        };
      })
      .filter((matchup): matchup is LeagueMatchupView => !!matchup);
  }

  currentContext(context: FantasyGameContextReadModel | null): FantasyGameContextReadModel | null {
    return isFantasyGameContextForLeagueWeek(context, this.league.Season, this.week) ? context : null;
  }

  matchupContext(
    matchup: LeagueMatchupView,
    context: FantasyGameContextReadModel | null
  ): FantasyGameContextMatchup | null {
    const current = this.currentContext(context);
    if (!current) return null;
    return current.FantasyMatchups.find(candidate => candidate.FantasyMatchupID === matchup.matchupID) ?? null;
  }

  scoreboardState(matchup: LeagueMatchupView): MatchupScoreboardState {
    const decisionWindows = this.latestFantasyContextState?.decisionWindows;
    return buildMatchupScoreboardState(matchup.completionState, [
      findFantasyRelevanceTeam(decisionWindows, matchup.left.team.TeamID),
      findFantasyRelevanceTeam(decisionWindows, matchup.right.team.TeamID)
    ]);
  }

  starterProgress(
    matchup: LeagueMatchupView,
    state: FantasyContextState,
    side: 'left' | 'right'
  ): MatchupStarterProgressView | null {
    const resolved = this.matchupContext(matchup, state.context);
    const team = side === 'left' ? matchup.left.team : matchup.right.team;
    return buildMatchupStarterProgress(
      findFantasyRelevanceTeam(state.decisionWindows, team.TeamID),
      resolved?.RemainingRelevance?.NextScoringWindowID ?? null,
      side
    );
  }

  scoringWindow(
    matchup: LeagueMatchupView,
    state: FantasyContextState
  ): MatchupScoringWindowView | null {
    return buildMatchupScoringWindow(
      this.matchupContext(matchup, state.context),
      this.currentContext(state.context)
    );
  }

  openMatchupDetailFromOverview(matchup: LeagueMatchupView): void {
    if (this.latestFantasyContextState) this.openMatchupDetail(matchup, this.latestFantasyContextState);
  }

  matchupAriaLabel(matchup: LeagueMatchupView): string {
    return `Open ${this.teamShortName(matchup.left.team)} versus ${this.teamShortName(matchup.right.team)} matchup details`;
  }

  teamShortName(team: FantasyTeam): string {
    return team.TeamAbbr?.trim() || team.Team?.trim() || team.Owner;
  }

  teamDisplayName(team: FantasyTeam): string {
    return team.Team?.trim() || team.Owner || `Team ${team.TeamID}`;
  }

  standingsRecord(team: FantasyTeam): string | null {
    const placement = team.Placements?.Current?.Regular;
    return placement ? this.formatRecord(placement) : null;
  }

  teamShortNameByID(teamID: string | number): string {
    const team = this.teamForID(teamID);
    return team ? this.teamShortName(team) : `Team ${teamID}`;
  }

  teamAvatar(teamID: string | number): string | null {
    return this.teamForID(teamID)?.Avatar || null;
  }

  affectedFantasyTeamIDs(game: FantasyGameContextGame): Array<string | number> {
    const source = game.FantasyTeams
      .filter(team => team.StarterCount > 0)
      .map(team => team.FantasyTeamID);
    const seen = new Set<string>();
    return source.filter(teamID => {
      const key = String(teamID);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  mustWatchGames(context: FantasyGameContextReadModel | null): FantasyGameContextGame[] {
    const current = this.currentContext(context);
    return current ? getMustWatchGames(current).slice(0, 5) : [];
  }

  nflLogo(teamID: string | number): string | null {
    return this.nflTeamsSignal().find(team => String(team.ID) === String(teamID))?.Logo || null;
  }

  nflAbbr(teamID: string | number): string {
    const team = this.nflTeamsSignal().find(candidate => String(candidate.ID) === String(teamID));
    return team?.Abv || String(teamID);
  }

  gameIsLiveForFantasy(game: FantasyGameContextGame): boolean {
    return (game.RemainingRelevance?.LockedActiveStarterCount ?? 0) > 0;
  }

  gameIsFinal(game: FantasyGameContextGame): boolean {
    return /^Final/i.test(game.Status ?? '');
  }

  hasNflScore(game: FantasyGameContextGame): boolean {
    return this.gameIsFinal(game)
      && game.AwayScore !== null
      && game.AwayScore !== undefined
      && game.HomeScore !== null
      && game.HomeScore !== undefined;
  }

  formatFantasyPoints(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.matchupScoreFormatter.format(Number(value));
  }

  formatNflScore(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
    return this.nflScoreFormatter.format(Number(value));
  }

  recapGameAriaLabel(game: WeeklyRecapKeyGame): string {
    return `${this.nflAbbr(game.AwayNFLTeamID)} at ${this.nflAbbr(game.HomeNFLTeamID)}, ${this.formatNflScore(game.AwayScore)} to ${this.formatNflScore(game.HomeScore)}`;
  }

  recapPlayer(player: WeeklyRecapKeyPlayer): Player | null {
    for (const team of this.league.Teams) {
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

  recapPlayerNflLogo(player: WeeklyRecapKeyPlayer): string | null {
    return this.recapPlayer(player)?.TeamNFL?.Logo || null;
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

  openTeam(teamID: string | number): void {
    const numericID = Number(teamID);
    if (Number.isFinite(numericID)) this.teamDialog.open(numericID);
  }

  openGameDetail(game: FantasyGameContextGame, state: FantasyContextState): void {
    const current = this.currentContext(state.context);
    if (!current) return;
    this.openContextDialog({
      mode: 'game',
      context: current,
      decisionWindows: state.decisionWindows,
      matchups: state.matchups,
      nflTeams: state.nflTeams,
      league: this.league,
      gameId: game.GameID
    });
  }

  openMatchupDetail(matchup: LeagueMatchupView, state: FantasyContextState): void {
    const current = this.currentContext(state.context);
    if (!current) return;
    const resolved = this.matchupContext(matchup, current);
    if (!resolved) return;
    this.openContextDialog({
      mode: 'matchup',
      context: current,
      decisionWindows: state.decisionWindows,
      matchups: state.matchups,
      nflTeams: state.nflTeams,
      league: this.league,
      fantasyMatchupId: resolved.FantasyMatchupID
    });
  }

  private openContextDialog(data: FantasyGameContextDialogData): void {
    this.dialog.open(FantasyGameContextDialogComponent, {
      data,
      width: 'calc(100vw - 16px)',
      maxWidth: '760px',
      maxHeight: 'calc(100dvh - 16px)',
      autoFocus: false,
      restoreFocus: true,
      panelClass: 'fantasy-context-dialog-panel'
    });
  }

  private mapParticipant(
    participant: MatchupParticipant,
    teamByID: Map<number, FantasyTeam>
  ): LeagueMatchupTeamView | null {
    const team = teamByID.get(participant.TeamID);
    if (!team) return null;

    return {
      team,
      points: participant.Points,
      pointsDisplay: this.formatFantasyPoints(participant.Points),
      context: this.getTeamContext(team)
    };
  }

  private currentMatchupsReadModel(): MatchupsReadModel | null {
    const readModel = this.matchupsReadModelSignal();
    return readModel?.Season === this.league.Season ? readModel : null;
  }

  private getTeamContext(team: FantasyTeam): LeagueMatchupTeamContextView | null {
    if (this.league.FinalScoredWeek > 0) {
      const placement = team.Placements?.Current?.Regular;
      if (!placement) return null;

      const standing = this.normalizeStanding(placement.Place);
      const record = this.formatRecord(placement);
      const streak = placement.Streak?.trim() || null;
      const pointsFor = Number.isFinite(placement.Points) ? placement.Points : null;

      if (standing === null && !record && !streak && pointsFor === null) return null;
      return {
        mode: 'current',
        seasonLabel: null,
        standing,
        overallStanding: null,
        regularStanding: standing,
        record,
        streak,
        pointsFor,
        pointsForDisplay: pointsFor === null ? null : this.pointsForFormatter.format(pointsFor)
      };
    }

    const regularPlacement = team.Placements?.Previous?.Regular;
    const overallStanding = this.normalizeStanding(team.Placements?.Previous?.Playoffs?.Place);
    const regularStanding = this.normalizeStanding(regularPlacement?.Place);
    const record = regularPlacement ? this.formatRecord(regularPlacement) : null;
    const pointsFor = regularPlacement && Number.isFinite(regularPlacement.Points)
      ? regularPlacement.Points
      : null;

    if (overallStanding === null && regularStanding === null && !record && pointsFor === null) return null;
    return {
      mode: 'previous',
      seasonLabel: this.previousSeasonLabel,
      standing: overallStanding,
      overallStanding,
      regularStanding,
      record,
      streak: regularPlacement?.Streak?.trim() || null,
      pointsFor,
      pointsForDisplay: pointsFor === null ? null : this.pointsForFormatter.format(pointsFor)
    };
  }

  private teamForID(teamID: string | number): FantasyTeam | null {
    return this.league.Teams.find(team => String(team.TeamID) === String(teamID)) ?? null;
  }

  private normalizeStanding(place: number | undefined): number | null {
    return Number.isFinite(place) && (place ?? 0) > 0 && (place ?? 999) < 999 ? place! : null;
  }

  private formatRecord(placement: PlacementRegularSeason): string | null {
    if (![placement.Wins, placement.Losses, placement.Ties].every(Number.isFinite)) return null;
    const baseRecord = `${placement.Wins}-${placement.Losses}`;
    return placement.Ties > 0 ? `${baseRecord}-${placement.Ties}` : baseRecord;
  }

  private get previousSeasonLabel(): string {
    const season = Number.parseInt(this.league.Season, 10);
    return Number.isFinite(season) ? String(season - 1) : 'Previous';
  }
}
