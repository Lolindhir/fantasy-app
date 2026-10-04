/**
 * Layout helpers for published projection ranges. The range values, the axis and the level are
 * data; these functions only map them to CSS percentages and pick the published level.
 */

export interface RangeBarGeometry {
  left: number;
  width: number;
}

export interface MatchupRangeTeamView {
  label: string;
  bar: RangeBarGeometry;
  marker: number;
  projected: string;
  lower: string;
  upper: string;
  ariaLabel: string;
}

export interface MatchupRangeView {
  levelLabel: string;
  teams: MatchupRangeTeamView[];
  ticks: Array<{ value: number; position: number }>;
  scored: { left: string; right: string };
}

export interface PlayerRangeBarView {
  left: number;
  width: number;
  marker: number;
  ariaLabel: string;
}

/** The published range of one level (the display level chosen by the data), if present. */
export function rangeAtLevel<T extends { Level: number }>(
  ranges: readonly T[] | null | undefined,
  level: number | null | undefined
): T | null {
  if (level === null || level === undefined) return null;
  return ranges?.find(range => range.Level === level) ?? null;
}

export function axisPosition(value: number, axis: { Min: number; Max: number }): number {
  return Math.max(0, Math.min(100, ((value - axis.Min) / (axis.Max - axis.Min)) * 100));
}

export function rangeBarGeometry(
  range: { Lower: number; Upper: number },
  axis: { Min: number; Max: number }
): RangeBarGeometry {
  const left = axisPosition(range.Lower, axis);
  return { left, width: axisPosition(range.Upper, axis) - left };
}
