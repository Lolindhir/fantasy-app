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
  'not-played-reported': 'Did not play',
  'not-played-reserve': 'Did not play',
  'not-played-unexplained': 'Did not play',
  bye: 'Bye',
  unknown: 'Result unknown'
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
  CUT: 'Released',
  DEV: 'Practice squad'
};

export function findPlayerInjuryHistory(
  history: PlayerInjuryHistoryReadModel | null | undefined,
  playerId: string | number
): PlayerInjuryHistoryPlayer | null {
  return history?.Players.find(p => p.ID === String(playerId)) ?? null;
}

const NOT_INJURY = /^not injury related/i;
const INJURY_GAME_STATUSES = new Set(['Out', 'Doubtful', 'Questionable', 'Probable']);

/** Report entries that describe a real injury; "not injury related" rests and notes are dropped. */
function injuryEntries(week: PlayerInjuryHistoryWeek): { status: string; reasons: string[] }[] {
  const entries: { status: string; reasons: string[] }[] = [];
  for (const r of week.Report ?? []) {
    const reasons = r.Reasons.filter(x => !NOT_INJURY.test(x));
    const status = r.Game && INJURY_GAME_STATUSES.has(r.Game) ? r.Game : '';
    // Full practice participation without a game designation is a note, not an injury signal.
    const fullPractice = !!r.Practice && /^full participation/i.test(r.Practice);
    if (status || (reasons.length && !fullPractice)) entries.push({ status, reasons });
  }
  return entries;
}

function reportText(entries: { status: string; reasons: string[] }[]): string {
  return entries.map(e => [e.status, e.reasons.join(', ')].filter(Boolean).join(' · ')).join(' / ') || '—';
}

const NOT_PLAYED = new Set<PlayerAvailabilityState>(['not-played-reported', 'not-played-reserve', 'not-played-unexplained']);

/**
 * Newest season first, newest week first. Pure formatting of published values; only weeks with a real injury report or a
 * missed game are listed (healthy, bye and pending weeks without an injury signal are left out).
 */
export function buildInjuryHistoryView(player: PlayerInjuryHistoryPlayer | null): InjuryHistorySeasonView[] {
  if (!player) return [];
  return [...player.Seasons]
    .sort((a, b) => b.Season - a.Season)
    .map(season => {
      const rows: InjuryHistoryRow[] = [];
      for (const w of [...season.Weeks].sort((a, b) => b.Week - a.Week)) {
        const entries = injuryEntries(w);
        if (!NOT_PLAYED.has(w.State) && entries.length === 0) continue;
        rows.push({
          week: w.Week,
          postseason: w.GameType !== null && w.GameType !== 'REG',
          stateLabel: w.State === 'unknown' ? 'Result pending' : (STATE_LABEL[w.State] ?? 'Unknown'),
          stateClass: STATE_CLASS[w.State] ?? 'unknown',
          report: entries.length ? reportText(entries) : w.State === 'not-played-reserve' ? 'Reserve list' : w.State === 'not-played-unexplained' ? 'No report' : '—',
          roster: w.Roster?.Status && w.Roster.Status !== 'ACT' ? (ROSTER_LABEL[w.Roster.Status] ?? w.Roster.Status) : ''
        });
      }
      return { season: season.Season, rows, affectedWeeks: rows.filter(r => r.stateClass === 'out').length };
    })
    .filter(season => season.rows.length > 0);
}
