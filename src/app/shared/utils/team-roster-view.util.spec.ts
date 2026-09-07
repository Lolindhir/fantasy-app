import type { DecisionWindowPlayerLockFact } from '../../core/models/decision-window.models';
import type { Player, RankingEntry } from '../../core/models/player.models';
import {
  buildRosterPlayerGroups,
  formatRosterNextLockValue,
  isCombinedRankingAvailable,
  sortRosterPlayers,
  type RosterNextLockContext
} from './team-roster-view.util';

describe('team roster view utilities', () => {
  it('keeps Combined Ranking unavailable until three scored weeks are complete', () => {
    expect(isCombinedRankingAvailable(undefined)).toBeFalse();
    expect(isCombinedRankingAvailable(0)).toBeFalse();
    expect(isCombinedRankingAvailable(2)).toBeFalse();
    expect(isCombinedRankingAvailable(3)).toBeTrue();
  });

  it('groups the resolved roster status buckets independently', () => {
    const roster = makePlayer('roster', { salary: 10 });
    const taxi = makePlayer('taxi', { salary: 8 });
    const ir = makePlayer('ir', { salary: 7 });

    const groups = buildRosterPlayerGroups(
      [roster, taxi, ir],
      'rosterStatus',
      'salary',
      { roster: [roster], taxi: [taxi], ir: [ir] }
    );

    expect(groups.map(group => group.key)).toEqual(['roster', 'taxi', 'ir']);
    expect(groups[0].players.map(player => player.ID)).toEqual(['roster']);
    expect(groups[1].players.map(player => player.ID)).toEqual(['taxi']);
    expect(groups[2].players.map(player => player.ID)).toEqual(['ir']);
  });

  it('groups positions in football order and sorts each group independently', () => {
    const players = [
      makePlayer('wr-low', { position: 'WR', salary: 10 }),
      makePlayer('qb', { position: 'QB', salary: 8 }),
      makePlayer('rb', { position: 'RB', salary: 9 }),
      makePlayer('wr-high', { position: 'WR', salary: 20 })
    ];

    const groups = buildRosterPlayerGroups(players, 'position', 'salary');

    expect(groups.map(group => group.label)).toEqual(['Quarterbacks', 'Running Backs', 'Wide Receivers']);
    expect(groups[2].players.map(player => player.ID)).toEqual(['wr-high', 'wr-low']);
  });

  it('splits current ranked and unranked players without promoting previous ranks', () => {
    const current = makePlayer('current', { currentRank: 20 });
    const previousOnly = makePlayer('previous', { previousRank: 2 });

    const groups = buildRosterPlayerGroups([previousOnly, current], 'rankingStatus', 'ranking');

    expect(groups[0].players.map(player => player.ID)).toEqual(['current']);
    expect(groups[1].players.map(player => player.ID)).toEqual(['previous']);
  });

  it('sorts Combined Ranking by current rank, then previous rank, then salary', () => {
    const rankedSecond = makePlayer('ranked-second', { currentRank: 8, salary: 1 });
    const rankedFirst = makePlayer('ranked-first', { currentRank: 2, salary: 1 });
    const previousSecond = makePlayer('previous-second', { previousRank: 12, salary: 100 });
    const previousFirst = makePlayer('previous-first', { previousRank: 4, salary: 1 });
    const rookieCheap = makePlayer('rookie-cheap', { salary: 5 });
    const rookieExpensive = makePlayer('rookie-expensive', { salary: 20 });

    const sorted = sortRosterPlayers(
      [previousSecond, rookieCheap, rankedSecond, previousFirst, rookieExpensive, rankedFirst],
      'ranking'
    );

    expect(sorted.map(player => player.ID)).toEqual([
      'ranked-first',
      'ranked-second',
      'previous-first',
      'previous-second',
      'rookie-expensive',
      'rookie-cheap'
    ]);
  });

  it('treats zero Combined Ranking values as unranked', () => {
    const zero = makePlayer('zero', { currentRank: 0, previousRank: 3 });
    const current = makePlayer('current', { currentRank: 50 });

    const sorted = sortRosterPlayers([zero, current], 'ranking');

    expect(sorted.map(player => player.ID)).toEqual(['current', 'zero']);
  });

  it('sorts age in both ascending and descending direction', () => {
    const younger = makePlayer('younger', { age: 22 });
    const middle = makePlayer('middle', { age: 27 });
    const older = makePlayer('older', { age: 31 });

    expect(sortRosterPlayers([middle, older, younger], 'ageAsc').map(player => player.ID))
      .toEqual(['younger', 'middle', 'older']);
    expect(sortRosterPlayers([middle, older, younger], 'ageDesc').map(player => player.ID))
      .toEqual(['older', 'middle', 'younger']);
  });

  it('sorts Next Lock by actionability with already locked players intentionally last', () => {
    const players = [
      makePlayer('locked-late'),
      makePlayer('bye'),
      makePlayer('future-late'),
      makePlayer('no-team'),
      makePlayer('unknown-z'),
      makePlayer('future-early'),
      makePlayer('locked-early'),
      makePlayer('missing-a')
    ];
    const context = lockContext('2026-09-06T16:00:00Z', [
      lockFact('future-early', 'scheduled', '2026-09-06T17:00:00Z'),
      lockFact('future-late', 'scheduled', '2026-09-06T20:00:00Z'),
      lockFact('unknown-z', 'unknown'),
      lockFact('no-team', 'no-team'),
      lockFact('bye', 'bye'),
      lockFact('locked-early', 'scheduled', '2026-09-06T13:00:00Z'),
      lockFact('locked-late', 'scheduled', '2026-09-06T15:00:00Z')
    ]);

    expect(sortRosterPlayers(players, 'nextLock', context).map(player => player.ID)).toEqual([
      'future-early',
      'future-late',
      'missing-a',
      'unknown-z',
      'no-team',
      'bye',
      'locked-early',
      'locked-late'
    ]);
  });

  it('recomputes future vs Locked from StartsAtUtc at kickoff without new lock facts', () => {
    const scheduled = makePlayer('scheduled');
    const bye = makePlayer('bye');
    const facts = [
      lockFact('scheduled', 'scheduled', '2026-09-06T18:00:00Z'),
      lockFact('bye', 'bye')
    ];

    const before = lockContext('2026-09-06T17:59:00Z', facts);
    expect(sortRosterPlayers([bye, scheduled], 'nextLock', before).map(player => player.ID))
      .toEqual(['scheduled', 'bye']);
    expect(formatRosterNextLockValue(scheduled, before)).not.toBe('Locked');

    const atKickoff = lockContext('2026-09-06T18:00:00Z', facts);
    expect(sortRosterPlayers([scheduled, bye], 'nextLock', atKickoff).map(player => player.ID))
      .toEqual(['bye', 'scheduled']);
    expect(formatRosterNextLockValue(scheduled, atKickoff)).toBe('Locked');
  });

  it('uses explicit deterministic dynamic values for non-scheduled lock states', () => {
    const players = [makePlayer('unknown'), makePlayer('no-team'), makePlayer('bye'), makePlayer('missing')];
    const context = lockContext('2026-09-06T16:00:00Z', [
      lockFact('unknown', 'unknown'),
      lockFact('no-team', 'no-team'),
      lockFact('bye', 'bye')
    ]);

    expect(formatRosterNextLockValue(players[0], context)).toBe('Unknown');
    expect(formatRosterNextLockValue(players[1], context)).toBe('No team');
    expect(formatRosterNextLockValue(players[2], context)).toBe('Bye');
    expect(formatRosterNextLockValue(players[3], context)).toBe('Unknown');
  });

  it('keeps Next Lock composable with existing roster-status and position grouping', () => {
    const rosterLate = makePlayer('roster-late', { position: 'WR' });
    const rosterEarly = makePlayer('roster-early', { position: 'WR' });
    const taxi = makePlayer('taxi', { position: 'QB' });
    const ir = makePlayer('ir', { position: 'RB' });
    const players = [rosterLate, taxi, rosterEarly, ir];
    const context = lockContext('2026-09-06T16:00:00Z', [
      lockFact('roster-late', 'scheduled', '2026-09-06T20:00:00Z'),
      lockFact('roster-early', 'scheduled', '2026-09-06T17:00:00Z'),
      lockFact('taxi', 'unknown'),
      lockFact('ir', 'bye')
    ]);

    const statusGroups = buildRosterPlayerGroups(
      players,
      'rosterStatus',
      'nextLock',
      { roster: [rosterLate, rosterEarly], taxi: [taxi], ir: [ir] },
      context
    );
    expect(statusGroups[0].players.map(player => player.ID)).toEqual(['roster-early', 'roster-late']);
    expect(statusGroups[1].players.map(player => player.ID)).toEqual(['taxi']);
    expect(statusGroups[2].players.map(player => player.ID)).toEqual(['ir']);

    const positionGroups = buildRosterPlayerGroups(players, 'position', 'nextLock', undefined, context);
    expect(positionGroups.map(group => group.label)).toEqual(['Quarterbacks', 'Running Backs', 'Wide Receivers']);
    expect(positionGroups[2].players.map(player => player.ID)).toEqual(['roster-early', 'roster-late']);
  });
});

