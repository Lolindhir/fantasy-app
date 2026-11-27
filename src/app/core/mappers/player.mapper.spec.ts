import type { GameHistory, RawNFLTeam, RawPlayer } from '../models/player.models';
import { mapRawPlayerToPlayer, type PlayerMappingContext } from './player.mapper';

describe('player mapper NFL team resolution', () => {
  const nflTeams: RawNFLTeam[] = [
    { ID: 'AAA', Name: 'Alphas', Abv: 'AAA', Logo: 'aaa.png', LegacyIDs: ['7'] },
    { ID: '12', Name: 'Legacy Keyed', Abv: 'LKY', Logo: 'lky.png' }
  ];
  const context: PlayerMappingContext = {
    nflTeams,
    seasonYear: 2026,
    currentWeek: 1,
    playoffStartWeek: 15,
    lastWeek: 18
  };

  function makeRawPlayer(teamId: string, isFreeAgent = false): RawPlayer {
    return {
      ID: 'p1',
      NameFirst: 'Test',
      NameLast: 'Player',
      TeamID: teamId,
      IsFreeAgent: isFreeAgent,
      Number: '1',
      PointHistory: {
        SeasonMinus1: { Season: 0 },
        SeasonMinus2: { Season: 0 },
        SeasonMinus3: { Season: 0 }
      },
      Ranking: []
    } as unknown as RawPlayer;
  }

  it('resolves the NFL team by current ID and by legacy ID', () => {
    expect(mapRawPlayerToPlayer(makeRawPlayer('AAA'), context).TeamNFL.Name).toBe('Alphas');
    expect(mapRawPlayerToPlayer(makeRawPlayer('7'), context).TeamNFL.Name).toBe('Alphas');
    expect(mapRawPlayerToPlayer(makeRawPlayer('12'), context).TeamNFL.Name).toBe('Legacy Keyed');
  });

  it('falls back to a neutral team instead of crashing for an unknown team reference', () => {
    const player = mapRawPlayerToPlayer(makeRawPlayer('ZZZ'), context);

    expect(player.TeamNFL.ID).toBe('ZZZ');
    expect(player.TeamNFL.Name).toBe('Unknown team');
    expect(player.TeamNFL.Logo).toBeTruthy();
  });

  it('distinguishes missing game history from recorded zero and negative points', () => {
    const raw = makeRawPlayer('AAA');
    const game = (week: number, points: number): GameHistory => ({
      GameID: `game-${week}`,
      TeamID: 'AAA',
      TeamAbv: 'AAA',
      GameDetails: {
        Week: week, WeekFinal: true, WeekScored: true, WeekPlayoff: false,
        Date: '', Home: 'AAA', HomeID: 'AAA', Away: 'BBB', AwayID: 'BBB',
        HomePoints: 0, AwayPoints: 0
      },
      FantasyPoints: points,
      SnapCount: 1,
      SnapPercentage: 1,
      Attempts: 0
    });
    const zero = game(1, 0);
    const negative = game(3, -2.5);
    raw.GameHistory = [zero, negative];
    const player = mapRawPlayerToPlayer(raw, { ...context, currentWeek: 3 });

    expect(player.GameHistory).toBe(raw.GameHistory);
    expect(player.GameHistoryFull?.map(row => [row.Week, row.Game?.FantasyPoints ?? null]))
      .toEqual([[1, 0], [2, null], [3, -2.5]]);
    expect(player.GameHistoryFull?.[0].Game).toBe(zero);
    expect(player.GameHistoryFull?.[1].Game).toBeNull();
    expect(player.GameHistoryFull?.[2].Game).toBe(negative);
  });

  it('keeps absent raw history absent and provides only missing display rows', () => {
    const raw = makeRawPlayer('AAA');
    const player = mapRawPlayerToPlayer(raw, { ...context, currentWeek: 2 });
    expect(player.GameHistory).toBeUndefined();
    expect(player.GameHistoryFull?.map(row => row.Game)).toEqual([null, null]);
  });

  it('keeps the free-agent team for free agents regardless of their team reference', () => {
    expect(mapRawPlayerToPlayer(makeRawPlayer('AAA', true), context).TeamNFL.ID).toBe('FA');
  });
});
