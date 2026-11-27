import { TestBed } from '@angular/core/testing';
import { defer, lastValueFrom, of, throwError } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import { DataService, type LeagueWithPlayersAndTransactions } from '../../core/services/data.service';
import { OverviewDataScope } from './overview-data-scope.service';

describe('OverviewDataScope', () => {
  const context = { nflTeams: [{ ID: 'NYG', Logo: 'giants.png' }] } as unknown as LeagueWithPlayersAndTransactions;
  const windows = { DecisionWindows: [] } as unknown as DecisionWindowsReadModel;
  let dataService: jasmine.SpyObj<DataService>;
  let scope: OverviewDataScope;

  beforeEach(() => {
    dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueWithPlayersAndTransactions', 'getNflTeams', 'getDecisionWindows'
    ]);
    dataService.getLeagueWithPlayersAndTransactions.and.returnValue(defer(() => of(context)));
    dataService.getDecisionWindows.and.returnValue(defer(() => of(windows)));
    TestBed.configureTestingModule({
      providers: [OverviewDataScope, { provide: DataService, useValue: dataService }]
    });
    scope = TestBed.inject(OverviewDataScope);
  });

  it('reuses the parent bundle and only requests Decision Windows when a child subscribes', async () => {
    expect(dataService.getDecisionWindows).not.toHaveBeenCalled();
    expect(await lastValueFrom(scope.context$)).toBe(context);
    expect(await lastValueFrom(scope.nflTeams$)).toBe(context.nflTeams);
    expect(await lastValueFrom(scope.nflTeams$)).toBe(context.nflTeams);
    expect(dataService.getLeagueWithPlayersAndTransactions).toHaveBeenCalledTimes(1);
    expect(dataService.getNflTeams).not.toHaveBeenCalled();
    expect(dataService.getDecisionWindows).not.toHaveBeenCalled();
    expect(await lastValueFrom(scope.decisionWindows$)).toBe(windows);
    expect(await lastValueFrom(scope.decisionWindows$)).toBe(windows);
    expect(dataService.getDecisionWindows).toHaveBeenCalledTimes(1);
  });

  it('shares a failed decision-window load without blocking the base context or retrying within the page', async () => {
    const failure = new Error('unavailable');
    dataService.getDecisionWindows.and.returnValue(throwError(() => failure));
    await expectAsync(lastValueFrom(scope.decisionWindows$)).toBeRejectedWith(failure);
    await expectAsync(lastValueFrom(scope.decisionWindows$)).toBeRejectedWith(failure);
    expect(dataService.getDecisionWindows).toHaveBeenCalledTimes(1);
    expect(await lastValueFrom(scope.context$)).toBe(context);
    const nextPage = TestBed.runInInjectionContext(() => new OverviewDataScope());
    dataService.getDecisionWindows.and.returnValue(of(windows));
    expect(await lastValueFrom(nextPage.decisionWindows$)).toBe(windows);
    expect(dataService.getDecisionWindows).toHaveBeenCalledTimes(2);
  });
});
