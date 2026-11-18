import type { RawRivalryGame, RawRivalryRecord, RivalryReadModel } from '../../core/models/rivalry.models';
import { RivalryLookup, formatRivalryRecord } from './team-rivalry.service';

const game = (id: string, season: string, week: number, outcome: 'win' | 'loss' | 'tie'): RawRivalryGame => ({
  Season: season, Week: week, FantasyMatchupID: id, Stage: 'regular-season', Bracket: null, Outcome: outcome,
  TeamPoints: 100, OpponentPoints: 90, Margin: 10
});

const record = (teamId: number, opponentId: number, filter: RawRivalryRecord['Filter'], games: RawRivalryGame[]): RawRivalryRecord => ({
  TeamID: teamId, OpponentID: opponentId, Filter: filter, Wins: 1, Losses: 1, Ties: 0, PointsFor: 200, PointsAgainst: 180,
  BiggestWinMatchupID: games[0]?.FantasyMatchupID ?? null, ClosestLossMatchupID: null, Games: games
});

const model: RivalryReadModel = {
  SchemaVersion: 1, Product: 'league-rivalry', CanonicalLeagueID: 'test',
  Seasons: [{ Season: '2025' }, { Season: '2024' }],
  Records: [
    record(1, 2, 'all', [game('a', '2024', 1, 'win'), game('b', '2025', 3, 'loss')]),
    record(1, 2, 'playoffs', []),
    record(1, 3, 'all', [game('c', '2025', 5, 'win')])
  ]
};

describe('RivalryLookup', () => {
  const lookup = new RivalryLookup(model);

  it('selects generated records without recounting', () => {
    const views = lookup.recordsFor(1, 'all');
    expect(views.map(view => view.opponentId)).toEqual([2, 3]);
    expect(views[0].wins).toBe(1);
    expect(views[0].lastGame.FantasyMatchupID).toBe('b');
    expect(views[0].biggestWin?.FantasyMatchupID).toBe('a');
    expect(views[0].closestLoss).toBeNull();
  });

  it('skips records without games and unknown pairs', () => {
    expect(lookup.recordsFor(1, 'playoffs')).toEqual([]);
    expect(lookup.headToHead(1, 9)).toBeNull();
    expect(lookup.headToHead(1, 3)?.games.length).toBe(1);
  });

  it('spans the covered seasons', () => {
    expect(lookup.seasonSpan).toBe('2024–2025');
  });

  it('formats records with ties only when present', () => {
    expect(formatRivalryRecord({ wins: 3, losses: 2, ties: 0 })).toBe('3-2');
    expect(formatRivalryRecord({ wins: 3, losses: 2, ties: 1 })).toBe('3-2-1');
  });
});
