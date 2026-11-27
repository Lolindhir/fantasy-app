import type { FantasyTeam, FantasyTeamSummary } from '../../core/models/league.models';
import type {
  FantasyMatchupReadModel,
  MatchupCompletionState,
  MatchupStage,
  MatchupWeekReadModel,
  MatchupsReadModel
} from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel, WeeklyRecapWinProbability } from '../../core/models/weekly-recap.models';
import type { PastSeasonsIndex } from '../../core/services/data-api.service';
import type { WeekRecapContent, WeekRecapUpset } from '../components/week-recap-content/week-recap-content';
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
  /** Historical FantasyGameContext used to open a matchup's detail; null when the season has none. */
  contextPath?: string | null;
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
  /** Presentation-only text from authoritative playoff bracket metadata; null for legacy/unknown data. */
  playoffLabel: string | null;
  participants: WeekScoreboardParticipant[];
}

/** One known fantasy week and its actual pairings, without inferred future opponents. */
export interface ScheduleOverviewWeek {
  week: number;
  isPlayoff: boolean;
  state: MatchupCompletionState;
  matchups: WeekScoreboardMatchup[];
}

export interface ScheduleOverview {
  upcoming: ScheduleOverviewWeek[];
  played: ScheduleOverviewWeek[];
}

export type SeasonGridOutcome = 'win' | 'loss' | 'tie';

export interface SeasonGridCell {
  week: number;
  points: number | null;
  outcome: SeasonGridOutcome | null;
  /** Highest score of this week among the scored participants (ties mark every holder). */
  isWeekHigh: boolean;
}

export interface SeasonGridRow<T extends FantasyTeamSummary = FantasyTeam> {
  teamID: number;
  team: T | null;
  cells: SeasonGridCell[];
}

export interface SeasonGrid<T extends FantasyTeamSummary = FantasyTeam> {
  weeks: WeekTab[];
  regularWeekCount: number;
  playoffWeekCount: number;
  rows: SeasonGridRow<T>[];
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
        : null,
      contextPath: entry.Resources.FantasyGameContext?.Exists === true
        ? entry.Resources.FantasyGameContext.Path || null
        : null
    }));

  return [{ season: currentSeason, isCurrent: true, matchupsPath: null, recapsPath: null, contextPath: null }, ...past];
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

function indexTeams<T extends FantasyTeamSummary>(teams: readonly T[]): Map<number, T> {
  return new Map(teams.map(team => [Number(team.TeamID), team]));
}

function isWinner(matchup: FantasyMatchupReadModel, teamID: number): boolean {
  return matchup.Result?.Type === 'win' && Number(matchup.Result.WinnerTeamID) === teamID;
}

/** Labels use published bracket provenance only; never infer playoff position from points or standings. */
export function playoffMatchupLabel(matchup: FantasyMatchupReadModel): string | null {
  const round = matchup.PlayoffRound;
  const total = matchup.PlayoffRoundCount;
  const place = matchup.PlayoffPlacement;
  let label: string | null = null;

  if (matchup.Bracket === 'consolation') {
    label = 'Consolation';
  } else if (matchup.Bracket === 'placement') {
    if (place != null && Number.isInteger(place) && place > 1) {
      const suffix = place % 100 >= 11 && place % 100 <= 13 ? 'th'
        : place % 10 === 1 ? 'st' : place % 10 === 2 ? 'nd' : place % 10 === 3 ? 'rd' : 'th';
      label = `${place}${suffix} place`;
    }
  } else if (matchup.Bracket === 'championship') {
    if (round != null && total != null && Number.isInteger(round) && Number.isInteger(total)
        && round >= 1 && total >= round) {
      const remaining = total - round;
      label = remaining === 0 ? 'Final'
        : remaining === 1 ? 'Semifinal'
        : remaining === 2 ? 'Quarterfinal'
        : `Playoff round ${round}`;
    }
  }

  // A round's leg is shown only when the canonical format proves it spans multiple weeks.
  const leg = matchup.PlayoffRoundWeek;
  const legs = matchup.PlayoffRoundWeeks;
  if (label && leg != null && legs != null && Number.isInteger(leg) && Number.isInteger(legs)
      && legs > 1 && leg >= 1 && leg <= legs) {
    return `${label} · ${leg}/${legs}`;
  }
  return label;
}

/** Assign display-only Roman ordinals to repeated playoff fixtures, not bracket seeds.
 * First observed fixture order is stable across legs because identity uses the unordered team pair.
 * Missing/ambiguous team pairs are never numbered.
 */
