import { Component, Input } from '@angular/core';

import type { DecisionWindowGame } from '../../../core/models/decision-window.models';
import type { NFLTeam } from '../../../core/models/player.models';

@Component({
  selector: 'app-team-lineup-matchup',
  standalone: true,
  templateUrl: './team-lineup-matchup.html',
  styleUrl: './team-lineup-matchup.scss'
})
export class TeamLineupMatchupComponent {
  @Input({ required: true }) game!: DecisionWindowGame;
  @Input() nflTeams: NFLTeam[] = [];

  get awayAbbr(): string {
    return this.resolveTeam(this.game.AwayTeamID, this.game.AwayTeamAbbr)?.Abv
      || this.game.AwayTeamAbbr
      || this.game.AwayTeamID;
  }

  get homeAbbr(): string {
    return this.resolveTeam(this.game.HomeTeamID, this.game.HomeTeamAbbr)?.Abv
      || this.game.HomeTeamAbbr
      || this.game.HomeTeamID;
  }

  get awayLogo(): string | null {
    return this.resolveTeam(this.game.AwayTeamID, this.game.AwayTeamAbbr)?.Logo || null;
  }

  get homeLogo(): string | null {
    return this.resolveTeam(this.game.HomeTeamID, this.game.HomeTeamAbbr)?.Logo || null;
  }

  private resolveTeam(teamId: string, teamAbbr: string | null): NFLTeam | null {
    const normalizedAbbr = teamAbbr?.trim().toUpperCase() ?? '';
    return this.nflTeams.find(candidate => candidate.ID === teamId)
      ?? this.nflTeams.find(candidate => candidate.Abv.trim().toUpperCase() === normalizedAbbr)
      ?? null;
  }
}
