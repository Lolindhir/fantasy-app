import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';

import type { FantasyTeam } from '../../../core/models/league.models';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';

export type TeamIdentityElement = 'logo' | 'abbr' | 'name' | 'owner';
export type TeamIdentitySize = 'small' | 'medium' | 'large';
export type TeamIdentityAlign = 'start' | 'end';

@Component({
  selector: 'app-team-identity',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './team-identity.html',
  styleUrl: './team-identity.scss'
})
export class TeamIdentityComponent {
  @Input({ required: true }) team!: FantasyTeam;
  @Input() elements: readonly TeamIdentityElement[] = ['logo', 'name'];
  @Input() size: TeamIdentitySize = 'medium';
  @Input() align: TeamIdentityAlign = 'start';
  @Input() interactive = true;

  private teamDetailDialog = inject(TeamDetailDialogService);

  hasElement(element: TeamIdentityElement): boolean {
    return this.elements.includes(element);
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
    return `Open ${this.displayName} team details`;
  }

  openTeam(): void {
    if (!this.interactive) return;
    this.teamDetailDialog.open(this.team.TeamID);
  }
}
