import type { FantasyTeam } from '../../core/models/league.models';
import type { TeamSeasonIdentity } from '../services/team-season.service';
import type { FantasyMatchupReadModel, MatchupWeekReadModel, MatchupsReadModel } from '../../core/models/matchup.models';
import {
  buildTeamSchedule,
  countRegularSeasonRecords,
  formatScheduleRecord,
  resolveScheduleOpponent
} from './team-schedule.util';

function matchup(id: string, a: number, b: number, scores: [number, number] | null, winner?: number | 'tie'): FantasyMatchupReadModel {
  return {
    FantasyMatchupID: id,
    Participants: [
      { TeamID: a, Points: scores?.[0] ?? 0, ScoreKind: 'standard' },
      { TeamID: b, Points: scores?.[1] ?? 0, ScoreKind: 'standard' }
    ],
    CompletionState: scores ? 'final' : 'open',
    Result: !scores ? null : winner === 'tie' ? { Type: 'tie', WinnerTeamID: null } : { Type: 'win', WinnerTeamID: winner as number }
  };
}

function week(number: number, stage: 'regular-season' | 'playoffs', matchups: FantasyMatchupReadModel[]): MatchupWeekReadModel {
  const allFinal = matchups.every(entry => entry.CompletionState === 'final');
  return {
    Week: number,
    Stage: stage,
    FirstKickoffUtc: `2026-09-${String(10 + number).padStart(2, '0')}T17:00:00Z`,
    CompletionState: allFinal ? 'final' : 'open',
    Matchups: matchups
  };
}

function model(weeks: MatchupWeekReadModel[], active: number | null): MatchupsReadModel {
  return { SchemaVersion: 1, Season: '2026', Weeks: weeks, Summary: { LastCompletedWeek: null, ActiveOrNextWeek: active } };
}

