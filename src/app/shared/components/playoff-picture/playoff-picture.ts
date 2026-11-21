import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { TeamIdentityComponent, type TeamIdentityElement } from '../team-identity/team-identity';
import type { CurrentStandingRow } from '../../utils/league-standings-view.util';
import {
  formatPlayoffCell,
  formatPlayoffPercent,
  type PlayoffOddsView
} from '../../utils/schedule-outlook-view.util';
import { PlayoffOddsPillComponent } from '../playoff-odds-pill/playoff-odds-pill';

interface PicturePlaceCell {
  place: number;
  text: string;
  /** Background strength 0..1 for the heatmap tint. */
  intensity: number;
  inPlayoffs: boolean;
  label: string;
}

interface PictureRow {
  row: CurrentStandingRow;
  cells: PicturePlaceCell[];
  hasPlaces: boolean;
}

/** Collapsible "Playoff Picture": every team's share of each final regular-season place plus the playoff status. */
@Component({
  selector: 'app-playoff-picture',
  standalone: true,
  imports: [CommonModule, TeamIdentityComponent, PlayoffOddsPillComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './playoff-picture.html',
  styleUrl: './playoff-picture.scss'
})
export class PlayoffPictureComponent {
  @Input({ required: true }) odds!: PlayoffOddsView;
  @Input({ required: true }) standings: readonly CurrentStandingRow[] = [];

  expanded = false;
  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];

  get placeNumbers(): number[] {
    return Array.from({ length: this.odds.teamCount }, (_, index) => index + 1);
  }

  get rows(): PictureRow[] {
    return this.standings.flatMap(row => {
      const team = this.odds.teams.get(Number(row.team.TeamID));
      if (!team) return [];
      const cells = team.places.map((probability, index): PicturePlaceCell => ({
        place: index + 1,
        text: formatPlayoffCell(probability),
        intensity: probability,
        inPlayoffs: this.odds.playoffTeams !== null && index < this.odds.playoffTeams,
        label: `Place ${index + 1}: ${formatPlayoffPercent(probability)}`
      }));
      return [{ row, cells, hasPlaces: cells.length > 0 }];
    });
  }

  teamView(row: CurrentStandingRow) {
    return this.odds.teams.get(Number(row.team.TeamID))!;
  }

  toggle(): void {
    this.expanded = !this.expanded;
  }
}
