import type {
  FantasyMatchupReadModel,
  MatchupCompletionState,
  MatchupStage,
  MatchupsReadModel
} from '../../core/models/matchup.models';
import {
  buildRivalryRecords,
  formatRivalryRecord,
  isConsolationMatchup,
  type RivalryOptions
} from './team-rivalry.util';

function duel(
  a: number, aPoints: number | null, b: number, bPoints: number | null,
  result: 'a' | 'b' | 'tie' | null = null,
  state: MatchupCompletionState = 'final'
): FantasyMatchupReadModel {
  const resolved = result ?? (aPoints === null || bPoints === null ? null : aPoints === bPoints ? 'tie' : aPoints > bPoints ? 'a' : 'b');
  return {
    FantasyMatchupID: `m-${a}-${b}-${aPoints}`,
    Participants: [
      { TeamID: a, Points: aPoints, ScoreKind: 'standard' },
      { TeamID: b, Points: bPoints, ScoreKind: 'standard' }
    ],
    CompletionState: state,
    Result: resolved === null || state !== 'final'
      ? null
      : resolved === 'tie'
        ? { Type: 'tie', WinnerTeamID: null }
        : { Type: 'win', WinnerTeamID: resolved === 'a' ? a : b }
  };
}

function season(year: string, weeks: Array<[number, MatchupStage, FantasyMatchupReadModel[]]>): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: year,
    Weeks: weeks.map(([week, stage, matchups]) => ({
      Week: week, Stage: stage, FirstKickoffUtc: null, CompletionState: 'final', Matchups: matchups
    })),
    Summary: { LastCompletedWeek: null, ActiveOrNextWeek: null }
  };
}

const allComplete: RivalryOptions = { filter: 'all', isSeasonComplete: () => true };

// Six-team playoff: semis 1v4 and 2v3 (week 14) with consolation 5v6, finals 1v2 and third place 3v4 (week 15).
const playoffSeason = season('2025', [
  [1, 'regular-season', [duel(1, 100, 2, 90), duel(3, 80, 4, 80)]],
  [14, 'playoffs', [duel(1, 120, 4, 100), duel(2, 110, 3, 90), duel(5, 70, 6, 75)]],
  [15, 'playoffs', [duel(1, 130, 2, 131), duel(3, 95, 4, 85)]]
]);

