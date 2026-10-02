// CI currently enters its focused Angular regression run through this spec. Keep the
// #520 Matchups Overview regressions on that existing path without changing workflow cadence.
import '../components/league-matchups/league-matchups.spec';
import './matchups-overview-view.util.spec';

import type {
  DecisionWindow,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
import { buildDecisionWindowTeamRows } from './decision-window-view.util';
import {
  buildCurrentStandings,
  buildSeasonHistory
} from './league-standings-view.util';
import {
  buildNeutralFantasyTeamOrderIndex,
  sortFantasyTeamsByNeutralOrder
} from './fantasy-team-order.util';

describe('fantasy-team neutral ordering', () => {
  it('uses resolved All-Time Overall order instead of input or TeamID order', () => {
    const teams = [
      createTeam(1, 3, 1, 1),
      createTeam(6, 5, 2, 2),
      createTeam(3, 1, 3, 3),
      createTeam(2, 2, 4, 4)
    ];

    const ordered = sortFantasyTeamsByNeutralOrder(teams);

    expect(ordered.map(team => team.TeamID)).toEqual([3, 2, 1, 6]);
    expect([...buildNeutralFantasyTeamOrderIndex(teams).entries()]).toEqual([
      ['3', 0],
      ['2', 1],
      ['1', 2],
      ['6', 3]
    ]);
  });

  it('rejects unresolved duplicate places instead of falling back to TeamID', () => {
    const teams = [
      createTeam(1, 1, 1, 1),
      createTeam(9, 1, 2, 2)
    ];

    expect(() => sortFantasyTeamsByNeutralOrder(teams)).toThrowError(
      /neutral order is not fully resolved/i
    );
  });

  it('keeps Current Standings semantics stronger than neutral All-Time order', () => {
    const neutralFirst = createTeam(9, 1, 2, 2);
    const currentFirst = createTeam(2, 2, 1, 1);
    const league = {
      Season: '2026',
      Standings: [
        {
          Season: '2026',
          RegularSeason: [
            { TeamID: 2, Place: 1 },
            { TeamID: 9, Place: 2 }
          ]
        }
      ]
    } as unknown as League;

    const ordered = buildCurrentStandings(
      league,
      sortFantasyTeamsByNeutralOrder([currentFirst, neutralFirst])
    );

    expect(ordered.map(row => row.team.TeamID)).toEqual([2, 9]);
  });

  it('keeps Decision Window attention priority stronger than the neutral fallback', () => {
    const neutralFirst = createTeam(9, 1, 2, 2);
    const attentionFirst = createTeam(2, 2, 1, 1);
    const teams = sortFantasyTeamsByNeutralOrder([attentionFirst, neutralFirst]);
    const model = {
      TeamLineupEvaluations: [
        {
          FantasyTeamID: 9,
          State: 'ready',
          ExpectedStarterCount: 10,
          StarterCount: 10,
          OpenStarterSlots: 0,
          Issues: []
        },
        {
          FantasyTeamID: 2,
          State: 'action-required',
          ExpectedStarterCount: 10,
          StarterCount: 9,
          OpenStarterSlots: 1,
          Issues: []
        }
      ]
    } as unknown as DecisionWindowsReadModel;
    const window = {
      FantasyContextState: 'available',
      AffectedFantasyTeams: [
        {
          FantasyTeamID: 9,
          AffectedRosteredPlayerCount: 0,
          AffectedStarterCount: 0,
          Players: []
        },
        {
          FantasyTeamID: 2,
          AffectedRosteredPlayerCount: 0,
          AffectedStarterCount: 0,
          Players: []
        }
      ]
    } as unknown as DecisionWindow;

    const rows = buildDecisionWindowTeamRows(model, window, teams);

    expect(rows.map(row => row.teamId)).toEqual([2, 9]);
  });
});

describe('historical Season Archive identity', () => {
  it('uses season-specific avatars and never leaks the current team avatar into history', () => {
    const league = {
      Teams: [
        {
          TeamID: 1,
          Owner: 'Owner 1',
          Avatar: 'current-team-1.png',
          OwnerAvatar: 'current-owner-1.png'
        },
        {
          TeamID: 2,
          Owner: 'Owner 2',
          Avatar: 'current-team-2.png',
          OwnerAvatar: 'current-owner-2.png'
        }
      ],
      Standings: [
        {
          Season: '2025',
          Playoffs: [
            {
              Place: 1,
              PlaceOrdinal: '1st',
              TeamID: 1,
              Owner: 'Owner 1',
              OwnerAvatar: 'historical-owner-1.png',
              TeamName: 'Historical Team 1',
              TeamAvatar: 'historical-team-1.png'
            },
            {
              Place: 2,
              PlaceOrdinal: '2nd',
              TeamID: 2,
              Owner: 'Owner 2',
              OwnerAvatar: 'historical-owner-2.png',
              TeamName: 'Historical Team 2',
              TeamAvatar: null
            }
          ],
          RegularSeason: []
        }
      ]
    } as unknown as League;

    const history = buildSeasonHistory(league);
    const season = history.seasons[0];

    expect(season.playoffResults[0].teamAvatar).toBe('historical-team-1.png');
    expect(season.playoffResults[0].ownerAvatar).toBe('historical-owner-1.png');
    expect(season.playoffResults[1].teamAvatar).toBe('assets/default-team-avatar.png');
    expect(season.playoffResults[1].ownerAvatar).toBe('historical-owner-2.png');
    expect(season.playoffResults.map(row => row.teamAvatar)).not.toContain('current-team-1.png');
    expect(season.playoffResults.map(row => row.teamAvatar)).not.toContain('current-team-2.png');
  });
});

function createTeam(
  teamID: number,
  allTimeOverallPlace: number,
  currentRegularPlace: number,
  previousOverallPlace: number
): FantasyTeam {
  return {
    TeamID: teamID,
    Team: `Team ${teamID}`,
    TeamAbbr: `T${teamID}`,
    Owner: `Owner ${teamID}`,
    Avatar: `team-${teamID}.png`,
    OwnerAvatar: `owner-${teamID}.png`,
    Placements: {
      Current: {
        Regular: { Place: currentRegularPlace },
        Awards: []
      },
      Previous: {
        Regular: {},
        Playoffs: { Place: previousOverallPlace },
        Awards: []
      },
      AllTime: {
        Regular: {},
        Playoffs: { Place: allTimeOverallPlace },
        Awards: []
      }
    }
  } as unknown as FantasyTeam;
}
