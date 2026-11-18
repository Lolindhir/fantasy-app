import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';

import type { FantasyTeam } from '../../../core/models/league.models';
import { ChampionBadgeComponent } from '../champion-badge/champion-badge';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';

/** Minimal identity; a historic snapshot (season-specific name, owner, logo) is as valid as a current team. */
export type TeamIdentitySubject = Pick<FantasyTeam, 'TeamID' | 'Team' | 'Owner' | 'Avatar'> & Partial<Pick<FantasyTeam, 'TeamAbbr' | 'IsDefendingChampion'>>;
export type TeamIdentityElement = 'logo' | 'abbr' | 'name' | 'owner';
export type TeamIdentitySize = 'small' | 'medium' | 'large';
export type TeamIdentityAlign = 'start' | 'end';

@Component({
  selector: 'app-team-identity',
  standalone: true,
  imports: [CommonModule, ChampionBadgeComponent],
  templateUrl: './team-identity.html',
  styleUrl: './team-identity.scss'
})
export class TeamIdentityComponent {
  @Input({ required: true }) team!: TeamIdentitySubject;
  @Input() elements: readonly TeamIdentityElement[] = ['logo', 'name'];
  @Input() size: TeamIdentitySize = 'medium';
  @Input() align: TeamIdentityAlign = 'start';
  @Input() interactive = true;
  /** Opt-in per surface (#662): shows the defending-champion trophy badge on the logo. */
  @Input() championBadge = false;

  private teamDetailDialog = inject(TeamDetailDialogService);

  hasElement(element: TeamIdentityElement): boolean {
    return this.elements.includes(element);
  }

  get showChampionBadge(): boolean {
    return this.championBadge && this.hasElement('logo') && this.team.IsDefendingChampion === true;
  }

  get hasText(): boolean {
    return this.hasElement('abbr') || this.hasElement('name') || this.hasElement('owner');
  }

  get displayName(): string {
    return this.team.Team?.trim() || this.team.Owner?.trim() || `Team ${this.team.TeamID}`;
  }

  get displayAbbreviation(): string {
    const configured = this.team.TeamAbbr?.trim();
    if (configured) return configured;

    const words = this.displayName.split(/\s+/).filter(Boolean);
    if (words.length > 1) {
      return words
        .map(word => word.charAt(0))
        .join('')
        .slice(0, 3)
        .toUpperCase();
    }

    return this.displayName.slice(0, 3).toUpperCase();
  }

  get avatarFallback(): string {
    return this.displayName.charAt(0).toUpperCase() || '?';
  }

  get ariaLabel(): string {
    return `Open ${this.displayName} team details${this.showChampionBadge ? ' (defending champion)' : ''}`;
  }

  openTeam(): void {
    if (!this.interactive) return;
    this.teamDetailDialog.open(this.team.TeamID);
  }
}
