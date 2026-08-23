import type {
  DraftPick,
  FantasyTeam,
  League,
  PlacementRegularSeason,
  Player
} from '../../core/models/fantasy.models';
import { getPositionColor } from './position-color.util';
import { calculateTopPlayersSalary } from './trade-calculator.util';

export type SalaryLens = 'current' | 'projected';
export type SalaryHealthStatus = 'healthy' | 'watch' | 'over';

export interface TeamRosterSplit {
  roster: Player[];
  taxi: Player[];
  ir: Player[];
}

export interface TeamRosterLimits {
  roster?: number;
  taxi?: number;
  ir?: number;
}

export interface SalaryPositionBreakdown {
  position: string;
  salary: number;
  percentage: number;
  color: string;
  playerCount: number;
}

export interface TeamSalaryLensSummary {
  lens: SalaryLens;
  salary: number;
  cap: number;
  capSpace: number;
  utilization: number;
  topPlayers: Player[];
  mostExpensive: Player[];
  byPosition: SalaryPositionBreakdown[];
}

export interface SalaryMovement {
  player: Player;
  current: number;
  projected: number;
  delta: number;
}

export interface TeamSalarySummary {
  health: SalaryHealthStatus;
  current: TeamSalaryLensSummary;
  projected: TeamSalaryLensSummary;
  biggestIncreases: SalaryMovement[];
  biggestDecreases: SalaryMovement[];
}

export interface TeamSeasonSummary {
  season: string;
  record: string;
  finalPlace?: string;
  usesPreviousSeason: boolean;
}

export interface TeamOpenPicksSummary {
  season: number;
  count: number;
  picks: DraftPick[];
}

const SALARY_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K'];

export function splitTeamRoster(team: FantasyTeam): TeamRosterSplit {
  const taxiIds = new Set(team.Taxi.map(player => player.ID));
  const irIds = new Set(team.Reserve.map(player => player.ID));

  return {
    roster: team.Roster.filter(player => !taxiIds.has(player.ID) && !irIds.has(player.ID)),
    taxi: [...team.Taxi],
    ir: [...team.Reserve]
  };
}

export function getTeamRosterLimits(league: League): TeamRosterLimits {
  return {
    roster: league.RosterSize?.length || undefined,
    taxi: readPositiveSetting(league.Settings ?? {}, 'taxi_slots'),
    ir: readPositiveSetting(league.Settings ?? {}, 'reserve_slots')
  };
}

export function buildTeamSalarySummary(team: FantasyTeam, league: League): TeamSalarySummary {
  const current = buildLensSummary(team.Roster, league, 'current');
  const projected = buildLensSummary(team.Roster, league, 'projected');
  const movements = team.Roster
    .map(player => ({
      player,
      current: player.Salary,
      projected: player.SalaryProjected,
      delta: player.SalaryProjected - player.Salary
    }))
    .filter(item => item.delta !== 0);

  return {
    health: getSalaryHealth(current.salary, current.cap, projected.salary, projected.cap),
    current,
    projected,
    biggestIncreases: movements
      .filter(item => item.delta > 0)
      .sort((a, b) => b.delta - a.delta || a.player.Name.localeCompare(b.player.Name))
      .slice(0, 5),
    biggestDecreases: movements
      .filter(item => item.delta < 0)
      .sort((a, b) => a.delta - b.delta || a.player.Name.localeCompare(b.player.Name))
      .slice(0, 5)
  };
}

export function getSalaryHealth(
  currentSalary: number,
  currentCap: number,
  projectedSalary: number,
  projectedCap: number
): SalaryHealthStatus {
  if (currentSalary > currentCap) {
    return 'over';
  }
  if (projectedSalary > projectedCap) {
    return 'watch';
  }
  return 'healthy';
}

export function getTeamSeasonSummary(team: FantasyTeam, league: League): TeamSeasonSummary {
  const current = team.Placements.Current.Regular;
  const hasMeaningfulCurrentStanding = isMeaningfulPlacement(current);
  const source = hasMeaningfulCurrentStanding ? team.Placements.Current : team.Placements.Previous;
  const finalPlacement = source.Playoffs?.Place && source.Playoffs.Place > 0
    ? source.Playoffs
    : source.Regular;

  return {
    season: hasMeaningfulCurrentStanding ? league.Season : String(league.SeasonAsNumber - 1),
    record: source.Regular.Record || buildRecord(source.Regular),
    finalPlace: finalPlacement.PlaceOrdinal || (finalPlacement.Place > 0 ? ordinal(finalPlacement.Place) : undefined),
    usesPreviousSeason: !hasMeaningfulCurrentStanding
  };
}

