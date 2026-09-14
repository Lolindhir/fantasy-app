import {
  DAY_MS,
  HOUR_MS,
  MINUTE_MS,
  SECOND_MS,
  formatCountdownDuration
} from './countdown.util';

describe('countdown util', () => {
  it('implements the exact adaptive threshold contract', () => {
    expect(formatCountdownDuration(7 * DAY_MS)).toBe('7 days');
    expect(formatCountdownDuration(7 * DAY_MS - HOUR_MS)).toBe('6 days 23 h');
    expect(formatCountdownDuration(DAY_MS)).toBe('1 day 0 h');
    expect(formatCountdownDuration(DAY_MS - SECOND_MS)).toBe('23 h 59 min');
    expect(formatCountdownDuration(HOUR_MS)).toBe('1 h 0 min');
    expect(formatCountdownDuration(HOUR_MS - SECOND_MS)).toBe('59 min 59 s');
    expect(formatCountdownDuration(MINUTE_MS)).toBe('1 min 0 s');
    expect(formatCountdownDuration(MINUTE_MS - SECOND_MS)).toBe('59 s');
    expect(formatCountdownDuration(0)).toBe('0 s');
    expect(formatCountdownDuration(-SECOND_MS)).toBe('0 s');
  });

  it('keeps the secondary unit visible when it is zero', () => {
    expect(formatCountdownDuration(2 * DAY_MS)).toBe('2 days 0 h');
    expect(formatCountdownDuration(3 * HOUR_MS)).toBe('3 h 0 min');
    expect(formatCountdownDuration(43 * MINUTE_MS)).toBe('43 min 0 s');
  });

  it('never introduces a week unit', () => {
    expect(formatCountdownDuration(14 * DAY_MS)).toBe('14 days');
    expect(formatCountdownDuration(21 * DAY_MS + 23 * HOUR_MS)).toBe('21 days');
  });

  it('covers representative fixture-style durations', () => {
    expect(formatCountdownDuration(12 * DAY_MS + 8 * HOUR_MS)).toBe('12 days');
    expect(formatCountdownDuration(6 * DAY_MS + 4 * HOUR_MS)).toBe('6 days 4 h');
    expect(formatCountdownDuration(3 * HOUR_MS + 17 * MINUTE_MS)).toBe('3 h 17 min');
    expect(formatCountdownDuration(43 * MINUTE_MS + 12 * SECOND_MS)).toBe('43 min 12 s');
    expect(formatCountdownDuration(37 * SECOND_MS)).toBe('37 s');
  });
});
