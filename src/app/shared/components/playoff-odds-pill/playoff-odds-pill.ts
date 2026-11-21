import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import {
  playoffPillLabel,
  playoffPillText,
  type PlayoffOddsTeamView
} from '../../utils/schedule-outlook-view.util';

/** Playoff status of one team: "Playoffs NN%" while alive, Clinched (green) or Eliminated (dimmed). */
@Component({
  selector: 'app-playoff-odds-pill',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (text; as value) {
      <span class="pill" [ngClass]="'pill--' + team.status" [attr.title]="label" [attr.aria-label]="label">
        @if (team.status === 'alive') {
          <span class="pill-label">Playoffs</span>
        }
        <strong>{{ value }}</strong>
      </span>
    }
  `,
  styleUrl: './playoff-odds-pill.scss'
})
export class PlayoffOddsPillComponent {
  @Input({ required: true }) team!: PlayoffOddsTeamView;

  get text(): string | null { return playoffPillText(this.team); }
  get label(): string | null { return playoffPillLabel(this.team); }
}
