import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import type { MatchupPlayerStatusTeamView } from './matchup-player-status.util';

@Component({
  selector: 'app-matchup-player-status',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './matchup-player-status.html',
  styleUrl: './matchup-player-status.scss'
})
export class MatchupPlayerStatusComponent {
  @Input({ required: true }) teams: readonly MatchupPlayerStatusTeamView[] = [];

  @Output() readonly playerSelected = new EventEmitter<string>();
  @Output() readonly teamSelected = new EventEmitter<string | number>();
}
