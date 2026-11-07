import type { DraftPick, RawDraft } from '../../core/models/draft.models';
import type { FantasyTeam } from '../../core/models/league.models';
import type { Player } from '../../core/models/player.models';
import type { RawTransaction } from '../../core/models/transaction.models';
import { mapRawTransactions } from '../../core/mappers/transaction.mapper';
import { acquisitionLabel, buildPlayerJourney } from './player-journey.util';

const teams = [1, 2, 3].map(id => ({ TeamID: id, Team: `Team ${id}` }) as FantasyTeam);
const players = [{ ID: 'p1', Name: 'Player One' }, { ID: 'p2', Name: 'Player Two' }] as Player[];

function raw(overrides: Partial<RawTransaction>): RawTransaction {
  return {
    Source: 'sleeper',
    TransactionID: 'tx',
    Type: 'free_agent',
    Status: 'complete',
    Season: '2026',
    Week: 1,
    CreatedAt: 1,
    CreatedDate: '',
    RosterIDs: [],
    Adds: null,
    Drops: null,
    DraftPicks: null,
    Notes: null,
    ...overrides
  };
}

function draft(season: string, picks: Partial<DraftPick>[], start: number | null = null): RawDraft {
  return {
    DraftKey: `${season}_Rookie`,
    DisplayDraftKey: `${season} Rookie`,
    Season: season,
    SleeperStartTime: start,
    Picks: picks.map((pick, index) => ({
      PickKey: `${season}_R_${index}`,
      Round: 1,
      DisplayPick: '1.01',
      CurrentOwnerRosterID: 1,
      PlayerID: null,
      ...pick
    }))
  } as unknown as RawDraft;
}

describe('buildPlayerJourney', () => {
  it('chains draft, add, trade and drop newest first using EffectiveAt, not CreatedAt', () => {
    const transactions = mapRawTransactions([
      raw({ TransactionID: 'add', Type: 'waiver', EffectiveAt: 2000, CreatedAt: 9000, RosterIDs: [1], Adds: { p1: 1 } }),
      raw({ TransactionID: 'trade', Type: 'trade', EffectiveAt: 3000, CreatedAt: 1000, RosterIDs: [1, 2], Adds: { p1: 2 }, Drops: { p1: 1 } }),
      raw({ TransactionID: 'drop', Type: 'free_agent', EffectiveAt: 4000, CreatedAt: 500, RosterIDs: [2], Drops: { p1: 2 } }),
      raw({ TransactionID: 'other', EffectiveAt: 2500, Adds: { p2: 3 } })
    ], teams, players);
    const drafts = [draft('2025', [{ PlayerID: 'p1', CurrentOwnerRosterID: 1 }, { PlayerID: 'p2' }], 1000)];

    const journey = buildPlayerJourney('p1', transactions, drafts, teams);

    expect(journey.events.map(event => event.kind)).toEqual(['dropped', 'traded', 'added', 'drafted']);
    expect(journey.events.map(event => event.at)).toEqual([4000, 3000, 2000, 1000]);
    const trade = journey.events[1];
    expect(trade.fromTeam?.TeamID).toBe(1);
    expect(trade.team?.TeamID).toBe(2);
    expect(trade.transactionID).toBe('trade');
    expect(journey.events[2].detail).toBe('Waiver claim');
    expect(journey.events[3].detail).toBe('Pick 1.01 · 2025 Rookie');
    expect(journey.events[3].dateApproximate).toBe(false);
    expect(journey.teams.map(team => team.TeamID)).toEqual([2, 1]);
  });

  it('keeps waiver claims as an event without any bid', () => {
    const transactions = mapRawTransactions([
      raw({ TransactionID: 'w', Type: 'waiver', EffectiveAt: 5, RosterIDs: [3], Adds: { p1: 3 }, Notes: 'bid 12' })
    ], teams, players);
    const [event] = buildPlayerJourney('p1', transactions, [], teams).events;
    expect(event.kind).toBe('added');
    expect(event.detail).toBe('Waiver claim');
    expect(JSON.stringify(event)).not.toContain('12');
  });

  it('orders a draft with an unknown date before moves of the same season and marks it approximate', () => {
    const transactions = mapRawTransactions([
      raw({ Season: '2025', EffectiveAt: Date.UTC(2025, 5, 1), Adds: { p1: 2 }, RosterIDs: [2] })
    ], teams, players);
    const journey = buildPlayerJourney('p1', transactions, [draft('2025', [{ PlayerID: 'p1' }])], teams);

    expect(journey.events.map(event => event.kind)).toEqual(['added', 'drafted']);
    expect(journey.events[1].dateApproximate).toBe(true);
  });

  it('does not invent teams for unknown rosters and does not list a pick twice', () => {
    const transactions = mapRawTransactions([
      raw({ EffectiveAt: 10, Adds: { p1: 99 }, RosterIDs: [99] })
    ], teams, players);
    const dup = draft('2024', [{ PlayerID: 'p1', PickKey: 'same' }, { PlayerID: 'p1', PickKey: 'same' }], 5);
    const journey = buildPlayerJourney('p1', transactions, [dup], teams);

    expect(journey.events.filter(event => event.kind === 'drafted').length).toBe(1);
    expect(journey.events.find(event => event.kind === 'added')?.team).toBeNull();
    expect(journey.teams.map(team => team.TeamID)).toEqual([1]);
  });

  it('returns an empty journey for a player without history', () => {
    expect(buildPlayerJourney('nobody', [], [], teams)).toEqual({ events: [], teams: [] });
    expect(acquisitionLabel('free_agent')).toBe('Free agent');
    expect(acquisitionLabel('some_new_type')).toBe('some new type');
  });
});
