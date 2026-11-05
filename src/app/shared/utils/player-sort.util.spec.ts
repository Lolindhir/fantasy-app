import type { Player } from '../../core/models/player.models';
import {
  comparePlayersByDepthChart,
  formatPlayerPositionDepth,
  getPlayerDepthChartLabel,
  getPlayerDepthChartOrder
} from './player-sort.util';

function player(
  id: string,
  position: string,
  depthSlot: string | null,
  depthOrder: number | null,
  salary = 10
): Player {
  return {
    ID: id,
    NameFirst: 'Test',
    NameLast: id,
    Position: position,
    SleeperDepthChartPosition: depthSlot,
    SleeperDepthChartOrder: depthOrder,
    Salary: salary
  } as Player;
}

describe('Sleeper depth-chart position consistency', () => {
  it('keeps normal QB/RB/TE/K ranks and all common WR alignment slots', () => {
    for (const position of ['QB', 'RB', 'TE', 'K']) {
      expect(getPlayerDepthChartLabel(player(position, position, position, 1)))
        .toBe(`${position} #1`);
    }
    for (const slot of ['WR', 'LWR', 'RWR', 'SWR']) {
      expect(getPlayerDepthChartLabel(player(slot, 'WR', slot, 2))).toBe('WR #2');
    }
  });

  it('does not mistake Travis Hunter’s defensive RCB #1 for WR #1', () => {
    const hunter = player('12530', 'WR', 'RCB', 1);
    expect(getPlayerDepthChartOrder(hunter)).toBeUndefined();
    expect(getPlayerDepthChartLabel(hunter)).toBeUndefined();
    expect(formatPlayerPositionDepth(hunter)).toBe('WR');
  });

  it('suppresses other cross-position slots without special-casing a player name', () => {
    const receiverWithRbSlot = player('8223', 'WR', 'RB', 6);
    const rbWithReceiverSlot = player('rb', 'RB', 'SWR', 1);
    expect(getPlayerDepthChartLabel(receiverWithRbSlot)).toBeUndefined();
    expect(getPlayerDepthChartLabel(rbWithReceiverSlot)).toBeUndefined();
  });

  it('preserves a valid order without a slot and leaves missing/invalid order unavailable', () => {
    expect(getPlayerDepthChartLabel(player('no-slot', 'WR', null, 2))).toBe('WR #2');
    expect(getPlayerDepthChartOrder(player('none', 'WR', 'LWR', null))).toBeUndefined();
    expect(getPlayerDepthChartOrder(player('zero', 'WR', 'LWR', 0))).toBeUndefined();
    expect(getPlayerDepthChartOrder(player('negative', 'WR', 'LWR', -1))).toBeUndefined();
  });

  it('sorts conflicted depth entries after valid ones and retains the salary fallback', () => {
    const wrOne = player('wr1', 'WR', 'LWR', 1, 5);
    const wrThree = player('wr3', 'WR', 'SWR', 3, 5);
    const hunter = player('hunter', 'WR', 'RCB', 1, 100);
    const rbSlot = player('rb-slot', 'WR', 'RB', 6, 30);
    const noDepth = player('no-depth', 'WR', null, null, 20);

    expect([hunter, noDepth, wrThree, rbSlot, wrOne]
      .sort(comparePlayersByDepthChart)
      .map(value => value.ID))
      .toEqual(['wr1', 'wr3', 'hunter', 'rb-slot', 'no-depth']);
  });
});
