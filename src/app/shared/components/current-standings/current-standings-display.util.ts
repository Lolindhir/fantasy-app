import type { CurrentStandingRow } from '../../utils/league-standings-view.util';

export interface StandingRecentResult {
  week: number;
  result: 'W' | 'L' | 'T';
}

export function recentStandingResults(row: CurrentStandingRow): StandingRecentResult[] {
  const regular = row.team.Placements?.Current?.Regular;
  if (!regular || typeof regular.Record !== 'string') return [];
  const record = regular.Record;
  const expected = regular.Wins + regular.Losses + regular.Ties;
  if (!/^[WLT]*$/.test(record) || !Number.isInteger(expected) || record.length !== expected) return [];

  const start = Math.max(0, record.length - 5);
  return [...record.slice(start)].map((result, index) => ({
    week: start + index + 1,
    result: result as StandingRecentResult['result']
  }));
}

export function recentStandingResultsLabel(results: readonly StandingRecentResult[]): string {
  const descriptions = { W: 'win', L: 'loss', T: 'tie' };
  return `Last ${results.length} completed games: ${results.map(item =>
    `week ${item.week} ${descriptions[item.result]}`
  ).join(', ')}`;
}

export function standingCanonicalDelta(row: CurrentStandingRow): number | null {
  const regular = row.team.Placements?.Current?.Regular;
  if (!regular || regular.Place !== row.displayPlace) return null;
  const delta = regular.PlaceDelta;
  return typeof delta === 'number' && Number.isFinite(delta) ? delta : null;
}

export function standingMovementText(row: CurrentStandingRow): string {
  const delta = standingCanonicalDelta(row);
  if (delta === null || delta === 0) return '—';
  return delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`;
}

export function standingMovementLabel(row: CurrentStandingRow): string {
  const delta = standingCanonicalDelta(row);
  if (delta === null) return 'No previous week available';
  if (delta === 0) return 'No change since last week';
  const magnitude = Math.abs(delta);
  return `Moved ${delta > 0 ? 'up' : 'down'} ${magnitude} ${magnitude === 1 ? 'place' : 'places'} since last week`;
}

export function standingPlayoffCutline(row: CurrentStandingRow, playoffTeams: number | null, teamCount: number): boolean {
  return playoffTeams !== null && Number.isInteger(playoffTeams)
    && playoffTeams > 0 && playoffTeams < teamCount && row.displayPlace === playoffTeams + 1;
}

export function standingPointDifferential(row: CurrentStandingRow): number {
  return row.team.Points - row.team.PointsAgainst;
}

export function standingPerGame(row: CurrentStandingRow, points: number): number | null {
  const games = row.team.Wins + row.team.Losses + row.team.Ties;
  return games > 0 && Number.isFinite(points) ? points / games : null;
}
