import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../core/models/season-statistics.models';

/** Display-only helpers for the season statistics read model (Issue #506); no calculation of statistics happens here. */

export function statisticsByTeam(teams: readonly SeasonStatisticsTeam[] | null | undefined): Map<string, SeasonStatisticsTeam> {
  return new Map((teams ?? []).map(team => [String(team.TeamID), team]));
}

/** English number format with an explicit sign, for example +2.8 or -0.6; null stays unavailable. */
export function formatSigned(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '–';
  const text = Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  if (Number(text.replace(/,/g, '')) === 0) return text;
  return `${value > 0 ? '+' : '-'}${text}`;
}

export function formatDecimal(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '–';
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatAllPlay(team: SeasonStatisticsTeam): string {
  const { Wins: wins, Losses: losses, Ties: ties } = team.AllPlay;
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
}

/** Sign class for luck-like values: positive, negative or neutral. */
export function signClass(value: number | null | undefined): 'pos' | 'neg' | 'zero' {
  if (value === null || value === undefined || value === 0) return 'zero';
  return value > 0 ? 'pos' : 'neg';
}

export interface BiggestUpsetHighlight {
  key: string;
  icon: string;
  title: string;
  owner: string;
  valueDisplay: string;
  reason: string;
}

/** Hall of Fame tile of the all-time biggest upset; the generator chose the game, this only renders it. */
export function buildBiggestUpsetHighlight(
  current: SeasonStatisticsReadModel | null,
  bySeason: ReadonlyMap<string, SeasonStatisticsReadModel>
): BiggestUpsetHighlight | null {
  const upset = current?.BiggestUpsetAllTime;
  if (!upset) return null;
  const doc = upset.Season === current?.Season ? current : bySeason.get(String(upset.Season));
  const teams = statisticsByTeam(doc?.Teams);
  const winner = teams.get(String(upset.WinnerTeamID));
  const loser = teams.get(String(upset.LoserTeamID));
  if (!winner) return null;
  const chance = Math.round(upset.WinnerPregameWinProbability * 100);
  return {
    key: 'biggest-upset',
    icon: '💥',
    title: 'Biggest Upset',
    owner: winner.Owner,
    valueDisplay: `${chance}% win chance`,
    reason: `${upset.Season} Week ${upset.Week}: ${winner.TeamName} beat ${loser?.TeamName ?? 'the favorite'} `
      + `${formatDecimal(upset.WinnerPoints, 2)}-${formatDecimal(upset.LoserPoints, 2)} with a ${chance}% pregame win chance.`
  };
}
