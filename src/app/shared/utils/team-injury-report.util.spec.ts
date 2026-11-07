import type { FantasyTeam, Player } from '../../core/models/fantasy.models';
import {
  buildTeamInjuryReport,
  injuryKind,
  isPlayerInjured
} from './team-injury-report.util';

function player(id: string, designation: string | null, injured = designation !== null, description = ''): Player {
  return {
    ID: id,
    Name: `Player ${id}`,
    Injured: injured,
    InjuryDetails: { Designation: designation ?? '', Description: description, Date: '', ReturnDate: '' }
  } as unknown as Player;
}

function team(roster: Player[], taxi: Player[] = [], reserve: Player[] = []): FantasyTeam {
  return { Roster: roster, Taxi: taxi, Reserve: reserve, Starter: [] } as unknown as FantasyTeam;
}

describe('team injury report utilities', () => {
  it('maps designations and keeps unrecognized or empty ones Unknown', () => {
    expect(injuryKind(player('a', 'Out'))).toBe('out');
    expect(injuryKind(player('a', 'questionable'))).toBe('questionable');
    expect(injuryKind(player('a', 'IR'))).toBe('ir');
    expect(injuryKind(player('a', 'Suspended'))).toBe('unknown');
    expect(injuryKind(player('a', '', true))).toBe('unknown');
  });

  it('lists only injured players and returns an empty report otherwise', () => {
    const healthy = player('h', null, false);
    expect(isPlayerInjured(healthy)).toBeFalse();
    expect(buildTeamInjuryReport(team([healthy]))).toEqual([]);
  });

  it('roster mode orders by designation with the long-term cases at the bottom and ignores starters', () => {
    const rows = buildTeamInjuryReport(
      team([
        player('ir', 'IR'),
        player('o', 'Out'),
        player('d', 'Doubtful'),
        player('sq', 'Questionable'),
        player('aq', 'Questionable'),
        player('u', '', true)
      ]),
      { starterIds: new Set(['sq']) }
    );
    expect(rows.map(row => row.player.ID)).toEqual(['u', 'aq', 'sq', 'd', 'o', 'ir']);
    expect(rows.every(row => row.lockLabel === null)).toBeTrue();
  });

  it('lineup mode keeps only starters, soonest lock first, then most severe', () => {
    const lock = (id: string, startsAt: string) => ({
      FantasyTeamID: 1, PlayerID: id, NFLTeamID: 'GB', Kind: 'scheduled' as const, GameID: 'g-' + id,
      DecisionWindowID: 'w-' + id, StartsAtUtc: startsAt, IsStarter: true
    });
    const rows = buildTeamInjuryReport(
      team([player('late-out', 'Out'), player('early-q', 'Questionable'), player('early-out', 'Out'), player('bench', 'Out')]),
      {
        mode: 'lineup',
        starterIds: new Set(['late-out', 'early-q', 'early-out']),
        lockContext: {
          fantasyTeamId: 1,
          now: new Date('2026-11-08T10:00:00Z'),
          playerLockFacts: [
            lock('late-out', '2026-11-08T21:25:00Z'),
            lock('early-q', '2026-11-08T18:00:00Z'),
            lock('early-out', '2026-11-08T18:00:00Z')
          ]
        }
      }
    );
    expect(rows.map(row => row.player.ID)).toEqual(['early-out', 'early-q', 'late-out']);
    expect(rows.every(row => row.isStarter && row.lockLabel !== null)).toBeTrue();
  });

  it('marks IR and Taxi placement and does not flag starters without lineup context', () => {
    const onIr = player('ir', 'IR');
    const onTaxi = player('tx', 'Questionable');
    const rows = buildTeamInjuryReport(team([onIr, onTaxi], [onTaxi], [onIr]));
    expect(rows.find(row => row.player.ID === 'ir')?.placement).toBe('ir');
    expect(rows.find(row => row.player.ID === 'tx')?.placement).toBe('taxi');
    expect(rows.every(row => !row.isStarter && row.lockLabel === null)).toBeTrue();
  });

  it('adds a lock hint in lineup mode only', () => {
    const starter = player('s', 'Out');
    const bench = player('b', 'Out');
    const rows = buildTeamInjuryReport(team([starter, bench]), {
      mode: 'lineup',
      starterIds: new Set(['s']),
      lockContext: {
        fantasyTeamId: 1,
        now: new Date('2026-11-08T12:00:00Z'),
        playerLockFacts: [{
          FantasyTeamID: 1, PlayerID: 's', NFLTeamID: 'GB', Kind: 'scheduled', GameID: 'g',
          DecisionWindowID: 'w', StartsAtUtc: '2026-11-08T11:00:00Z', IsStarter: true
        }]
      }
    });
    expect(rows.length).toBe(1);
    expect(rows[0].lockLabel).toBe('Locked');
  });

  it('carries the provider description unchanged', () => {
    const [row] = buildTeamInjuryReport(team([player('a', 'Questionable', true, ' Concussion ')]));
    expect(row.description).toBe('Concussion');
  });
});
