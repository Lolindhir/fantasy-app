import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { PositionStylePipe } from '../../pipes/position-style.pipe';
import type { MatchupPlayerStatusTeamView } from './matchup-player-status.util';

@Component({
  selector: 'app-matchup-player-status',
  standalone: true,
  imports: [CommonModule, PositionStylePipe],
  templateUrl: './matchup-player-status.html',
  styleUrl: './matchup-player-status.scss'
})
export class MatchupPlayerStatusComponent {
  @Input({ required: true }) teams: readonly MatchupPlayerStatusTeamView[] = [];

  @Output() readonly playerSelected = new EventEmitter<string>();
  @Output() readonly teamSelected = new EventEmitter<string | number>();
  @Output() readonly gameSelected = new EventEmitter<string>();

  formatPoints(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return '–';
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  }

  benchOptionsLabel(count: number): string {
    return `${count} bench player${count === 1 ? '' : 's'} could take the slot`;
  }
}
