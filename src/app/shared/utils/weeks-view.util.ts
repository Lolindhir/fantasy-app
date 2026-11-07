import type { FantasyTeam } from '../../core/models/league.models';
import type {
  FantasyMatchupReadModel,
  MatchupCompletionState,
  MatchupStage,
  MatchupWeekReadModel,
  MatchupsReadModel
} from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import type { PastSeasonsIndex } from '../../core/services/data-api.service';
import type { WeekRecapContent } from '../components/week-recap-content/week-recap-content';
import { buildNeutralFantasyTeamOrderIndex } from './fantasy-team-order.util';

/**
 * Pure presentation helpers of the Weeks page. They only select and arrange values that the generated
 * Matchups and WeeklyRecaps files already contain; no statistic, rank or standing is computed here.
 */

export interface WeeksSeasonOption {
  season: string;
  isCurrent: boolean;
  /** Null for the current season (loaded from Matchups.json / WeeklyRecaps.json). */
  matchupsPath: string | null;
  recapsPath: string | null;
}

export interface WeekTab {
  week: number;
  stage: MatchupStage;
  isPlayoff: boolean;
  state: MatchupCompletionState;
}

export interface WeekScoreboardParticipant {
  teamID: number;
  team: FantasyTeam | null;
  points: number | null;
  isWinner: boolean;
}

export interface WeekScoreboardMatchup {
  matchupID: string;
  state: MatchupCompletionState;
  isTie: boolean;
  participants: WeekScoreboardParticipant[];
}

export type SeasonGridOutcome = 'win' | 'loss' | 'tie';

export interface SeasonGridCell {
  week: number;
  points: number | null;
  outcome: SeasonGridOutcome | null;
  /** Highest score of this week among the scored participants (ties mark every holder). */
  isWeekHigh: boolean;
}

export interface SeasonGridRow {
  teamID: number;
  team: FantasyTeam | null;
  cells: SeasonGridCell[];
}

export interface SeasonGrid {
  weeks: WeekTab[];
  regularWeekCount: number;
  playoffWeekCount: number;
  rows: SeasonGridRow[];
}

export type WeekRecapStatus = 'available' | 'pending-final' | 'missing';

export interface WeekRecapSelection {
  status: WeekRecapStatus;
  content: WeekRecapContent | null;
}

/** Current season first, then archived seasons that have a Matchups file, newest first. */
export function buildWeeksSeasonOptions(
  index: PastSeasonsIndex | null | undefined,
  currentSeason: string
): WeeksSeasonOption[] {
  const past = (index?.Seasons ?? [])
    .filter(entry =>
      entry.Resources?.Matchups?.Exists === true
      && !!entry.Resources.Matchups.Path
      && Number(entry.Season) < Number(currentSeason))
    .sort((left, right) => Number(right.Season) - Number(left.Season))
    .map((entry): WeeksSeasonOption => ({
      season: entry.Season,
      isCurrent: false,
      matchupsPath: entry.Resources.Matchups!.Path,
      recapsPath: entry.Resources.WeeklyRecaps?.Exists === true
        ? entry.Resources.WeeklyRecaps.Path || null
        : null
    }));

  return [{ season: currentSeason, isCurrent: true, matchupsPath: null, recapsPath: null }, ...past];
}

/** A requested season is honored only when it is selectable; otherwise the current season applies. */
export function resolveWeeksSeason(
  options: readonly WeeksSeasonOption[],
  requested: string | null | undefined
): WeeksSeasonOption | null {
  if (options.length === 0) return null;
  return options.find(option => option.season === requested) ?? options[0];
}

export function buildWeekTabs(model: MatchupsReadModel | null | undefined): WeekTab[] {
  return (model?.Weeks ?? [])
    .map(week => ({
      week: week.Week,
      stage: week.Stage,
      isPlayoff: week.Stage === 'playoffs',
      state: week.CompletionState
    }))
    .sort((left, right) => left.week - right.week);
}

function weekIsSettled(week: MatchupWeekReadModel): boolean {
  return week.CompletionState === 'final'
    || (week.Matchups.length > 0 && week.Matchups.every(matchup => matchup.CompletionState === 'final'));
}

/**
 * The default week is the last settled week. A week counts as settled when the file marks it final or all
 * of its matchups are final (archived weeks can carry an `unknown` week state with final matchups).
 */
export function resolveDefaultWeek(model: MatchupsReadModel | null | undefined): number | null {
  const weeks = [...(model?.Weeks ?? [])].sort((left, right) => left.Week - right.Week);
  if (weeks.length === 0) return null;

  const settled = weeks.filter(weekIsSettled);
  if (settled.length > 0) return settled[settled.length - 1].Week;

  const summaryWeek = model?.Summary?.LastCompletedWeek ?? null;
  if (summaryWeek !== null && weeks.some(week => week.Week === summaryWeek)) return summaryWeek;

  return weeks[0].Week;
}

/** Picks the requested week when it exists, otherwise the default week. */
export function resolveSelectedWeek(
  model: MatchupsReadModel | null | undefined,
  ...candidates: Array<number | null | undefined>
): number | null {
  const available = new Set((model?.Weeks ?? []).map(week => week.Week));
  for (const candidate of candidates) {
    if (candidate !== null && candidate !== undefined && available.has(candidate)) return candidate;
  }
  return resolveDefaultWeek(model);
}

