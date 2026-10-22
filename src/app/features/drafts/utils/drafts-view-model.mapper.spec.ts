import type { DraftPick, Player, RawDraft } from '../../../core/models/fantasy.models';
import { DraftPickCardComponent } from '../components/draft-pick-card/draft-pick-card';
import { createDraftViewModels } from './drafts-view-model.mapper';

describe('historical draft identity in the routed Drafts page', () => {
  const historical = { Name: 'Tom Brady', Position: 'QB', Picture: '/historical-brady.png' };
  const reusedIdPlayer = {
    ID: '167', Name: 'Different Current Player', NameShort: 'Wrong',
    NameLast: 'Current', Position: 'WR', Picture: '/current.png'
  } as Player;
  const pick = {
    PickKey: '2024_Free_Agent_R27_OO1',
    DraftKey: '2024_Free_Agent',
    Season: '2024',
    DraftType: 'Free_Agent',
    DraftInstance: 1,
    Round: 27,
    PositionInRound: 1,
    OverallPick: 157,
    DisplayPick: '27.01',
    OriginalOwnerRosterID: 1,
    CurrentOwnerRosterID: 1,
    IsCurrentlyTraded: false,
    TradeHistory: [],
    PlayerID: '167',
    PlayerName: 'Tom Brady',
    PlayerRef: historical,
    Status: 'Picked',
    SleeperPickNo: 157,
    SleeperPickedBy: null
  } as DraftPick;
  const draft = {
    DraftKey: '2024_Free_Agent', Season: '2024', DraftNo: 1,
    DraftType: 'Free_Agent', DraftInstance: 1,
    Status: 'Complete', Settings: { Rounds: 30, Type: 'linear' },
    Picks: [pick]
  } as RawDraft;

  it('prioritizes draft-season evidence over a reused current Sleeper ID', () => {
    const vm = createDraftViewModels([draft], [], [reusedIdPlayer])[0];
    const item = vm.orderedPicks[0];

    expect(item.selectedPlayer).toBeUndefined();
    expect(item.selectedPlayerName).toBe('Tom Brady');
    expect(item.selectedPlayerPosition).toBe('QB');
    expect(item.isPicked).toBeTrue();

    const card = new DraftPickCardComponent();
    card.item = item;
    card.draftVm = vm;
    expect(card.hasSelectedPlayer).toBeTrue();
    expect(card.selectedPlayerPicture).toBe('/historical-brady.png');
    expect(card.tileContextLabel).toBe('Tom Brady');
    expect(card.context.selectedPlayer).toBeUndefined();
    expect(card.context.selectedPlayerName).toBe('Tom Brady');
  });

  it('never backfills a missing historical portrait or position from the current player', () => {
    const incompletePick = {
      ...pick,
      PlayerRef: { Name: 'Tom Brady', Position: null, Picture: null }
    };
    const vm = createDraftViewModels([{ ...draft, Picks: [incompletePick] }], [], [reusedIdPlayer])[0];
    const card = new DraftPickCardComponent();
    card.item = vm.orderedPicks[0];
    card.draftVm = vm;

    expect(card.selectedPlayerPicture).toBeUndefined();
    expect(card.item.selectedPlayerPosition).toBeUndefined();
    expect(card.item.selectedPlayer).toBeUndefined();
    expect(card.tileContextLabel).toBe('Tom Brady');
  });

  it('retains the existing current-player fallback for older App JSON with no PlayerRef', () => {
    const olderPick = { ...pick, PlayerRef: undefined, PlayerName: null };
    const vm = createDraftViewModels([{ ...draft, Picks: [olderPick] }], [], [reusedIdPlayer])[0];
    const card = new DraftPickCardComponent();
    card.item = vm.orderedPicks[0];
    card.draftVm = vm;

    expect(card.item.selectedPlayer).toBe(reusedIdPlayer);
    expect(card.item.selectedPlayerName).toBe('Wrong');
    expect(card.selectedPlayerPicture).toBe('/current.png');
    expect(card.tileContextLabel).toBe('Current');
  });
});
