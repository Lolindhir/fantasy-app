import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type {
  FantasyTeam,
  League,
  LeagueMatchupParticipant,
  PlacementRegularSeason
} from '../../../core/models/league.models';
import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';

interface LeagueMatchupTeamContextView {
  seasonLabel: string | null;
  standing: number | null;
  record: string | null;
  streak: string | null;
  pointsFor: number | null;
}

interface LeagueMatchupTeamView {
  team: FantasyTeam;
  points: number;
  context: LeagueMatchupTeamContextView | null;
}

interface LeagueMatchupView {
  matchupID: number;
  left: LeagueMatchupTeamView;
  right: LeagueMatchupTeamView;
  showScore: boolean;
}

@Component({
  selector: 'app-league-matchups',
  standalone: true,
  imports: [CommonModule, TeamIdentityComponent],
  templateUrl: './league-matchups.html',
  styleUrl: './league-matchups.scss'
})
export class LeagueMatchupsComponent {
  @Input({ required: true }) league!: League;

  readonly teamIdentityElements: readonly TeamIdentityElement[] = ['logo', 'name', 'owner'];

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

  private mapParticipant(
    participant: LeagueMatchupParticipant,
    teamByID: Map<number, FantasyTeam>
  ): LeagueMatchupTeamView | null {
    const team = teamByID.get(participant.TeamID);
    if (!team) return null;

    return {
      team,
      points: participant.Points ?? 0,
      context: this.getTeamContext(team)
    };
  }

  private getTeamContext(team: FantasyTeam): LeagueMatchupTeamContextView | null {
    if (this.league.FinalScoredWeek > 0) {
      return this.mapPlacementContext(team.Placements?.Current?.Regular, null, true);
    }

    return this.mapPlacementContext(
      team.Placements?.Previous?.Regular,
      this.previousSeasonLabel,
      false
    );
  }

  private mapPlacementContext(
    placement: PlacementRegularSeason | undefined,
    seasonLabel: string | null,
    includeCurrentForm: boolean
  ): LeagueMatchupTeamContextView | null {
    if (!placement) return null;

    const standing = Number.isFinite(placement.Place) && placement.Place > 0
      ? placement.Place
      : null;
    const record = placement.Record?.trim() || this.formatRecord(placement);

    if (standing === null && !record) return null;

    return {
      seasonLabel,
      standing,
      record,
      streak: includeCurrentForm ? placement.Streak?.trim() || null : null,
      pointsFor: includeCurrentForm && Number.isFinite(placement.Points)
        ? placement.Points
        : null
    };
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
