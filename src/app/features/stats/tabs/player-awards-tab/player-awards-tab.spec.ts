import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';

import type { PlayerAwardHistoryReadModel, PlayerAwardKey } from '../../../../core/models/player-award-history.models';
import type { Player } from '../../../../core/models/player.models';
import { DataService, type LeagueWithPlayers } from '../../../../core/services/data.service';
import { PlayerAwardsTabComponent } from './player-awards-tab';
import { ALL_TIME, buildPlayerAwardsView } from './player-awards-view.util';

const counts = (mvp: number, hero = 0): Record<PlayerAwardKey, number> => ({ MVP: mvp, MatchupHero: hero, Heartbreaker: 0, UnsungHero: 0 });

const refs = (id: string, total: number, extra: Partial<PlayerAwardHistoryReadModel['Players'][number]> = {}): PlayerAwardHistoryReadModel['Players'][number] => ({
  PlayerID: id, Name: `Ref ${id}`, Position: 'QB', Picture: null, Counts: counts(total), Total: total, Entries: [], ...extra
});

const history: PlayerAwardHistoryReadModel = {
  SchemaVersion: 1,
  Awards: ['MVP', 'MatchupHero', 'Heartbreaker', 'UnsungHero'],
  Seasons: [
    { Season: 2024, Weeks: [1], Players: [{ PlayerID: 'b', Counts: counts(2), Total: 2 }, { PlayerID: 'a', Counts: counts(1), Total: 1 }, { PlayerID: 'c', Counts: counts(1), Total: 1 }] },
    { Season: 2025, Weeks: [1], Players: [{ PlayerID: 'a', Counts: counts(1), Total: 1 }] }
  ],
  Players: [refs('a', 3), refs('b', 2), refs('gone', 1), refs('c', 0)]
};

const current = (id: string): Player => ({ ID: id, Name: `Current ${id}`, Position: 'RB', Picture: 'pic', TeamNFL: { ID: 'KC', Logo: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=' } } as unknown as Player);

describe('player awards view', () => {
  it('keeps the generator order, shares ranks by equal totals and prefers the current record', () => {
    const view = buildPlayerAwardsView(history, [current('a')]);
    expect(view.seasons).toEqual(['2025', '2024']);
    const rows = view.rows('2024');
    expect(rows.map(row => [row.playerId, row.rank])).toEqual([['b', 1], ['a', 2], ['c', 2]]);
    expect(rows[1].name).toBe('Current a');
    expect(rows[1].teamAbbr).toBe('KC');
    expect(rows[0].name).toBe('Ref b');
    expect(rows[0].player).toBeNull();
  });

  it('shows players the app no longer lists from the award file in the all-time view', () => {
    const rows = buildPlayerAwardsView(history, []).rows(ALL_TIME);
    expect(rows.map(row => row.playerId)).toEqual(['a', 'b', 'gone']);
  });

  it('offers no season view for a file without per-season rankings', () => {
    const old: PlayerAwardHistoryReadModel = { ...history, Seasons: [{ Season: 2024, Weeks: [1] }] };
    const view = buildPlayerAwardsView(old, []);
    expect(view.seasons).toEqual([]);
    expect(view.rows(ALL_TIME).length).toBe(3);
  });
});

describe('PlayerAwardsTabComponent', () => {
  function create(awards: PlayerAwardHistoryReadModel | null) {
    const dataService = jasmine.createSpyObj<DataService>('DataService', ['getLeagueWithPlayers', 'getPlayerAwardHistory']);
    dataService.getLeagueWithPlayers.and.returnValue(of({ league: { Season: '2025' }, teams: [], players: [current('a')] } as unknown as LeagueWithPlayers));
    dataService.getPlayerAwardHistory.and.returnValue(of(awards));
    TestBed.configureTestingModule({
      imports: [PlayerAwardsTabComponent],
      providers: [{ provide: DataService, useValue: dataService }, { provide: MatDialog, useValue: { open: jasmine.createSpy('open') } }]
    });
    const fixture = TestBed.createComponent(PlayerAwardsTabComponent);
    fixture.detectChanges();
    return { fixture, root: fixture.nativeElement as HTMLElement };
  }

  const names = (root: HTMLElement) => Array.from(root.querySelectorAll('.pa-name')).map(node => node.textContent?.trim());

  it('lists the all-time ranking and switches to a season', () => {
    const { fixture, root } = create(history);
    expect(names(root)).toEqual(['Current a', 'Ref b', 'Ref gone']);
    fixture.componentInstance.selectSeason('2025');
    fixture.detectChanges();
    expect(names(root)).toEqual(['Current a']);
    expect(root.querySelector('.pa-nfl-logo')?.getAttribute('src')).toContain('data:image');
  });

  it('shows a note instead of a table when the file is unavailable', () => {
    const { root } = create(null);
    expect(root.querySelector('.pa-table')).toBeNull();
    expect(root.textContent).toContain('No player award data');
  });
});
