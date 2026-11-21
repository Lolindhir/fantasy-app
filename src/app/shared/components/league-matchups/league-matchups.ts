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
  FantasyGameMarket,
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
import type { NFLTeam } from '../../../core/models/player.models';
import type { WeeklyRecapsReadModel } from '../../../core/models/weekly-recap.models';
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
  resolveOverviewDisplayWeek,
  resolveOverviewWeeklyPhase,
  selectOverviewRecap,
  type OverviewRecapSelection,
  type OverviewStandingRow,
  type OverviewTopContext,
  type OverviewWeeklyPhase
} from '../../utils/overview-weekly-dashboard.util';
import { playoffLockedPlace, playoffMarker, resolvePlayoffOdds, type PlayoffOddsView } from '../../utils/schedule-outlook-view.util';
import type { ScheduleOutlookReadModel } from '../../../core/models/schedule-outlook.models';
import { formatProjectionPoints } from '../../utils/projection-range.util';
import { WinChanceBarComponent } from '../win-chance-bar/win-chance-bar';
import {
  type FantasyGameContextDialogData
} from '../fantasy-game-context-dialog/fantasy-game-context-dialog';
import { ChampionBadgeComponent } from '../champion-badge/champion-badge';
import { WeekRecapContentComponent } from '../week-recap-content/week-recap-content';
import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';
import { findNflTeam } from '../../utils/nfl-team-key.util';
import { TeamRivalryService, formatRivalryRecord } from '../../services/team-rivalry.service';

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
    TeamIdentityComponent,
    WeekRecapContentComponent,
    ChampionBadgeComponent,
    WinChanceBarComponent
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
  private readonly rivalryService = inject(TeamRivalryService);
  private latestFantasyContextState: FantasyContextState | null = null;

  private readonly matchups$ = this.dataService.getMatchups().pipe(
    catchError(() => of(null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly matchupsReadModelSignal = toSignal(this.matchups$, { initialValue: null });

  private readonly rivalryLookupSignal = toSignal(
    this.rivalryService.getLookup().pipe(catchError(() => of(null))),
    { initialValue: null }
  );

  private readonly weeklyRecaps$ = (this.dataService.getWeeklyRecaps?.() ?? of(null)).pipe(
    catchError(() => of(null)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  private readonly weeklyRecapsSignal = toSignal<WeeklyRecapsReadModel | null>(this.weeklyRecaps$, { initialValue: null });

  private readonly scheduleOutlookSignal = toSignal<ScheduleOutlookReadModel | null>(
    (this.dataService.getScheduleOutlook?.() ?? of(null)).pipe(catchError(() => of(null))),
    { initialValue: null }
  );

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

  private readonly fantasyContextStateSignal = toSignal(this.fantasyContextState$, {
    initialValue: {
      context: null,
      decisionWindows: null,
      matchups: null,
      nflTeams: []
    } as FantasyContextState
  });

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

  get playoffCutlineStartPlace(): number | null {
    const playoffTeams = this.league?.Settings?.['playoff_teams'];
    const teamCount = this.league?.Teams?.length ?? 0;
    return typeof playoffTeams === 'number'
      && Number.isInteger(playoffTeams)
      && playoffTeams > 0
      && playoffTeams < teamCount
      ? playoffTeams + 1
      : null;
  }

  /** Generated playoff status (Issue #1588); null unless the current season's regular season is running. */
  get playoffOdds(): PlayoffOddsView | null {
    const outlook = this.scheduleOutlookSignal();
    const season = this.league?.Season;
    if (!this.playoffOddsMemo || this.playoffOddsMemo.outlook !== outlook || this.playoffOddsMemo.season !== season) {
      this.playoffOddsMemo = { outlook, season, value: resolvePlayoffOdds(outlook, season) };
    }
    return this.playoffOddsMemo!.value;
  }
  private playoffOddsMemo: { outlook: ScheduleOutlookReadModel | null; season: string | undefined; value: PlayoffOddsView | null } | null = null;

  get playoffLegend(): { clinched: boolean; eliminated: boolean } {
    const teams = [...(this.playoffOdds?.teams.values() ?? [])];
    return { clinched: teams.some(team => team.status === 'clinched'), eliminated: teams.some(team => team.status === 'eliminated') };
  }

  playoffFlag(row: OverviewStandingRow): 'x' | 'e' | null {
    return playoffMarker(this.playoffOdds, row.team.TeamID);
  }

  playoffFlagPlace(row: OverviewStandingRow): number | null {
    return playoffLockedPlace(this.playoffOdds, row.team.TeamID);
  }

  get playoffLegendPlace(): boolean {
    const teams = [...(this.playoffOdds?.teams.keys() ?? [])];
    return teams.some(id => playoffLockedPlace(this.playoffOdds, id) !== null);
  }

  playoffFlagLabel(row: OverviewStandingRow): string | null {
    const flag = this.playoffFlag(row);
    const place = this.playoffFlagPlace(row);
    const base = flag === 'x' ? 'Clinched a playoff place' : flag === 'e' ? 'Eliminated from playoff contention' : null;
    return base === null ? null : place === null ? base : `${base}; final place ${place} is locked`;
  }

  get hasOverviewContextData(): boolean {
    return Array.isArray(this.league?.Standings)
      && Array.isArray(this.league?.Teams)
      && this.league.Teams.every(team => !!team.Placements);
  }

  get week(): number | null {
    const state = this.fantasyContextStateSignal();
    return resolveOverviewDisplayWeek(
      this.league,
      this.currentMatchupsReadModel(),
      state.decisionWindows,
      state.context
    );
  }

  get currentWeekSurfaceReady(): boolean {
    const readModel = this.currentMatchupsReadModel();
    const week = this.week;
    return week !== null && !!readModel?.Weeks.find(candidate => candidate.Week === week);
  }

  get overviewPhase(): OverviewWeeklyPhase {
    return resolveOverviewWeeklyPhase(this.currentMatchupsReadModel(), this.nowSignal(), this.week);
  }

  get topContext(): OverviewTopContext | null {
    if (!this.hasOverviewContextData) return null;
    return buildOverviewTopContext(this.league, this.currentMatchupsReadModel(), this.week);
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
    if (!this.currentWeekSurfaceReady) return [];

    const readModel = this.currentMatchupsReadModel();
    const week = this.week;
    if (!readModel || week === null) return [];

    const weekModel = readModel.Weeks.find(candidate => candidate.Week === week);
    if (!weekModel) return [];

    const teamByID = new Map(this.league.Teams.map(team => [team.TeamID, team]));
    const ordered = orderOverviewCurrentMatchups(this.league, weekModel.Matchups, this.topContext?.standings ?? null);

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

  /** All-time record of the left team against the right team ("3-2") from Rivalry.json; null without a counted game. */
  headToHead(matchup: LeagueMatchupView): string | null {
    const record = this.rivalryLookupSignal()?.headToHead(Number(matchup.left.team.TeamID), Number(matchup.right.team.TeamID));
    return record ? formatRivalryRecord(record) : null;
  }

  /** Tone of the all-time record from the left team's view: lead (green), trail (red) or tie. */
  headToHeadTone(matchup: LeagueMatchupView): 'lead' | 'trail' | 'tie' | null {
    const record = this.rivalryLookupSignal()?.headToHead(Number(matchup.left.team.TeamID), Number(matchup.right.team.TeamID));
    if (!record) return null;
    return record.wins > record.losses ? 'lead' : record.wins < record.losses ? 'trail' : 'tie';
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

  matchupProjection(
    matchup: LeagueMatchupView,
    context: FantasyGameContextReadModel | null
  ): { left: string; right: string; leftFallback: boolean; rightFallback: boolean } | null {
    if (matchup.completionState === 'final') return null;
    const teams = this.matchupContext(matchup, context)?.Projection?.Teams;
    if (!teams) return null;

    const teamOf = (teamID: string | number) =>
      teams.find(team => String(team.FantasyTeamID) === String(teamID));
    const leftTeam = teamOf(matchup.left.team.TeamID);
    const rightTeam = teamOf(matchup.right.team.TeamID);
    const left = leftTeam?.DisplayProjectedScore ?? leftTeam?.ProjectedFinalScore ?? null;
    const right = rightTeam?.DisplayProjectedScore ?? rightTeam?.ProjectedFinalScore ?? null;
    if (left === null && right === null) return null;

    const usesFallback = (team: typeof leftTeam) =>
      team?.DisplayProjectionMethod === 'season-bestball-actual-efficiency-v1';
    return {
      left: formatProjectionPoints(left), right: formatProjectionPoints(right),
      leftFallback: usesFallback(leftTeam), rightFallback: usesFallback(rightTeam)
    };
  }

  /** Generated chance of an open matchup; raw fractions avoid mistaken 0/100 from rounded values. */
  winChance(
    matchup: LeagueMatchupView,
    context: FantasyGameContextReadModel | null
  ): { left: number; right: number; leftRaw: number | null; rightRaw: number | null; deterministic: boolean; live: boolean; estimated: boolean } | null {
    if (matchup.completionState === 'final') return null;
    const teams = this.matchupContext(matchup, context)?.Projection?.Teams;
    if (!teams) return null;
    const find = (teamID: string | number) => teams.find(team => String(team.FantasyTeamID) === String(teamID));
    const left = find(matchup.left.team.TeamID);
    const right = find(matchup.right.team.TeamID);
    const leftChance = left?.DisplayWinProbability ?? left?.WinProbability;
    const rightChance = right?.DisplayWinProbability ?? right?.WinProbability;
    if (leftChance == null || rightChance == null || !left || !right) return null;
    return {
      left: leftChance,
      right: rightChance,
      leftRaw: left.DisplayWinProbabilityRaw ?? left.WinProbabilityRaw ?? null,
      rightRaw: right.DisplayWinProbabilityRaw ?? right.WinProbabilityRaw ?? null,
      deterministic: (left.DisplayWinProbabilityIsDeterministic ?? left.WinProbabilityIsDeterministic) === true
        && (right.DisplayWinProbabilityIsDeterministic ?? right.WinProbabilityIsDeterministic) === true,
      live: left.FinalStarterCount > 0 || right.FinalStarterCount > 0,
      estimated: left.DisplayWinProbabilityBasis === 'season-bestball-efficiency-estimate'
        || right.DisplayWinProbabilityBasis === 'season-bestball-efficiency-estimate'
    };
  }

  scoreboardState(matchup: LeagueMatchupView): MatchupScoreboardState {
    const decisionWindows = this.currentDecisionWindows();
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

  standingMovementText(placeDelta: number | null): string {
    if (placeDelta === null || placeDelta === 0) return '—';
    return placeDelta > 0 ? `▲${placeDelta}` : `▼${Math.abs(placeDelta)}`;
  }

  standingMovementLabel(placeDelta: number | null): string {
    if (placeDelta === null) return 'No previous week available';
    if (placeDelta === 0) return 'No change since last week';

    const places = Math.abs(placeDelta);
    const unit = places === 1 ? 'place' : 'places';
    return `Moved ${placeDelta > 0 ? 'up' : 'down'} ${places} ${unit} since last week`;
  }

  teamDisplayName(team: FantasyTeam): string {
    return team.Team?.trim() || team.Owner || `Team ${team.TeamID}`;
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

  get nflTeams(): NFLTeam[] {
    return this.nflTeamsSignal();
  }

  nflLogo(teamID: string | number): string | null {
    return findNflTeam(this.nflTeamsSignal(), teamID)?.Logo || null;
  }

  gameIsLiveForFantasy(game: FantasyGameContextGame): boolean {
    // Generated locked-active starters are evidence of the live NFL window, not
    // a real-time NFL score. Final is authoritative even for stale locked paths.
    return !this.gameIsFinal(game) && (game.RemainingRelevance?.LockedActiveStarterCount ?? 0) > 0;
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

  hasImpliedNflScores(market: FantasyGameMarket): boolean {
    return market.ImpliedAwayPoints !== null && Number.isFinite(market.ImpliedAwayPoints)
      && market.ImpliedHomePoints !== null && Number.isFinite(market.ImpliedHomePoints);
  }

  formatImpliedNflScore(value: number | null): string {
    return value === null || !Number.isFinite(value) ? '–' : `≈${this.nflScoreFormatter.format(value)}`;
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
      fantasyMatchupId: resolved.FantasyMatchupID,
      headToHead: this.headToHead(matchup),
      headToHeadTone: this.headToHeadTone(matchup)
    });
  }

  private openContextDialog(data: FantasyGameContextDialogData): void {
    void import('../fantasy-game-context-dialog/fantasy-game-context-dialog').then(({ FantasyGameContextDialogComponent }) => {
      this.dialog.open(FantasyGameContextDialogComponent, {
        data,
        width: 'calc(100vw - 16px)',
        maxWidth: '760px',
        maxHeight: 'calc(100dvh - 16px)',
        autoFocus: false,
        restoreFocus: true,
        panelClass: 'fantasy-context-dialog-panel'
      });
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
    const displayWeek = this.week;
    const snapshot = displayWeek !== null && displayWeek > 1
      ? this.overviewStandingForTeam(team.TeamID)
      : null;
    if (snapshot) {
      const standing = this.normalizeStanding(snapshot.displayPlace);
      const pointsFor = Number.isFinite(snapshot.points) ? snapshot.points : null;
      return {
        mode: 'current',
        seasonLabel: null,
        standing,
        overallStanding: null,
        regularStanding: standing,
        record: snapshot.record,
        streak: snapshot.streak,
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

  private overviewStandingForTeam(teamID: string | number): OverviewStandingRow | null {
    return this.topContext?.standings.find(row => String(row.team.TeamID) === String(teamID)) ?? null;
  }

  private currentDecisionWindows(): DecisionWindowsReadModel | null {
    const decisionWindows = this.latestFantasyContextState?.decisionWindows ?? null;
    return decisionWindows
      && decisionWindows.Season === this.league.Season
      && decisionWindows.LineupWeek === this.week
      ? decisionWindows
      : null;
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
