import {
  axisPosition,
  formatProjectionPoints,
  playerProjectionView,
  rangeAtLevel,
  rangeBarGeometry,
  scoredSoFarNote
} from './projection-range.util';

describe('projection range layout helpers', () => {
  it('picks the published range of the requested level only', () => {
    const ranges = [
      { Level: 0.5, Lower: 13, Upper: 20 },
      { Level: 0.8, Lower: 10, Upper: 25 },
      { Level: 0.9, Lower: 8, Upper: 30 }
    ];

    expect(rangeAtLevel(ranges, 0.8)).toEqual({ Level: 0.8, Lower: 10, Upper: 25 });
    expect(rangeAtLevel(ranges, 0.95)).toBeNull();
    expect(rangeAtLevel(ranges, null)).toBeNull();
    expect(rangeAtLevel(undefined, 0.9)).toBeNull();
  });

  it('maps a published range onto the published axis as clamped percentages', () => {
    const axis = { Min: 100, Max: 200 };

    expect(rangeBarGeometry({ Lower: 125, Upper: 175 }, axis)).toEqual({ left: 25, width: 50 });
    expect(rangeBarGeometry({ Lower: 80, Upper: 250 }, axis)).toEqual({ left: 0, width: 100 });
    expect(axisPosition(150, axis)).toBe(50);
    expect(axisPosition(90, axis)).toBe(0);
    expect(axisPosition(260, axis)).toBe(100);
  });

  it('formats projections with one decimal and unknown values as a dash', () => {
    expect(formatProjectionPoints(224.56)).toBe('224.6');
    expect(formatProjectionPoints(10.04)).toBe('10.0');
    expect(formatProjectionPoints(-1.46)).toBe('-1.5');
    expect(formatProjectionPoints(null)).toBe('–');
    expect(formatProjectionPoints(undefined)).toBe('–');
    expect(formatProjectionPoints(Number.NaN)).toBe('–');
  });

  it('mentions scored points only once a team has scored, with their own precision', () => {
    expect(scoredSoFarNote(0, 0)).toBeNull();
    expect(scoredSoFarNote(15.6, 0)).toBe('Scored so far 15.6 and 0.');
    expect(scoredSoFarNote(15.6, 37.66)).toBe('Scored so far 15.6 and 37.66.');
  });

  it('builds the player projection with the number, the bar and the range text', () => {
    const view = playerProjectionView({
      projected: 21.07,
      range: { Lower: 6.59, Upper: 39.1 },
      axis: { Min: 0, Max: 50 }
    });

    expect(view.projected).toBe('21.1');
    expect(view.rangeText).toBe('6.6 – 39.1');
    expect(view.bar?.left).toBeCloseTo(13.18, 6);
    expect(view.bar?.width).toBeCloseTo(65.02, 6);
    expect(view.bar?.marker).toBeCloseTo(42.14, 6);
    expect(view.ariaLabel).toBe('Projected 21.1, range 6.6 to 39.1');
  });

  it('keeps the projection number when there is no range or no axis', () => {
    expect(playerProjectionView({ projected: 12.5, range: null, axis: { Min: 0, Max: 50 } })).toEqual({
      projected: '12.5',
      bar: null,
      rangeText: null,
      ariaLabel: 'Projected 12.5'
    });

    const withoutAxis = playerProjectionView({ projected: 12.5, range: { Lower: 4, Upper: 24 }, axis: null });
    expect(withoutAxis.bar).toBeNull();
    expect(withoutAxis.rangeText).toBe('4.0 – 24.0');
  });
});
