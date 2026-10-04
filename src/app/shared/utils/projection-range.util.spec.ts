import { axisPosition, rangeAtLevel, rangeBarGeometry } from './projection-range.util';

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
});
