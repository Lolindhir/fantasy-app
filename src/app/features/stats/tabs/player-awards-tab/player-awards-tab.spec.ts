import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of, Subject, throwError } from 'rxjs';

import type { PlayerAwardHistoryReadModel, PlayerAwardKey } from '../../../../core/models/player-award-history.models';
import type { Player, PlayerIdentitySummary } from '../../../../core/models/player.models';
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

const current = (id: string): PlayerIdentitySummary => ({ ID: id, Name: `Current ${id}`, Position: 'RB', Picture: 'pic', TeamNFL: { ID: 'KC', Logo: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=' } } as unknown as PlayerIdentitySummary);

describe('player awards view', () => {
  it('keeps the generator order, shares ranks by equal totals and prefers the current record', () => {
    const view = buildPlayerAwardsView(history, [current('a')]);
    expect(view.seasons).toEqual(['2025', '2024']);
    const rows = view.rows('2024');
    expect(rows.map(row => [row.playerId, row.rank])).toEqual([['b', 1], ['a', 2], ['c', 2]]);
    expect(rows[1].name).toBe('Current a');
    expect(rows[1].teamAbbr).toBe('KC');
    expect(rows[0].name).toBe('Ref b');
    expect(rows[0].interactive).toBeFalse();
    expect(rows[1].interactive).toBeTrue();
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
  function create(awards: PlayerAwardHistoryReadModel | null, identitiesFail = false) {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayers', 'getPlayerIdentitySummaries', 'getPlayerAwardHistory'
    ]);
    const fullPlayer = { ...current('a'), Salary: 123 } as Player;
    dataService.getLeagueWithPlayers.and.returnValue(of({ players: [fullPlayer] } as LeagueWithPlayers));
    dataService.getPlayerIdentitySummaries.and.returnValue(identitiesFail
      ? throwError(() => new Error('identities unavailable')) : of([current('a')]));
    dataService.getPlayerAwardHistory.and.returnValue(of(awards));
    const open = jasmine.createSpy('open');
    TestBed.configureTestingModule({
      imports: [PlayerAwardsTabComponent],
      providers: [{ provide: DataService, useValue: dataService }, { provide: MatDialog, useValue: { open } }]
    });
    const fixture = TestBed.createComponent(PlayerAwardsTabComponent);
    fixture.detectChanges();
    return { fixture, root: fixture.nativeElement as HTMLElement, dataService, open, fullPlayer };
  }

  const names = (root: HTMLElement) => Array.from(root.querySelectorAll('.pa-name')).map(node => node.textContent?.trim());

  it('lists the all-time ranking and switches to a season', () => {
    const { fixture, root, dataService } = create(history);
    expect(dataService.getLeagueWithPlayers).not.toHaveBeenCalled();
    expect(dataService.getPlayerIdentitySummaries).toHaveBeenCalledOnceWith(['a', 'b', 'gone', 'c']);
    expect(names(root)).toEqual(['Current a', 'Ref b', 'Ref gone']);
    fixture.componentInstance.selectSeason('2025');
    fixture.detectChanges();
    expect(names(root)).toEqual(['Current a']);
    expect(root.querySelector('.pa-nfl-logo')?.getAttribute('src')).toContain('data:image');
  });

  it('shows a note instead of a table when the file is unavailable', () => {
    const { root, dataService } = create(null);
    expect(root.querySelector('.pa-table')).toBeNull();
    expect(root.textContent).toContain('No player award data');
    expect(dataService.getPlayerIdentitySummaries).not.toHaveBeenCalled();
    expect(dataService.getLeagueWithPlayers).not.toHaveBeenCalled();
  });

  it('retains published rankings if current identities are unavailable', () => {
    const { root, dataService } = create(history, true);
    expect(names(root)).toEqual(['Ref a', 'Ref b', 'Ref gone']);
    expect(Array.from(root.querySelectorAll<HTMLButtonElement>('.pa-identity')).every(button => button.disabled)).toBeTrue();
    expect(dataService.getLeagueWithPlayers).not.toHaveBeenCalled();
  });

  it('loads the full current player only on demand and keeps historic-only rows noninteractive', async () => {
    const { fixture, root, dataService, open, fullPlayer } = create(history);
    const component = fixture.componentInstance;
    const [active, historical] = component.rows();
    expect(root.querySelectorAll<HTMLButtonElement>('.pa-identity')[1].disabled).toBeTrue();
    await component.openPlayer(historical);
    expect(dataService.getLeagueWithPlayers).not.toHaveBeenCalled();
    await component.openPlayer(active);
    expect(dataService.getLeagueWithPlayers).toHaveBeenCalledTimes(1);
    expect(open.calls.mostRecent().args[1].data).toBe(fullPlayer);
  });

  it('suppresses repeat clicks while loading and allows retry after failure', async () => {
    const { fixture, dataService, open } = create(history);
    const component = fixture.componentInstance;
    const pending = new Subject<LeagueWithPlayers>();
    dataService.getLeagueWithPlayers.and.returnValue(pending);
    const row = component.rows()[0];
    const request = component.openPlayer(row);
    expect(component.openingPlayerId()).toBe('a');
    await component.openPlayer(row);
    expect(dataService.getLeagueWithPlayers).toHaveBeenCalledTimes(1);
    pending.error(new Error('unavailable'));
    await request;
    expect(component.openingPlayerId()).toBeNull();
    expect(component.playerOpenError()).toBeTrue();
    expect(open).not.toHaveBeenCalled();
    dataService.getLeagueWithPlayers.and.returnValue(of({ players: [] } as unknown as LeagueWithPlayers));
    await component.openPlayer(row);
    expect(component.playerOpenError()).toBeTrue();
    expect(open).not.toHaveBeenCalled();
    dataService.getLeagueWithPlayers.and.returnValue(of({ players: [{ ...current('a'), Salary: 123 } as Player] } as LeagueWithPlayers));
    await component.openPlayer(row);
    expect(component.playerOpenError()).toBeFalse();
    expect(open).toHaveBeenCalledTimes(1);
  });

  it('does not open a dialog after the awards tab is destroyed', async () => {
    const { fixture, dataService, open, fullPlayer } = create(history);
    const pending = new Subject<LeagueWithPlayers>();
    dataService.getLeagueWithPlayers.and.returnValue(pending);
    const request = fixture.componentInstance.openPlayer(fixture.componentInstance.rows()[0]);
    fixture.destroy();
    pending.next({ players: [fullPlayer] } as LeagueWithPlayers);
    pending.complete();
    await request;
    expect(open).not.toHaveBeenCalled();
  });
});