describe('team rivalry utilities', () => {
  it('counts wins, losses, ties and points from finalized results', () => {
    const records = buildRivalryRecords(3, [playoffSeason], { ...allComplete, filter: 'regular' });
    expect(records.length).toBe(1);
    expect(records[0].opponentId).toBe(4);
    expect(formatRivalryRecord(records[0])).toBe('0-0-1');
    expect(records[0].pointsFor).toBe(80);
    expect(records[0].pointsAgainst).toBe(80);
  });

  it('counts the same pair from both sides symmetrically', () => {
    const [fromOne] = buildRivalryRecords(1, [playoffSeason], allComplete).filter(r => r.opponentId === 2);
    const [fromTwo] = buildRivalryRecords(2, [playoffSeason], allComplete).filter(r => r.opponentId === 1);
    expect([fromOne.wins, fromOne.losses]).toEqual([fromTwo.losses, fromTwo.wins]);
    expect(fromOne.pointsFor).toBe(fromTwo.pointsAgainst);
  });

  it('does not count consolation games but counts the third-place game', () => {
    const five = buildRivalryRecords(5, [playoffSeason], allComplete);
    expect(five).toEqual([]);

    const three = buildRivalryRecords(3, [playoffSeason], { ...allComplete, filter: 'playoffs' });
    expect(three.map(record => record.opponentId).sort()).toEqual([2, 4]);
  });

  it('classifies a consolation matchup only when neither team reaches the final playoff week', () => {
    const consolation = playoffSeason.Weeks[1].Matchups[2];
    const semifinal = playoffSeason.Weeks[1].Matchups[0];
    expect(isConsolationMatchup(playoffSeason, 14, consolation)).toBeTrue();
    expect(isConsolationMatchup(playoffSeason, 14, semifinal)).toBeFalse();
    expect(isConsolationMatchup(playoffSeason, 15, playoffSeason.Weeks[2].Matchups[0])).toBeFalse();
  });

  it('filters regular season and playoffs separately', () => {
    const regular = buildRivalryRecords(1, [playoffSeason], { ...allComplete, filter: 'regular' });
    const playoffs = buildRivalryRecords(1, [playoffSeason], { ...allComplete, filter: 'playoffs' });
    const all = buildRivalryRecords(1, [playoffSeason], allComplete);

    expect(regular.map(r => [r.opponentId, r.games.length])).toEqual([[2, 1]]);
    expect(playoffs.map(r => r.opponentId).sort()).toEqual([2, 4]);
    expect(all.find(r => r.opponentId === 2)?.games.length).toBe(2);
  });

  it('skips playoff games of a season whose playoffs are not complete', () => {
    const records = buildRivalryRecords(1, [playoffSeason], { filter: 'all', isSeasonComplete: () => false });
    expect(records.map(r => [r.opponentId, r.games.length])).toEqual([[2, 1]]);
  });

  it('ignores open and unknown matchups and results without a winner payload', () => {
    const data = season('2026', [
      [1, 'regular-season', [duel(1, 90, 2, 80)]],
      [2, 'regular-season', [duel(1, 70, 2, 60, null, 'open'), duel(3, 1, 4, 2, null, 'unknown')]]
    ]);
    const records = buildRivalryRecords(1, [data], allComplete);
    expect(records.length).toBe(1);
    expect(records[0].games.length).toBe(1);
  });

  it('keeps ties separate and aggregates across seasons in chronological order', () => {
    const s2024 = season('2024', [[3, 'regular-season', [duel(1, 100, 2, 100)]], [1, 'regular-season', [duel(2, 90, 1, 80)]]]);
    const s2025 = season('2025', [[2, 'regular-season', [duel(1, 120, 2, 100)]]]);
    const [record] = buildRivalryRecords(1, [s2025, s2024], allComplete);

    expect(formatRivalryRecord(record)).toBe('1-1-1');
    expect(record.games.map(game => `${game.season}-${game.week}`)).toEqual(['2024-1', '2024-3', '2025-2']);
    expect(record.lastGame.season).toBe('2025');
    expect(record.pointsFor).toBe(300);
    expect(record.pointsAgainst).toBe(290);
  });

  it('identifies the biggest win and the closest loss by margin', () => {
    const data = season('2025', [
      [1, 'regular-season', [duel(1, 150, 2, 100)]],
      [2, 'regular-season', [duel(1, 110, 2, 100)]],
      [3, 'regular-season', [duel(1, 99, 2, 100)]],
      [4, 'regular-season', [duel(1, 50, 2, 100)]]
    ]);
    const [record] = buildRivalryRecords(1, [data], allComplete);
    expect(record.biggestWin?.week).toBe(1);
    expect(record.closestLoss?.week).toBe(3);
  });

  it('has no highlight for outcomes that never happened and tolerates missing scores', () => {
    const data = season('2025', [[1, 'regular-season', [duel(1, null, 2, null, 'a')]]]);
    const [record] = buildRivalryRecords(1, [data], allComplete);
    expect(record.wins).toBe(1);
    expect(record.biggestWin).toBeNull();
    expect(record.closestLoss).toBeNull();
    expect(record.pointsFor).toBe(0);
  });

  it('orders opponents by number of meetings then team id (display order, not a ranking)', () => {
    const data = season('2025', [
      [1, 'regular-season', [duel(1, 1, 5, 0), duel(2, 1, 3, 0)]],
      [2, 'regular-season', [duel(1, 1, 5, 0)]],
      [3, 'regular-season', [duel(1, 1, 3, 0)]]
    ]);
    expect(buildRivalryRecords(1, [data], allComplete).map(record => record.opponentId)).toEqual([5, 3]);
  });
});
