import type { FantasyTeam, League } from '../../core/models/league.models';
import {
  buildSeasonHistory,
  buildSeasonResults,
  getCurrentSeasonAwards
} from './league-standings-view.util';

const award = (name: string, teamId: number) => ({
  Name: name,
  TeamID: teamId,
  Owner: 'Owner ' + teamId,
  TeamName: 'Team ' + teamId,
  Type: { Name: 'Special', DisplayText: 'Special', Order: 1 },
  IconUnicode: '1F3AF',
  Icon: '🎯',
  StatDisplay: 'A season statistic'
});

function league(isFinished: boolean): League {
  return {
    Season: '2025',
    IsFinished: isFinished,
    Standings: [{
      Season: '2025',
      Playoffs: isFinished ? [
        { TeamID: 2, Place: 1, PlaceOrdinal: '1st', Owner: 'Owner 2', TeamName: 'Team 2', TeamAvatar: 'team-2.png' },
        { TeamID: 4, Place: 4, PlaceOrdinal: '4th', Owner: 'Owner 4', TeamName: 'Team 4', TeamAvatar: 'historic-team-4.png', OwnerAvatar: 'historic-owner-4.png' }
      ] : null,
      RegularSeason: [
        { TeamID: 4, Place: 1, PlaceOrdinal: '1st', Owner: 'Owner 4', TeamName: 'Team 4', Wins: 10, Losses: 3, Points: 2472.16 },
        { TeamID: 2, Place: 2, PlaceOrdinal: '2nd', Owner: 'Owner 2', TeamName: 'Team 2', Wins: 9, Losses: 4, Points: 2200 }
      ],
      Awards: [award('Regular Season King', 4), award('Clutch Peaker', 2)]
    }]
  } as unknown as League;
}

function team(id: number, playoffPlace: number): FantasyTeam {
  return {
    TeamID: id,
    Team: 'Team ' + id,
    Owner: 'Owner ' + id,
    OwnerAvatar: 'owner-' + id + '.png',
    Avatar: 'team-' + id + '.png',
    Placements: {
      Previous: {
        Playoffs: { Place: playoffPlace, PlaceOrdinal: playoffPlace + 'th' }
      }
    }
  } as unknown as FantasyTeam;
}

describe('Regular Season Champion achievement', () => {
  it('uses the season placement and historical TeamID avatar snapshot, not award names', () => {
    const history = buildSeasonHistory(league(true)).seasons[0];

    expect(history.regularSeasonWinner?.teamId).toBe(4);
    expect(history.regularSeasonWinner?.record).toBe('10-3');
    expect(history.regularSeasonWinner?.points).toBe(2472.16);
    expect(history.regularSeasonWinner?.teamAvatar).toBe('historic-team-4.png');
    expect(history.regularSeasonWinner?.ownerAvatar).toBe('historic-owner-4.png');
    expect(history.awards.map(row => row.name)).toEqual(['Clutch Peaker']);

    const outcome = buildSeasonResults([team(2, 1), team(4, 4)], league(true));
    expect(outcome.regularSeasonChampion?.teamId).toBe(4);
    expect(outcome.regularSeasonChampion?.record).toBe('10-3');
    expect(outcome.remainingTeams.find(row => row.teamId === 4)?.isRegularSeasonChampion).toBeTrue();
    expect(outcome.champion?.isRegularSeasonChampion).toBeFalse();
  });

  it('does not award a completed-season title while the season is still running', () => {
    const outcome = buildSeasonResults([team(2, 1), team(4, 4)], league(false));

    expect(outcome.regularSeasonChampion).toBeUndefined();
    expect(outcome.teams.some(row => row.isRegularSeasonChampion)).toBeFalse();
  });

  it('filters only the legacy placement award, leaving other special/dynamic awards intact', () => {
    expect(getCurrentSeasonAwards(league(true)).map(row => row.Name)).toEqual(['Clutch Peaker']);
  });
});
