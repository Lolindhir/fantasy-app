import type { RawTeamSeasonTeam, TeamSeasonsReadModel } from '../../core/models/team-season.models';
import { DEFAULT_TEAM_AVATAR, TeamSeasonLookup } from './team-season.service';

const team = (teamId: number, name: string, abbr: string, avatar: string | null): RawTeamSeasonTeam => ({
  TeamID: teamId, CanonicalLeagueRosterID: `r${teamId}`, CanonicalLeagueMemberID: `m${teamId}`, OwnerID: `u${teamId}`,
  Owner: `Owner ${teamId}`, OwnerAvatar: 'owner.png', TeamName: name, TeamNameSource: 'provider', TeamAbbr: abbr, TeamAvatar: avatar
});

const model: TeamSeasonsReadModel = {
  SchemaVersion: 1, Product: 'league-teams', CanonicalLeagueID: 'test', CurrentSeason: '2025',
  Seasons: [
    { Season: '2024', Teams: [team(1, 'Old Name', 'OLD', null)] },
    { Season: '2025', Teams: [team(1, 'New Name', 'NEW', 'new.png')] }
  ]
};

describe('TeamSeasonLookup', () => {
  const lookup = new TeamSeasonLookup(model);

  it('returns the identity of exactly the requested season', () => {
    expect(lookup.identity(2024, 1)?.Team).toBe('Old Name');
    expect(lookup.identity('2025', '1')?.TeamAbbr).toBe('NEW');
  });

  it('uses the neutral default logo for a season without a logo, never a later one', () => {
    expect(lookup.identity(2024, 1)?.Avatar).toBe(DEFAULT_TEAM_AVATAR);
    expect(lookup.identity(2025, 1)?.Avatar).toBe('new.png');
  });

  it('keeps manager and team fields separate and returns null for unknown season or team', () => {
    const identity = lookup.identity(2025, 1);
    expect(identity?.Owner).toBe('Owner 1');
    expect(identity?.OwnerAvatar).toBe('owner.png');
    expect(identity?.Avatar).toBe('new.png');
    expect(lookup.identity(2023, 1)).toBeNull();
    expect(lookup.identity(2025, 9)).toBeNull();
  });
});