export function getEarliestOpenPicks(team: FantasyTeam, currentSeason: number): TeamOpenPicksSummary | undefined {
  const openPicks = team.DraftPicks.filter(pick => {
    const season = Number(pick.Season);
    return Number.isFinite(season) && season >= currentSeason && isOpenPick(pick);
  });

  if (!openPicks.length) {
    return undefined;
  }

  const season = Math.min(...openPicks.map(pick => Number(pick.Season)));
  const picks = openPicks.filter(pick => Number(pick.Season) === season);
  return { season, count: picks.length, picks };
}

export function getPositionCounts(players: Player[]): Array<{ position: string; count: number }> {
  const counts = new Map<string, number>();
  players.forEach(player => counts.set(player.Position || '?', (counts.get(player.Position || '?') ?? 0) + 1));

  return [...counts.entries()]
    .map(([position, count]) => ({ position, count }))
    .sort((a, b) => positionOrder(a.position) - positionOrder(b.position) || a.position.localeCompare(b.position));
}

function buildLensSummary(roster: Player[], league: League, lens: SalaryLens): TeamSalaryLensSummary {
  const selector = lens === 'current'
    ? (player: Player) => player.Salary
    : (player: Player) => player.SalaryProjected;
  const cap = lens === 'current' ? league.SalaryCap : league.SalaryCapProjected;
  const salaryResult = calculateTopPlayersSalary(roster, league.SalaryRelevantTeamSize, selector);

  return {
    lens,
    salary: salaryResult.cap,
    cap,
    capSpace: cap - salaryResult.cap,
    utilization: cap > 0 ? (salaryResult.cap / cap) * 100 : 0,
    topPlayers: salaryResult.topPlayers,
    mostExpensive: salaryResult.topPlayers.slice(0, 5),
    byPosition: buildPositionBreakdown(salaryResult.topPlayers, selector, salaryResult.cap)
  };
}

function buildPositionBreakdown(
  players: Player[],
  selector: (player: Player) => number,
  totalSalary: number
): SalaryPositionBreakdown[] {
  const positions = new Map<string, { salary: number; playerCount: number }>();

  players.forEach(player => {
    const position = player.Position || '?';
    const current = positions.get(position) ?? { salary: 0, playerCount: 0 };
    positions.set(position, {
      salary: current.salary + selector(player),
      playerCount: current.playerCount + 1
    });
  });

  return [...positions.entries()]
    .map(([position, value]) => ({
      position,
      salary: value.salary,
      percentage: totalSalary > 0 ? (value.salary / totalSalary) * 100 : 0,
      color: getPositionColor(position),
      playerCount: value.playerCount
    }))
    .sort((a, b) => positionOrder(a.position) - positionOrder(b.position) || b.salary - a.salary);
}

function positionOrder(position: string): number {
  const index = SALARY_POSITIONS.indexOf(position);
  return index >= 0 ? index : SALARY_POSITIONS.length;
}

function readPositiveSetting(settings: Record<string, unknown>, key: string): number | undefined {
  const value = settings[key];
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : undefined;
}

function isMeaningfulPlacement(placement: PlacementRegularSeason): boolean {
  return placement.Place > 0 || placement.Wins > 0 || placement.Losses > 0 || placement.Ties > 0;
}

function buildRecord(placement: PlacementRegularSeason): string {
  return placement.Ties > 0
    ? `${placement.Wins}-${placement.Losses}-${placement.Ties}`
    : `${placement.Wins}-${placement.Losses}`;
}

function isOpenPick(pick: DraftPick): boolean {
  return pick.Status !== 'Picked' && !pick.PlayerID;
}

function ordinal(value: number): string {
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
  switch (value % 10) {
    case 1: return `${value}st`;
    case 2: return `${value}nd`;
    case 3: return `${value}rd`;
    default: return `${value}th`;
  }
}
