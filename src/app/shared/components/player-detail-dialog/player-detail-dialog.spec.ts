import { TestBed } from '@angular/core/testing';
import type { MatDialogRef } from '@angular/material/dialog';
import { of, Subject, throwError } from 'rxjs';

import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { Player } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import type { PlayerWeekProjectionView } from '../../utils/player-week-projection.util';
import { PlayerDetailDialogComponent } from './player-detail-dialog';

describe('PlayerDetailDialogComponent projection fallback', () => {
  const projection: PlayerWeekProjectionView = {
    season: 2026, week: 3, projection: null, projectedValue: 10,
    projectedText: '10', rangeText: null, levelLabel: null, result: null
  };
  const actual = { state: 'final' as const, pointsText: '0', tone: 'below' as const };
  const context = (status = 'final', week = 3, points = -2): FantasyGameContextReadModel => ({
    Season: '2026', Week: week,
    Games: [{ Status: status, FantasyTeams: [{ Players: [{ PlayerID: 'p1', Points: points }] }] }]
  } as unknown as FantasyGameContextReadModel);

  function create(view: PlayerWeekProjectionView | null, gameHistory: unknown[] = []) {
    const data = jasmine.createSpyObj<DataService>('DataService', [
      'getPlayerAwardHistory', 'getPlayerWeekProjections', 'getFantasyGameContextBase',
      'getFantasyGameContext', 'getMatchupProjections', 'getPlayerWeekFantasy'
    ]);
    data.getPlayerAwardHistory.and.returnValue(of(null));
    data.getPlayerWeekProjections.and.returnValue(of(new Map(view ? [['p1', view]] : [])));
    data.getFantasyGameContextBase.and.returnValue(of(context()));
    TestBed.configureTestingModule({ providers: [{ provide: DataService, useValue: data }] });
    const player = { ID: 'p1', GameHistory: gameHistory } as unknown as Player;
    const ref = jasmine.createSpyObj<MatDialogRef<PlayerDetailDialogComponent>>('MatDialogRef', ['close']);
    const component = TestBed.runInInjectionContext(() => new PlayerDetailDialogComponent(player, ref));
    return { component, data };
  }

  it('uses the published actual including zero, without any context or duplicate projection read', () => {
    const { component, data } = create({ ...projection, result: actual }, [
      { GameDetails: { Week: 3 }, FantasyPoints: 99 }
    ]);
    component.ngOnInit();
    expect(component.weekResult).toBe(actual);
    expect(data.getPlayerWeekProjections).toHaveBeenCalledTimes(1);
    expect(data.getFantasyGameContextBase).not.toHaveBeenCalled();
    expect(data.getFantasyGameContext).not.toHaveBeenCalled();
    expect(data.getPlayerWeekFantasy).not.toHaveBeenCalled();
    expect(data.getMatchupProjections).not.toHaveBeenCalled();
  });

  it('uses the matching Game Log result before the raw matchup fallback', () => {
    const { component, data } = create(projection, [
      { GameDetails: { Week: 3 }, FantasyPoints: -1 }
    ]);
    component.ngOnInit();
    expect(component.weekResult).toEqual({ state: 'game-log', pointsText: '-1', tone: 'below' });
    expect(data.getFantasyGameContextBase).not.toHaveBeenCalled();
  });

  it('reads only raw context when an existing record has no actual or Game Log result', () => {
    const { component, data } = create(projection);
    component.ngOnInit();
    expect(component.weekProjection).toBe(projection);
    expect(component.weekResult).toEqual({ state: 'matchup', pointsText: '-2', tone: 'below' });
    expect(data.getFantasyGameContextBase).toHaveBeenCalledTimes(1);
    expect(data.getFantasyGameContext).not.toHaveBeenCalled();
    expect(data.getMatchupProjections).not.toHaveBeenCalled();
    expect(data.getPlayerWeekFantasy).not.toHaveBeenCalled();
  });

  it('does not request context without a published player record', () => {
    const { component, data } = create(null);
    component.ngOnInit();
    expect(component.weekProjection).toBeNull();
    expect(component.weekResult).toBeNull();
    expect(data.getFantasyGameContextBase).not.toHaveBeenCalled();
  });

  it('retains the projection when raw context is unavailable', () => {
    const { component, data } = create(projection);
    data.getFantasyGameContextBase.and.returnValue(throwError(() => new Error('unavailable')));
    component.ngOnInit();
    expect(component.weekProjection).toBe(projection);
    expect(component.weekResult).toBeNull();
  });

  it('rejects scheduled placeholders and other-week context results', () => {
    const { component, data } = create(projection);
    const pending = new Subject<FantasyGameContextReadModel>();
    data.getFantasyGameContextBase.and.returnValue(pending);
    component.ngOnInit();
    pending.next(context('scheduled', 3, 0));
    expect(component.weekResult).toBeNull();
    pending.next(context('final', 4, 20));
    expect(component.weekResult).toBeNull();
    pending.complete();
  });
});
