import { Subscription } from 'rxjs';

import {
  createAdaptiveCountdownClock,
  shouldEmitAdaptiveCountdownTick
} from './countdown-clock.util';

describe('countdown clock util', () => {
  let subscription: Subscription | null = null;

  beforeEach(() => {
    jasmine.clock().install();
  });

  afterEach(() => {
    subscription?.unsubscribe();
    subscription = null;
    jasmine.clock().uninstall();
  });

  it('emits visibly every second when a relevant target is under one hour away', () => {
    jasmine.clock().mockDate(new Date('2026-09-04T10:00:00.250Z'));
    const observed: string[] = [];

    subscription = createAdaptiveCountdownClock(() => ['2026-09-04T10:30:00Z'])
      .subscribe(now => observed.push(now.toISOString()));

    expect(observed).toEqual(['2026-09-04T10:00:00.250Z']);

    jasmine.clock().tick(750);
    expect(observed[observed.length - 1]).toBe('2026-09-04T10:00:01.000Z');

    jasmine.clock().tick(1_000);
    expect(observed[observed.length - 1]).toBe('2026-09-04T10:00:02.000Z');
  });

  it('does not emit visible second updates above one hour but still emits at the minute boundary', () => {
    jasmine.clock().mockDate(new Date('2026-09-04T10:00:30Z'));
    const observed: string[] = [];

    subscription = createAdaptiveCountdownClock(() => ['2026-09-04T12:00:00Z'])
      .subscribe(now => observed.push(now.toISOString()));

    jasmine.clock().tick(29_000);
    expect(observed).toEqual(['2026-09-04T10:00:30.000Z']);

    jasmine.clock().tick(1_000);
    expect(observed).toEqual([
      '2026-09-04T10:00:30.000Z',
      '2026-09-04T10:01:00.000Z'
    ]);
  });

  it('emits the rollover tick even when the next target no longer needs second cadence', () => {
    const target = Date.parse('2026-09-04T10:00:45Z');
    const previousObserved = Date.parse('2026-09-04T10:00:44Z');

    expect(shouldEmitAdaptiveCountdownTick(
      new Date('2026-09-04T10:00:45Z'),
      [target],
      previousObserved
    )).toBeTrue();
  });

  it('uses the same end-of-day interpretation for date-only league targets', () => {
    expect(shouldEmitAdaptiveCountdownTick(
      new Date('2026-09-05T23:59:30Z'),
      ['2026-09-05']
    )).toBeTrue();
  });
});
