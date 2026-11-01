import type { DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../core/models/fantasy-game-context.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
import type {
  FantasyMatchupReadModel,
  MatchupWeekReadModel,
  MatchupsReadModel
} from '../../core/models/matchup.models';
import type {
  WeeklyRecapKeyGame,
  WeeklyRecapKeyPlayer,
  WeeklyRecapTeamAwards,
  WeeklyRecapsReadModel,
  WeeklyRecapWeek
} from '../../core/models/weekly-recap.models';
import {
  buildNeutralFantasyTeamOrderIndex,
  getNeutralFantasyTeamOrderPosition,
  type FantasyTeamNeutralOrderIndex
} from './fantasy-team-order.util';
import { buildCurrentStandings } from './league-standings-view.util';

export type OverviewWeeklyPhase = 'recap' | 'prep' | 'live';

export interface OverviewStandingRow {
  team: FantasyTeam;
  displayPlace: number;
  wins: number;
  losses: number;
  ties: number;
  points: number;
  pointsAgainst: number;
  record: string;
  streak: string | null;
  /**
   * Canonical weekly place movement (generator-owned `PlaceDelta`, positive = moved up).
   * `null` when no comparable value exists for the displayed standings snapshot.
   */
  placeDelta: number | null;
}

export interface OverviewLastMatchupParticipant {
  team: FantasyTeam;
  points: number | null;
  isWinner: boolean;
}

export interface OverviewLastMatchup {
  matchupID: string;
  participants: [OverviewLastMatchupParticipant, OverviewLastMatchupParticipant];
}

export interface OverviewTopContext {
  standings: OverviewStandingRow[];
  lastCompletedWeek: number | null;
  lastMatchups: OverviewLastMatchup[];
}

export interface OverviewRecapSelection {
  week: number;
  games: WeeklyRecapKeyGame[];
  players: WeeklyRecapKeyPlayer[];
  awards: WeeklyRecapTeamAwards | null;
  prominent: boolean;
}

interface OverviewEffectiveStandingContext {
  currentPlaces: ReadonlyMap<string, number> | null;
  neutralOrder: FantasyTeamNeutralOrderIndex | null;
}

interface MatchupSortKey {
  sum: number;
  distance: number;
  best: number;
}

const prepLeadMs = 24 * 60 * 60 * 1000;

export function resolveOverviewWeeklyPhase(
  readModel: MatchupsReadModel | null | undefined,
  now: Date,
  displayWeek: number | null = readModel?.Summary.ActiveOrNextWeek ?? null
): OverviewWeeklyPhase {
  if (!readModel) return 'prep';

  const activeWeek = findWeek(readModel, displayWeek);
  const kickoffMs = parseUtc(activeWeek?.FirstKickoffUtc);
  const nowMs = now.getTime();

  if (kickoffMs !== null) {
    if (nowMs >= kickoffMs) return 'live';
    if (nowMs >= kickoffMs - prepLeadMs) return 'prep';
  }

  // Between a completed week and the next 24h prep window, recap is the active
  // presentation. Before Week 1 there is no recap source, so use the prep layout
  // without fabricating recap content.
  return getLastCompletedWeek(readModel) ? 'recap' : 'prep';
}

export function isOverviewCurrentWeekSurfaceReady(
  league: League,
  readModel: MatchupsReadModel | null | undefined,
  decisionWindows: DecisionWindowsReadModel | null | undefined,
  fantasyContext: FantasyGameContextReadModel | null | undefined
): boolean {
  if (!readModel || readModel.Season !== league.Season) return false;

  const activeWeek = readModel.Summary.ActiveOrNextWeek;
  if (activeWeek === null) return false;

  const lastCompletedWeek = readModel.Summary.LastCompletedWeek ?? 0;
  if (!currentStandingsCoverCompletedWeek(league, lastCompletedWeek)) return false;

  if (!decisionWindows
    || decisionWindows.Season !== league.Season
    || decisionWindows.LineupWeek !== activeWeek) {
    return false;
  }

  return !!fantasyContext
    && fantasyContext.Season === league.Season
    && fantasyContext.Week === activeWeek;
}

export function resolveOverviewDisplayWeek(
  league: League,
  readModel: MatchupsReadModel | null | undefined,
  decisionWindows: DecisionWindowsReadModel | null | undefined,
  fantasyContext: FantasyGameContextReadModel | null | undefined
): number | null {
  if (!readModel || readModel.Season !== league.Season) return null;

  const activeWeek = readModel.Summary.ActiveOrNextWeek;
  if (activeWeek === null) return null;

  if (isOverviewCurrentWeekSurfaceReady(league, readModel, decisionWindows, fantasyContext)) {
    return activeWeek;
  }

  // Rollover is atomic in the Overview. If the source-owned Matchups model has
  // already discovered N+1 but the rest of the weekly context has not caught up,
  // keep presenting N rather than partially exposing N+1 or hiding the surface.
  const retainedWeek = activeWeek - 1;
  return retainedWeek > 0 && findWeek(readModel, retainedWeek)
    ? retainedWeek
    : activeWeek;
}

export function buildOverviewTopContext(
  league: League,
  readModel: MatchupsReadModel | null | undefined,
  displayWeek: number | null = readModel?.Summary.ActiveOrNextWeek ?? null
): OverviewTopContext {
  const standings = buildOverviewStandingsSnapshot(league, readModel, displayWeek);
  const lastWeek = displayWeek === null
    ? getLastCompletedWeek(readModel)
    : getFinalWeek(readModel, displayWeek - 1);
  if (!lastWeek) {
    return { standings, lastCompletedWeek: null, lastMatchups: [] };
  }

  const teamByID = new Map(league.Teams.map(team => [String(team.TeamID), team]));
  const historicalStandings = buildOverviewStandingsSnapshot(
    league,
    readModel,
    lastWeek.Week,
    false
  );
  const orderedLastMatchups = orderOverviewCurrentMatchups(
    league,
    lastWeek.Matchups,
    historicalStandings
  );
  const lastMatchups: OverviewLastMatchup[] = [];

  for (const matchup of orderedLastMatchups) {
    if (matchup.CompletionState !== 'final' || matchup.Participants.length !== 2) continue;

    const mapped = matchup.Participants.map(participant => {
      const team = teamByID.get(String(participant.TeamID));
      if (!team) return null;

      return {
        team,
        points: participant.Points,
        isWinner: matchup.Result?.Type === 'win'
          && String(matchup.Result.WinnerTeamID) === String(participant.TeamID)
      } satisfies OverviewLastMatchupParticipant;
    });

    if (!mapped[0] || !mapped[1]) continue;
    lastMatchups.push({
      matchupID: matchup.FantasyMatchupID,
      participants: [mapped[0], mapped[1]]
    });
  }

  return {
    standings,
    lastCompletedWeek: lastWeek.Week,
    lastMatchups
  };
}

export function selectOverviewRecap(
  readModel: WeeklyRecapsReadModel | null | undefined,
  season: string,
  lastCompletedWeek: number | null,
  phase: OverviewWeeklyPhase
): OverviewRecapSelection | null {
  if (!readModel || readModel.Season !== season || lastCompletedWeek === null) return null;

  const recap = readModel.Weeks.find(candidate => candidate.Week === lastCompletedWeek);
  if (!recap) return null;

  return selectRecapDensity(recap, phase === 'recap');
}

export function orderOverviewCurrentMatchups(
  league: League,
  matchups: readonly FantasyMatchupReadModel[],
  standings: readonly OverviewStandingRow[] | null = null
): FantasyMatchupReadModel[] {
  const context = buildEffectiveStandingContext(league, standings);
  const teamByID = new Map(league.Teams.map(team => [String(team.TeamID), team]));

  const oriented = matchups.map(matchup => ({
    matchup: orientMatchupParticipants(matchup, teamByID, context),
    key: buildMatchupSortKey(matchup, teamByID, context)
  }));

  oriented.sort((left, right) => {
    if (left.key && right.key) {
      const ranked = left.key.sum - right.key.sum
        || left.key.distance - right.key.distance
        || left.key.best - right.key.best;
      if (ranked !== 0) return ranked;
    }

    return left.matchup.FantasyMatchupID.localeCompare(right.matchup.FantasyMatchupID);
  });

  return oriented.map(entry => entry.matchup);
}

export function getLastCompletedWeek(
  readModel: MatchupsReadModel | null | undefined
): MatchupWeekReadModel | null {
  if (!readModel || readModel.Summary.LastCompletedWeek === null) return null;

  const week = findWeek(readModel, readModel.Summary.LastCompletedWeek);
  return week?.CompletionState === 'final' ? week : null;
}

function buildOverviewStandingsSnapshot(
  league: League,
  readModel: MatchupsReadModel | null | undefined,
  displayWeek: number | null,
  useCurrentFallback = true
): OverviewStandingRow[] {
  // The only fallback is the separately generated current table before a
  // historical week is required. No score, streak or ranking replay from Matchups.
  if (!readModel || displayWeek === null) {
    return useCurrentFallback ? buildCurrentOverviewStandingRows(league) : [];
  }
  if (readModel.Season !== league.Season) return [];

  const playoffStartWeek = Number(league.PlayoffStartWeek);
  const completedWeek = Number.isFinite(playoffStartWeek) && playoffStartWeek > 0
    ? Math.min(displayWeek - 1, Math.max(0, playoffStartWeek - 1))
    : Math.max(0, displayWeek - 1);
  if (completedWeek <= 0) {
    return useCurrentFallback ? buildCurrentOverviewStandingRows(league) : [];
  }

  const season = league.Standings.find(row => row.Season === league.Season);
  const snapshot = season?.Weeks?.find(row => row.Week === completedWeek);
  if (!snapshot || snapshot.Teams.length !== league.Teams.length || league.Teams.length === 0) return [];

  const teams = new Map(league.Teams.map(team => [String(team.TeamID), team]));
  if (teams.size !== league.Teams.length) return [];
  const seen = new Set<string>();
  const standings: OverviewStandingRow[] = [];
  for (const row of snapshot.Teams) {
    const key = String(row.TeamID);
    const team = teams.get(key);
    const counts = [row.Wins, row.Losses, row.Ties];
    if (!team || seen.has(key)
      || !Number.isInteger(row.Place) || row.Place < 1 || row.Place > teams.size
      || counts.some(count => !Number.isInteger(count) || count < 0)
      || counts.reduce((total, count) => total + count, 0) !== completedWeek
      || !Number.isFinite(row.Points) || !Number.isFinite(row.PointsAgainst)
      || typeof row.Streak !== 'string' || !/^[1-9][0-9]*[WLT]$/.test(row.Streak)) {
      return []; // incomplete or stale product is unknown, not evidence to replay
    }
    seen.add(key);
    standings.push({
      team,
      displayPlace: row.Place,
      wins: row.Wins,
      losses: row.Losses,
      ties: row.Ties,
      points: row.Points,
      pointsAgainst: row.PointsAgainst,
      record: formatStandingRecord(row.Wins, row.Losses, row.Ties),
      streak: row.Streak,
      placeDelta: resolveCanonicalPlaceDelta(team, row.Place, completedWeek, completedWeek)
    });
  }

  // Shared ranking can include equal places (competition ranking: 1,1,3).
  // Stable canonical roster-ID order from the product resolves display-only ties.
  return standings.sort((a, b) => a.displayPlace - b.displayPlace
    || Number(a.team.TeamID) - Number(b.team.TeamID));
}

// The generator owns weekly position changes. Match the historical movement to
// the exact completed week of the as-of snapshot, not to the current League week.
// Older data without history may use current PlaceDelta only for the current table.
function resolveCanonicalPlaceDelta(
  team: FantasyTeam,
  displayPlace: number,
  completedWeek: number,
  gamesInSnapshot: number
): number | null {
  const placement = team.Placements?.Current?.Regular;
  if (!placement) return null;

  if (Array.isArray(placement.WeeklyMovements)) {
    const movement = placement.WeeklyMovements.find(entry => entry.Week === completedWeek);
    if (!movement || movement.Place !== displayPlace) return null;
    return typeof movement.PlaceDelta === 'number' && Number.isFinite(movement.PlaceDelta)
      ? movement.PlaceDelta
      : null;
  }

  const delta = placement.PlaceDelta;
  if (typeof delta !== 'number' || !Number.isFinite(delta)) return null;

  const currentGames = Number(placement.Wins ?? 0) + Number(placement.Losses ?? 0) + Number(placement.Ties ?? 0);
  if (currentGames !== gamesInSnapshot || Number(placement.Place) !== displayPlace) return null;

  return delta;
}

function buildCurrentOverviewStandingRows(league: League): OverviewStandingRow[] {
  return buildCurrentStandings(league, league.Teams).map(({ team, displayPlace }) => {
    const placement = team.Placements?.Current?.Regular;
    const wins = Number(placement?.Wins ?? 0);
    const losses = Number(placement?.Losses ?? 0);
    const ties = Number(placement?.Ties ?? 0);
    return {
      team,
      displayPlace,
      wins,
      losses,
      ties,
      points: Number(placement?.Points ?? team.Points ?? 0),
      pointsAgainst: Number(placement?.PointsAgainst ?? team.PointsAgainst ?? 0),
      record: formatStandingRecord(wins, losses, ties),
      streak: placement?.Streak?.trim() || null,
      placeDelta: typeof placement?.PlaceDelta === 'number' && Number.isFinite(placement.PlaceDelta)
        ? placement.PlaceDelta
        : null
    };
  });
}

function formatStandingRecord(wins: number, losses: number, ties: number): string {
  const base = `${wins}-${losses}`;
  return ties > 0 ? `${base}-${ties}` : base;
}

function getFinalWeek(
  readModel: MatchupsReadModel | null | undefined,
  weekNumber: number
): MatchupWeekReadModel | null {
  if (!readModel || weekNumber <= 0) return null;
  const week = findWeek(readModel, weekNumber);
  return week?.CompletionState === 'final' ? week : null;
}

function currentStandingsCoverCompletedWeek(league: League, lastCompletedWeek: number): boolean {
  if (lastCompletedWeek <= 0) return true;
  if (!Array.isArray(league.Teams) || league.Teams.length === 0) return false;

  const playoffStartWeek = Number(league.PlayoffStartWeek);
  const requiredCompletedRegularGames = Number.isFinite(playoffStartWeek) && playoffStartWeek > 0
    ? Math.min(lastCompletedWeek, Math.max(0, playoffStartWeek - 1))
    : lastCompletedWeek;

  return league.Teams.every(team => {
    const regular = team.Placements?.Current?.Regular;
    if (!regular) return false;

    const values = [regular.Wins, regular.Losses, regular.Ties].map(Number);
    if (values.some(value => !Number.isFinite(value) || value < 0)) return false;

    return values[0] + values[1] + values[2] >= requiredCompletedRegularGames;
  });
}

function selectRecapDensity(recap: WeeklyRecapWeek, prominent: boolean): OverviewRecapSelection {
  return {
    week: recap.Week,
    games: recap.KeyGames.slice(0, 2),
    players: recap.KeyPlayers.slice(0, 3),
    awards: recap.TeamAwards?.State === 'available' ? recap.TeamAwards : null,
    prominent
  };
}

function buildEffectiveStandingContext(
  league: League,
  standings: readonly OverviewStandingRow[] | null = null
): OverviewEffectiveStandingContext {
  return {
    currentPlaces: standings
      ? new Map(standings.map(row => [String(row.team.TeamID), row.displayPlace]))
      : resolveUsableCurrentPlaces(league),
    neutralOrder: tryBuildNeutralOrder(league.Teams)
  };
}

function resolveUsableCurrentPlaces(league: League): ReadonlyMap<string, number> | null {
  if (league.FinalScoredWeek <= 0 || league.Teams.length === 0) return null;

  const currentStanding = Array.isArray(league.Standings)
    ? league.Standings.find(standing => standing.Season === league.Season)
    : undefined;
  const rowPlaceByTeam = new Map(
    currentStanding?.RegularSeason.map(row => [String(row.TeamID), normalizePlace(row.Place)]) ?? []
  );
  const resolved = new Map<string, number>();
  // Equal canonical places are legitimate ties; validate team coverage, not place uniqueness.
  for (const team of league.Teams) {
    const place = rowPlaceByTeam.get(String(team.TeamID))
      ?? normalizePlace(team.Placements?.Current?.Regular?.Place);
    if (place === null) return null;

    resolved.set(String(team.TeamID), place);
  }

  return resolved;
}

function effectiveStanding(
  team: FantasyTeam,
  context: OverviewEffectiveStandingContext
): number | null {
  const current = context.currentPlaces?.get(String(team.TeamID));
  if (current !== undefined) return current;

  const previous = normalizePlace(team.Placements?.Previous?.Playoffs?.Place);
  if (previous !== null) return previous;

  if (context.neutralOrder) {
    return getNeutralFantasyTeamOrderPosition(context.neutralOrder, team.TeamID) + 1;
  }

  return null;
}

function orientMatchupParticipants(
  matchup: FantasyMatchupReadModel,
  teamByID: ReadonlyMap<string, FantasyTeam>,
  context: OverviewEffectiveStandingContext
): FantasyMatchupReadModel {
  if (matchup.Participants.length !== 2) return matchup;

  const first = matchup.Participants[0];
  const second = matchup.Participants[1];
  const firstTeam = teamByID.get(String(first.TeamID));
  const secondTeam = teamByID.get(String(second.TeamID));
  if (!firstTeam || !secondTeam) return matchup;

  const firstStanding = effectiveStanding(firstTeam, context);
  const secondStanding = effectiveStanding(secondTeam, context);
  let swap = false;

  if (firstStanding !== null && secondStanding !== null && firstStanding !== secondStanding) {
    swap = firstStanding > secondStanding;
  } else if (context.neutralOrder) {
    swap = getNeutralFantasyTeamOrderPosition(context.neutralOrder, first.TeamID)
      > getNeutralFantasyTeamOrderPosition(context.neutralOrder, second.TeamID);
  }

  if (!swap) return matchup;
  return { ...matchup, Participants: [second, first] };
}

function buildMatchupSortKey(
  matchup: FantasyMatchupReadModel,
  teamByID: ReadonlyMap<string, FantasyTeam>,
  context: OverviewEffectiveStandingContext
): MatchupSortKey | null {
  if (matchup.Participants.length !== 2) return null;

  const teams = matchup.Participants.map(participant => teamByID.get(String(participant.TeamID)) ?? null);
  if (!teams[0] || !teams[1]) return null;

  const a = effectiveStanding(teams[0], context);
  const b = effectiveStanding(teams[1], context);
  if (a === null || b === null) return null;

  return {
    sum: a + b,
    distance: Math.abs(a - b),
    best: Math.min(a, b)
  };
}

function tryBuildNeutralOrder(teams: readonly FantasyTeam[]): FantasyTeamNeutralOrderIndex | null {
  try {
    return buildNeutralFantasyTeamOrderIndex(teams);
  } catch {
    return null;
  }
}

function findWeek(
  readModel: MatchupsReadModel,
  week: number | null
): MatchupWeekReadModel | null {
  if (week === null) return null;
  return readModel.Weeks.find(candidate => candidate.Week === week) ?? null;
}

function normalizePlace(value: number | null | undefined): number | null {
  const place = Number(value);
  return Number.isFinite(place) && place > 0 && place < 999 ? place : null;
}

function parseUtc(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}
