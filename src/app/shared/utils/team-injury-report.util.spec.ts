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

  it('sorts starters first, then by severity, then by name', () => {
    const rows = buildTeamInjuryReport(
      team([
        player('q', 'Questionable'),
        player('o', 'Out'),
        player('d', 'Doubtful'),
        player('sq', 'Questionable'),
        player('u', '', true)
      ]),
      { starterIds: new Set(['sq']) }
    );
    expect(rows.map(row => row.player.ID)).toEqual(['sq', 'o', 'd', 'q', 'u']);
    expect(rows[0].isStarter).toBeTrue();
  });

  it('marks IR and Taxi placement and does not flag starters without lineup context', () => {
    const onIr = player('ir', 'IR');
    const onTaxi = player('tx', 'Questionable');
    const rows = buildTeamInjuryReport(team([onIr, onTaxi], [onTaxi], [onIr]));
    expect(rows.find(row => row.player.ID === 'ir')?.placement).toBe('ir');
    expect(rows.find(row => row.player.ID === 'tx')?.placement).toBe('taxi');
    expect(rows.every(row => !row.isStarter && row.lockLabel === null)).toBeTrue();
  });

  it('adds a lock hint for starters only', () => {
    const starter = player('s', 'Out');
    const bench = player('b', 'Out');
    const rows = buildTeamInjuryReport(team([starter, bench]), {
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
    expect(rows[0].lockLabel).toBe('Locked');
    expect(rows[1].lockLabel).toBeNull();
  });

  it('carries the provider description unchanged', () => {
    const [row] = buildTeamInjuryReport(team([player('a', 'Questionable', true, ' Concussion ')]));
    expect(row.description).toBe('Concussion');
  });
});
