import type {
  PlayerAvailabilityState,
  PlayerInjuryHistoryPlayer,
  PlayerInjuryHistoryReadModel,
  PlayerInjuryHistoryWeek
} from '../../core/models/player-injury-history.models';

export interface InjuryHistoryRow {
  week: number;
  postseason: boolean;
  stateLabel: string;
  stateClass: string;
  report: string;
  roster: string;
}

export interface InjuryHistorySeasonView {
  season: number;
  rows: InjuryHistoryRow[];
  affectedWeeks: number;
}

const STATE_LABEL: Record<PlayerAvailabilityState, string> = {
  played: 'Played',
  'not-played-reported': 'Did not play (reported)',
  'not-played-reserve': 'Did not play (reserve list)',
  'not-played-unexplained': 'Did not play (no report)',
  bye: 'Bye',
  unknown: 'Unknown'
};

const STATE_CLASS: Record<PlayerAvailabilityState, string> = {
  played: 'played',
  'not-played-reported': 'out',
  'not-played-reserve': 'out',
  'not-played-unexplained': 'out',
  bye: 'bye',
  unknown: 'unknown'
};

const ROSTER_LABEL: Record<string, string> = {
  RES: 'Reserve list',
  PUP: 'Physically unable to perform',
  INA: 'Inactive',
  ACT: 'Active',
  CUT: 'Released',
  DEV: 'Practice squad'
};

export function findPlayerInjuryHistory(
  history: PlayerInjuryHistoryReadModel | null | undefined,
  playerId: string | number
): PlayerInjuryHistoryPlayer | null {
  return history?.Players.find(p => p.ID === String(playerId)) ?? null;
}

function reportText(week: PlayerInjuryHistoryWeek): string {
  if (!week.Report?.length) return '—';
  return week.Report
    .map(r => [r.Game, r.Reasons.join(', ')].filter(Boolean).join(' · ') || (r.Practice ?? ''))
    .filter(Boolean)
    .join(' / ') || '—';
}

/** Newest season first, newest week first. Pure formatting of published values. */
export function buildInjuryHistoryView(player: PlayerInjuryHistoryPlayer | null): InjuryHistorySeasonView[] {
  if (!player) return [];
  return [...player.Seasons]
    .sort((a, b) => b.Season - a.Season)
    .map(season => ({
      season: season.Season,
      affectedWeeks: season.Weeks.filter(w => w.State !== 'played' && w.State !== 'bye').length,
      rows: [...season.Weeks]
        .sort((a, b) => b.Week - a.Week)
        .map(w => ({
          week: w.Week,
          postseason: w.GameType !== null && w.GameType !== 'REG',
          stateLabel: STATE_LABEL[w.State] ?? 'Unknown',
          stateClass: STATE_CLASS[w.State] ?? 'unknown',
          report: reportText(w),
          roster: w.Roster?.Status ? (ROSTER_LABEL[w.Roster.Status] ?? w.Roster.Status) : '—'
        }))
    }));
}