describe('team-schedule.util', () => {
  const season = model([
    week(1, 'regular-season', [matchup('m1', 1, 2, [100, 90], 1), matchup('m1b', 3, 4, [80, 85], 4)]),
    week(2, 'regular-season', [matchup('m2', 2, 1, [70, 70], 'tie'), matchup('m2b', 3, 4, [60, 50], 3)]),
    week(3, 'regular-season', [matchup('m3', 1, 3, null), matchup('m3b', 2, 4, null)]),
    week(4, 'regular-season', [matchup('m4', 2, 4, null)])
  ], 3);

  it('counts final results as wins, losses and ties', () => {
    const records = countRegularSeasonRecords(season);
    expect(records.get(1)).toEqual({ wins: 1, losses: 0, ties: 1 });
    expect(records.get(2)).toEqual({ wins: 0, losses: 1, ties: 1 });
    expect(records.get(3)).toEqual({ wins: 1, losses: 1, ties: 0 });
  });

  it('lists every regular-season week in data order with outcome from the team viewpoint', () => {
    const schedule = buildTeamSchedule(season, 1, { isCurrentSeason: true });
    expect(schedule.rows.map(row => row.week)).toEqual([1, 2, 3, 4]);
    expect(schedule.rows[0]).toEqual(jasmine.objectContaining({ outcome: 'win', ownPoints: 100, opponentPoints: 90, opponentID: 2 }));
    expect(schedule.rows[1]).toEqual(jasmine.objectContaining({ outcome: 'tie', ownPoints: 70, opponentPoints: 70 }));
    expect(formatScheduleRecord(schedule.record)).toBe('1-0-1');
  });

  it('shows open weeks without result, marks the active week and keeps a bye row without opponent', () => {
    const schedule = buildTeamSchedule(season, 1, { isCurrentSeason: true });
    expect(schedule.rows[2]).toEqual(jasmine.objectContaining({ outcome: null, ownPoints: null, state: 'open', isCurrentWeek: true, matchupID: 'm3' }));
    expect(schedule.rows[3]).toEqual(jasmine.objectContaining({ matchupID: null, opponentID: null, opponentRecord: null }));
    expect(buildTeamSchedule(season, 1, { isCurrentSeason: false }).rows.some(row => row.isCurrentWeek)).toBeFalse();
  });

  it('attaches the final regular-season record of the opponent', () => {
    const schedule = buildTeamSchedule(season, 1, { isCurrentSeason: true });
    expect(schedule.rows[0].opponentRecord).toEqual({ wins: 0, losses: 1, ties: 1 });
  });

  it('appends playoff games only for participating teams and counts them outside the regular-season record', () => {
    const withPlayoffs = model([
      ...season.Weeks,
      week(5, 'playoffs', [matchup('p5', 1, 2, [90, 80], 1), matchup('p5b', 3, 4, [1, 2], 4)]),
      week(6, 'playoffs', [matchup('p6', 3, 4, [1, 2], 4)])
    ], null);
    const schedule = buildTeamSchedule(withPlayoffs, 1, { isCurrentSeason: false });
    expect(schedule.rows.filter(row => row.isPlayoff).map(row => row.week)).toEqual([5]);
    expect(schedule.record).toEqual({ wins: 1, losses: 0, ties: 1 });
    expect(schedule.upcomingPlayoffStartWeek).toBeNull();
  });

  it('announces the playoff start week only while the current season has no playoff weeks yet', () => {
    expect(buildTeamSchedule(season, 1, { isCurrentSeason: true, playoffStartWeek: 14 }).upcomingPlayoffStartWeek).toBe(14);
    expect(buildTeamSchedule(season, 1, { isCurrentSeason: false, playoffStartWeek: 14 }).upcomingPlayoffStartWeek).toBeNull();
    expect(buildTeamSchedule(season, 1, { isCurrentSeason: true, playoffStartWeek: 0 }).upcomingPlayoffStartWeek).toBeNull();
  });

  it('keeps known 0-0 separate from an absent team or unknown result', () => {
    const open = model([week(1, 'regular-season', [matchup('m', 1, 2, null)])], 1);
    expect(buildTeamSchedule(open, 1, { isCurrentSeason: true }).record).toEqual({ wins: 0, losses: 0, ties: 0 });
    const absent = buildTeamSchedule(open, 9, { isCurrentSeason: true });
    expect(absent.record).toBeNull();
    expect(absent.rows).toEqual([]);
    const unknown = { ...matchup('m', 1, 2, null), CompletionState: 'unknown' as const };
    expect(countRegularSeasonRecords(model([week(1, 'regular-season', [unknown])], 1)).has(1)).toBeFalse();
    const invalid = matchup('bad', 1, 2, [10, 5], 9);
    const invalidSchedule = buildTeamSchedule(model([week(1, 'regular-season', [invalid])], null), 1, { isCurrentSeason: true });
    expect(invalidSchedule.record).toBeNull();
    expect(invalidSchedule.rows[0].outcome).toBeNull();
    expect(invalidSchedule.rows[0].opponentRecord).toBeNull();
  });

  it('uses individually final matchups even while the enclosing week is open', () => {
    const mixed = model([week(1, 'regular-season', [
      matchup('finished', 1, 2, [10, 5], 1), matchup('open', 3, 4, null)
    ])], 1);
    expect(mixed.Weeks[0].CompletionState).toBe('open');
    expect(countRegularSeasonRecords(mixed).get(1)).toEqual({ wins: 1, losses: 0, ties: 0 });
    expect(countRegularSeasonRecords(mixed).get(3)).toEqual({ wins: 0, losses: 0, ties: 0 });
  });

  it('resolves historical-only opponents without borrowing a current team name or logo', () => {
    const current = [{ TeamID: 1, Team: 'Current team', Owner: 'New owner', Avatar: 'current.png' }] as FantasyTeam[];
    const historic: TeamSeasonIdentity = { TeamID: 7, Team: 'Historic opponent', TeamAbbr: 'HIS',
      Avatar: 'old.png', Owner: 'Old owner', OwnerAvatar: null };
    const lookup = { identity: (season: string | number, id: string | number) =>
      String(season) === '2024' && Number(id) === 7 ? historic : null };
    expect(resolveScheduleOpponent(current, lookup, '2024', '2026', 7)).toBe(historic);
    expect(resolveScheduleOpponent(current, lookup, '2024', '2026', 1)).toBeNull();
    expect(resolveScheduleOpponent(current, null, '2024', '2026', 1)).toBeNull();
    expect(resolveScheduleOpponent(current, lookup, '2026', '2026', 1)).toBe(current[0]);
  });

  it('handles a missing season file', () => {
    const schedule = buildTeamSchedule(null, 1, { isCurrentSeason: true });
    expect(schedule.rows).toEqual([]);
    expect(schedule.record).toBeNull();
    expect(formatScheduleRecord(schedule.record)).toBe('–');
  });
});
