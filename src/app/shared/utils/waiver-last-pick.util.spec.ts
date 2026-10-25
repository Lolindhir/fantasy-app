import type { Transaction } from '../../core/models/transaction.models';
import { buildLastWaiverPickByTeam } from './waiver-last-pick.util';

describe('buildLastWaiverPickByTeam', () => {
  it('uses the latest successful waiver processing date, not the claim submission date', () => {
    const transactions = [
      makeTransaction(1, 1791972330619, { CreatedAt: 1791900000000 }),
      makeTransaction(1, 1792922698543, { CreatedAt: 1791000000000 }),
      makeTransaction(2, 1792317947771)
    ];

    expect(buildLastWaiverPickByTeam(transactions, '2026')).toEqual({
      1: 1792922698543,
      2: 1792317947771
    });
  });

  it('ignores failed claims, free-agent pickups, drops only and other seasons', () => {
    const transactions = [
      makeTransaction(1, 100),
      makeTransaction(1, 200, { Status: 'failed' }),
      makeTransaction(1, 300, { Type: 'free_agent' }),
      makeTransaction(1, 400, { Participants: [{
        RosterID: 1, AddedPlayers: [], DroppedPlayers: [],
        AcquiredDraftPicks: [], SentDraftPicks: []
      }] }),
      makeTransaction(1, 500, { Season: '2025' }),
      makeTransaction(3, 800, { Status: 'failed' })
    ];

    expect(buildLastWaiverPickByTeam(transactions, '2026')).toEqual({ 1: 100 });
  });

  it('assigns an acquisition only to the participant actually receiving a player', () => {
    const transactions = [makeTransaction(1, 100, {
      Participants: [
        { RosterID: 1, AddedPlayers: [], DroppedPlayers: [], AcquiredDraftPicks: [], SentDraftPicks: [] },
        { RosterID: 2, AddedPlayers: [{ PlayerID: '42' }], DroppedPlayers: [], AcquiredDraftPicks: [], SentDraftPicks: [] }
      ]
    })];

    expect(buildLastWaiverPickByTeam(transactions, '2026')).toEqual({ 2: 100 });
  });

  it('does not create a pick for teams without one or for invalid timestamps', () => {
    const transactions = [
      makeTransaction(1, NaN),
      makeTransaction(2, 0),
      makeTransaction(3, 100)
    ];

    expect(buildLastWaiverPickByTeam(transactions, '2026')).toEqual({ 3: 100 });
  });
});

function makeTransaction(
  teamId: number,
  effectiveAt: number,
  overrides: Partial<Transaction> = {}
): Transaction {
  return {
    Season: '2026',
    Type: 'waiver',
    Status: 'complete',
    CreatedAt: 1,
    EffectiveAt: effectiveAt,
    Participants: [{
      RosterID: teamId,
      AddedPlayers: [{ PlayerID: 'player' }],
      DroppedPlayers: []
    }],
    ...overrides
  } as Transaction;
}
