import { Observable, concat, defer, map, of, share, timer } from 'rxjs';

import { HOUR_MS, SECOND_MS } from './countdown.util';

export type CountdownClockTarget = Date | string | number | null | undefined;

const secondAlignedClock$ = defer(() => {
  const firstTickDelay = SECOND_MS - (Date.now() % SECOND_MS);
  return timer(firstTickDelay, SECOND_MS).pipe(map(() => new Date()));
}).pipe(share());

export function createAdaptiveCountdownClock(
  getTargets: (now: Date) => readonly CountdownClockTarget[] = () => []
): Observable<Date> {
  return new Observable<Date>(subscriber => {
    let firstEmission = true;
    let previousObservedMs = Date.now();

    const subscription = concat(
      defer(() => of(new Date())),
      secondAlignedClock$
    ).subscribe({
      next: now => {
        const nowMs = now.getTime();
        if (
          firstEmission
          || shouldEmitAdaptiveCountdownTick(now, getTargets(now), previousObservedMs)
        ) {
          subscriber.next(now);
        }
        firstEmission = false;
        previousObservedMs = nowMs;
      },
      error: error => subscriber.error(error),
      complete: () => subscriber.complete()
    });

    return () => subscription.unsubscribe();
  });
}

export function shouldEmitAdaptiveCountdownTick(
  now: Date,
  targets: readonly CountdownClockTarget[],
  previousObservedMs = now.getTime() - SECOND_MS
): boolean {
  const nowMs = now.getTime();

  if (now.getSeconds() === 0) return true;

  return targets.some(target => {
    const targetMs = getTargetMs(target);
    if (targetMs === null) return false;

    const remainingMs = targetMs - nowMs;
    if (remainingMs > 0 && remainingMs < HOUR_MS) return true;

    return targetMs > previousObservedMs && targetMs <= nowMs;
  });
}

function getTargetMs(target: CountdownClockTarget): number | null {
  if (target instanceof Date) {
    const value = target.getTime();
    return Number.isFinite(value) ? value : null;
  }

  if (typeof target === 'number') {
    return Number.isFinite(target) ? target : null;
  }

  if (typeof target === 'string' && target.trim()) {
    const normalized = /^\d{4}-\d{2}-\d{2}$/.test(target)
      ? `${target}T23:59:59Z`
      : target;
    const value = Date.parse(normalized);
    return Number.isFinite(value) ? value : null;
  }

  return null;
}
