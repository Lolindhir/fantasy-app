import type { PlayerInjuryHistoryPlayer } from '../../core/models/player-injury-history.models';
import { buildInjuryHistoryView, findPlayerInjuryHistory } from './player-injury-history-view.util';

const player: PlayerInjuryHistoryPlayer = {
  ID: '1',
  Seasons: [
    { Season: 2023, Weeks: [{ Week: 1, GameType: 'REG', Team: 'SF', State: 'unknown', Participation: 'unknown', Report: null, Roster: null }] },
    {
      Season: 2024,
      Weeks: [
        { Week: 2, GameType: 'REG', Team: 'SF', State: 'not-played-reported', Participation: 'not-played', Report: [{ Game: 'Out', Practice: null, Reasons: ['Knee'] }], Roster: { Status: 'RES', Code: 'R01' } },
        { Week: 1, GameType: 'REG', Team: 'SF', State: 'played', Participation: 'played', Report: null, Roster: { Status: 'ACT', Code: 'A01' } }
      ]
    }
  ]
};

describe('player injury history view', () => {
  it('orders newest season and week first and never labels unknown as healthy', () => {
    const view = buildInjuryHistoryView(player);
    expect(view.map(s => s.season)).toEqual([2024, 2023]);
    expect(view[0].rows.map(r => r.week)).toEqual([2, 1]);
    expect(view[0].rows[0].report).toBe('Out · Knee');
    expect(view[0].rows[0].roster).toBe('Reserve list');
    expect(view[1].rows[0].stateLabel).toBe('Unknown');
    expect(view[1].rows[0].stateClass).toBe('unknown');
  });

  it('finds a player by id and handles a missing history', () => {
    expect(findPlayerInjuryHistory({ ContractVersion: 1, Product: 'x', Coverage: [], Players: [player] }, 1)).toBe(player);
    expect(findPlayerInjuryHistory(null, 1)).toBeNull();
    expect(buildInjuryHistoryView(null)).toEqual([]);
  });
});
