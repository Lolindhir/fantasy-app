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
  now: Date
): OverviewWeeklyPhase {
  if (!readModel) return 'prep';

  const activeWeek = findWeek(readModel, readModel.Summary.ActiveOrNextWeek);
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

export function buildOverviewTopContext(
  league: League,
  readModel: MatchupsReadModel | null | undefined
): OverviewTopContext {
  const standings = buildCurrentStandings(league, league.Teams);
  const lastWeek = getLastCompletedWeek(readModel);
  if (!lastWeek) {
    return { standings, lastCompletedWeek: null, lastMatchups: [] };
  }

  const teamByID = new Map(league.Teams.map(team => [String(team.TeamID), team]));
  const lastMatchups: OverviewLastMatchup[] = [];

  for (const matchup of lastWeek.Matchups) {
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
  matchups: readonly FantasyMatchupReadModel[]
): FantasyMatchupReadModel[] {
  const context = buildEffectiveStandingContext(league);
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
    prominent
  };
}

function buildEffectiveStandingContext(league: League): OverviewEffectiveStandingContext {
  return {
    currentPlaces: resolveUsableCurrentPlaces(league),
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
  const seenPlaces = new Set<number>();

  for (const team of league.Teams) {
    const place = rowPlaceByTeam.get(String(team.TeamID))
      ?? normalizePlace(team.Placements?.Current?.Regular?.Place);
    if (place === null || seenPlaces.has(place)) return null;

    resolved.set(String(team.TeamID), place);
    seenPlaces.add(place);
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
