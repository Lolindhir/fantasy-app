import { Injectable, inject } from '@angular/core';
import { Observable, catchError, defaultIfEmpty, forkJoin, map, of, shareReplay, switchMap } from 'rxjs';

import type { MatchupsReadModel } from '../../core/models/matchup.models';
import { DataService } from '../../core/services/data.service';

/**
 * Loads the Matchups read models of every available season (archived seasons plus the current one)
 * once and shares them between all head-to-head views. Archived seasons that fail to load are skipped;
 * a failing current-season file makes the whole history unavailable (null).
 */
@Injectable({ providedIn: 'root' })
export class TeamRivalryHistoryService {
  private readonly dataService = inject(DataService);

  private history$?: Observable<MatchupsReadModel[] | null>;

  /** Current-season Matchups first-loaded, archived seasons from the past index (duplicates of the current season dropped). */
  getSeasons(): Observable<MatchupsReadModel[] | null> {
    this.history$ ??= forkJoin([
      this.dataService.getMatchups(),
      this.dataService.getPastSeasonsIndex().pipe(
        catchError(() => of(null)),
        map(index => (index?.Seasons ?? [])
          .map(season => ({ season: season.Season, resource: season.Resources['Matchups'] }))
          .filter(entry => !!entry.resource && entry.resource.Exists
            && typeof entry.resource.Path === 'string' && entry.resource.Path.length > 0)
          .map(entry => entry.resource!.Path)
          .filter((path): path is string => !!path))
      )
    ]).pipe(
      switchMap(([current, paths]) => forkJoin(
        paths.map(path => this.dataService.getPastMatchupsRaw(path).pipe(catchError(() => of(null))))
      ).pipe(
        defaultIfEmpty([] as Array<MatchupsReadModel | null>),
        map(archived => [...archived, current]
          .filter((season): season is MatchupsReadModel => !!season)
          .filter((season, index, all) => all.findIndex(other => other.Season === season.Season) === index))
      )),
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.history$;
  }
}