export function buildPlayoffDisplayLabels(model: MatchupsReadModel | null | undefined): ReadonlyMap<string, string> {
  const groups = new Map<string, Map<string, number>>();
  const entries: Array<{ key: string; group: string; pair: string | null; label: string }> = [];

  for (const week of [...(model?.Weeks ?? [])].sort((a, b) => a.Week - b.Week)) {
    if (week.Stage !== 'playoffs') continue;
    for (const matchup of week.Matchups) {
      const label = playoffMatchupLabel(matchup);
      if (!label) continue;

      const baseLabel = label.split(' · ')[0];
      const group = `${matchup.Bracket}:${matchup.PlayoffRound ?? 'unknown'}:${matchup.PlayoffRoundCount ?? 'unknown'}:${matchup.PlayoffPlacement ?? 'none'}:${baseLabel}`;
      const ids = matchup.Participants.map(participant => Number(participant.TeamID));
      const pair = ids.length === 2 && ids.every(id => Number.isSafeInteger(id) && id > 0) && ids[0] !== ids[1]
        ? [...ids].sort((a, b) => a - b).join(':')
        : null;
      // No ordinal without an authoritative round; unknowns still keep their base label.
      if (pair !== null && Number.isSafeInteger(matchup.PlayoffRound) && (matchup.PlayoffRound ?? 0) > 0) {
        const known = groups.get(group) ?? new Map<string, number>();
        if (!known.has(pair)) known.set(pair, known.size + 1);
        groups.set(group, known);
      }
      entries.push({ key: `${week.Week}:${matchup.FantasyMatchupID}`, group, pair, label });
    }
  }

  const toRoman = (number: number): string => {
    const parts: string[] = [];
    for (const [value, numeral] of [[10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']] as const) {
      while (number >= value) {
        parts.push(numeral);
        number -= value;
      }
    }
    return parts.join('');
  };

  const result = new Map<string, string>();
  for (const entry of entries) {
    const group = groups.get(entry.group);
    const ordinal = entry.pair === null ? null : group?.get(entry.pair);
    if (ordinal !== undefined && ordinal !== null && group && group.size > 1) {
      const separator = entry.label.indexOf(' · ');
      const base = separator < 0 ? entry.label : entry.label.slice(0, separator);
      const leg = separator < 0 ? '' : entry.label.slice(separator);
      result.set(entry.key, `${base} ${toRoman(ordinal)}${leg}`);
    } else {
      result.set(entry.key, entry.label);
    }
  }
  return result;
}

export function buildWeekScoreboard(
  week: MatchupWeekReadModel | null | undefined,
  teams: readonly FantasyTeam[],
  displayLabels?: ReadonlyMap<string, string>
): WeekScoreboardMatchup[] {
  if (!week) return [];
  const teamByID = indexTeams(teams);

  return week.Matchups.map(matchup => ({
    matchupID: matchup.FantasyMatchupID,
    state: matchup.CompletionState,
    isTie: matchup.Result?.Type === 'tie',
    playoffLabel: displayLabels?.get(`${week.Week}:${matchup.FantasyMatchupID}`) ?? playoffMatchupLabel(matchup),
    participants: matchup.Participants.map(participant => ({
      teamID: Number(participant.TeamID),
      team: teamByID.get(Number(participant.TeamID)) ?? null,
      points: participant.Points ?? null,
      isWinner: isWinner(matchup, Number(participant.TeamID))
    }))
  }));
}

/**
 * Full-league schedule: upcoming weeks nearest first, finished weeks newest first.
 * Historical seasons are entirely retrospective, even when some old finality evidence
 * is unknown. We keep the underlying unknown states visible instead of inventing results.
 */
export function buildScheduleOverview(
  model: MatchupsReadModel | null | undefined,
  teams: readonly FantasyTeam[],
  isCurrentSeason: boolean,
  displayLabels: ReadonlyMap<string, string> = buildPlayoffDisplayLabels(model)
): ScheduleOverview {
  const upcoming: ScheduleOverviewWeek[] = [];
  const played: ScheduleOverviewWeek[] = [];

  for (const week of [...(model?.Weeks ?? [])].sort((a, b) => a.Week - b.Week)) {
    const row: ScheduleOverviewWeek = {
      week: week.Week,
      isPlayoff: week.Stage === 'playoffs',
      state: week.CompletionState,
      matchups: buildWeekScoreboard(week, teams, displayLabels)
    };
    (isCurrentSeason && !weekIsSettled(week) ? upcoming : played).push(row);
  }
  return { upcoming, played: played.reverse() };
}

/** Underdog winners of a week exactly as marked by the generator (no threshold or chance is derived here); upsets come first. */
export function selectRecapUpsets(winProbabilities: readonly WeeklyRecapWinProbability[] | null | undefined): WeekRecapUpset[] {
  const result: WeekRecapUpset[] = [];
  for (const matchup of winProbabilities ?? []) {
    const winnerTeamID = matchup.UnderdogWinnerFantasyTeamID;
    if (!matchup.UpsetLevel || winnerTeamID === null || winnerTeamID === undefined) continue;
    const winner = matchup.Teams.find(team => String(team.FantasyTeamID) === String(winnerTeamID));
    const loser = matchup.Teams.find(team => String(team.FantasyTeamID) !== String(winnerTeamID));
    result.push({
      matchupID: matchup.FantasyMatchupID,
      level: matchup.UpsetLevel,
      winnerTeamID,
      loserTeamID: loser?.FantasyTeamID ?? null,
      winnerChance: winner?.PregameWinProbability ?? null
    });
  }
  return result.sort((left, right) =>
    (left.level === right.level ? 0 : left.level === 'upset' ? -1 : 1) || (left.winnerChance ?? 100) - (right.winnerChance ?? 100));
}

/** An absolute display claim requires complete, unambiguous published evidence. */
export function allFavoritesWon(
  winProbabilities: readonly WeeklyRecapWinProbability[] | null | undefined,
  week: MatchupWeekReadModel
): boolean {
  if (week.CompletionState !== 'final' || !week.Matchups.length ||
      !winProbabilities || winProbabilities.length !== week.Matchups.length) return false;

  const byID = new Map(winProbabilities.map(row => [row.FantasyMatchupID, row]));
  if (byID.size !== winProbabilities.length ||
      new Set(week.Matchups.map(row => row.FantasyMatchupID)).size !== week.Matchups.length) return false;

  return week.Matchups.every(matchup => {
    const recap = byID.get(matchup.FantasyMatchupID);
    if (!recap || !matchup.FantasyMatchupID?.trim() || matchup.CompletionState !== 'final' ||
        matchup.Result?.Type !== 'win' || matchup.Result.WinnerTeamID === null ||
        recap.Upset !== false || recap.UpsetLevel !== null ||
        recap.UnderdogWinnerFantasyTeamID !== null ||
        matchup.Participants.length !== 2 || recap.Teams.length !== 2) return false;

    const participants = new Set(matchup.Participants.map(team => String(team.TeamID)));
    const recapTeams = new Set(recap.Teams.map(team => String(team.FantasyTeamID)));
    if (participants.size !== 2 || recapTeams.size !== 2 ||
        !recap.Teams.every(team => participants.has(String(team.FantasyTeamID)))) return false;

    const winner = recap.Teams.find(team => String(team.FantasyTeamID) === String(matchup.Result?.WinnerTeamID));
    const loser = recap.Teams.find(team => String(team.FantasyTeamID) !== String(matchup.Result?.WinnerTeamID));
    const winnerChance = winner?.PregameWinProbability;
    const loserChance = loser?.PregameWinProbability;
    // Do not infer a favorite from equal rounded chances or an absent probability.
    return typeof winnerChance === 'number' && Number.isFinite(winnerChance) &&
      typeof loserChance === 'number' && Number.isFinite(loserChance) &&
      loserChance >= 0 && winnerChance <= 100 && winnerChance > loserChance;
  });
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
        awards: recap.TeamAwards?.State === 'available' ? recap.TeamAwards : null,
        playerAwards: recap.PlayerAwards?.State === 'available' ? recap.PlayerAwards : null,
        underdog: selectRecapUpsets(recap.WinProbabilities)[0] ?? null,
        allFavoritesWon: allFavoritesWon(recap.WinProbabilities, week)
      }
    };
  }

  return { status: weekIsSettled(week) ? 'missing' : 'pending-final', content: null };
}

function orderedTeamIDs(
  model: MatchupsReadModel,
  teams: readonly FantasyTeamSummary[]
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
export function buildSeasonGrid<T extends FantasyTeamSummary>(
  model: MatchupsReadModel | null | undefined,
  teams: readonly T[]
): SeasonGrid<T> | null {
  if (!model || model.Weeks.length === 0) return null;

  const weeks = buildWeekTabs(model);
  const teamByID = indexTeams(teams);
  const sortedWeeks = [...model.Weeks].sort((left, right) => left.Week - right.Week);

  const rows = orderedTeamIDs(model, teams).map((teamID): SeasonGridRow<T> => ({
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
