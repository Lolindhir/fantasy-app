import type { Player, RankingEntry } from '../../core/models/player.models';
import {
  buildRosterPlayerGroups,
  isCombinedRankingAvailable,
  sortRosterPlayers
} from './team-roster-view.util';

describe('team roster view utilities', () => {
  it('keeps Combined Ranking unavailable until three scored weeks are complete', () => {
    expect(isCombinedRankingAvailable(undefined)).toBeFalse();
    expect(isCombinedRankingAvailable(0)).toBeFalse();
    expect(isCombinedRankingAvailable(2)).toBeFalse();
    expect(isCombinedRankingAvailable(3)).toBeTrue();
  });

  it('groups roster status with IR taking precedence over Taxi', () => {
    const roster = makePlayer('roster', { salary: 10 });
    const taxi = makePlayer('taxi', { salary: 8, taxi: true });
    const ir = makePlayer('ir', { salary: 7, reserve: true });
    const taxiIr = makePlayer('taxi-ir', { salary: 6, taxi: true, reserve: true });

    const groups = buildRosterPlayerGroups([roster, taxi, ir, taxiIr], 'rosterStatus', 'salary');

    expect(groups.map(group => group.key)).toEqual(['roster', 'taxi', 'ir']);
    expect(groups[0].players.map(player => player.ID)).toEqual(['roster']);
    expect(groups[1].players.map(player => player.ID)).toEqual(['taxi']);
    expect(groups[2].players.map(player => player.ID)).toEqual(['ir', 'taxi-ir']);
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
});

interface PlayerOptions {
  salary?: number;
  projected?: number;
  position?: string;
  age?: number;
  taxi?: boolean;
  reserve?: boolean;
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
    Taxi: options.taxi ?? false,
    Reserve: options.reserve ?? false,
    Stats: { Ranking: ranking }
  } as unknown as Player;
}
