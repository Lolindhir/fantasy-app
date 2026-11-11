import { Injectable, inject } from '@angular/core';
import { catchError, combineLatest, map, of, type Observable } from 'rxjs';

import type { FantasyGameContextReadModel } from '../../core/models/fantasy-game-context.models';
import type { MatchupsReadModel } from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import { DataService } from '../../core/services/data.service';
import type { WeeksSeasonOption } from '../utils/weeks-view.util';

export interface TeamScheduleSeasonData {
  season: string;
  /** Null when the season file could not be loaded. */
  matchups: MatchupsReadModel | null;
  recaps: WeeklyRecapsReadModel | null;
  /** Game contexts that make a matchup's detail dialog openable. */
  contexts: FantasyGameContextReadModel[];
}

/** Loads the generated files of one season the way the Weeks page does (current files or past_seasons archives). */
@Injectable({ providedIn: 'root' })
export class TeamScheduleDataService {
  private readonly dataService = inject(DataService);

  load(option: WeeksSeasonOption): Observable<TeamScheduleSeasonData> {
    const matchups$ = (option.matchupsPath
      ? this.dataService.getPastMatchupsRaw(option.matchupsPath)
      : this.dataService.getMatchups()).pipe(catchError(() => of(null)));

    const recaps$: Observable<WeeklyRecapsReadModel | null> = (option.isCurrent
      ? this.dataService.getWeeklyRecaps() as Observable<WeeklyRecapsReadModel | null>
      : option.recapsPath ? this.dataService.getPastWeeklyRecapsRaw(option.recapsPath) as Observable<WeeklyRecapsReadModel | null> : of<WeeklyRecapsReadModel | null>(null))
      .pipe(catchError(() => of(null as WeeklyRecapsReadModel | null)));

    const contexts$: Observable<FantasyGameContextReadModel[]> = (option.isCurrent
      ? combineLatest({
          active: this.dataService.getFantasyGameContext().pipe(catchError(() => of(null))),
          finished: this.dataService.getFantasyGameContextHistory().pipe(
            map(history => history.Weeks ?? []),
            catchError(() => of([] as FantasyGameContextReadModel[]))
          )
        }).pipe(map(({ active, finished }) => active
          ? [...finished.filter(week => week.Week !== active.Week), active]
          : finished))
      : option.contextPath
        ? this.dataService.getPastFantasyGameContextRaw(option.contextPath).pipe(map(season => season.Weeks ?? []))
        : of([] as FantasyGameContextReadModel[]))
      .pipe(catchError(() => of([] as FantasyGameContextReadModel[])));

    return combineLatest({ matchups: matchups$, recaps: recaps$, contexts: contexts$ }).pipe(
      map(({ matchups, recaps, contexts }) => ({ season: option.season, matchups, recaps, contexts }))
    );
  }
}
