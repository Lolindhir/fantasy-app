import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { defer, of, Subject, throwError } from 'rxjs';

import type { RawDraft } from '../../core/models/draft.models';
import type { Transaction } from '../../core/models/transaction.models';
import { DataService, type LeagueWithPlayers } from '../../core/services/data.service';
import { LeagueActivityComponent } from './league-activity';

describe('LeagueActivityComponent context reuse', () => {
  const transactionPath = 'data/past_seasons/Transactions/Transactions_2025.json';
  const draftPath = 'data/past_seasons/Drafts/Drafts_2025.json';
  const currentDraft = { DraftKey: 'current' } as RawDraft;
  const pastDraft = { DraftKey: 'past' } as RawDraft;
  const context = {
    league: { Season: '2026' }, teams: [], players: [], drafts: [currentDraft]
  } as unknown as LeagueWithPlayers;
  const move = (season: string): Transaction => ({
    Season: season, TransactionID: season, Type: 'trade', EffectiveAt: Date.UTC(Number(season), 0, 1),
    Participants: [], DraftPicks: []
  } as unknown as Transaction);

  function create(query: Record<string, string> = {}) {
    let bundleSubscriptions = 0;
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayers', 'getPastSeasonsIndex', 'getTransactionsForContext',
      'getTransactionsForSources', 'getPastDraftsRaw'
    ]);
    dataService.getLeagueWithPlayers.and.returnValue(defer(() => {
      bundleSubscriptions++;
      return of(context);
    }));
    dataService.getPastSeasonsIndex.and.returnValue(of({
      GeneratedAt: null, Seasons: [
        { Season: '2025', Resources: {
          Transactions: { Exists: true, Path: transactionPath },
          Drafts: { Exists: true, Path: draftPath }
        } },
        { Season: '2024', Resources: { Transactions: { Exists: false, Path: 'unavailable' } } },
        { Season: '2026', Resources: { Transactions: { Exists: true, Path: 'current-archive' } } }
      ]
    }));
    dataService.getTransactionsForContext.and.callFake((_context, includeCurrent, paths) => of([
      ...(includeCurrent ? [move('2026')] : []),
      ...(paths.includes(transactionPath) ? [move('2025')] : [])
    ]));
    dataService.getPastDraftsRaw.and.returnValue(of([pastDraft]));
    TestBed.configureTestingModule({
      imports: [LeagueActivityComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
        { provide: DataService, useValue: dataService }
      ]
    });
    const component = TestBed.createComponent(LeagueActivityComponent).componentInstance;
    return { component, dataService, bundleSubscriptions: () => bundleSubscriptions };
  }

  it('reuses one context for current, historical and all seasons, without reloading on a filter change', () => {
    const { component, dataService, bundleSubscriptions } = create();
    const seen: Array<{ season: string; count: number; drafts: RawDraft[] }> = [];
    const subscription = component.vm$.subscribe(vm => seen.push({
      season: vm.SelectedSeason, count: vm.VisibleCount, drafts: vm.Drafts
    }));
    component.selectSeason('2025');
    component.selectSeason('all');
    component.setFilter('add');
    expect(seen).toEqual([
      { season: '2026', count: 1, drafts: [currentDraft] },
      { season: '2025', count: 1, drafts: [pastDraft] },
      { season: 'all', count: 2, drafts: [currentDraft, pastDraft] },
      { season: 'all', count: 0, drafts: [currentDraft, pastDraft] }
    ]);
    expect(bundleSubscriptions()).toBe(1);
    expect(dataService.getTransactionsForSources).not.toHaveBeenCalled();
    expect(dataService.getTransactionsForContext.calls.allArgs()).toEqual([
      [context, true, []], [context, false, [transactionPath]], [context, true, [transactionPath]]
    ]);
    expect(dataService.getPastDraftsRaw).toHaveBeenCalledTimes(2);
    subscription.unsubscribe();
  });

  it('cancels a superseded season and publishes the selected season only with its matching data', () => {
    const { component, dataService } = create();
    const pending = new Subject<Transaction[]>();
    dataService.getTransactionsForContext.and.callFake((_context, current, paths) =>
      current && paths.length ? of([move('2026'), move('2025')]) : current ? of([move('2026')]) : pending
    );
    const seen: Array<[string, number]> = [];
    const subscription = component.vm$.subscribe(vm => seen.push([vm.SelectedSeason, vm.TotalCount]));
    component.selectSeason('2025');
    expect(seen).toEqual([['2026', 1]]);
    component.selectSeason('all');
    pending.next([move('2025')]);
    pending.complete();
    expect(seen).toEqual([['2026', 1], ['all', 2]]);
    subscription.unsubscribe();
  });

  it('keeps transaction failures explicit and can recover without another context load', () => {
    const { component, dataService, bundleSubscriptions } = create({ season: '2025' });
    dataService.getTransactionsForContext.and.returnValue(throwError(() => new Error('archive unavailable')));
    const seen: Array<[string, number, boolean]> = [];
    const subscription = component.vm$.subscribe(vm => seen.push([vm.SelectedSeason, vm.TotalCount, component.loadFailed]));
    dataService.getTransactionsForContext.and.returnValue(of([move('2025')]));
    dataService.getPastDraftsRaw.and.returnValue(throwError(() => new Error('optional draft unavailable')));
    component.selectSeason('2025');
    expect(seen).toEqual([['2025', 0, true], ['2025', 1, false]]);
    expect(bundleSubscriptions()).toBe(1);
    subscription.unsubscribe();
  });
});
