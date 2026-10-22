import type { RawDraft, DraftPick } from '../../../core/models/draft.models';
import type { Player } from '../../../core/models/player.models';
import type { TransactionParticipant, TransactionDraftPick } from '../../../core/models/transaction.models';
import { buildTransactionPickContext, getTransactionCardAssets, getTransactionPreviewLimit } from './transaction-card.presenter';

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

  it('always shows every traded asset, regardless of card density', () => {
    for (const density of ['mini', 'compact', 'detail'] as const) {
      expect(getTransactionPreviewLimit('trade', density, false))
        .toBe(Number.POSITIVE_INFINITY);
    }
    expect(getTransactionPreviewLimit('add', 'compact', false)).toBe(3);
    expect(getTransactionPreviewLimit('cut', 'mini', false)).toBe(1);
    expect(getTransactionPreviewLimit('add', 'compact', true))
      .toBe(Number.POSITIVE_INFINITY);
  });

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
    expect(received[1].secondary).toBe('');
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

  it('shows historical names, portraits and positions without a phantom current Player or team', () => {
    const stale = {
      Name: 'Wrong Current Name', Picture: '/current.png', Position: 'TE',
      TeamNFL: { Abv: 'SEA', Logo: '/sea.png' }
    } as Player;
    const ref = { Name: 'Tyreek Hill', Position: 'WR', Picture: '/tyreek.png' };
    const archived: TransactionParticipant = {
      ...participant,
      DroppedPlayers: [
        { PlayerID: '3321', PlayerRef: ref },
        { PlayerID: '3321', Player: stale, PlayerRef: ref }
      ]
    };
    const assets = getTransactionCardAssets(archived, 'outgoing');
    for (const asset of assets) {
      expect(asset.label).toBe('Tyreek Hill');
      expect(asset.portrait).toBe('/tyreek.png');
      expect(asset.position).toBe('WR');
      expect(asset.nflTeamLogo).toBeUndefined();
      expect(asset.nflTeamAbv).toBeUndefined();
    }
    expect(assets[0].player).toBeUndefined();
    expect(assets[1].player).toBeUndefined();

    const noPortrait = getTransactionCardAssets({
      ...participant,
      DroppedPlayers: [{
        PlayerID: '9',
        Player: stale,
        PlayerRef: { Name: 'Older Historical Player', Position: null, Picture: null }
      }]
    }, 'outgoing')[0];
    expect(noPortrait.label).toBe('Older Historical Player');
    expect(noPortrait.portrait).toBeUndefined();
    expect(noPortrait.position).toBeUndefined();
    expect(noPortrait.player).toBeUndefined();
  });

  it('keeps traded pick summary free from selected player and original owner', () => {
    const [asset] = getTransactionCardAssets(participant, 'incoming').filter(asset => asset.kind === 'pick');
    expect(asset.label).toBe('2028 FA · R4');
    expect(asset.secondary).toBe('');
    expect(asset.pick?.OriginalOwnerRosterID).toBe(2);
  });

  it('opens the existing draft context only for one exactly identifiable pick', () => {
    const transactionPick = participant.AcquiredDraftPicks[0];
    const recorded = {
      PickKey: '2028_FA:4:2',
      DraftKey: '2028_FA',
      Season: '2028',
      DraftType: 'free_agent',
      DraftInstance: 1,
      Round: 4,
      PositionInRound: 2,
      OverallPick: 20,
      OriginalOwnerRosterID: 2,
      CurrentOwnerRosterID: 1,
      IsCurrentlyTraded: true,
      DisplayPick: '4.02',
      PlayerID: null,
      PlayerName: null,
      TradeHistory: [],
      Status: 'upcoming',
      SleeperPickNo: null,
      SleeperPickedBy: null
    } satisfies DraftPick;
    const draft = {
      DraftKey: '2028_FA',
      Season: '2028',
      DraftType: 'free_agent',
      DraftInstance: 1,
      DisplayDraftKey: '2028 Free Agent',
      DisplayAbrDraftKey: '2028 FA',
      DisplayDraftType: 'Free Agent',
      DraftNo: 1,
      SleeperStatus: null,
      SleeperStartTime: null,
      DraftStartTimeUtc: null,
      Status: 'upcoming',
      DisplayStatus: 'Upcoming',
      Picks: [recorded],
      Settings: { Rounds: 4, Type: 'linear' }
    } satisfies RawDraft;
    const asset = getTransactionCardAssets({
      ...participant,
      AcquiredDraftPicks: [{ ...transactionPick, PickKey: recorded.PickKey }]
    }, 'incoming').find(asset => asset.kind === 'pick')!;
    const context = buildTransactionPickContext(asset, [draft], []);
    expect(context?.pick).toBe(recorded);
    expect(context?.draft).toBe(draft);
    expect(context?.currentOwner?.id).toBe(1);
    expect(context?.originalOwner?.id).toBe(2);
    expect(buildTransactionPickContext(asset, [draft, draft], [])).toBeNull();
    expect(buildTransactionPickContext(asset, [], [])).toBeNull();
  });

  it('does not guess a pick from another draft when an explicit DraftKey differs', () => {
    const asset = getTransactionCardAssets(participant, 'incoming').find(asset => asset.kind === 'pick')!;
    const wrongDraft: RawDraft = {
      DraftKey: '2028_Rookie',
      Season: '2028',
      DraftType: 'Rookie',
      DraftInstance: 1,
      DisplayDraftKey: '2028 Rookie',
      DisplayAbrDraftKey: '2028 Rookie',
      DisplayDraftType: 'Rookie',
      DraftNo: 1,
      SleeperStatus: null,
      SleeperStartTime: null,
      DraftStartTimeUtc: null,
      Status: 'upcoming',
      DisplayStatus: 'Upcoming',
      Settings: { Rounds: 5, Type: 'linear' },
      Picks: []
    };
    expect(buildTransactionPickContext(asset, [wrongDraft], [])).toBeNull();
  });
});
