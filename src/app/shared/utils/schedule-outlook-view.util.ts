import type {
  OpponentStrengthClass,
  PlayoffOddsStatus,
  PlayoffOddsTeam,
  RemainingScheduleClass,
  ScheduleOutlookReadModel,
  ScheduleOutlookTeam
} from '../../core/models/schedule-outlook.models';

/**
 * Display mapping for the generator-owned ScheduleOutlook read model (Issues #1588, #1589).
 * No domain probabilities are calculated here: only display rounding and read-model validation.
 * Everything returns null while the file is missing, unavailable, from another season or after the regular season.
 */
export interface PlayoffOddsTeamView {
  teamId: number;
  status: PlayoffOddsStatus;
  /** Share between 0 and 1; null when the generator published none. */
  probability: number | null;
  /** Place shares, index 0 = place 1; empty when unavailable. */
  places: number[];
  /** Formatted exact masses; optional on legacy snapshots. */
  placeLabels?: string[];
  possiblePlaces?: number[];
  model?: string;
}

export interface PlayoffOddsView {
  teams: ReadonlyMap<number, PlayoffOddsTeamView>;
  /** Number of playoff places (from the generator); null when unknown. */
  playoffTeams: number | null;
  teamCount: number;
  hasDecidedTeam: boolean;
  model?: string;
  /** Points per team and game of the league, as published; null when unknown. */
  leagueMeanPoints: number | null;
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
    const view = toTeamView(team, odds.Teams.length, odds.Model, odds.Provenance?.PlaceMassDenominator);
    if (!view || teams.has(view.teamId)) return null;
    teams.set(view.teamId, view);
  }
  const playoffTeams = odds.Provenance?.PlayoffTeams;
  return {
    teams,
    playoffTeams: typeof playoffTeams === 'number' && Number.isInteger(playoffTeams) && playoffTeams > 0
      && playoffTeams < odds.Teams.length ? playoffTeams : null,
    teamCount: odds.Teams.length,
    hasDecidedTeam: [...teams.values()].some(team => team.status !== 'alive'),
    model: odds.Model,
    leagueMeanPoints: finiteOrNull(outlook.RegularSeason?.MatchupForecast?.Scoring?.LeagueMeanPoints ?? odds.Scoring?.LeagueMeanPoints)
  };
}

