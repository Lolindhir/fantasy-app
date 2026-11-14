import { Injectable, inject } from '@angular/core';
import { Observable, map, shareReplay } from 'rxjs';

import type { RawRivalryGame, RawRivalryRecord, RivalryFilter, RivalryReadModel } from '../../core/models/rivalry.models';
import { DataService } from '../../core/services/data.service';

export interface RivalryRecordView {
  opponentId: number;
  wins: number;
  losses: number;
  ties: number;
  pointsFor: number;
  pointsAgainst: number;
  /** Counted duels, oldest first (generator order). */
  games: RawRivalryGame[];
  lastGame: RawRivalryGame;
  biggestWin: RawRivalryGame | null;
  closestLoss: RawRivalryGame | null;
}

export function formatRivalryRecord(record: Pick<RivalryRecordView, 'wins' | 'losses' | 'ties'>): string {
  return record.ties > 0 ? `${record.wins}-${record.losses}-${record.ties}` : `${record.wins}-${record.losses}`;
}

/** Selects and displays the generated Rivalry.json product; it counts and classifies nothing. */
export class RivalryLookup {
  constructor(private readonly model: RivalryReadModel) {}

  get seasonSpan(): string {
    const years = this.model.Seasons.map(season => Number(season.Season)).sort((a, b) => a - b);
    if (!years.length) return '';
    return years[0] === years[years.length - 1] ? `${years[0]}` : `${years[0]}–${years[years.length - 1]}`;
  }

  /** Records of one team against every opponent in generator order (most meetings first). */
  recordsFor(teamId: number, filter: RivalryFilter): RivalryRecordView[] {
    return this.model.Records
      .filter(record => record.TeamID === teamId && record.Filter === filter && record.Games.length > 0)
      .map(record => this.toView(record));
  }

  headToHead(teamId: number, opponentId: number): RivalryRecordView | null {
    const record = this.model.Records.find(candidate =>
      candidate.TeamID === teamId && candidate.OpponentID === opponentId && candidate.Filter === 'all' && candidate.Games.length > 0);
    return record ? this.toView(record) : null;
  }

  private toView(record: RawRivalryRecord): RivalryRecordView {
    const byId = (id: string | null) => (id ? record.Games.find(game => game.FantasyMatchupID === id) ?? null : null);
    return {
      opponentId: record.OpponentID,
      wins: record.Wins,
      losses: record.Losses,
      ties: record.Ties,
      pointsFor: record.PointsFor,
      pointsAgainst: record.PointsAgainst,
      games: record.Games,
      lastGame: record.Games[record.Games.length - 1],
      biggestWin: byId(record.BiggestWinMatchupID),
      closestLoss: byId(record.ClosestLossMatchupID)
    };
  }
}

@Injectable({ providedIn: 'root' })
export class TeamRivalryService {
  private readonly dataService = inject(DataService);
  private lookup$?: Observable<RivalryLookup>;

  getLookup(): Observable<RivalryLookup> {
    this.lookup$ ??= this.dataService.getRivalry().pipe(
      map(model => new RivalryLookup(model)),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.lookup$;
  }
}
