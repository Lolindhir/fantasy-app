import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Injector, Input, OnInit, inject } from '@angular/core';

import type { FantasyTeam, League } from '../../../core/models/fantasy.models';
import type { RawRivalryGame, RivalryFilter } from '../../../core/models/rivalry.models';
import { RivalryLookup, TeamRivalryService, formatRivalryRecord, type RivalryRecordView } from '../../services/team-rivalry.service';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { SharedMaterialImports } from '../../shared-material-imports';

type RivalsState = 'loading' | 'ready' | 'unavailable';

interface RivalryOpponentView {
  record: RivalryRecordView;
  name: string;
  avatar: string;
  recordLabel: string;
}

/** Head-to-head record of one team against every other team, read from the generated Rivalry.json product. */
@Component({
  selector: 'app-team-rivals-tab',
  standalone: true,
  imports: [CommonModule, MatButtonToggleModule, SharedMaterialImports],
  templateUrl: './team-rivals-tab.html',
  styleUrl: './team-rivals-tab.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TeamRivalsTabComponent implements OnInit {
  private readonly history = inject(TeamRivalryService);
  private readonly injector = inject(Injector);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input({ required: true }) team!: FantasyTeam;
  @Input({ required: true }) league!: League;

  state: RivalsState = 'loading';
  filter: RivalryFilter = 'all';
  expanded = new Set<number>();
  opponents: RivalryOpponentView[] = [];
  private lookup: RivalryLookup | null = null;

  ngOnInit(): void {
    this.history.getLookup().subscribe({
      next: lookup => {
        this.lookup = lookup;
        this.state = 'ready';
        this.opponents = this.computeOpponents();
        this.cdr.markForCheck();
      },
      error: () => {
        this.state = 'unavailable';
        this.cdr.markForCheck();
      }
    });
  }

  private computeOpponents(): RivalryOpponentView[] {
    if (!this.lookup) return [];
    return this.lookup.recordsFor(Number(this.team.TeamID), this.filter).map(record => {
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
    return this.lookup?.seasonSpan ?? '';
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

  /** The util keeps games chronological (lastGame relies on it); the list shows the newest first. */
  gamesNewestFirst(view: RivalryOpponentView): RawRivalryGame[] {
    return [...view.record.games].reverse();
  }

  trackGame(_: number, game: RawRivalryGame): string {
    return game.FantasyMatchupID;
  }

  outcomeLetter(game: RawRivalryGame): string {
    return game.Outcome === 'win' ? 'W' : game.Outcome === 'loss' ? 'L' : 'T';
  }

  scoreLabel(game: RawRivalryGame): string {
    if (game.TeamPoints === null || game.OpponentPoints === null) return '–';
    return `${this.points(game.TeamPoints)}–${this.points(game.OpponentPoints)}`;
  }

  gameLabel(game: RawRivalryGame): string {
    return `${game.Season} W${game.Week}`;
  }

  /** One decimal, no thousands separator: easier to scan than "1,962.26". */
  points(value: number): string {
    return value.toFixed(1);
  }

  /** Overall tone of a record: more wins than losses is green, fewer is red. */
  recordTone(record: RivalryRecordView): 'win' | 'loss' | 'even' {
    return record.wins > record.losses ? 'win' : record.wins < record.losses ? 'loss' : 'even';
  }

  /** Signed point differential (PF - PA) of a whole record. */
  differential(record: RivalryRecordView): string {
    return this.signed(record.pointsFor - record.pointsAgainst);
  }

  differentialTone(record: RivalryRecordView): 'win' | 'loss' | 'even' {
    const diff = Math.round((record.pointsFor - record.pointsAgainst) * 10);
    return diff > 0 ? 'win' : diff < 0 ? 'loss' : 'even';
  }

  /** Signed margin of one game from the viewpoint of this team; null without scores. */
  gameMargin(game: RawRivalryGame): string | null {
    if (game.TeamPoints === null || game.OpponentPoints === null) return null;
    return this.signed(game.TeamPoints - game.OpponentPoints);
  }

  private signed(value: number): string {
    const rounded = Math.round(value * 10) / 10;
    return `${rounded > 0 ? '+' : ''}${rounded.toFixed(1)}`;
  }

  isBiggestWin(view: RivalryOpponentView, game: RawRivalryGame): boolean {
    return view.record.biggestWin?.FantasyMatchupID === game.FantasyMatchupID;
  }

  isClosestLoss(view: RivalryOpponentView, game: RawRivalryGame): boolean {
    return view.record.closestLoss?.FantasyMatchupID === game.FantasyMatchupID;
  }
}
