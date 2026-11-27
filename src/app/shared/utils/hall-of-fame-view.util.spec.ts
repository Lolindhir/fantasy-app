import type { Player } from '../../core/models/player.models';
import type { PlayerAwardHistoryReadModel } from '../../core/models/player-award-history.models';
import type { LeagueRecordsReadModel } from '../../core/models/league-records.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
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

  it('preserves published tied leaders, joins by player ID and uses historical portrait fallback', () => {
    const history = { Leaders: { MVP: [
      { PlayerID: 'a', Name: 'First', Count: 4 },
      { PlayerID: 'b', Name: 'Second', Count: 4 },
      { PlayerID: 'c', Name: 'Third', Count: 4 }
    ] }, Players: [{ PlayerID: 'b', Picture: 'historic.png' }] } as unknown as PlayerAwardHistoryReadModel;
    const current = [{ ID: 'a', Name: 'Different display name', Picture: 'current.png', TeamNFL: { Logo: 'nfl.png', Abv: 'NYG' } }] as unknown as Player[];
    const [award] = buildHallOfFameSections(leagueWith([], '2026', false), [], null, history, current).playerLegends;
    expect(award.valueDisplay).toBe('4×');
    expect(award.players?.map(player => player.name)).toEqual(['First', 'Second', 'Third']);
    expect(award.players?.map(player => player.picture)).toEqual(['current.png', 'historic.png', null]);
    expect(award.players?.[0].teamLogo).toBe('nfl.png');
    expect(award.players?.[1].player).toBeNull();
  });

  it('uses the historical identity for a historical upset, not a current team logo', () => {
    const records = { CanonicalLeagueID: 'l', Records: { BiggestUpset: { Season: 2024, Week: 3, WinnerTeamID: 1, LoserTeamID: 2,
      WinnerPoints: 100, LoserPoints: 90, WinnerPregameWinProbability: 0.1,
      WinnerCanonicalLeagueRosterID: 'r', LoserCanonicalLeagueRosterID: 'r2' } } } as LeagueRecordsReadModel;
    const standings = [{ Season: '2024', Playoffs: [playoff(2, 2, 'Other Team', null)] }];
    const [award] = buildHallOfFameSections(leagueWith(standings, '2026', false), [], records, null, [], new TeamSeasonLookup(teamSeasons)).bests;
    expect(award.team?.Team).toBe('Season Team');
    expect(award.team?.Avatar).toBe('assets/default-team-avatar.png');
    expect(award.valueDisplay).toBe('10% win chance');
    expect(award.upset?.winner.team.Team).toBe('Season Team');
    expect(award.upset?.loser.team.Team).toBe('Other Team');
    expect(award.upset?.loser.team.Avatar).toBe('assets/default-team-avatar.png');
    expect(award.upset?.winner.points).toBe(100);
    expect(award.upset?.loser.points).toBe(90);
    expect(award.upset?.season).toBe('2024');
    expect(award.upset?.week).toBe(3);
    expect(award.upset?.pregameProbability).toBe(0.1);
  });

  it('requires canonical roster identity and matching current manager before linking a record', () => {
    const records = { CanonicalLeagueID: 'l', Records: { BiggestUpset: { Season: 2026, Week: 3, WinnerTeamID: 1, LoserTeamID: 2,
      WinnerPoints: 100, LoserPoints: 90, WinnerPregameWinProbability: 0.1,
      WinnerCanonicalLeagueRosterID: 'r-current', LoserCanonicalLeagueRosterID: 'r2' } } } as LeagueRecordsReadModel;
    const snapshot = { ...teamSeasons.Seasons[0].Teams[0], CanonicalLeagueRosterID: 'r-current', TeamName: 'Current snapshot' };
    const lookup = new TeamSeasonLookup({ ...teamSeasons, Seasons: [...teamSeasons.Seasons, { Season: '2026', Teams: [snapshot] }] });
    const current = [{ TeamID: 1, OwnerID: 'o', Team: 'Current team',
      Placements: { AllTime: { Playoffs: { Place: 999 }, Regular: { Place: 999 } } } }] as unknown as FantasyTeam[];
    const league = leagueWith([], '2026', false);
    const side = (input: LeagueRecordsReadModel, teams = current, evidence = lookup) =>
      buildHallOfFameSections(league, teams, input, null, [], evidence).bests[0].upset!.winner;
    expect(side(records).interactive).toBeTrue();
    expect(side(records).team.Team).toBe('Current snapshot');
    expect(side(records, [{ ...current[0], OwnerID: 'new-manager' }]).interactive).toBeFalse();
    const conflict = { ...records, Records: { BiggestUpset: { ...records.Records.BiggestUpset!, WinnerCanonicalLeagueRosterID: 'wrong-roster' } } };
    expect(side(conflict).interactive).toBeFalse();
    expect(side(conflict).team.Team).toBe('Team 1');
    expect(side({ ...records, CanonicalLeagueID: 'other-league' }).team.Team).toBe('Team 1');
    const historical = { ...records, Records: { BiggestUpset: { ...records.Records.BiggestUpset!, Season: 2024, WinnerCanonicalLeagueRosterID: 'r' } } };
    expect(side(historical).team.Team).toBe('Season Team');
    expect(side(historical).interactive).toBeFalse();
  });

  it('uses the current team identity for season-spanning team awards', () => {
    const league = leagueWith([{ Season: 'AllTime', LegacyHighlights: [{ Key: 'ChampOfChamps', TeamID: 1 }] }], '2026', false);
    const teams = [{ TeamID: 1, Team: 'Renamed Team', Owner: 'Manager One', OwnerAvatar: 'manager.png', Avatar: 'team.png', Placements: { AllTime: { Playoffs: { Place: 999 }, Regular: { Place: 999 } } } }] as unknown as FantasyTeam[];
    const [award] = buildHallOfFameSections(league, teams, null, null).legacy;
    expect(award.team?.Team).toBe('Renamed Team');
    expect(award.title).toBe('All-Time Leader');
    expect(award.valueDisplay).toBe('#1 Overall standings');
    expect(award.team?.Avatar).toBe('team.png');
  });

  it('does not manufacture a record when the shared product has no qualifying upset', () => {
    const records = { Records: { BiggestUpset: null } } as LeagueRecordsReadModel;
    expect(buildHallOfFameSections(leagueWith([], '2026', false), [], records, null).bests).toEqual([]);
  });

  it('builds empty sections when nothing is available', () => {
    const sections = buildHallOfFameSections(leagueWith([], '2026', false), [], null, null);
    expect(sections).toEqual({ legacy: [], bests: [], playerLegends: [] });
  });
});
