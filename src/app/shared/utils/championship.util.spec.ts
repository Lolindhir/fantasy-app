import type { Standing } from '../../core/models/fantasy.models';
import {
  GENERIC_CHAMPIONSHIP_RING_SRC,
  buildTrophyRoom,
  getDefendingChampionTeamId,
  getLatestChampionSeason,
  getSeasonRingSrc,
  DEFAULT_TEAM_AVATAR_SRC
} from './championship.util';

function playoff(place: number, teamId: number, extra: Record<string, unknown> = {}) {
  return {
    Place: place,
    PlaceOrdinal: `${place}`,
    TeamID: teamId,
    Owner: `Owner ${teamId}`,
    OwnerAvatar: `owner-${teamId}-s`,
    TeamName: `Team ${teamId} S`,
    TeamAvatar: `avatar-${teamId}-s`,
    ...extra
  };
}

function standing(season: string, playoffs: ReturnType<typeof playoff>[], regularWinner?: number): Standing {
  return {
    Season: season,
    Playoffs: playoffs,
    RegularSeason: regularWinner === undefined
      ? []
      : [{ Place: 1, PlaceOrdinal: '1st', TeamID: regularWinner, Owner: `Owner ${regularWinner}`, TeamName: `Team ${regularWinner} RS` }]
  };
}

describe('championship util', () => {
  const standings: Standing[] = [
    standing('AllTime', [playoff(1, 9)]),
    standing('2026', []),
    standing('2025', [playoff(1, 3), playoff(2, 2), playoff(3, 4)], 3),
    standing('2024', [playoff(1, 7, { TeamName: 'Old Name', TeamAvatar: 'old-avatar' }), playoff(2, 3)], 3)
  ];

  it('keeps the last champion defending while the new season is running', () => {
    expect(getLatestChampionSeason(standings, '2026', false)).toBe('2025');
    expect(getDefendingChampionTeamId(standings, '2026', false)).toBe('3');
  });

  it('ignores the AllTime pseudo season and an undecided current playoff', () => {
    const running = [...standings, standing('2027', [playoff(0, 1)])];
    expect(getDefendingChampionTeamId(running, '2027', false)).toBe('3');
  });

  it('crowns the new champion once the current season is finished', () => {
    const finished = standings.map(s => s.Season === '2026' ? standing('2026', [playoff(1, 2)]) : s);
    expect(getDefendingChampionTeamId(finished, '2026', true)).toBe('2');
    expect(getDefendingChampionTeamId(finished, '2026', false)).toBe('3');
  });

  it('returns null without any decided champion', () => {
    expect(getDefendingChampionTeamId([standing('2026', [])], '2026', false)).toBeNull();
  });

  it('builds rings, banners and plaques with the historical season identity', () => {
    const room = buildTrophyRoom({ Standings: standings, Season: '2026', IsFinished: false }, { TeamID: 3 });

    expect(room.rings.map(r => r.season)).toEqual(['2025']);
    expect(room.banners.map(b => [b.season, b.place])).toEqual([['2025', 1], ['2024', 2]]);
    expect(room.banners[0].teamAvatar).toBe('avatar-3-s');
    expect(room.plaques.map(p => p.season)).toEqual(['2025', '2024']);
  });

  it('does not mix the current team identity into old seasons', () => {
    const room = buildTrophyRoom({ Standings: standings, Season: '2026', IsFinished: false }, { TeamID: 7 });
    expect(room.banners[0].teamName).toBe('Old Name');
    expect(room.banners[0].teamAvatar).toBe('old-avatar');
  });

  it('falls back to the default team logo like the Standings when a season has no stored logo', () => {
    const noLogo = [standing('2024', [playoff(1, 5, { TeamAvatar: '' }), playoff(2, 3)], 5)];
    const room = buildTrophyRoom({ Standings: noLogo, Season: '2026', IsFinished: false }, { TeamID: 5 });
    expect(room.banners[0].teamAvatar).toBe(DEFAULT_TEAM_AVATAR_SRC);
    expect(room.plaques[0].teamAvatar).toBe(DEFAULT_TEAM_AVATAR_SRC);
  });

  it('uses the season ring path contract and a generic fallback constant', () => {
    expect(getSeasonRingSrc(2025)).toBe('assets/awards/rings/2025.png');
    expect(GENERIC_CHAMPIONSHIP_RING_SRC).toBe('assets/awards/ui/award-championship-ring.png');
  });
});
