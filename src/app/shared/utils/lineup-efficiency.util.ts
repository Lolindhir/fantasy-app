import type {
  WeeklyRecapSeasonEfficiency,
  WeeklyRecapTeamPerformance,
  WeeklyRecapsReadModel
} from '../../core/models/weekly-recap.models';
import type { Player } from '../../core/models/player.models';

/**
 * Pure presentation helpers for lineup efficiency. Every number comes from WeeklyRecaps.json
 * (generator-owned); nothing is computed, ranked or averaged here.
 */

export interface LineupEfficiencyLookup {
  week(teamID: string | number, week: number): WeeklyRecapTeamPerformance | null;
  season(teamID: string | number): WeeklyRecapSeasonEfficiency | null;
}

const EMPTY_LOOKUP: LineupEfficiencyLookup = { week: () => null, season: () => null };

export function buildLineupEfficiencyLookup(
  recaps: WeeklyRecapsReadModel | null | undefined,
  season: string
): LineupEfficiencyLookup {
  if (!recaps || recaps.Season !== season) return EMPTY_LOOKUP;

  const weekly = new Map<string, WeeklyRecapTeamPerformance>();
  for (const week of recaps.Weeks) {
    for (const team of week.TeamPerformance ?? []) weekly.set(`${week.Week}:${team.FantasyTeamID}`, team);
  }
  const seasonal = new Map((recaps.SeasonEfficiency ?? []).map(entry => [String(entry.FantasyTeamID), entry]));

  return {
    week: (teamID, week) => weekly.get(`${week}:${teamID}`) ?? null,
    season: teamID => seasonal.get(String(teamID)) ?? null
  };
}

export function hasLineupEfficiency(lookup: LineupEfficiencyLookup, teamIDs: ReadonlyArray<string | number>, weeks: readonly number[]): boolean {
  return teamIDs.some(teamID => lookup.season(teamID) !== null || weeks.some(week => lookup.week(teamID, week) !== null));
}

/** Teams holding the highest weekly efficiency (ties mark every holder), like the highest score in the points view; keys are "week:teamID". */
export function weeklyEfficiencyHighs(
  lookup: LineupEfficiencyLookup,
  teamIDs: ReadonlyArray<string | number>,
  weeks: readonly number[]
): ReadonlySet<string> {
  const highs = new Set<string>();
  for (const week of weeks) {
    const values = teamIDs
      .map(teamID => ({ teamID, value: lookup.week(teamID, week)?.EfficiencyPercent ?? null }))
      .filter((entry): entry is { teamID: string | number; value: number } => entry.value !== null);
    if (values.length < 2) continue;
    const high = Math.max(...values.map(entry => entry.value));
    for (const entry of values) if (entry.value === high) highs.add(`${week}:${entry.teamID}`);
  }
  return highs;
}

/** "82.3%" for a present value, an en dash for unknown (never 0%). */
export function formatEfficiency(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value) ? '–' : `${value.toFixed(1)}%`;
}

export interface OptimalLineupSlotView {
  slot: string;
  playerID: string | null;
  name: string;
  position: string | null;
  picture: string | null;
  points: number;
}

export interface OptimalLineupView {
  teamID: number;
  efficiency: number | null;
  actual: number;
  potential: number;
  missed: number;
  slots: OptimalLineupSlotView[];
}

/** Slot label without the running index: "FLEX-2" becomes "FLEX". */
export function slotLabel(slotID: string): string {
  return slotID.replace(/-\d+$/, '');
}

export function buildOptimalLineupView(
  performance: WeeklyRecapTeamPerformance,
  players: readonly Player[]
): OptimalLineupView {
  const byID = new Map(players.map(player => [String(player.ID), player]));
  return {
    teamID: performance.FantasyTeamID,
    efficiency: performance.EfficiencyPercent,
    actual: performance.ActualStarterPoints,
    potential: performance.PotentialPoints,
    missed: performance.MissedPoints,
    slots: performance.OptimalLineup.map(slot => {
      const player = slot.PlayerID ? byID.get(String(slot.PlayerID)) : undefined;
      return {
        slot: slot.SlotID,
        playerID: slot.PlayerID,
        name: player?.Name ?? 'Unknown player',
        position: player?.Position ?? null,
        picture: player?.Picture || null,
        points: slot.Points
      };
    })
  };
}