interface PlayerOptions {
  salary?: number;
  projected?: number;
  position?: string;
  age?: number;
  currentRank?: number;
  previousRank?: number;
}

function makePlayer(id: string, options: PlayerOptions = {}): Player {
  const ranking: RankingEntry[] = [];
  if (options.currentRank !== undefined) ranking.push({ Type: 'Combined', Value: options.currentRank });
  if (options.previousRank !== undefined) ranking.push({ Type: 'Combined_Previous', Value: options.previousRank });

  return {
    ID: id,
    Name: id,
    Position: options.position ?? 'WR',
    Salary: options.salary ?? 0,
    SalaryProjected: options.projected ?? 0,
    Age: options.age ?? 25,
    Stats: { Ranking: ranking }
  } as unknown as Player;
}

function lockContext(now: string, facts: DecisionWindowPlayerLockFact[]): RosterNextLockContext {
  return {
    fantasyTeamId: 42,
    playerLockFacts: facts,
    now: new Date(now)
  };
}

function lockFact(
  playerId: string,
  kind: DecisionWindowPlayerLockFact['Kind'],
  startsAtUtc: string | null = null
): DecisionWindowPlayerLockFact {
  return {
    FantasyTeamID: 42,
    PlayerID: playerId,
    NFLTeamID: kind === 'no-team' ? null : 'NE',
    Kind: kind,
    GameID: kind === 'scheduled' ? `${playerId}-game` : null,
    DecisionWindowID: kind === 'scheduled' ? `${playerId}-window` : null,
    StartsAtUtc: startsAtUtc,
    IsStarter: false
  };
}
