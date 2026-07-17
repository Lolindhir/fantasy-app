import type { FantasyTeam } from '../../core/models/league.models';
import type { TransactionDraftPick } from '../../core/models/transaction.models';
import {
  getDraftPickDisplayLabel,
  getDraftPickExactLabel,
  getDraftPickOriginalOwnerLabel,
  getDraftPickOriginalOwnerShortLabel,
  getDraftPickRoundOrdinal,
  getDraftPickTrackKey,
  getDraftPickTitle,
  getFantasyTeamAbbr,
  getTransactionTypeLabel
} from './transaction-display.util';

describe('transaction-display.util', () => {
  const mightyGiants = {
    TeamID: 1,
    Team: 'Mighty Giants',
    TeamAbbr: 'MiG',
    Owner: 'Lolindhir'
  } as FantasyTeam;

  it('formats supported transaction types for the UI', () => {
    expect(getTransactionTypeLabel('trade')).toBe('Trade');
    expect(getTransactionTypeLabel('waiver')).toBe('Waiver');
    expect(getTransactionTypeLabel('free_agent')).toBe('Free Agency');
  });

  it('uses the resolved draft position when available', () => {
    const pick = createPick({
      ResolvedDraftPick: {
        DisplayPick: '2.03'
      } as TransactionDraftPick['ResolvedDraftPick']
    });

    expect(getDraftPickTitle(pick)).toBe('2026 Rookie');
    expect(getDraftPickRoundOrdinal(pick)).toBe('2nd');
    expect(getDraftPickExactLabel(pick)).toBe('2.03');
    expect(getDraftPickDisplayLabel(pick)).toContain('pick 2.03');
  });

  it('retains original-owner identity for same-round picks', () => {
    const pick = createPick();

    expect(getDraftPickOriginalOwnerLabel(pick)).toBe('Mighty Giants');
    expect(getDraftPickOriginalOwnerShortLabel(pick)).toBe('MiG');
    expect(getDraftPickTrackKey(pick)).toContain('OO1');
  });

  it('derives a compact team abbreviation when none is stored', () => {
    expect(getFantasyTeamAbbr({ Team: 'Fighting Childish' } as FantasyTeam, 4)).toBe('FC');
  });

  function createPick(overrides: Partial<TransactionDraftPick> = {}): TransactionDraftPick {
    return {
      DraftType: 'Rookie',
      DraftSource: 'Sleeper',
      DraftKey: '2026_Rookie',
      Season: '2026',
      Round: 2,
      OriginalOwnerRosterID: 1,
      PreviousOwnerRosterID: 1,
      NewOwnerRosterID: 2,
      OriginalOwner: mightyGiants,
      PreviousOwner: mightyGiants,
      ...overrides
    };
  }
});
