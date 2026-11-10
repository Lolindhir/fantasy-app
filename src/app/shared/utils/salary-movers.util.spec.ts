import type { Player } from '../../core/models/fantasy.models';
import { buildSalaryMovers } from './salary-movers.util';

function player(id: string, delta: number | null | undefined, extra: Partial<Player> = {}): Player {
  return {
    ID: id,
    Name: `Player ${id}`,
    SalaryProjectedDelta: delta,
    ...extra
  } as unknown as Player;
}

describe('buildSalaryMovers', () => {
  it('sorts by the generator-owned delta and splits up and down', () => {
    const movers = buildSalaryMovers([player('a', 5), player('b', -7), player('c', 9), player('d', -2)]);
    expect(movers.up.map(m => m.player.ID)).toEqual(['c', 'a']);
    expect(movers.down.map(m => m.player.ID)).toEqual(['b', 'd']);
    expect(movers.up[0].delta).toBe(9);
  });

  it('skips unknown, missing and zero deltas instead of treating them as 0', () => {
    const movers = buildSalaryMovers([player('a', null), player('b', undefined), player('c', 0), player('d', 3)]);
    expect(movers.up.map(m => m.player.ID)).toEqual(['d']);
    expect(movers.down).toEqual([]);
  });

  it('limits each list and applies the pool filter', () => {
    const players = Array.from({ length: 8 }, (_, i) => player(String(i), i + 1));
    expect(buildSalaryMovers(players).up.length).toBe(5);
    expect(buildSalaryMovers(players, p => p.ID !== '7').up[0].player.ID).toBe('6');
    expect(buildSalaryMovers(players, () => true, 2).up.length).toBe(2);
  });

  it('orders equal deltas deterministically by name', () => {
    const movers = buildSalaryMovers([player('b', 4), player('a', 4)]);
    expect(movers.up.map(m => m.player.ID)).toEqual(['a', 'b']);
  });
});
