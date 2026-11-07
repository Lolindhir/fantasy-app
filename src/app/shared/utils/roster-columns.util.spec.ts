import {
  decodeColumns, defaultColumns, encodeColumns, normalizeColumns, formatCompactRosterSalary,
  mobileRosterColumnMinWidth, mobileRosterColumnTrackWidth, mobileRosterFlexibleMetricCount, mobileRosterMinimumTableWidth,
  presetColumns, selectedPreset, storageKey, toggleMetric
} from './roster-columns.util';

describe('roster column preferences', () => {
  it('uses complete desktop and performance mobile defaults', () => {
    expect(defaultColumns('desktop')).toEqual(['ppg', 'weekProjection', 'ranking', 'depth', 'age', 'salary', 'salaryProjected']);
    expect(defaultColumns('mobile')).toEqual(['ppg', 'ranking', 'depth', 'age']);
    expect(selectedPreset(defaultColumns('desktop'))).toBe('all');
    expect(selectedPreset(defaultColumns('mobile'))).toBe('performance');
  });

  it('shows the weekly projection by default on desktop only and keeps it selectable on mobile', () => {
    expect(defaultColumns('desktop')).toContain('weekProjection');
    expect(defaultColumns('mobile')).not.toContain('weekProjection');
    expect(toggleMetric(defaultColumns('mobile'), 'weekProjection', true))
      .toEqual(['ppg', 'weekProjection', 'ranking', 'depth', 'age']);
    expect(normalizeColumns(['salary', 'weekProjection'], 'mobile')).toEqual(['weekProjection', 'salary']);
  });

  it('canonicalizes selection order, rejects unknown fields and avoids an empty metric list', () => {
    expect(normalizeColumns(['salary', 'ppg', 'ppg', 'not-a-column'], 'mobile')).toEqual(['ppg', 'salary']);
    expect(normalizeColumns([], 'mobile')).toEqual(defaultColumns('mobile'));
    expect(normalizeColumns(['wrong'], 'desktop')).toEqual(defaultColumns('desktop'));
  });

  it('supports presets and custom selection with the final metric always retained', () => {
    expect(presetColumns('financial')).toEqual(['salary', 'salaryProjected']);
    const custom = toggleMetric(presetColumns('financial'), 'ppg', true);
    expect(custom).toEqual(['ppg', 'salary', 'salaryProjected']);
    expect(selectedPreset(custom)).toBe('custom');
    expect(toggleMetric(['ppg'], 'ppg', false)).toEqual(['ppg']);
  });

  it('uses separate keys per layout and validates stored payloads', () => {
    expect(storageKey('desktop')).not.toEqual(storageKey('mobile'));
    expect(decodeColumns(encodeColumns(['ppg', 'age']), 'mobile')).toEqual(['ppg', 'age']);
    expect(decodeColumns('{oops', 'desktop')).toEqual(defaultColumns('desktop'));
    expect(decodeColumns('{"version":9,"columns":["salary"]}', 'desktop'))
      .toEqual(defaultColumns('desktop'));
    expect(decodeColumns('{"version":1,"columns":["unknown"]}', 'mobile'))
      .toEqual(defaultColumns('mobile'));
  });
  it('keeps mobile roster salary amounts readable within narrow metric columns', () => {
    expect(formatCompactRosterSalary(54_000_000)).toBe('$54.0M');
    expect(formatCompactRosterSalary(40_800_000)).toBe('$40.8M');
    expect(formatCompactRosterSalary(-13_200_000, true)).toBe('-$13.2M');
    expect(formatCompactRosterSalary(900_000, true)).toBe('+$0.9M');
    expect(formatCompactRosterSalary(0)).toBe('$0.0M');
    expect(formatCompactRosterSalary(Number.NaN)).toBe('—');
  });


  it('keeps the fixed identity constant for two, four and six selected metrics', () => {
    const two = ['rank', 'name', 'salary', 'salaryProjected'];
    const four = ['rank', 'name', 'ppg', 'ranking', 'depth', 'age'];
    const six = [...four, 'salary', 'salaryProjected'];

    expect(two.slice(0, 2)).toEqual(four.slice(0, 2));
    expect(four.slice(0, 2)).toEqual(six.slice(0, 2));
    expect(mobileRosterColumnMinWidth('rank')).toBe(22);
    expect(mobileRosterColumnMinWidth('name')).toBe(110);
    expect(mobileRosterColumnTrackWidth('rank')).toBe('22px');
    expect(mobileRosterColumnTrackWidth('name')).toBe('110px');

    expect(mobileRosterMinimumTableWidth(two)).toBe(284);
    expect(mobileRosterMinimumTableWidth(four)).toBe(344);
    expect(mobileRosterMinimumTableWidth(six)).toBe(496);
    expect(mobileRosterFlexibleMetricCount(two)).toBe(2);
    expect(mobileRosterFlexibleMetricCount(four)).toBe(4);
    expect(mobileRosterFlexibleMetricCount(six)).toBe(6);
    expect(mobileRosterColumnTrackWidth('ppg'))
      .toBe('calc(44px + var(--roster-flex-extra))');
  });

  it('includes Next Lock in the same mobile metric width calculation', () => {
    const columns = ['rank', 'name', 'dynamicStat', 'ppg', 'salary'];
    expect(mobileRosterMinimumTableWidth(columns)).toBe(370);
    expect(mobileRosterFlexibleMetricCount(columns)).toBe(3);
    expect(mobileRosterColumnTrackWidth('dynamicStat'))
      .toBe('calc(122px + var(--roster-flex-extra))');
  });

});
