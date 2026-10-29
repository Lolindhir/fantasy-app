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
  avatar: string | null;
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
  /** "Scored so far 15.6 and 37.66." or null while neither team has scored. */
  scoredNote: string | null;
}

export interface PlayerProjectionView {
  /** "10.6": projections are estimates and carry one decimal. */
  projected: string;
  /** Null when no range is published for this player. */
  bar: { left: number; width: number; marker: number } | null;
  /** "6.6 – 39.1", shown under the bar. */
  rangeText: string | null;
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

const projectionFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1
});
const scoreFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2
});

/** Projections and ranges are estimates: one decimal. Real scores keep their own precision. */
export function formatProjectionPoints(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '–';
  return projectionFormatter.format(Number(value));
}

export function scoredSoFarNote(left: number, right: number): string | null {
  if (!(left > 0) && !(right > 0)) return null;
  return `Scored so far ${scoreFormatter.format(left)} and ${scoreFormatter.format(right)}.`;
}

export function playerProjectionView(input: {
  projected: number;
  range: { Lower: number; Upper: number } | null;
  axis: { Min: number; Max: number } | null;
}): PlayerProjectionView {
  const projected = formatProjectionPoints(input.projected);
  if (!input.range) {
    return { projected, bar: null, rangeText: null, ariaLabel: `Projected ${projected}` };
  }
  const lower = formatProjectionPoints(input.range.Lower);
  const upper = formatProjectionPoints(input.range.Upper);
  const rangeText = `${lower} – ${upper}`;
  const ariaLabel = `Projected ${projected}, range ${lower} to ${upper}`;
  if (!input.axis) return { projected, bar: null, rangeText, ariaLabel };
  const geometry = rangeBarGeometry(input.range, input.axis);
  return {
    projected,
    bar: { left: geometry.left, width: geometry.width, marker: axisPosition(input.projected, input.axis) },
    rangeText,
    ariaLabel
  };
}
