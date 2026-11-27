import { Injectable, inject } from '@angular/core';
import { catchError, defer, map, of, shareReplay } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import { DataService } from '../../core/services/data.service';

type DecisionWindowsResult =
  | { ok: true; model: DecisionWindowsReadModel }
  | { ok: false; error: unknown };

/** Provided by Overview only; never a root cache. Children share the exact page context. */
@Injectable()
export class OverviewDataScope {
  private readonly dataService = inject(DataService);

  readonly context$ = defer(() => this.dataService.getLeagueWithPlayersAndTransactions()).pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly nflTeams$ = this.context$.pipe(map(context => context.nflTeams));

  // Replay the outcome, including failure, for this page instance. Each child retains its own
  // unavailable presentation; a failed synchronous first load must not trigger a second request.
  private readonly decisionWindowsResult$ = defer(() => this.dataService.getDecisionWindows()).pipe(
    map((model): DecisionWindowsResult => ({ ok: true, model })),
    catchError((error: unknown) => of<DecisionWindowsResult>({ ok: false, error })),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly decisionWindows$ = this.decisionWindowsResult$.pipe(
    map(result => {
      if (!result.ok) throw result.error;
      return result.model;
    })
  );
}
