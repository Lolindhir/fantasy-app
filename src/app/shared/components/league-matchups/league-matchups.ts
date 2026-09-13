import { CommonModule } from '@angular/common';
import { Component, inject, Input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { catchError, combineLatest, map, of, shareReplay, tap } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextMatchupGame,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';
import type {
  FantasyTeam,
  League,
  PlacementRegularSeason
} from '../../../core/models/league.models';
import type { MatchupParticipant, MatchupsReadModel } from '../../../core/models/matchup.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import {
  getCompletedImpactGames,
  getMustWatchGames,
  getNextFantasyMatchupGame,
  isFantasyGameContextForLeagueWeek,
  isFantasyMatchupFinalWindowGame
} from '../../utils/fantasy-game-context.util';
import {
  buildMatchupScoringWindow,
  buildMatchupStarterProgress,
  findFantasyRelevanceTeam,
  type MatchupScoringWindowView,
  type MatchupStarterProgressView
} from '../../utils/matchups-overview-view.util';
import {
  FantasyGameContextDialogComponent,
  type FantasyGameContextDialogData
} from '../fantasy-game-context-dialog/fantasy-game-context-dialog';
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
  left: LeagueMatchupTeamView;
  right: LeagueMatchupTeamView;
}

interface FantasyContextState {
  context: FantasyGameContextReadModel | null;
  decisionWindows: DecisionWindowsReadModel | null;
  matchups: MatchupsReadModel | null;
  nflTeams: NFLTeam[];
}

interface FantasyMatchupPreviewEventView {
  game: FantasyGameContextMatchupGame;
  contextGame: FantasyGameContextGame | null;
  starterCount: number;
  optionCount: number;
}

interface FantasyMatchupPreviewView {
  primary: FantasyMatchupPreviewEventView;
  isLive: boolean;
  isFinalWindow: boolean;
  isFinalWindowCommitted: boolean;
}

