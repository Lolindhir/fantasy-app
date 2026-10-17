import type { Player } from '../../../core/models/player.models';
import type { TransactionParticipant, TransactionDraftPick } from '../../../core/models/transaction.models';
import { getTransactionCardAssets } from './transaction-card.presenter';

describe('transaction-card presenter', () => {
  const participant: TransactionParticipant = {
    RosterID: 1,
    AddedPlayers: [{ PlayerID: 'incoming-player' }],
    DroppedPlayers: [{ PlayerID: 'outgoing-player' }],
    AcquiredDraftPicks: [{
      DraftType: 'free_agent', DraftKey: '2028_FA', Season: '2028', Round: 4,
      OriginalOwnerRosterID: 2, PreviousOwnerRosterID: 2, NewOwnerRosterID: 1
    } as TransactionDraftPick],
    SentDraftPicks: []
  };

  it('preserves an add with a simultaneous drop as one participant, with both directions', () => {
    expect(getTransactionCardAssets(participant, 'incoming').map(asset => asset.label)).toEqual([
      'Player incoming-player', '2028 FA · R4'
    ]);
    expect(getTransactionCardAssets(participant, 'outgoing').map(asset => asset.label)).toEqual([
      'Player outgoing-player'
    ]);
  });

  it('retains the original owner and unknown-player fallback instead of inventing identity', () => {
    const received = getTransactionCardAssets(participant, 'incoming');
    expect(received[0].player).toBeUndefined();
    expect(received[1].originalOwner).toBe('Team 2');
    expect(received[1].secondary).toBe('Original: Team 2');
  });

  it('keeps portrait, natural position and NFL identity together for immediate recognition', () => {
    const player = {
      Name: 'Darius Cooper',
      Picture: '/player.png',
      Position: 'WR',
      TeamNFL: { Abv: 'PHI', Logo: '/eagles.svg' }
    } as Player;
    const withIdentifiedPlayer: TransactionParticipant = {
      ...participant,
      AddedPlayers: [{ PlayerID: 'resolved', Player: player }]
    };

    const [asset] = getTransactionCardAssets(withIdentifiedPlayer, 'incoming');

    expect(asset.label).toBe('Darius Cooper');
    expect(asset.portrait).toBe('/player.png');
    expect(asset.position).toBe('WR');
    expect(asset.nflTeamAbv).toBe('PHI');
    expect(asset.nflTeamLogo).toBe('/eagles.svg');
  });
});
