import type { RawNFLTeam, RawPlayer } from '../models/player.models';
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

  it('keeps the free-agent team for free agents regardless of their team reference', () => {
    expect(mapRawPlayerToPlayer(makeRawPlayer('AAA', true), context).TeamNFL.ID).toBe('FA');
  });
});
