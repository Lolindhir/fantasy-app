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

  getLeagueData(): Observable<LeagueDataLoadResult> {
    return forkJoin({
      leagueRaw: this.getLeagueRaw(),
      playersRaw: this.getPlayersRaw(),
      nflTeamsRaw: this.getNflTeamsRaw(),
      draftsRaw: this.getDraftsRaw()
    });
  }
}
