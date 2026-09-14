import type {
  DecisionWindow,
  DecisionWindowsReadModel
} from '../../core/models/decision-window.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
import { buildDecisionWindowTeamRows } from './decision-window-view.util';
import { buildCurrentStandings } from './league-standings-view.util';
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
