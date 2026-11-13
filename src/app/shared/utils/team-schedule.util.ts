import type {
  FantasyMatchupReadModel,
  MatchupCompletionState,
  MatchupStage,
  MatchupsReadModel
} from '../../core/models/matchup.models';

/**
 * Pure presentation helpers of the Team Detail Schedule tab. They select and arrange what the generated
 * Matchups file already contains; the only arithmetic is counting the delivered final results (design rule 4).
 * Team identity across seasons is the TeamID, like the Rivals tab.
 */

export type ScheduleOutcome = 'win' | 'loss' | 'tie';

export interface ScheduleRecord {
  wins: number;
  losses: number;
  ties: number;
}

export interface TeamScheduleRow {
  key: string;
  week: number;
  stage: MatchupStage;
  isPlayoff: boolean;
  /** The week the Matchups summary marks as active or next. */
  isCurrentWeek: boolean;
  /** Null when the team has no game in that regular-season week (bye). */
  matchupID: string | null;
  opponentID: number | null;
  state: MatchupCompletionState;
  /** Set only for a final matchup with a delivered result. */
  outcome: ScheduleOutcome | null;
  ownPoints: number | null;
  opponentPoints: number | null;
  firstKickoffUtc: string | null;
  /** Final regular-season record of the opponent in this season file; null without an opponent. */
  opponentRecord: ScheduleRecord | null;
}

export interface TeamSchedule {
  rows: TeamScheduleRow[];
  /** Regular-season record of the team, counted from the final results. */
  record: ScheduleRecord;
  /** Start week of the playoffs while the file holds no playoff weeks yet; otherwise null. */
  upcomingPlayoffStartWeek: number | null;
}

function emptyRecord(): ScheduleRecord {
  return { wins: 0, losses: 0, ties: 0 };
}

/** Counts the final regular-season results of every team. */
export function countRegularSeasonRecords(model: MatchupsReadModel | null | undefined): Map<number, ScheduleRecord> {
  const records = new Map<number, ScheduleRecord>();
  for (const week of model?.Weeks ?? []) {
    if (week.Stage !== 'regular-season') continue;
    for (const matchup of week.Matchups) {
      if (matchup.CompletionState !== 'final' || !matchup.Result) continue;
      for (const participant of matchup.Participants) {
        const record = records.get(participant.TeamID) ?? emptyRecord();
        if (matchup.Result.Type === 'tie') record.ties++;
        else if (matchup.Result.WinnerTeamID === participant.TeamID) record.wins++;
        else record.losses++;
        records.set(participant.TeamID, record);
      }
    }
  }
  return records;
}

function resolveOutcome(matchup: FantasyMatchupReadModel, teamID: number): ScheduleOutcome | null {
  if (matchup.CompletionState !== 'final' || !matchup.Result) return null;
  if (matchup.Result.Type === 'tie') return 'tie';
  return matchup.Result.WinnerTeamID === teamID ? 'win' : 'loss';
}

export function buildTeamSchedule(
  model: MatchupsReadModel | null | undefined,
  teamID: number,
  options: { isCurrentSeason: boolean; playoffStartWeek?: number | null }
): TeamSchedule {
  const weeks = [...(model?.Weeks ?? [])].sort((left, right) => left.Week - right.Week);
  const records = countRegularSeasonRecords(model);
  const activeWeek = options.isCurrentSeason ? model?.Summary?.ActiveOrNextWeek ?? null : null;
  const rows: TeamScheduleRow[] = [];

  for (const week of weeks) {
    const matchup = week.Matchups.find(candidate => candidate.Participants.some(entry => entry.TeamID === teamID));
    const isPlayoff = week.Stage === 'playoffs';
    // A playoff week without a game for this team is not part of its schedule.
    if (!matchup && isPlayoff) continue;

    const own = matchup?.Participants.find(entry => entry.TeamID === teamID);
    const other = matchup?.Participants.find(entry => entry.TeamID !== teamID);
    const outcome = matchup ? resolveOutcome(matchup, teamID) : null;
    rows.push({
      key: `${week.Stage}-${week.Week}`,
      week: week.Week,
      stage: week.Stage,
      isPlayoff,
      isCurrentWeek: activeWeek === week.Week,
      matchupID: matchup?.FantasyMatchupID ?? null,
      opponentID: other?.TeamID ?? null,
      state: matchup?.CompletionState ?? week.CompletionState,
      outcome,
      ownPoints: outcome && own ? own.Points : null,
      opponentPoints: outcome && other ? other.Points : null,
      firstKickoffUtc: week.FirstKickoffUtc,
      opponentRecord: other ? records.get(other.TeamID) ?? emptyRecord() : null
    });
  }

  const hasPlayoffWeeks = weeks.some(week => week.Stage === 'playoffs');
  const startWeek = options.playoffStartWeek ?? null;
  return {
    rows,
    record: records.get(teamID) ?? emptyRecord(),
    upcomingPlayoffStartWeek: options.isCurrentSeason && !hasPlayoffWeeks && startWeek && startWeek > 0 ? startWeek : null
  };
}

export function formatScheduleRecord(record: ScheduleRecord): string {
  return record.ties > 0 ? `${record.wins}-${record.losses}-${record.ties}` : `${record.wins}-${record.losses}`;
}
