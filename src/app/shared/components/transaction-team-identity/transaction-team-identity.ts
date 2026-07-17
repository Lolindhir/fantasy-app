import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { FantasyTeam } from '../../../core/models/league.models';
import {
  getFantasyTeamAbbr,
  getFantasyTeamName
} from '../../utils/transaction-display.util';

@Component({
  selector: 'app-transaction-team-identity',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './transaction-team-identity.html',
  styleUrl: './transaction-team-identity.scss'
})
export class TransactionTeamIdentityComponent {
  @Input() team?: FantasyTeam;
  @Input() rosterID?: number;
  @Input() mode: 'responsive' | 'full' | 'abbr' = 'responsive';

  get teamName(): string {
    return getFantasyTeamName(this.team, this.rosterID);
  }

  get teamAbbr(): string {
    return getFantasyTeamAbbr(this.team, this.rosterID);
  }

  get avatar(): string {
    return this.team?.Avatar || 'assets/default-team-avatar.png';
  }
}
