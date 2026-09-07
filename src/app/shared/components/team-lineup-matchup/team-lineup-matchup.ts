import { Component, Input } from '@angular/core';

import type { DecisionWindowGame } from '../../../core/models/decision-window.models';
import type { NFLTeam } from '../../../core/models/player.models';

type NflTeamWithCity = NFLTeam & { City?: string };

@Component({
  selector: 'app-team-lineup-matchup',
  standalone: true,
  templateUrl: './team-lineup-matchup.html',
  styleUrl: './team-lineup-matchup.scss'
})
export class TeamLineupMatchupComponent {
  @Input({ required: true }) game!: DecisionWindowGame;
  @Input() nflTeams: NFLTeam[] = [];

  get awayName(): string {
    return this.fullTeamName(this.resolveTeam(this.game.AwayTeamID, this.game.AwayTeamAbbr), this.game.AwayTeamAbbr, this.game.AwayTeamID);
  }

  get homeName(): string {
    return this.fullTeamName(this.resolveTeam(this.game.HomeTeamID, this.game.HomeTeamAbbr), this.game.HomeTeamAbbr, this.game.HomeTeamID);
  }

  get awayLogo(): string | null {
    return this.resolveTeam(this.game.AwayTeamID, this.game.AwayTeamAbbr)?.Logo || null;
  }

  get homeLogo(): string | null {
    return this.resolveTeam(this.game.HomeTeamID, this.game.HomeTeamAbbr)?.Logo || null;
  }

  private resolveTeam(teamId: string, teamAbbr: string | null): NflTeamWithCity | null {
    const normalizedAbbr = teamAbbr?.trim().toUpperCase() ?? '';
    return (this.nflTeams.find(candidate => candidate.ID === teamId)
      ?? this.nflTeams.find(candidate => candidate.Abv.trim().toUpperCase() === normalizedAbbr)
      ?? null) as NflTeamWithCity | null;
  }

  private fullTeamName(team: NflTeamWithCity | null, fallbackAbbr: string | null, fallbackId: string): string {
    if (!team) return fallbackAbbr || fallbackId;

    const city = team.City?.trim();
    const name = team.Name?.trim();
    if (city && name) {
      return name.toLocaleLowerCase().startsWith(city.toLocaleLowerCase())
        ? name
        : `${city} ${name}`;
    }

    return name || team.Abv || fallbackAbbr || fallbackId;
  }
}
