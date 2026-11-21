import type {
  OpponentStrengthClass,
  PlayoffOddsStatus,
  PlayoffOddsTeam,
  RemainingScheduleClass,
  ScheduleOutlookReadModel
} from '../../core/models/schedule-outlook.models';

/**
 * Display mapping for the generator-owned ScheduleOutlook read model (Issues #1588, #1589).
 * Nothing is calculated here: probabilities, statuses and strength classes are shown as published.
 * Everything returns null while the file is missing, unavailable, from another season or after the regular season.
 */
export interface PlayoffOddsTeamView {
  teamId: number;
  status: PlayoffOddsStatus;
  /** Share between 0 and 1; null when the generator published none. */
  probability: number | null;
  /** Place shares, index 0 = place 1; empty when unavailable. */
  places: number[];
}

export interface PlayoffOddsView {
  teams: ReadonlyMap<number, PlayoffOddsTeamView>;
  /** Number of playoff places (from the generator); null when unknown. */
  playoffTeams: number | null;
  teamCount: number;
  hasDecidedTeam: boolean;
}

const STATUSES: readonly PlayoffOddsStatus[] = ['clinched', 'eliminated', 'alive'];

export function resolvePlayoffOdds(
  outlook: ScheduleOutlookReadModel | null | undefined,
  season: number | string | null | undefined
): PlayoffOddsView | null {
  const odds = outlook?.PlayoffOdds;
  if (!outlook || !odds || odds.Available !== true || String(outlook.Season) !== String(season)) return null;
  // Probabilities are only meaningful while the regular season is running.
  if (odds.Provenance?.RegularSeasonComplete !== false) return null;
  if (!Array.isArray(odds.Teams) || odds.Teams.length === 0) return null;

  const teams = new Map<number, PlayoffOddsTeamView>();
  for (const team of odds.Teams) {
    const view = toTeamView(team, odds.Teams.length);
    if (!view) return null;
    teams.set(view.teamId, view);
  }
  const playoffTeams = odds.Provenance?.PlayoffTeams;
  return {
    teams,
    playoffTeams: typeof playoffTeams === 'number' && Number.isInteger(playoffTeams) && playoffTeams > 0
      && playoffTeams < odds.Teams.length ? playoffTeams : null,
    teamCount: odds.Teams.length,
    hasDecidedTeam: [...teams.values()].some(team => team.status !== 'alive')
  };
}

function toTeamView(team: PlayoffOddsTeam, teamCount: number): PlayoffOddsTeamView | null {
  if (!Number.isInteger(team.TeamID) || !team.Status || !STATUSES.includes(team.Status)) return null;
  const places = Array.isArray(team.PlaceProbabilities)
    && team.PlaceProbabilities.length === teamCount
    && team.PlaceProbabilities.every(value => typeof value === 'number' && Number.isFinite(value))
    ? team.PlaceProbabilities
    : [];
  return {
    teamId: team.TeamID,
    status: team.Status,
    probability: typeof team.PlayoffProbability === 'number' && Number.isFinite(team.PlayoffProbability)
      ? team.PlayoffProbability
      : null,
    places
  };
}

/** Whole percent; only an exact 0 or 1 shows 0% / 100%, everything in between shows "<1%" or ">99%". */
export function formatPlayoffPercent(probability: number): string {
  if (probability <= 0) return '0%';
  if (probability >= 1) return '100%';
  if (probability < 0.01) return '<1%';
  if (probability > 0.99) return '>99%';
  return `${Math.round(probability * 100)}%`;
}

/** Matrix cell text without the percent sign; empty for an exact 0. */
export function formatPlayoffCell(probability: number): string {
  return probability <= 0 ? '' : formatPlayoffPercent(probability).replace('%', '');
}

function ordinal(place: number): string {
  const rest = place % 100;
  if (rest >= 11 && rest <= 13) return `${place}th`;
  return `${place}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[place % 10] ?? 'th'}`;
}

/** Place the team has certain (published share exactly 1), e.g. 1 for "Clinched 1st"; null otherwise. */
function certainPlace(team: PlayoffOddsTeamView): number | null {
  const index = team.places.findIndex(share => share >= 1);
  return index >= 0 ? index + 1 : null;
}

export function playoffPillText(team: PlayoffOddsTeamView): string | null {
  if (team.status === 'clinched') {
    const place = certainPlace(team);
    return place === null ? 'Clinched' : `Clinched ${ordinal(place)}`;
  }
  if (team.status === 'eliminated') return 'Eliminated';
  return team.probability === null ? null : formatPlayoffPercent(team.probability);
}

export function playoffPillLabel(team: PlayoffOddsTeamView): string | null {
  const text = playoffPillText(team);
  if (text === null) return null;
  return team.status === 'alive'
    ? `Playoff chance ${text} if every remaining game were a coin flip`
    : `${text} for the playoffs`;
}

/** Compact Overview marker: x = clinched, e = eliminated, nothing while undecided. */
export function playoffMarker(odds: PlayoffOddsView | null, teamId: number | string): 'x' | 'e' | null {
  const status = odds?.teams.get(Number(teamId))?.status;
  return status === 'clinched' ? 'x' : status === 'eliminated' ? 'e' : null;
}

export interface TeamScheduleOutlookView {
  remaining: RemainingScheduleClass | null;
  remainingGames: number;
  opponentByWeek: ReadonlyMap<number, OpponentStrengthClass>;
}

export function resolveTeamScheduleOutlook(
  outlook: ScheduleOutlookReadModel | null | undefined,
  season: number | string | null | undefined,
  teamId: number | string
): TeamScheduleOutlookView | null {
  if (!outlook || String(outlook.Season) !== String(season)) return null;
  const team = outlook.RegularSeason?.Teams?.find(candidate => String(candidate.TeamID) === String(teamId));
  if (!team) return null;
  const opponentByWeek = new Map<number, OpponentStrengthClass>();
  for (const game of team.Upcoming ?? []) {
    if (game.OpponentClass) opponentByWeek.set(game.Week, game.OpponentClass);
  }
  return {
    remaining: team.RemainingSoSClass ?? null,
    remainingGames: team.RemainingGames,
    opponentByWeek
  };
}

export const OPPONENT_CLASS_VIEW: Record<OpponentStrengthClass, { symbol: string; label: string; title: string }> = {
  weaker: { symbol: '↓', label: 'Weaker', title: 'Opponent has scored fewer points than the league average' },
  similar: { symbol: '=', label: 'Similar', title: 'Opponent has scored about as many points as the league average' },
  stronger: { symbol: '↑', label: 'Stronger', title: 'Opponent has scored more points than the league average' }
};

export const REMAINING_CLASS_LABEL: Record<RemainingScheduleClass, string> = {
  easier: 'Easier than average',
  average: 'Average',
  harder: 'Harder than average'
};
