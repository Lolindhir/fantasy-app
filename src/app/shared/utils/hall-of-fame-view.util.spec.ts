import type { League } from '../../core/models/league.models';
import type { TeamSeasonsReadModel } from '../../core/models/team-season.models';
import { TeamSeasonLookup } from '../services/team-season.service';
import { buildHallOfFameChampions, buildHallOfFameSections } from './hall-of-fame-view.util';

function playoff(teamId: number, place: number, teamName: string, teamAvatar: string | null) {
  return { TeamID: teamId, Place: place, PlaceOrdinal: `${place}.`, Owner: `Owner ${teamId}`, TeamName: teamName, OwnerAvatar: null, TeamAvatar: teamAvatar };
}

function season(name: string, championId: number | null, regularWinnerId: number) {
  return {
    Season: name,
    Playoffs: championId === null ? [] : [playoff(championId, 1, `Old ${championId}`, 'old.png'), playoff(2, 2, 'Second', null)],
    RegularSeason: [{ TeamID: regularWinnerId, Place: 1, PlaceOrdinal: '1.', Owner: `Owner ${regularWinnerId}`, TeamName: 'x', Wins: 10, Losses: 4, Ties: 0, Points: 1, PointsAgainst: 1, WinPercentageDisplay: '' }],
    Awards: []
  };
}

function leagueWith(standings: unknown[], current: string, finished: boolean): League {
  return { Season: current, IsFinished: finished, Standings: standings } as unknown as League;
}

const teamSeasons: TeamSeasonsReadModel = {
  SchemaVersion: 1,
  Product: 'league-teams',
  CanonicalLeagueID: 'l',
  CurrentSeason: '2026',
  Seasons: [{
    Season: '2024',
    Teams: [{
      TeamID: 1, CanonicalLeagueRosterID: 'r', CanonicalLeagueMemberID: 'm', OwnerID: 'o', Owner: 'Season Owner', OwnerAvatar: 'owner.png',
      TeamName: 'Season Team', TeamNameSource: 'provider', TeamAbbr: 'SEA', TeamAvatar: null
    }]
  }]
};

describe('hall of fame view util', () => {
  it('lists decided champions newest first and skips running and undecided seasons', () => {
    const league = leagueWith([season('2026', 1, 1), season('2025', 3, 3), season('2024', 1, 2), season('2023', null, 1), season('AllTime', 1, 1)], '2026', false);
    expect(buildHallOfFameChampions(league, null).map(c => c.season)).toEqual(['2025', '2024']);
  });

  it('counts the current season once the league is finished', () => {
    const league = leagueWith([season('2026', 1, 1), season('2025', 3, 3)], '2026', true);
    expect(buildHallOfFameChampions(league, null).map(c => c.season)).toEqual(['2026', '2025']);
  });

  it('shows the identity of the season from the team identity product, with the neutral default logo and no fallback to a later season', () => {
    const league = leagueWith([season('2024', 1, 2), season('2025', 3, 3)], '2026', false);
    const [y2025, y2024] = buildHallOfFameChampions(league, new TeamSeasonLookup(teamSeasons));
    expect(y2024.teamName).toBe('Season Team');
    expect(y2024.owner).toBe('Season Owner');
    expect(y2024.teamAvatar).toBe('assets/default-team-avatar.png');
    expect(y2024.ownerAvatar).toBe('owner.png');
    expect(y2024.isRegularSeasonChampion).toBe(false);
    expect(y2024.ringSrc).toBe('assets/awards/rings/2024.png');
    // Season unknown to the product: the standings snapshot of that season is shown.
    expect(y2025.teamName).toBe('Old 3');
    expect(y2025.isRegularSeasonChampion).toBe(true);
  });

  it('builds empty sections when nothing is available', () => {
    const sections = buildHallOfFameSections(leagueWith([], '2026', false), [], null, new Map(), null);
    expect(sections).toEqual({ legacy: [], bests: [], playerLegends: [] });
  });
});
