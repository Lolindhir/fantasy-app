import type { InjuryImpactSeason, InjuryImpactSeasonTotal } from '../../core/models/injury-impact.models';
import { formatDecimal } from './season-statistics-view.util';

/** Display-only helpers for the Fantasy Injury Impact read model (Issue #1621); no impact is calculated here, only formatted and scaled. */

export interface InjuryImpactWeekBar {
  week: number;
  impact: number | null;
  /** 0 to 100, relative to the largest weekly impact of the season so all teams share one scale. */
  heightPercent: number;
  lowerBound: boolean;
  unknownEvidence: boolean;
  /** No verified projection for the week; never shown as zero. */
  unavailable: boolean;
  label: string;
}

export interface InjuryImpactTopPlayerView {
  id: string;
  name: string;
  position: string | null;
  picture: string | null;
  impactDisplay: string;
  weeks: number;
}

export interface TeamInjuryImpactView {
  total: number;
  totalDisplay: string;
  isLowerBound: boolean;
  perWeekDisplay: string;
  weeksWithImpact: number;
  weeksComputed: number;
  peakDisplay: string | null;
  hasUnknownEvidence: boolean;
  bars: InjuryImpactWeekBar[];
  topPlayers: InjuryImpactTopPlayerView[];
}

/** A lower bound carries a leading "≥" so a partly unknown week is never read as an exact value. */
export function formatImpact(value: number | null | undefined, lowerBound: boolean): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '–';
  return `${lowerBound ? '≥ ' : ''}${formatDecimal(value, 1)}`;
}

export function buildInjuryImpactByTeam(season: InjuryImpactSeason | null | undefined): Map<string, TeamInjuryImpactView> {
  const result = new Map<string, TeamInjuryImpactView>();
  if (!season) return result;
  const teamIdByRoster = new Map(season.Teams.map(team => [team.CanonicalLeagueRosterID, String(team.TeamID)]));
  const maxWeekly = Math.max(0, ...season.Weeks.flatMap(week => week.Teams.map(team => team.Impact)));
  const unavailable = season.UnavailableWeeks.map(item => item.Week);
  const weekNumbers = [...new Set([...season.Weeks.map(week => week.Week), ...unavailable])].sort((a, b) => a - b);

  for (const total of season.SeasonTotals) {
    const teamId = teamIdByRoster.get(total.CanonicalLeagueRosterID);
    if (teamId === undefined) continue;
    const entries = new Map(season.Weeks.map(week => [week.Week, week.Teams.find(team => team.CanonicalLeagueRosterID === total.CanonicalLeagueRosterID)]));
    const bars = weekNumbers.map(week => weekBar(week, entries.get(week), unavailable.includes(week), maxWeekly));
    result.set(teamId, {
      total: total.Impact,
      totalDisplay: formatImpact(total.Impact, total.IsLowerBound),
      isLowerBound: total.IsLowerBound,
      perWeekDisplay: formatImpact(total.ImpactPerWeek, total.IsLowerBound),
      weeksWithImpact: total.WeeksWithImpact,
      weeksComputed: total.WeeksComputed,
      peakDisplay: peak(total),
      hasUnknownEvidence: bars.some(bar => bar.unknownEvidence),
      bars,
      // A player who cost nothing (an equal replacement was available) is not listed.
      topPlayers: total.TopPlayers.filter(player => player.SingleReturnImpact > 0).map(player => {
        const ref = season.PlayerRefs?.[player.CanonicalPlayerID];
        return {
          id: player.CanonicalPlayerID,
          name: ref?.Name ?? 'Unknown player',
          position: ref?.Position ?? null,
          picture: ref?.Picture ?? null,
          impactDisplay: formatDecimal(player.SingleReturnImpact, 1),
          weeks: player.Weeks
        };
      })
    });
  }
  return result;
}

function peak(total: InjuryImpactSeasonTotal): string | null {
  return total.PeakWeek && total.PeakWeek.Impact > 0 ? `Week ${total.PeakWeek.Week} (${formatDecimal(total.PeakWeek.Impact, 1)})` : null;
}

function weekBar(
  week: number,
  entry: { Impact: number; IsLowerBound: boolean; HasUnknownEvidence: boolean } | undefined,
  isUnavailable: boolean,
  maxWeekly: number
): InjuryImpactWeekBar {
  if (!entry || isUnavailable) {
    return { week, impact: null, heightPercent: 0, lowerBound: false, unknownEvidence: false, unavailable: true, label: `Week ${week}: not available` };
  }
  const heightPercent = maxWeekly > 0 && entry.Impact > 0 ? Math.max(6, (entry.Impact / maxWeekly) * 100) : 0;
  const markers = [entry.IsLowerBound ? 'lower bound' : '', entry.HasUnknownEvidence ? 'some availability unknown' : ''].filter(Boolean).join(', ');
  return {
    week,
    impact: entry.Impact,
    heightPercent,
    lowerBound: entry.IsLowerBound,
    unknownEvidence: entry.HasUnknownEvidence,
    unavailable: false,
    label: `Week ${week}: ${formatImpact(entry.Impact, entry.IsLowerBound)} pts${markers ? ` (${markers})` : ''}`
  };
}