export function parseWeekParam(value: string | null | undefined): number | null {
  if (value === null || value === undefined || !/^\d+$/.test(value.trim())) return null;
  return Number(value.trim());
}

function indexTeams(teams: readonly FantasyTeam[]): Map<number, FantasyTeam> {
  return new Map(teams.map(team => [Number(team.TeamID), team]));
}

function isWinner(matchup: FantasyMatchupReadModel, teamID: number): boolean {
  return matchup.Result?.Type === 'win' && Number(matchup.Result.WinnerTeamID) === teamID;
}

export function buildWeekScoreboard(
  week: MatchupWeekReadModel | null | undefined,
  teams: readonly FantasyTeam[]
): WeekScoreboardMatchup[] {
  if (!week) return [];
  const teamByID = indexTeams(teams);

  return week.Matchups.map(matchup => ({
    matchupID: matchup.FantasyMatchupID,
    state: matchup.CompletionState,
    isTie: matchup.Result?.Type === 'tie',
    participants: matchup.Participants.map(participant => ({
      teamID: Number(participant.TeamID),
      team: teamByID.get(Number(participant.TeamID)) ?? null,
      points: participant.Points ?? null,
      isWinner: isWinner(matchup, Number(participant.TeamID))
    }))
  }));
}

/** Recap of one week; a missing recap is a visible state, never an error or an invented value. */
export function selectWeekRecap(
  recaps: WeeklyRecapsReadModel | null | undefined,
  season: string,
  week: MatchupWeekReadModel | null | undefined
): WeekRecapSelection {
  if (!week) return { status: 'missing', content: null };

  const recap = recaps && recaps.Season === season
    ? recaps.Weeks.find(candidate => candidate.Week === week.Week)
    : undefined;

  if (recap) {
    return {
      status: 'available',
      content: {
        games: recap.KeyGames,
        players: recap.KeyPlayers,
        awards: recap.TeamAwards?.State === 'available' ? recap.TeamAwards : null
      }
    };
  }

  return { status: weekIsSettled(week) ? 'missing' : 'pending-final', content: null };
}

function orderedTeamIDs(
  model: MatchupsReadModel,
  teams: readonly FantasyTeam[]
): number[] {
  const known = [...teams];
  try {
    const order = buildNeutralFantasyTeamOrderIndex(known);
    known.sort((left, right) => (order.get(String(left.TeamID)) ?? 0) - (order.get(String(right.TeamID)) ?? 0));
  } catch {
    known.sort((left, right) => Number(left.TeamID) - Number(right.TeamID));
  }

  const ids = known.map(team => Number(team.TeamID));
  const seen = new Set(ids);
  const extra = new Set<number>();
  for (const week of model.Weeks) {
    for (const matchup of week.Matchups) {
      for (const participant of matchup.Participants) {
        const id = Number(participant.TeamID);
        if (!seen.has(id)) extra.add(id);
      }
    }
  }

  return [...ids, ...[...extra].sort((left, right) => left - right)];
}

/** Team x week table of the values already present in the Matchups file. */
export function buildSeasonGrid(
  model: MatchupsReadModel | null | undefined,
  teams: readonly FantasyTeam[]
): SeasonGrid | null {
  if (!model || model.Weeks.length === 0) return null;

  const weeks = buildWeekTabs(model);
  const teamByID = indexTeams(teams);
  const sortedWeeks = [...model.Weeks].sort((left, right) => left.Week - right.Week);

  const rows = orderedTeamIDs(model, teams).map((teamID): SeasonGridRow => ({
    teamID,
    team: teamByID.get(teamID) ?? null,
    cells: sortedWeeks.map((week): SeasonGridCell => {
      const matchup = week.Matchups.find(candidate =>
        candidate.Participants.some(participant => Number(participant.TeamID) === teamID));
      const participant = matchup?.Participants.find(candidate => Number(candidate.TeamID) === teamID);
      const shown = !!matchup && matchup.CompletionState !== 'open' && participant?.Points != null;

      let outcome: SeasonGridOutcome | null = null;
      if (matchup && matchup.CompletionState === 'final' && matchup.Result) {
        outcome = matchup.Result.Type === 'tie'
          ? 'tie'
          : (isWinner(matchup, teamID) ? 'win' : 'loss');
      }

      return {
        week: week.Week,
        points: shown ? participant!.Points : null,
        outcome,
        isWeekHigh: false
      };
    })
  }));

  sortedWeeks.forEach((week, index) => {
    const scores = rows
      .map(row => row.cells[index].points)
      .filter((points): points is number => points !== null);
    if (scores.length < 2) return;

    const high = Math.max(...scores);
    for (const row of rows) {
      if (row.cells[index].points === high) row.cells[index].isWeekHigh = true;
    }
  });

  const playoffWeekCount = weeks.filter(week => week.isPlayoff).length;
  return { weeks, regularWeekCount: weeks.length - playoffWeekCount, playoffWeekCount, rows };
}
