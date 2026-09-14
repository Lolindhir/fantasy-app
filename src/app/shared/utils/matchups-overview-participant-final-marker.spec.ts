import type {
  FantasyRelevanceRemainingScoringPathState,
  FantasyRelevanceSlotState,
  FantasyRelevanceTeamState
} from '../../core/models/decision-window.models';
import {
  buildMatchupScoreboardState,
  buildMatchupStarterProgress
} from './matchups-overview-view.util';

function slot(
  id: string,
  state: FantasyRelevanceSlotState['State'],
  decisionWindowID: string | null = null
): FantasyRelevanceSlotState {
  return {
    SlotID: id,
    SlotType: id.split('-')[0],
    SlotOrdinal: 1,
    SlotIndex: 0,
    CurrentStarterID: `player-${id}`,
    State: state,
    GameID: `game-${id}`,
    DecisionWindowID: decisionWindowID,
    StartsAtUtc: null,
    Repairability: null
  };
}

function team(
  state: FantasyRelevanceRemainingScoringPathState | undefined,
  slots: FantasyRelevanceSlotState[]
): FantasyRelevanceTeamState {
  return {
    FantasyTeamID: 1,
    ActiveRosterPlayerCount: slots.length,
    StarterCount: slots.length,
    BenchCount: 0,
    IRCount: 0,
    TaxiCount: 0,
    UnlockedStarterCount: slots.filter(item => item.State === 'unlocked').length,
    LockedActiveStarterCount: slots.filter(item => item.State === 'locked-active').length,
    CompletedStarterCount: slots.filter(item => item.State === 'completed').length,
    EligibleBenchCandidateCount: 0,
    HasRemainingScoringPath: state === 'open',
    RemainingScoringPathState: state,
    Slots: slots,
    Players: []
  };
}

describe('Matchups Overview participant Final marker', () => {
  it('covers neither, left-only, right-only and both participant-final combinations', () => {
    const open = team('open', [slot('QB-1', 'unlocked', 'next')]);
    const final = team('none', [slot('QB-1', 'completed')]);

    expect(buildMatchupStarterProgress(open, 'next', 'left')?.showFinalMarker).toBeFalse();
    expect(buildMatchupStarterProgress(open, 'next', 'right')?.showFinalMarker).toBeFalse();

    expect(buildMatchupStarterProgress(final, 'next', 'left')?.showFinalMarker).toBeTrue();
    expect(buildMatchupStarterProgress(open, 'next', 'right')?.showFinalMarker).toBeFalse();

    expect(buildMatchupStarterProgress(open, 'next', 'left')?.showFinalMarker).toBeFalse();
    expect(buildMatchupStarterProgress(final, 'next', 'right')?.showFinalMarker).toBeTrue();

    expect(buildMatchupStarterProgress(final, 'next', 'left')?.showFinalMarker).toBeTrue();
    expect(buildMatchupStarterProgress(final, 'next', 'right')?.showFinalMarker).toBeTrue();
  });

  it('keeps the shared score plate active while one participant is final and the opponent is live', () => {
    const final = team('none', [slot('QB-1', 'completed')]);
    const live = team('open', [slot('RB-1', 'locked-active')]);

    expect(buildMatchupStarterProgress(final, null, 'left')?.showFinalMarker).toBeTrue();
    expect(buildMatchupScoreboardState('open', [final, live])).toBe('active');
    expect(buildMatchupScoreboardState('final', [final, live])).toBe('final');
  });

  it('keeps Live/Next/Later progress grammar intact for an open opponent beside a final participant', () => {
    const final = team('none', [slot('QB-1', 'completed')]);
    const opponent = team('open', [
      slot('RB-1', 'locked-active'),
      { ...slot('WR-1', 'unlocked', 'next'), SlotIndex: 1 },
      { ...slot('TE-1', 'unlocked', 'later'), SlotIndex: 2 }
    ]);

    expect(buildMatchupStarterProgress(final, 'next', 'left')?.groups.map(group => group.kind))
      .toEqual(['final']);
    expect(buildMatchupStarterProgress(opponent, 'next', 'right')?.groups.map(group => group.kind))
      .toEqual(['future', 'next', 'locked']);
    expect(buildMatchupStarterProgress(final, 'next', 'left')?.showFinalMarker).toBeTrue();
  });

  it('fails closed for unknown or pre-contract participant state', () => {
    const unknown = team('unknown', [slot('QB-1', 'unknown')]);
    const legacy = team(undefined, [slot('QB-1', 'completed')]);

    expect(buildMatchupStarterProgress(unknown, null, 'left')?.showFinalMarker).toBeFalse();
    expect(buildMatchupStarterProgress(legacy, null, 'left')?.showFinalMarker).toBeFalse();
  });

  it('does not infer participant Final from an all-completed green strip', () => {
    const openByContract = team('open', [
      slot('QB-1', 'completed'),
      { ...slot('RB-1', 'completed'), SlotIndex: 1 }
    ]);
    const view = buildMatchupStarterProgress(openByContract, null, 'left');

    expect(view?.groups.map(group => group.kind)).toEqual(['final']);
    expect(view?.showFinalMarker).toBeFalse();
  });
});
