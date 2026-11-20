
import { buildInjuryHistoryView, findPlayerInjuryHistory } from './player-injury-history-view.util';


describe('player injury history view', () => {
  it('lists only real injuries and missed games, newest first', () => {
    const view = buildInjuryHistoryView({
      ID: '1',
      Seasons: [
        {
          Season: 2024,
          Weeks: [
            { Week: 3, GameType: 'REG', Team: 'SF', State: 'played', Participation: 'played', Report: [{ Game: null, Practice: null, Reasons: ['Not injury related - resting player'] }], Roster: null },
            { Week: 2, GameType: 'REG', Team: 'SF', State: 'not-played-reported', Participation: 'not-played', Report: [{ Game: 'Out', Practice: null, Reasons: ['Knee'] }], Roster: { Status: 'RES', Code: 'R01' } },
            { Week: 1, GameType: 'REG', Team: 'SF', State: 'played', Participation: 'played', Report: [{ Game: 'Questionable', Practice: null, Reasons: ['Ankle'] }], Roster: null },
            { Week: 4, GameType: 'REG', Team: 'SF', State: 'unknown', Participation: 'unknown', Report: null, Roster: null }
          ]
        },
        { Season: 2023, Weeks: [{ Week: 1, GameType: 'REG', Team: 'SF', State: 'bye', Participation: 'no-game', Report: null, Roster: null }] }
      ]
    });
    expect(view.map(s => s.season)).toEqual([2024]);
    expect(view[0].rows.map(r => r.week)).toEqual([2, 1]);
    expect(view[0].rows[0].report).toBe('Out · Knee');
    expect(view[0].rows[0].roster).toBe('Reserve list');
    expect(view[0].rows[1].stateLabel).toBe('Played');
    expect(view[0].affectedWeeks).toBe(1);
  });

  it('shows an injury report of an unplayed game as result pending, never healthy', () => {
    const view = buildInjuryHistoryView({
      ID: '1',
      Seasons: [{ Season: 2026, Weeks: [{ Week: 11, GameType: 'REG', Team: 'SF', State: 'unknown', Participation: 'unknown', Report: [{ Game: 'Questionable', Practice: null, Reasons: ['Hamstring'] }], Roster: null }] }]
    });
    expect(view[0].rows[0].stateLabel).toBe('Result pending');
    expect(view[0].rows[0].stateClass).toBe('unknown');
  });

  it('ignores report notes with full practice participation and no game designation', () => {
    const view = buildInjuryHistoryView({
      ID: '1',
      Seasons: [{ Season: 2026, Weeks: [
        { Week: 11, GameType: 'REG', Team: 'KC', State: 'unknown', Participation: 'unknown', Report: [{ Game: null, Practice: 'Full Participation in Practice', Reasons: ['Knee'] }], Roster: null },
        { Week: 10, GameType: 'REG', Team: 'KC', State: 'played', Participation: 'played', Report: [{ Game: null, Practice: 'Full Participation in Practice', Reasons: ['Knee'] }], Roster: null }
      ] }]
    });
    expect(view).toEqual([]);
  });

  it('uses one label for missed games and explains reserve or missing reports in the text', () => {
    const view = buildInjuryHistoryView({
      ID: '1',
      Seasons: [{ Season: 2026, Weeks: [
        { Week: 3, GameType: 'REG', Team: 'SF', State: 'not-played-unexplained', Participation: 'not-played', Report: null, Roster: null },
        { Week: 2, GameType: 'REG', Team: 'SF', State: 'not-played-reserve', Participation: 'not-played', Report: null, Roster: { Status: 'RES', Code: 'R01' } },
        { Week: 1, GameType: 'REG', Team: 'SF', State: 'not-played-reported', Participation: 'not-played', Report: [{ Game: 'Out', Practice: null, Reasons: ['Knee'] }], Roster: null }
      ] }]
    });
    expect(view[0].rows.map(r => r.stateLabel)).toEqual(['Did not play', 'Did not play', 'Did not play']);
    expect(view[0].rows.map(r => r.report)).toEqual(['No report', 'Reserve list', 'Out · Knee']);
  });

  it('finds a player by id and handles a missing history', () => {
    const p = { ID: '1', Seasons: [] };
    expect(findPlayerInjuryHistory({ ContractVersion: 1, Product: 'x', Coverage: [], Players: [p] }, 1)).toBe(p);
    expect(findPlayerInjuryHistory(null, 1)).toBeNull();
    expect(buildInjuryHistoryView(null)).toEqual([]);
  });
});
