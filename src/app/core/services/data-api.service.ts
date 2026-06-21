import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';

import type { RawDraft } from '../models/draft.models';
import type { DataTimestamps, RawLeague } from '../models/league.models';
import type { RawNFLTeam, RawPlayer } from '../models/player.models';

export interface LeagueDataLoadResult {
  leagueRaw: RawLeague;
  playersRaw: RawPlayer[];
  nflTeamsRaw: RawNFLTeam[];
  draftsRaw: RawDraft[];
}

export interface PastSeasonResourceIndex {
  Path: string | null;
  Exists: boolean;
  ContentHash?: string | null;
  UpdatedAt?: string | null;
}

export interface PastSeasonIndexEntry {
  Season: string;
  Resources: {
    [resourceKey: string]: PastSeasonResourceIndex | undefined;
    Drafts?: PastSeasonResourceIndex;
    Transactions?: PastSeasonResourceIndex;
    Players?: PastSeasonResourceIndex;
    Games?: PastSeasonResourceIndex;
    Schedule?: PastSeasonResourceIndex;
    Standings?: PastSeasonResourceIndex;
    Teams?: PastSeasonResourceIndex;
  };
}

export interface PastSeasonsIndex {
  GeneratedAt: string | null;
  Seasons: PastSeasonIndexEntry[];
}

@Injectable({
  providedIn: 'root'
})
export class DataApiService {
  private http = inject(HttpClient);

  getTimestamps(): Observable<DataTimestamps> {
    return this.http.get<DataTimestamps>('data/Timestamps.json');
  }

  getLeagueRaw(): Observable<RawLeague> {
    return this.http.get<RawLeague>('data/League.json');
  }

  getPlayersRaw(): Observable<RawPlayer[]> {
    return this.http.get<RawPlayer[]>('data/Players.json');
  }

  getNflTeamsRaw(): Observable<RawNFLTeam[]> {
    return this.http.get<RawNFLTeam[]>('data/Teams.json');
  }

  getDraftsRaw(): Observable<RawDraft[]> {
    return this.http.get<RawDraft[]>('data/Drafts.json');
  }

  getPastSeasonsIndex(): Observable<PastSeasonsIndex> {
    return this.http.get<PastSeasonsIndex>('data/PastSeasonsIndex.json');
  }

  getPastDraftsRaw(path: string): Observable<RawDraft[]> {
    return this.http.get<RawDraft[]>(this.normalizeDataPath(path));
  }

  getLeagueData(): Observable<LeagueDataLoadResult> {
    return forkJoin({
      leagueRaw: this.getLeagueRaw(),
      playersRaw: this.getPlayersRaw(),
      nflTeamsRaw: this.getNflTeamsRaw(),
      draftsRaw: this.getDraftsRaw()
    });
  }

  private normalizeDataPath(path: string): string {
    const normalizedPath = path.replace(/\\/g, '/');
    const publicDataMarker = '/public/data/';
    const publicDataIndex = normalizedPath.indexOf(publicDataMarker);

    if (publicDataIndex >= 0) {
      return `data/${normalizedPath.slice(publicDataIndex + publicDataMarker.length)}`;
    }

    if (normalizedPath.startsWith('public/data/')) {
      return normalizedPath.slice('public/'.length);
    }

    return normalizedPath.startsWith('/') ? normalizedPath.slice(1) : normalizedPath;
  }
}