@Component({
  selector: 'app-league-matchups',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatIconModule, TeamIdentityComponent],
  templateUrl: './league-matchups.html',
  styleUrls: ['./league-matchups.scss', './league-matchups-refinements.scss']
})
export class LeagueMatchupsComponent {
  @Input({ required: true }) league!: League;

  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);
  private readonly teamDialog = inject(TeamDetailDialogService);
  private latestFantasyContextState: FantasyContextState | null = null;
  private readonly expandedScoringWindows = new Set<string>();
  private readonly matchups$ = this.dataService.getMatchups().pipe(
    catchError(() => of(null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly matchupsReadModelSignal = toSignal(this.matchups$, { initialValue: null });

  readonly mobileTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly desktopTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name'];

  readonly fantasyContextState$ = combineLatest({
    context: this.dataService.getFantasyGameContext().pipe(catchError(() => of(null))),
    decisionWindows: this.dataService.getDecisionWindows().pipe(catchError(() => of(null))),
    matchups: this.matchups$,
    nflTeams: this.dataService.getNflTeams().pipe(catchError(() => of([] as NFLTeam[])))
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

  get week(): number | null {
    return this.currentMatchupsReadModel()?.Summary.ActiveOrNextWeek ?? null;
  }

  get matchups(): LeagueMatchupView[] {
    const readModel = this.currentMatchupsReadModel();
    const week = this.week;
    if (!readModel || week === null) return [];

    const weekModel = readModel.Weeks.find(candidate => candidate.Week === week);
    if (!weekModel) return [];

    const teamByID = new Map(this.league.Teams.map(team => [team.TeamID, team]));

    return weekModel.Matchups
      .filter(matchup => matchup.Participants.length === 2)
      .map(matchup => {
        const participants = matchup.Participants
          .map(participant => this.mapParticipant(participant, teamByID))
          .filter((participant): participant is LeagueMatchupTeamView => !!participant);

        if (participants.length !== 2) return null;

        return {
          matchupID: matchup.FantasyMatchupID,
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

  scoringWindowGames(matchupID: string, scoringWindow: MatchupScoringWindowView): FantasyGameContextGame[] {
    return this.expandedScoringWindows.has(this.scoringWindowKey(matchupID, scoringWindow.decisionWindowID))
      ? scoringWindow.games
      : scoringWindow.mobileVisibleGames;
  }

  isScoringWindowExpanded(matchupID: string, scoringWindow: MatchupScoringWindowView): boolean {
    return this.expandedScoringWindows.has(this.scoringWindowKey(matchupID, scoringWindow.decisionWindowID));
  }

  expandScoringWindow(matchupID: string, scoringWindow: MatchupScoringWindowView): void {
    this.expandedScoringWindows.add(this.scoringWindowKey(matchupID, scoringWindow.decisionWindowID));
  }

  openMatchupDetailFromOverview(matchup: LeagueMatchupView): void {
    if (this.latestFantasyContextState) this.openMatchupDetail(matchup, this.latestFantasyContextState);
  }

  matchupAriaLabel(matchup: LeagueMatchupView): string {
    return `Open ${this.teamShortName(matchup.left.team)} versus ${this.teamShortName(matchup.right.team)} matchup details`;
  }

  matchupPreview(
    matchup: LeagueMatchupView,
    context: FantasyGameContextReadModel | null
  ): FantasyMatchupPreviewView | null {
    const current = this.currentContext(context);
    if (!current) return null;
    const resolved = this.matchupContext(matchup, current);
    if (!resolved) return null;

    const remaining = resolved.RemainingRelevance;
    const scoringGame = getNextFantasyMatchupGame(resolved);
    if (!scoringGame) return null;

    const starterCount = remaining?.NextScoringLockedActiveStarterCount !== undefined
      && remaining?.NextScoringUnlockedStarterCount !== undefined
      ? remaining.NextScoringLockedActiveStarterCount + remaining.NextScoringUnlockedStarterCount
      : scoringGame.LeftStarterCount + scoringGame.RightStarterCount;

    if (starterCount <= 0) return null;

    const scoring = this.buildPreviewEvent(
      scoringGame,
      current,
      starterCount,
      remaining?.NextScoringOptionCount ?? 0
    );

    return {
      primary: scoring,
      isLive: scoring.contextGame
        ? this.gameIsLiveForFantasy(scoring.contextGame)
        : (remaining?.NextScoringLockedActiveStarterCount ?? 0) > 0,
      isFinalWindow: isFantasyMatchupFinalWindowGame(resolved, scoring.game.GameID),
      isFinalWindowCommitted: remaining?.IsFinalScoringWindowCommitted ?? false
    };
  }

  teamShortName(team: FantasyTeam): string {
    return team.TeamAbbr?.trim() || team.Team?.trim() || team.Owner;
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

  completedGames(context: FantasyGameContextReadModel | null): FantasyGameContextGame[] {
    const current = this.currentContext(context);
    return current ? getCompletedImpactGames(current).slice(0, 5) : [];
  }

  nflLogo(teamID: string | number, nflTeams: NFLTeam[]): string | null {
    return nflTeams.find(team => String(team.ID) === String(teamID))?.Logo || null;
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

  private buildPreviewEvent(
    game: FantasyGameContextMatchupGame,
    context: FantasyGameContextReadModel,
    starterCount: number,
    optionCount: number
  ): FantasyMatchupPreviewEventView {
    return {
      game,
      contextGame: context.Games.find(candidate => candidate.GameID === game.GameID) ?? null,
      starterCount,
      optionCount
    };
  }

  private scoringWindowKey(matchupID: string, decisionWindowID: string): string {
    return `${matchupID}|${decisionWindowID}`;
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

    const points = participant.Points;

    return {
      team,
      points,
      pointsDisplay: this.formatFantasyPoints(points),
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
      standing: null,
      overallStanding,
      regularStanding,
      record,
      streak: null,
      pointsFor,
      pointsForDisplay: pointsFor === null ? null : this.pointsForFormatter.format(pointsFor)
    };
  }

  private teamForID(teamID: string | number): FantasyTeam | null {
    return this.league.Teams.find(team => String(team.TeamID) === String(teamID)) ?? null;
  }

  private normalizeStanding(place: number | undefined): number | null {
    return Number.isFinite(place) && (place ?? 0) > 0 ? place! : null;
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
