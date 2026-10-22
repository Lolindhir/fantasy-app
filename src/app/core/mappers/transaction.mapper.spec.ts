import type { FantasyTeam } from '../models/league.models';
import type { Player } from '../models/player.models';
import type { RawTransaction } from '../models/transaction.models';
import { mapRawTransaction, mapRawTransactions } from './transaction.mapper';

describe('transaction.mapper', () => {
  const teamOne = {
    TeamID: 1,
    Team: 'Team One',
    TeamAbbr: 'ONE',
    Owner: 'Owner One'
  } as FantasyTeam;
  const teamTwo = {
    TeamID: 2,
    Team: 'Team Two',
    TeamAbbr: 'TWO',
    Owner: 'Owner Two'
  } as FantasyTeam;
  const playerOne = {
    ID: 'player-1',
    Name: 'Player One'
  } as Player;
  const playerTwo = {
    ID: 'player-2',
    Name: 'Player Two'
  } as Player;

  it('maps player and draft-pick movement for every participant', () => {
    const transaction = mapRawTransaction(createRawTransaction({
      RosterIDs: [1, 2],
      Adds: {
        'player-1': 2,
        'player-2': 1
      },
      Drops: {
        'player-1': 1,
        'player-2': 2
      },
      DraftPicks: [
        {
          DraftType: 'Rookie',
          DraftKey: '2027_Rookie',
          Season: '2027',
          Round: 2,
          OriginalOwnerRosterID: 1,
          PreviousOwnerRosterID: 1,
          NewOwnerRosterID: 2
        }
      ]
    }), [teamOne, teamTwo], [playerOne, playerTwo]);

    expect(transaction.Participants.length).toBe(2);

    const participantOne = transaction.Participants[0];
    expect(participantOne.Team).toBe(teamOne);
    expect(participantOne.AddedPlayers.map(asset => asset.Player)).toEqual([playerTwo]);
    expect(participantOne.DroppedPlayers.map(asset => asset.Player)).toEqual([playerOne]);
    expect(participantOne.SentDraftPicks.length).toBe(1);

    const participantTwo = transaction.Participants[1];
    expect(participantTwo.Team).toBe(teamTwo);
    expect(participantTwo.AddedPlayers.map(asset => asset.Player)).toEqual([playerOne]);
    expect(participantTwo.DroppedPlayers.map(asset => asset.Player)).toEqual([playerTwo]);
    expect(participantTwo.AcquiredDraftPicks[0].PreviousOwner).toBe(teamOne);
    expect(participantTwo.AcquiredDraftPicks[0].NewOwner).toBe(teamTwo);
  });

  it('keeps same-round pick swaps distinct by original owner', () => {
    const transaction = mapRawTransaction(createRawTransaction({
      RosterIDs: [1, 2],
      DraftPicks: [
        {
          DraftType: 'Rookie',
          DraftKey: '2026_Rookie',
          Season: '2026',
          Round: 2,
          OriginalOwnerRosterID: 1,
          PreviousOwnerRosterID: 1,
          NewOwnerRosterID: 2
        },
        {
          DraftType: 'Rookie',
          DraftKey: '2026_Rookie',
          Season: '2026',
          Round: 2,
          OriginalOwnerRosterID: 2,
          PreviousOwnerRosterID: 2,
          NewOwnerRosterID: 1
        }
      ]
    }), [teamOne, teamTwo], []);

    const participantOne = transaction.Participants.find(participant => participant.RosterID === 1);
    const participantTwo = transaction.Participants.find(participant => participant.RosterID === 2);

    expect(participantOne?.AcquiredDraftPicks.map(pick => pick.OriginalOwnerRosterID)).toEqual([2]);
    expect(participantOne?.SentDraftPicks.map(pick => pick.OriginalOwnerRosterID)).toEqual([1]);
    expect(participantTwo?.AcquiredDraftPicks.map(pick => pick.OriginalOwnerRosterID)).toEqual([1]);
    expect(participantTwo?.SentDraftPicks.map(pick => pick.OriginalOwnerRosterID)).toEqual([2]);
  });

  it('keeps unresolved assets and discovers roster ids outside RosterIDs', () => {
    const transaction = mapRawTransaction(createRawTransaction({
      RosterIDs: [],
      Adds: { missing: '3' },
      Drops: {},
      DraftPicks: []
    }), [], []);

    expect(transaction.RosterIDs).toEqual([3]);
    expect(transaction.Participants[0].AddedPlayers[0]).toEqual({
      PlayerID: 'missing',
      Player: undefined
    });
  });

  it('keeps Tyreek Hill history when the current Players list omits him', () => {
    const historical = { Name: 'Tyreek Hill', Position: 'WR', Picture: '/historical-tyreek.png' };
    const transaction = mapRawTransaction(createRawTransaction({
      RosterIDs: [3], Drops: { '3321': 3 }, PlayerRefs: { '3321': historical }
    }), [], []);
    expect(transaction.Participants[0].DroppedPlayers[0]).toEqual({
      PlayerID: '3321', Player: undefined, PlayerRef: historical
    });
  });

  it('does not invent identities for unknown historical players', () => {
    const transaction = mapRawTransaction(createRawTransaction({
      RosterIDs: [3], Drops: { unknown: 3 }, PlayerRefs: {}
    }), [], []);
    expect(transaction.Participants[0].DroppedPlayers[0]).toEqual({
      PlayerID: 'unknown', Player: undefined
    });
  });

  it('orders by effective status time rather than waiver submission time', () => {
    const completedWaiver = createRawTransaction({
      TransactionID: 'waiver',
      CreatedAt: 1792268727874,
      CreatedDate: '2026-10-17',
      EffectiveAt: 1792317947771
    });
    const sameDayCut = createRawTransaction({
      TransactionID: 'cut',
      CreatedAt: 1792312508118,
      CreatedDate: '2026-10-18',
      EffectiveAt: 1792312508118
    });
    const ordered = mapRawTransactions([sameDayCut, completedWaiver], [], []);
    expect(ordered.map(transaction => transaction.TransactionID)).toEqual(['waiver', 'cut']);
    expect(ordered[0].EffectiveAtDate?.toISOString()).toBe('2026-10-18T10:05:47.771Z');
    expect(ordered[0].CreatedAtDate?.toISOString()).toBe('2026-10-17T20:25:27.874Z');
    const legacy = mapRawTransaction(createRawTransaction({ EffectiveAt: undefined }), [], []);
    expect(legacy.EffectiveAt).toBe(legacy.CreatedAt);
  });

  it('sorts mapped transactions newest first', () => {
    const older = createRawTransaction({
      TransactionID: 'older',
      CreatedAt: 100
    });
    const newer = createRawTransaction({
      TransactionID: 'newer',
      CreatedAt: 200
    });

    const mapped = mapRawTransactions([older, newer], [], []);

    expect(mapped.map(transaction => transaction.TransactionID)).toEqual(['newer', 'older']);
  });

  function createRawTransaction(
    overrides: Partial<RawTransaction> = {}
  ): RawTransaction {
    return {
      Source: 'Sleeper',
      TransactionID: 'transaction-1',
      Type: 'trade',
      Status: 'complete',
      Season: '2026',
      Week: 1,
      CreatedAt: 1781261326971,
      CreatedDate: '2026-06-12',
      RosterIDs: [1, 2],
      Adds: {},
      Drops: {},
      DraftPicks: [],
      Notes: null,
      ...overrides
    };
  }
});
