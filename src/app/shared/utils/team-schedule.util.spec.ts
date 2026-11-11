import type { FantasyMatchupReadModel, MatchupWeekReadModel, MatchupsReadModel } from '../../core/models/matchup.models';
import {
  buildTeamSchedule,
  countRegularSeasonRecords,
  formatScheduleKickoff,
  formatScheduleRecord
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

  it('handles a missing season file', () => {
    const schedule = buildTeamSchedule(null, 1, { isCurrentSeason: true });
    expect(schedule.rows).toEqual([]);
    expect(schedule.record).toEqual({ wins: 0, losses: 0, ties: 0 });
  });

  it('formats kickoff dates and tolerates invalid values', () => {
    expect(formatScheduleKickoff(null)).toBe('');
    expect(formatScheduleKickoff('garbage')).toBe('');
    expect(formatScheduleKickoff('2026-11-15T18:00:00Z')).toMatch(/Nov 1[45]/);
  });
});
