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
  if (delta === null || delta === 0) return '';
  return delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`;
}

export function standingMovementLabel(row: CurrentStandingRow): string {
  const delta = standingCanonicalDelta(row);
  if (delta === null) return 'No previous week available';
  if (delta === 0) return 'No change since last week';
  const magnitude = Math.abs(delta);
  return `Moved ${delta > 0 ? 'up' : 'down'} ${magnitude} ${magnitude === 1 ? 'place' : 'places'} since last week`;
}


export interface StandingPlacementPoint {
  week: number;
  place: number;
  x: number;
  y: number;
}

export interface StandingPlacementTrend {
  points: StandingPlacementPoint[];
  polyline: string;
  lastWeek: number;
  teamCount: number;
  description: string;
}

/**
 * Visualize generator-owned completed-week standings, never reconstruct a ranking.
 * W1 is recoverable from the canonical W2 movement's PreviousWeekPlace.
 * A missing or inconsistent intermediate week invalidates the whole chart,
 * rather than silently connecting unrelated snapshots.
 */
export function standingPlacementTrend(
  row: CurrentStandingRow,
  teamCount: number
): StandingPlacementTrend | null {
  const regular = row.team.Placements?.Current?.Regular;
  if (!regular || !Number.isInteger(teamCount) || teamCount < 2
      || regular.Place !== row.displayPlace
      || !isValidStandingPlace(row.displayPlace, teamCount)) return null;

  const counts = [regular.Wins, regular.Losses, regular.Ties];
  if (counts.some(count => !Number.isInteger(count) || count < 0)) return null;
  const games = counts.reduce((total, count) => total + count, 0);
  if (games < 1 || typeof regular.Record !== 'string'
      || !/^[WLT]+$/.test(regular.Record) || regular.Record.length !== games) return null;

  const movements = regular.WeeklyMovements;
  if (games > 1 && (!Array.isArray(movements) || movements.length !== games - 1)) return null;
  if (Array.isArray(movements) && movements.length !== Math.max(0, games - 1)) return null;

  const places: number[] = [];
  if (games === 1) {
    places.push(row.displayPlace);
  } else {
    const firstPlace = movements![0]?.PreviousWeekPlace;
    if (!isValidStandingPlace(firstPlace, teamCount)) return null;
    places.push(firstPlace);

    for (let week = 2; week <= games; week++) {
      const movement = movements![week - 2];
      if (!movement || movement.Week !== week
          || !isValidStandingPlace(movement.Place, teamCount)
          || movement.PreviousWeekPlace !== places[week - 2]
          || movement.PlaceDelta !== movement.PreviousWeekPlace - movement.Place) return null;
      places.push(movement.Place);
    }
    if (places[places.length - 1] !== row.displayPlace) return null;
  }

  const points = places.map((place, index) => ({
    week: index + 1,
    place,
    x: games === 1 ? 150 : 24 + (252 * index) / (games - 1),
    y: 20 + (55 * (place - 1)) / (teamCount - 1)
  }));

  return {
    points,
    polyline: points.map(point => `${point.x},${point.y}`).join(' '),
    lastWeek: games,
    teamCount,
    description: `Season placements through week ${games}: ${points
      .map(point => `week ${point.week} place ${point.place}`).join(', ')}`
  };
}

function isValidStandingPlace(value: unknown, teamCount: number): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= teamCount;
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
