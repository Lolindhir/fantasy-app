import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Injector, Input, OnInit, inject } from '@angular/core';

import type { FantasyTeam, League } from '../../../core/models/fantasy.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import { TeamRivalryHistoryService } from '../../services/team-rivalry-history.service';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { SharedMaterialImports } from '../../shared-material-imports';
import {
  buildRivalryRecords,
  formatRivalryRecord,
  isPlayoffsComplete,
  type RivalryFilter,
  type RivalryGame,
  type RivalryRecord
} from '../../utils/team-rivalry.util';

type RivalsState = 'loading' | 'ready' | 'unavailable';

interface RivalryOpponentView {
  record: RivalryRecord;
  name: string;
  avatar: string;
  recordLabel: string;
}

/** Head-to-head record of one team against every other team, counted from Matchups results. */
@Component({
  selector: 'app-team-rivals-tab',
  standalone: true,
  imports: [CommonModule, MatButtonToggleModule, SharedMaterialImports],
  templateUrl: './team-rivals-tab.html',
  styleUrl: './team-rivals-tab.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TeamRivalsTabComponent implements OnInit {
  private readonly history = inject(TeamRivalryHistoryService);
  private readonly injector = inject(Injector);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input({ required: true }) team!: FantasyTeam;
  @Input({ required: true }) league!: League;

  state: RivalsState = 'loading';
  filter: RivalryFilter = 'all';
  expanded = new Set<number>();
  opponents: RivalryOpponentView[] = [];
  private seasons: MatchupsReadModel[] = [];

  ngOnInit(): void {
    this.history.getSeasons().subscribe(seasons => {
      if (!seasons) {
        this.state = 'unavailable';
      } else {
        this.seasons = seasons;
        this.state = 'ready';
        this.opponents = this.computeOpponents();
      }
      this.cdr.markForCheck();
    });
  }

  private computeOpponents(): RivalryOpponentView[] {
    return buildRivalryRecords(this.team.TeamID, this.seasons, {
      filter: this.filter,
      // Playoffs are only countable once over.
      isSeasonComplete: season => isPlayoffsComplete(season, this.league.SeasonAsNumber, this.league.Status)
    }).map(record => {
      const opponent = this.league.Teams.find(candidate => Number(candidate.TeamID) === record.opponentId);
      return {
        record,
        name: opponent?.Team || `Team ${record.opponentId}`,
        avatar: opponent?.Avatar || 'assets/default-team-avatar.png',
        recordLabel: formatRivalryRecord(record)
      };
    });
  }

  get seasonSpan(): string {
    const years = this.seasons.map(season => Number(season.Season)).sort((a, b) => a - b);
    if (!years.length) return '';
    return years[0] === years[years.length - 1] ? `${years[0]}` : `${years[0]}–${years[years.length - 1]}`;
  }

  setFilter(filter: RivalryFilter): void {
    this.filter = filter;
    this.expanded.clear();
    this.opponents = this.computeOpponents();
  }

  isExpanded(opponentId: number): boolean {
    return this.expanded.has(opponentId);
  }

  toggle(opponentId: number): void {
    if (!this.expanded.delete(opponentId)) this.expanded.add(opponentId);
  }

  openOpponent(opponentId: number): void {
    // Loaded on demand: the dialog service imports the Team Detail dialog, which hosts this tab.
    void import('../../services/team-detail-dialog.service').then(({ TeamDetailDialogService }) =>
      this.injector.get(TeamDetailDialogService).open(opponentId));
  }

  trackOpponent(_: number, view: RivalryOpponentView): number {
    return view.record.opponentId;
  }

  trackGame(_: number, game: RivalryGame): string {
    return `${game.season}-${game.week}-${game.stage}`;
  }

  outcomeLetter(game: RivalryGame): string {
    return game.outcome === 'win' ? 'W' : game.outcome === 'loss' ? 'L' : 'T';
  }

  scoreLabel(game: RivalryGame): string {
    if (game.teamPoints === null || game.opponentPoints === null) return '–';
    return `${this.points(game.teamPoints)}–${this.points(game.opponentPoints)}`;
  }

  gameLabel(game: RivalryGame): string {
    return `${game.season} W${game.week}`;
  }

  points(value: number): string {
    return value.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
  }

  isBiggestWin(view: RivalryOpponentView, game: RivalryGame): boolean {
    return view.record.biggestWin === game;
  }

  isClosestLoss(view: RivalryOpponentView, game: RivalryGame): boolean {
    return view.record.closestLoss === game;
  }
}
