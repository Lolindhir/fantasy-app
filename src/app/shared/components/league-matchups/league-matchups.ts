import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { FantasyTeam, League, LeagueMatchupParticipant } from '../../../core/models/league.models';

interface LeagueMatchupTeamView {
  team: FantasyTeam;
  points: number;
  fallback: string;
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
  imports: [CommonModule],
  templateUrl: './league-matchups.html',
  styleUrl: './league-matchups.scss'
})
export class LeagueMatchupsComponent {
  @Input({ required: true }) league!: League;

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

    const teamName = team.Team || team.Owner || `Team ${team.TeamID}`;

    return {
      team,
      points: participant.Points ?? 0,
      fallback: teamName.trim().charAt(0).toUpperCase() || '?'
    };
  }
}