function finiteOrNull(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function isExactPlayoffModel(model: string | undefined): boolean {
  return model === 'playoff-odds-v3' || model === 'playoff-odds-v4';
}

export function playoffOddsBasis(model: string | undefined): string {
  if (model === 'playoff-odds-v4') return 'all remaining win/tie/loss outcomes (1% tie probability), with equal records sharing places';
  if (model === 'playoff-odds-v3') return 'all equally weighted remaining win/tie/loss outcomes, with equal records sharing places';
  if (model === 'playoff-odds-v1') return 'equally weighted remaining win/loss outcomes, with equal records sharing places';
  return 'team strength and the points tiebreak';
}

/** Display-only largest-remainder rounding from exact integer masses. Increase precision
 * to preserve visible positive tails; at the compact display limit use explicit bounds.
 * Exact zeros/ones are never inferred from floating-point values or rounded units.
 */
export function formatExactPlaceShares(masses: readonly string[], denominator: string): string[] | null {
  if (!/^[1-9][0-9]*$/.test(denominator) || !masses.length || masses.some(m => !/^(0|[1-9][0-9]*)$/.test(m))) return null;
  const total = BigInt(denominator);
  const values = masses.map(m => BigInt(m));
  if (values.reduce((sum, mass) => sum + mass, 0n) !== total) return null;
  for (let digits = 0; digits <= 2; digits++) {
    const scale = 100n * 10n ** BigInt(digits);
    const units = values.map(m => m * scale / total);
    const remainder = values.map((m, index) => ({ index, mass: m * scale % total }));
    remainder.sort((a, b) => a.mass === b.mass ? a.index - b.index : a.mass > b.mass ? -1 : 1);
    const left = Number(scale - units.reduce((sum, unit) => sum + unit, 0n));
    for (let i = 0; i < left; i++) units[remainder[i].index] += 1n;
    const hasHiddenTail = values.some((m, i) => m > 0n && m < total && (units[i] === 0n || units[i] === scale));
    if (hasHiddenTail && digits < 2) continue;
    return values.map((m, i) => {
      if (m === 0n) return '0%';
      if (m === total) return '100%';
      if (units[i] === 0n) return '<0.01%';
      if (units[i] === scale) return '>99.99%';
      return `${(Number(units[i]) / 10 ** digits).toFixed(digits)}%`;
    });
  }
  return null;
}

function toTeamView(team: PlayoffOddsTeam, teamCount: number, model: string, denominator?: string): PlayoffOddsTeamView | null {
  if (!Number.isInteger(team.TeamID) || !team.Status || !STATUSES.includes(team.Status)) return null;
  const places = Array.isArray(team.PlaceProbabilities)
    && team.PlaceProbabilities.length === teamCount
    && team.PlaceProbabilities.every(value => typeof value === 'number' && Number.isFinite(value))
    ? team.PlaceProbabilities
    : [];
  let exact: Pick<PlayoffOddsTeamView, 'placeLabels' | 'possiblePlaces'> = {};
  if (isExactPlayoffModel(model)) {
    const masses = team.PlaceMassNumerators;
    if (!denominator || !Array.isArray(masses) || masses.length !== teamCount || places.length !== teamCount
        || !Array.isArray(team.PossiblePlaces)) return null;
    const labels = formatExactPlaceShares(masses, denominator);
    const support = masses.flatMap((mass, index) => mass === '0' ? [] : [index + 1]);
    if (!labels || support.length !== team.PossiblePlaces.length || support.some((p, i) => p !== team.PossiblePlaces![i])) return null;
    exact = { placeLabels: labels, possiblePlaces: support };
  }
  return {
    ...exact,
    model,
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

export function ordinal(place: number): string {
  const rest = place % 100;
  if (rest >= 11 && rest <= 13) return `${place}th`;
  return `${place}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[place % 10] ?? 'th'}`;
}

/** Place the team has certain (published share exactly 1), e.g. 1 for "Clinched 1st"; null otherwise. */
function certainPlace(team: PlayoffOddsTeamView): number | null {
  if (team.possiblePlaces) return team.possiblePlaces.length === 1 ? team.possiblePlaces[0] : null;
  const index = team.places.findIndex(share => share >= 1);
  return index >= 0 ? index + 1 : null;
}

export function playoffPillText(team: PlayoffOddsTeamView): string | null {
  if (team.status === 'clinched') {
    const place = certainPlace(team);
    return place === null ? 'Clinched' : `Clinched ${ordinal(place)}`;
  }
  if (team.status === 'eliminated') return 'Eliminated';
  if (team.probability === null) return null;
  // Simulated values are never certain: an undecided team shows "<1%" / ">99%" instead of a hard 0% / 100%.
  if (team.probability <= 0) return '<1%';
  if (team.probability >= 1) return '>99%';
  return formatPlayoffPercent(team.probability);
}

export function playoffPillLabel(team: PlayoffOddsTeamView): string | null {
  const text = playoffPillText(team);
  if (text === null) return null;
  return team.status === 'alive'
    ? `Playoff chance ${text}, based on ${playoffOddsBasis(team.model)}`
    : `${text} for the playoffs`;
}

/** Compact Overview marker: x = clinched, e = eliminated, nothing while undecided. */
export function playoffMarker(odds: PlayoffOddsView | null, teamId: number | string): 'x' | 'e' | null {
  const status = odds?.teams.get(Number(teamId))?.status;
  return status === 'clinched' ? 'x' : status === 'eliminated' ? 'e' : null;
}

/** Final place that is already certain for a decided team (clinched or eliminated); null otherwise. */
export function playoffLockedPlace(odds: PlayoffOddsView | null, teamId: number | string): number | null {
  const team = odds?.teams.get(Number(teamId));
  return team && team.status !== 'alive' ? certainPlace(team) : null;
}

/** One upcoming opponent with the generator's numbers; every field is null when the generator published none. */
export interface UpcomingGameOutlook {
  week: number;
  opponentTeamId: number | null;
  opponentClass: OpponentStrengthClass | null;
  /** Share between 0 and 1 that the viewed team wins. */
  winProbability: number | null;
  /** Expected points of the viewed team minus the opponent. */
  margin: number | null;
  /** Opponent strength relative to the league average (1.0 = average). */
  opponentStrength: number | null;
  opponentMix: StrengthMix | null;
}

/** How a team's strength is mixed from this season and last season. */
export interface StrengthMix {
  /** Share of this season, between 0 and 1. */
  currentWeight: number;
  currentRelative: number | null;
  previousRelative: number | null;
  gamesPlayed: number | null;
}

export interface TeamScheduleOutlookView {
  remaining: RemainingScheduleClass | null;
  remainingGames: number;
  /** Average strength of the remaining opponents relative to the league average; null when unknown. */
  remainingStrength: number | null;
  /** Mean win chance over the remaining games (share between 0 and 1) and the summed expected wins. */
  remainingWinProbability: number | null;
  remainingExpectedWins: number | null;
  opponentByWeek: ReadonlyMap<number, OpponentStrengthClass>;
  gameByWeek: ReadonlyMap<number, UpcomingGameOutlook>;
  /** Points per team and game of the league; null when unknown. */
  leagueMeanPoints: number | null;
}

function strengthMix(team: ScheduleOutlookTeam | undefined): StrengthMix | null {
  const strength = team?.Strength;
  if (!strength || typeof strength.CurrentWeight !== 'number' || !Number.isFinite(strength.CurrentWeight)) return null;
  return {
    currentWeight: strength.CurrentWeight,
    currentRelative: finiteOrNull(strength.CurrentRelative),
    previousRelative: finiteOrNull(strength.PreviousRelative),
    gamesPlayed: finiteOrNull(strength.GamesPlayed)
  };
}

export function resolveTeamScheduleOutlook(
  outlook: ScheduleOutlookReadModel | null | undefined,
  season: number | string | null | undefined,
  teamId: number | string
): TeamScheduleOutlookView | null {
  if (!outlook || String(outlook.Season) !== String(season)) return null;
  const teams = outlook.RegularSeason?.Teams ?? [];
  const team = teams.find(candidate => String(candidate.TeamID) === String(teamId));
  if (!team) return null;
  const odds = outlook.PlayoffOdds;
  const oddsUsable = !!odds && odds.Available === true && odds.Provenance?.RegularSeasonComplete === false;
  const forecast = outlook.RegularSeason?.MatchupForecast;
  const forecastUsable = forecast?.Model === 'schedule-matchup-forecast-v1' && forecast.Provenance?.RegularSeasonComplete === false;
  const legacyUsable = !forecast && oddsUsable && !isExactPlayoffModel(odds?.Model);
  const forecastTeams = forecastUsable ? forecast.Teams : legacyUsable ? odds?.Teams : undefined;
  const oddsTeam = forecastTeams?.find(candidate => String(candidate.TeamID) === String(teamId));
  const opponentByWeek = new Map<number, OpponentStrengthClass>();
  const gameByWeek = new Map<number, UpcomingGameOutlook>();
  for (const game of team.Upcoming ?? []) {
    if (game.OpponentClass) opponentByWeek.set(game.Week, game.OpponentClass);
    const odd = oddsTeam?.Upcoming?.find(candidate => candidate.Week === game.Week);
    const opponent = teams.find(candidate => candidate.TeamID === game.OpponentTeamID);
    gameByWeek.set(game.Week, {
      week: game.Week,
      opponentTeamId: game.OpponentTeamID,
      opponentClass: game.OpponentClass ?? null,
      winProbability: finiteOrNull(odd?.WinProbability),
      margin: finiteOrNull(odd?.ExpectedMargin),
      opponentStrength: finiteOrNull(game.OpponentStrength),
      opponentMix: strengthMix(opponent)
    });
  }
  return {
    remaining: team.RemainingSoSClass ?? null,
    remainingGames: team.RemainingGames,
    remainingStrength: finiteOrNull(team.RemainingSoS),
    remainingWinProbability: finiteOrNull(oddsTeam?.RemainingWinProbability),
    remainingExpectedWins: finiteOrNull(oddsTeam?.RemainingExpectedWins),
    opponentByWeek,
    gameByWeek,
    leagueMeanPoints: forecastUsable ? finiteOrNull(forecast.Scoring?.LeagueMeanPoints)
      : legacyUsable ? finiteOrNull(odds?.Scoring?.LeagueMeanPoints) : null
  };
}

/** Whole points, e.g. "212". */
export function formatPoints(value: number): string {
  return String(Math.round(value));
}

/** Signed whole points, e.g. "+12" or "−8". */
export function formatMargin(value: number): string {
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : rounded < 0 ? `−${Math.abs(rounded)}` : '0';
}

/** Expected wins with one decimal, e.g. "1.4". */
export function formatExpectedWins(value: number): string {
  return value.toFixed(1);
}

/** Strength relative to the league average as published, e.g. "1.02×". */
export function formatStrength(value: number): string {
  return `${value.toFixed(2)}×`;
}

/** Share between 0 and 1 as whole percent, e.g. "77%". */
export function formatShare(value: number): string {
  return `${Math.round(value * 100)}%`;
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
