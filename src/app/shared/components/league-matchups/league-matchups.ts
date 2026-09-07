import { CommonModule } from '@angular/common';
import { Component, inject, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { catchError, map, of, shareReplay } from 'rxjs';

import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextMatchupGame,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';
import type {
  FantasyTeam,
  League,
  LeagueMatchupParticipant,
  PlacementRegularSeason
} from '../../../core/models/league.models';
import { DataService } from '../../../core/services/data.service';
import {
  getCompletedImpactGames,
  getFantasyMatchupContext,
  getNextFantasyMatchupGame,
  getUpcomingRelevantGames,
  isFantasyGameContextForLeagueWeek
} from '../../utils/fantasy-game-context.util';
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
  points: number;
  pointsDisplay: string;
  context: LeagueMatchupTeamContextView | null;
}

interface LeagueMatchupView {
  matchupID: number;
  left: LeagueMatchupTeamView;
  right: LeagueMatchupTeamView;
  showScore: boolean;
}

interface FantasyContextState {
  context: FantasyGameContextReadModel | null;
}

@Component({
  selector: 'app-league-matchups',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatIconModule, TeamIdentityComponent],
  templateUrl: './league-matchups.html',
  styleUrl: './league-matchups.scss'
})
export class LeagueMatchupsComponent {
  @Input({ required: true }) league!: League;

  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);

  readonly mobileTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr', 'owner'];
  readonly desktopTeamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name', 'owner'];

  readonly fantasyContextState$ = this.dataService.getFantasyGameContext().pipe(
    map(context => ({ context }) satisfies FantasyContextState),
    catchError(() => of({ context: null } satisfies FantasyContextState)),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  private readonly pointsForFormatter = new Intl.NumberFormat('de-DE', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  });

  private readonly matchupScoreFormatter = new Intl.NumberFormat('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });

  get week(): number | null {
    return this.league.Matchups?.Week ?? null;
  }

  get matchups(): LeagueMatchupView[] {
    const snapshot = this.league.Matchups;
    if (!snapshot || snapshot.Season !== this.league.Season) return [];

    const teamByID = new Map(this.league.Teams.map(team => [team.TeamID, team]));

    return snapshot.Matchups
      .filter(matchup => matchup.Participants.length === 2)
      .map(matchup => {
        const participants = matchup.Participants
          .map(participant => this.mapParticipant(participant, teamByID))
          .filter((participant): participant is LeagueMatchupTeamView => !!participant);

        if (participants.length !== 2) return null;

        return {
          matchupID: matchup.MatchupID,
          left: participants[0],
          right: participants[1],
          showScore: participants.some(participant => participant.points > 0)
        };
      })
      .filter((matchup): matchup is LeagueMatchupView => !!matchup)
      .sort((left, right) => left.matchupID - right.matchupID);
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
    return getFantasyMatchupContext(current, [matchup.left.team.TeamID, matchup.right.team.TeamID]);
  }

  matchupPreview(
    matchup: LeagueMatchupView,
    context: FantasyGameContextReadModel | null
  ): FantasyGameContextMatchupGame | null {
    const resolved = this.matchupContext(matchup, context);
    return resolved ? getNextFantasyMatchupGame(resolved) : null;
  }

  upcomingGames(context: FantasyGameContextReadModel | null): FantasyGameContextGame[] {
    const current = this.currentContext(context);
    return current ? getUpcomingRelevantGames(current).slice(0, 5) : [];
  }

  completedGames(context: FantasyGameContextReadModel | null): FantasyGameContextGame[] {
    const current = this.currentContext(context);
    return current ? getCompletedImpactGames(current).slice(0, 5) : [];
  }

  openGameDetail(game: FantasyGameContextGame, context: FantasyGameContextReadModel | null): void {
    const current = this.currentContext(context);
    if (!current) return;
    this.openContextDialog({ mode: 'game', context: current, league: this.league, gameId: game.GameID });
  }

  openMatchupDetail(matchup: LeagueMatchupView, context: FantasyGameContextReadModel | null): void {
    const current = this.currentContext(context);
    if (!current) return;
    const resolved = this.matchupContext(matchup, current);
    if (!resolved) return;
    this.openContextDialog({
      mode: 'matchup',
      context: current,
      league: this.league,
      fantasyMatchupId: resolved.FantasyMatchupID
    });
  }

  private openContextDialog(data: FantasyGameContextDialogData): void {
    this.dialog.open(FantasyGameContextDialogComponent, {
      data,
      width: '95vw',
      maxWidth: '800px',
      maxHeight: '90vh',
      autoFocus: false
    });
  }

  private mapParticipant(
    participant: LeagueMatchupParticipant,
    teamByID: Map<number, FantasyTeam>
  ): LeagueMatchupTeamView | null {
    const team = teamByID.get(participant.TeamID);
    if (!team) return null;

    const points = participant.Points ?? 0;

    return {
      team,
      points,
      pointsDisplay: this.matchupScoreFormatter.format(points),
      context: this.getTeamContext(team)
    };
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
