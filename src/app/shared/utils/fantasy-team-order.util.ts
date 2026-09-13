import type { FantasyTeam } from '../../core/models/league.models';

export type FantasyTeamNeutralOrderIndex = ReadonlyMap<string, number>;

/**
 * Applies the already-resolved All-Time Overall standings order to a current/live
 * fantasy-team collection. This utility intentionally does not invent a second
 * tie-breaker: duplicate or missing resolved places are contract errors.
 */
export function buildNeutralFantasyTeamOrderIndex(
  teams: readonly FantasyTeam[]
): FantasyTeamNeutralOrderIndex {
  const entries = teams.map(team => ({
    teamID: String(team.TeamID),
    place: resolveAllTimeOverallPlace(team)
  }));
  const seenTeamIDs = new Set<string>();
  const teamIDByPlace = new Map<number, string>();

  for (const entry of entries) {
    if (seenTeamIDs.has(entry.teamID)) {
      throw new Error(`Duplicate fantasy TeamID '${entry.teamID}' in neutral-order input.`);
    }

    const existingTeamID = teamIDByPlace.get(entry.place);
    if (existingTeamID !== undefined) {
      throw new Error(
        `All-Time Overall neutral order is not fully resolved: place ${entry.place} is shared by teams ${existingTeamID} and ${entry.teamID}.`
      );
    }

    seenTeamIDs.add(entry.teamID);
    teamIDByPlace.set(entry.place, entry.teamID);
  }

  entries.sort((left, right) => left.place - right.place);

  return new Map(entries.map((entry, index) => [entry.teamID, index]));
}

export function sortFantasyTeamsByNeutralOrder(
  teams: readonly FantasyTeam[]
): FantasyTeam[] {
  const orderIndex = buildNeutralFantasyTeamOrderIndex(teams);

  return [...teams].sort((left, right) =>
    getNeutralFantasyTeamOrderPosition(orderIndex, left.TeamID)
    - getNeutralFantasyTeamOrderPosition(orderIndex, right.TeamID)
  );
}

export function getNeutralFantasyTeamOrderPosition(
  orderIndex: FantasyTeamNeutralOrderIndex,
  teamID: string | number
): number {
  const position = orderIndex.get(String(teamID));
  if (position === undefined) {
    throw new Error(`Fantasy team '${teamID}' is missing from the resolved All-Time Overall neutral order.`);
  }

  return position;
}

function resolveAllTimeOverallPlace(team: FantasyTeam): number {
  const place = Number(team.Placements?.AllTime?.Playoffs?.Place);

  if (!Number.isFinite(place) || place <= 0 || place >= 999) {
    throw new Error(
      `Fantasy team '${team.TeamID}' has no resolved All-Time Overall place for neutral ordering.`
    );
  }

  return place;
}
