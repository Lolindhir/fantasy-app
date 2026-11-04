import {
  decodeColumns, defaultColumns, encodeColumns, normalizeColumns, formatCompactRosterSalary,
  presetColumns, selectedPreset, storageKey, toggleMetric
} from './roster-columns.util';

describe('roster column preferences', () => {
  it('uses complete desktop and performance mobile defaults', () => {
    expect(defaultColumns('desktop')).toEqual(['ppg', 'ranking', 'depth', 'age', 'salary', 'salaryProjected']);
    expect(defaultColumns('mobile')).toEqual(['ppg', 'ranking', 'depth', 'age']);
    expect(selectedPreset(defaultColumns('desktop'))).toBe('all');
    expect(selectedPreset(defaultColumns('mobile'))).toBe('performance');
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

});
