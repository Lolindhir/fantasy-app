import type { RawTeamSeasonTeam, TeamSeasonsReadModel } from '../../core/models/team-season.models';
import type { FantasyTeam } from '../../core/models/league.models';
import { DEFAULT_TEAM_AVATAR, TeamSeasonLookup, teamsWithSeasonIdentity } from './team-season.service';

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

  it('provides unique season roster and league witnesses for canonical joins', () => {
    expect(lookup.canonicalLeagueID).toBe('test');
    expect(lookup.roster('2024', 1)?.CanonicalLeagueRosterID).toBe('r1');
    expect(lookup.roster('2024', 9)).toBeNull();
    const duplicate = new TeamSeasonLookup({ ...model, Seasons: [
      { Season: '2024', Teams: [team(1, 'A', 'A', null), team(1, 'B', 'B', null)] }
    ] });
    expect(duplicate.roster('2024', 1)).toBeNull();
    expect(duplicate.identity('2024', 1)).toBeNull();
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

describe('teamsWithSeasonIdentity', () => {
  const lookup = new TeamSeasonLookup(model);
  const current = [{ TeamID: 1, Team: 'New Name', TeamAbbr: 'NEW', Avatar: 'new.png', Owner: 'Now', Wins: 3 }, { TeamID: 9, Team: 'Other', Avatar: 'o.png' }] as unknown as FantasyTeam[];

  it('overlays only identity fields of the requested past season', () => {
    const [team, unknown] = teamsWithSeasonIdentity(current, lookup, '2024');
    expect(team.Team).toBe('Old Name');
    expect(team.TeamAbbr).toBe('OLD');
    expect(team.Avatar).toBe(DEFAULT_TEAM_AVATAR);
    expect(team.Wins).toBe(3);
    expect(unknown.Team).toBe('Other');
  });

  it('keeps the current identity for the current season, a missing lookup and an unknown season', () => {
    expect(teamsWithSeasonIdentity(current, lookup, 2025)[0].Team).toBe('New Name');
    expect(teamsWithSeasonIdentity(current, null, '2024')[0].Team).toBe('New Name');
    expect(teamsWithSeasonIdentity(current, lookup, '2020')[0].Team).toBe('New Name');
  });
});
