import type { FantasyTeam } from '../../core/models/league.models';
import type {
  Transaction,
  TransactionDraftPick
} from '../../core/models/transaction.models';
import {
  buildMovesViewModel,
  getDraftPickAssetLabel,
  getDraftPickLabel,
  getDraftPickOriginalOwnerLabel,
  getDraftPickTrackKey,
  getIncomingAssetIcon,
  getIncomingAssetLabel,
  getOutgoingAssetIcon,
  getOutgoingAssetLabel
} from './moves-view-model.util';

describe('moves-view-model.util', () => {
  const mightyGiants = {
    TeamID: 1,
    Team: 'Mighty Giants',
    TeamAbbr: 'MiG',
    Owner: 'Lolindhir'
  } as FantasyTeam;
  const ruhrValleyPackers = {
    TeamID: 2,
    Team: 'Ruhr Valley Packers',
    TeamAbbr: 'RVP',
    Owner: 'Marcio231'
  } as FantasyTeam;

  it('builds season metrics for moves, players and picks', () => {
    const trade = createTransaction('trade-1', 'trade', 1, 1);
    trade.DraftPicks = [
      createPick(),
      createPick({
        OriginalOwnerRosterID: 2,
        PreviousOwnerRosterID: 2,
        NewOwnerRosterID: 1,
        OriginalOwner: ruhrValleyPackers
      })
    ];

    const viewModel = buildMovesViewModel([
      trade,
      createTransaction('cut-1', 'free_agent', 0, 1),
      createTransaction('waiver-with-cut', 'waiver', 1, 1),
      createTransaction('waiver-add', 'waiver', 1, 0)
    ]);

    expect(viewModel.SeasonLabel).toBe('2026');
    expect(viewModel.TotalCount).toBe(4);
    expect(viewModel.VisibleCount).toBe(4);
    expect(viewModel.TradeCount).toBe(1);
    expect(viewModel.RosterMoveCount).toBe(1);
    expect(viewModel.PlayerMoveCount).toBe(6);
    expect(viewModel.DraftPickCount).toBe(2);
    expect(viewModel.CutCount).toBe(2);
    expect(viewModel.WaiverAddCount).toBe(2);
  });

  it('filters the visible feed without changing the season summary', () => {
    const transactions = [
      createTransaction('trade-1', 'trade', 1, 1),
      createTransaction('waiver-1', 'waiver', 1, 0),
      createTransaction('cut-1', 'free_agent', 0, 1)
    ];

    const tradeViewModel = buildMovesViewModel(transactions, 'trade');
    const rosterViewModel = buildMovesViewModel(transactions, 'roster');

    expect(tradeViewModel.TotalCount).toBe(3);
    expect(tradeViewModel.VisibleCount).toBe(1);
    expect(tradeViewModel.Groups[0].Transactions[0].TransactionID).toBe('trade-1');
    expect(rosterViewModel.VisibleCount).toBe(1);
    expect(rosterViewModel.Groups[0].Transactions[0].TransactionID).toBe('cut-1');
  });

  it('provides filter counts for all activity types', () => {
    const viewModel = buildMovesViewModel([
      createTransaction('trade-1', 'trade', 1, 1),
      createTransaction('waiver-1', 'waiver', 1, 0),
      createTransaction('cut-1', 'free_agent', 0, 1),
      createTransaction('commissioner-1', 'commissioner', 1, 0)
    ]);

    expect(viewModel.Filters.map(filter => [filter.Id, filter.Count])).toEqual([
      ['all', 4],
      ['trade', 1],
      ['waiver', 1],
      ['roster', 2]
    ]);
  });

  it('uses receive and send language for trades', () => {
    expect(getIncomingAssetLabel('trade')).toBe('Receives');
    expect(getOutgoingAssetLabel('trade')).toBe('Sends');
    expect(getIncomingAssetIcon('trade')).toBe('call_received');
    expect(getOutgoingAssetIcon('trade')).toBe('call_made');
  });

  it('uses roster-action language for adds and drops', () => {
    expect(getIncomingAssetLabel('free_agent')).toBe('Added');
    expect(getOutgoingAssetLabel('free_agent')).toBe('Dropped');
    expect(getIncomingAssetLabel('waiver')).toBe('Added');
    expect(getOutgoingAssetLabel('waiver')).toBe('Dropped');
    expect(getIncomingAssetIcon('free_agent')).toBe('add');
    expect(getOutgoingAssetIcon('free_agent')).toBe('remove');
  });

  it('distinguishes same-round picks by original owner in the visible label', () => {
    const mightyGiantsPick = createPick({
      OriginalOwnerRosterID: 1,
      OriginalOwner: mightyGiants,
      PreviousOwnerRosterID: 1,
      NewOwnerRosterID: 2
    });
    const ruhrValleyPick = createPick({
      OriginalOwnerRosterID: 2,
      OriginalOwner: ruhrValleyPackers,
      PreviousOwnerRosterID: 2,
      NewOwnerRosterID: 1
    });

    expect(getDraftPickAssetLabel(mightyGiantsPick)).toBe('2026 Rookie 2nd');
    expect(getDraftPickLabel(mightyGiantsPick)).toBe('2026 Rookie 2nd (MiG)');
    expect(getDraftPickLabel(ruhrValleyPick)).toBe('2026 Rookie 2nd (RVP)');
    expect(getDraftPickTrackKey(mightyGiantsPick)).not.toBe(getDraftPickTrackKey(ruhrValleyPick));
  });

  it('provides the full original-owner name for tooltips', () => {
    const pick = createPick({
      OriginalOwnerRosterID: 1,
      OriginalOwner: mightyGiants
    });

    expect(getDraftPickOriginalOwnerLabel(pick)).toBe('Mighty Giants');
  });

  it('falls back to the roster id when the original team cannot be resolved', () => {
    const pick = createPick({
      OriginalOwnerRosterID: 5,
      OriginalOwner: undefined
    });

    expect(getDraftPickLabel(pick)).toBe('2026 Rookie 2nd (T5)');
    expect(getDraftPickOriginalOwnerLabel(pick)).toBe('Team 5');
  });

  function createTransaction(
    transactionID: string,
    type: string,
    addedPlayerCount: number,
    droppedPlayerCount: number
  ): Transaction {
    return {
      Source: 'Sleeper',
      TransactionID: transactionID,
      Type: type,
      Status: 'complete',
      Season: '2026',
      Week: 1,
      CreatedAt: 1781261326971,
      CreatedDate: '2026-06-12',
      CreatedAtDate: new Date(1781261326971),
      RosterIDs: [1],
      Participants: [
        {
          RosterID: 1,
          Team: mightyGiants,
          AddedPlayers: Array.from({ length: addedPlayerCount }, (_, index) => ({
            PlayerID: `added-${transactionID}-${index}`
          })),
          DroppedPlayers: Array.from({ length: droppedPlayerCount }, (_, index) => ({
            PlayerID: `dropped-${transactionID}-${index}`
          })),
          AcquiredDraftPicks: [],
          SentDraftPicks: []
        }
      ],
      DraftPicks: [],
      Notes: null
    };
  }

  function createPick(
    overrides: Partial<TransactionDraftPick> = {}
  ): TransactionDraftPick {
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
      NewOwner: ruhrValleyPackers,
      ...overrides
    };
  }
});
