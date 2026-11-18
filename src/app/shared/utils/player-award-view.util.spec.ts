import type { PlayerAwardHistoryReadModel } from '../../core/models/player-award-history.models';
import { buildPlayerAwardHighlights, findPlayerAwards, groupPlayerAwardEntries } from './player-award-view.util';

const history: PlayerAwardHistoryReadModel = {
  SchemaVersion: 1,
  Awards: ['MVP', 'MatchupHero', 'Heartbreaker', 'UnsungHero'],
  Seasons: [],
  Leaders: {
    MVP: [{ PlayerID: '1', Name: 'A One', Position: 'RB', Count: 3 }, { PlayerID: '2', Name: 'B Two', Position: 'WR', Count: 3 }],
    MatchupHero: [{ PlayerID: '1', Name: 'A One', Position: 'RB', Count: 1 }],
    Heartbreaker: [],
    UnsungHero: []
  },
  Players: [
    {
      PlayerID: '1', Name: 'A One', Position: 'RB', Counts: { MVP: 3, MatchupHero: 1, Heartbreaker: 0, UnsungHero: 0 }, Total: 4,
      Entries: [
        { Season: 2024, Week: 2, Award: 'MVP', Points: 30 },
        { Season: 2025, Week: 1, Award: 'MatchupHero', Points: 20 },
        { Season: 2025, Week: 1, Award: 'MVP', Points: 20 }
      ]
    },
    { PlayerID: '9', Name: 'Z Zero', Position: 'TE', Counts: { MVP: 0, MatchupHero: 0, Heartbreaker: 0, UnsungHero: 0 }, Total: 0, Entries: [] }
  ]
};

describe('player award view util', () => {
  it('builds one tile per award with a leader and lists ties together', () => {
    const tiles = buildPlayerAwardHighlights(history);
    expect(tiles.map(t => t.title)).toEqual(['Most Week MVPs', 'Most Matchup Heroes']);
    expect(tiles[0].owner).toBe('A One, B Two');
    expect(tiles[0].valueDisplay).toBe('3×');
  });

  it('summarizes large ties and keeps the names in the reason', () => {
    const many = ['A', 'B', 'C'].map((n, i) => ({ PlayerID: String(i), Name: n, Position: 'RB', Count: 2 }));
    const tiles = buildPlayerAwardHighlights({ ...history, Leaders: { MVP: many } });
    expect(tiles[0].owner).toBe('3 players tied');
    expect(tiles[0].reason).toContain('A, B, C');
  });

  it('returns no tiles when leaders are missing', () => {
    expect(buildPlayerAwardHighlights({ ...history, Leaders: undefined })).toEqual([]);
    expect(buildPlayerAwardHighlights(null)).toEqual([]);
  });

  it('finds only players with at least one award, matched by Sleeper ID', () => {
    expect(findPlayerAwards(history, 1)?.Name).toBe('A One');
    expect(findPlayerAwards(history, '9')).toBeNull();
  });

  it('groups entries newest season and week first', () => {
    const groups = groupPlayerAwardEntries(history.Players[0].Entries);
    expect(groups.map(g => g.season)).toEqual([2025, 2024]);
    expect(groups[0].entries.map(e => e.award)).toEqual(['MVP', 'MatchupHero']);
  });
});
