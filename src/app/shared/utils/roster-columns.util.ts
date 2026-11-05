export type RosterMetric = 'ppg' | 'weekProjection' | 'ranking' | 'depth' | 'age' | 'salary' | 'salaryProjected';
export type RosterLayout = 'desktop' | 'mobile';
export type RosterPreset = 'all' | 'performance' | 'financial' | 'custom';

export const METRICS: readonly RosterMetric[] = [
  'ppg', 'weekProjection', 'ranking', 'depth', 'age', 'salary', 'salaryProjected'
];
export const METRIC_LABELS: Readonly<Record<RosterMetric, string>> = {
  ppg: 'Points per Game',
  weekProjection: 'Projection (this week)',
  ranking: 'Combined Ranking',
  depth: 'Depth Chart',
  age: 'Age',
  salary: 'Current Salary',
  salaryProjected: 'Projected Salary'
};
const PRESETS: Record<Exclude<RosterPreset, 'custom'>, readonly RosterMetric[]> = {
  all: METRICS,
  performance: ['ppg', 'ranking', 'depth', 'age'],
  financial: ['salary', 'salaryProjected']
};

export function presetColumns(preset: Exclude<RosterPreset, 'custom'>): RosterMetric[] {
  return [...PRESETS[preset]];
}
export function defaultColumns(layout: RosterLayout): RosterMetric[] {
  return presetColumns(layout === 'desktop' ? 'all' : 'performance');
}
export function normalizeColumns(raw: unknown, layout: RosterLayout): RosterMetric[] {
  if (!Array.isArray(raw)) return defaultColumns(layout);
  const keys = new Set(raw.filter((v): v is RosterMetric =>
    typeof v === 'string' && (METRICS as readonly string[]).includes(v)));
  const normalized = METRICS.filter(v => keys.has(v));
  return normalized.length ? normalized : defaultColumns(layout);
}
export function selectedPreset(columns: readonly RosterMetric[]): RosterPreset {
  for (const key of ['all', 'performance', 'financial'] as const) {
    const reference = PRESETS[key];
    if (columns.length === reference.length && columns.every((v, i) => v === reference[i])) return key;
  }
  return 'custom';
}
export function toggleMetric(columns: readonly RosterMetric[], metric: RosterMetric, enabled: boolean): RosterMetric[] {
  const next = new Set(columns);
  if (enabled) next.add(metric);
  else if (next.size > 1) next.delete(metric);
  return METRICS.filter(v => next.has(v));
}
export function storageKey(layout: RosterLayout): string {
  return 'fantasy-app:team-roster:columns:v1:' + layout;
}
export function decodeColumns(raw: string | null, layout: RosterLayout): RosterMetric[] {
  if (!raw) return defaultColumns(layout);
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || !parsed || (parsed as { version?: unknown }).version !== 1) {
      return defaultColumns(layout);
    }
    return normalizeColumns((parsed as { columns?: unknown }).columns, layout);
  } catch {
    return defaultColumns(layout);
  }
}
export function encodeColumns(columns: readonly RosterMetric[]): string {
  return JSON.stringify({ version: 1, columns });
}

/** Compact display of existing dollar amounts in the mobile team roster only. */
export function formatCompactRosterSalary(amount: number, withPositiveSign = false): string {
  if (!Number.isFinite(amount)) return '—';
  const sign = amount < 0 ? '-' : withPositiveSign ? '+' : '';
  return `${sign}$${(Math.abs(amount) / 1_000_000).toFixed(1)}M`;
}


/**
 * Minimum pixel budgets for the compact Team Detail Roster. These dimensions
 * are the single source for the mobile <colgroup>; spare width is assigned to
 * data columns only, never to the sticky number / player identity.
 */
const MOBILE_ROSTER_MIN_WIDTH_PX: Readonly<Record<string, number>> = {
  rank: 22,
  name: 110,
  ppg: 44,
  weekProjection: 58,
  ranking: 58,
  depth: 66,
  age: 44,
  salary: 72,
  salaryProjected: 80,
  dynamicStat: 122
};

export function mobileRosterColumnMinWidth(column: string): number {
  return MOBILE_ROSTER_MIN_WIDTH_PX[column] ?? 80;
}

export function mobileRosterMinimumTableWidth(columns: readonly string[]): number {
  return columns.reduce((total, column) => total + mobileRosterColumnMinWidth(column), 0);
}

export function mobileRosterFlexibleMetricCount(columns: readonly string[]): number {
  return Math.max(1, columns.filter(column => column !== 'rank' && column !== 'name').length);
}

export function mobileRosterColumnTrackWidth(column: string): string {
  const minimum = mobileRosterColumnMinWidth(column);
  return column === 'rank' || column === 'name'
    ? `${minimum}px`
    : `calc(${minimum}px + var(--roster-flex-extra))`;
}
