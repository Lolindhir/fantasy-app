import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AboutComponent } from './about';

describe('Handbook navigation', () => {
  it('opens the Overview first, then supports safe deep links', () => {
    TestBed.configureTestingModule({});
    const params = new BehaviorSubject(convertToParamMap({}));
    const get = jasmine.createSpy('get').and.callFake((url: string) => of('# ' + url));
    const navigate = jasmine.createSpy('navigate').and.returnValue(Promise.resolve(true));
    const component = TestBed.runInInjectionContext(() => new AboutComponent(
      { get } as unknown as HttpClient,
      { queryParamMap: params.asObservable() } as unknown as ActivatedRoute,
      { navigate } as unknown as Router
    ));

    component.ngOnInit();
    expect(component.tabs[0].id).toBe('Overview');
    expect(component.tabs[1].id).toBe('league-philosophy');
    expect(component.selectedTab).toBe('Overview');
    expect(get).toHaveBeenCalledWith('docs/Overview.md', { responseType: 'text' });

    params.next(convertToParamMap({ section: 'Projections_Explanation' }));
    expect(component.selectedTab).toBe('Projections_Explanation');
    expect(get).toHaveBeenCalledWith('docs/Projections_Explanation.md', { responseType: 'text' });

    params.next(convertToParamMap({ section: '../secret' }));
    expect(component.selectedTab).toBe('Overview');
    expect(get).not.toHaveBeenCalledWith('docs/../secret.md', jasmine.anything());

    component.selectTab('league-philosophy');
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({
      queryParams: { section: 'league-philosophy' },
      queryParamsHandling: 'merge'
    }));
    const before = navigate.calls.count();
    component.selectTab('../secret');
    expect(navigate.calls.count()).toBe(before);
  });
});
