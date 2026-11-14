import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AboutComponent } from './about';

describe('Handbook navigation', () => {
  it('keeps one grouped page registry for mobile and desktop', () => {
    TestBed.configureTestingModule({});
    const component = TestBed.runInInjectionContext(() => new AboutComponent(
      { get: () => of('# Test') } as unknown as HttpClient,
      { queryParamMap: of(convertToParamMap({})) } as unknown as ActivatedRoute,
      { navigate: () => Promise.resolve(true) } as unknown as Router
    ));

    expect(component.groups.map(group => group.title)).toEqual([
      'Einstieg', 'Liga-Regeln', 'Daten & Analysen'
    ]);
    expect(component.tabs.map(tab => tab.id)).toEqual(component.groups.flatMap(group =>
      group.pages.map(page => page.id)
    ));
    expect(new Set(component.tabs.map(tab => tab.id)).size).toBe(component.tabs.length);
    expect(component.tabs[0].id).toBe('Overview');
    expect(component.tabs[1].id).toBe('league-philosophy');
    expect(component.mobileSelectionLabel).toBe('Themen wählen');
    expect(component.menuOpen).toBeFalse();
  });

  it('opens the Overview by default and preserves safe page deep links', () => {
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
    expect(component.selectedTab).toBe('Overview');
    expect(get).toHaveBeenCalledWith('docs/Overview.md', { responseType: 'text' });

    component.toggleMenu();
    expect(component.menuOpen).toBeTrue();
    params.next(convertToParamMap({ section: 'Projections_Explanation' }));
    expect(component.selectedTab).toBe('Projections_Explanation');
    expect(component.mobileSelectionLabel).toBe('Prognosen & Siegchancen');
    expect(component.menuOpen).toBeFalse();
    expect(get).toHaveBeenCalledWith('docs/Projections_Explanation.md', { responseType: 'text' });

    component.toggleMenu();
    component.selectTab('league-philosophy');
    expect(component.menuOpen).toBeFalse();
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({
      queryParams: { section: 'league-philosophy' },
      queryParamsHandling: 'merge'
    }));

    component.toggleMenu();
    component.closeMenu();
    expect(component.menuOpen).toBeFalse();

    params.next(convertToParamMap({ section: '../secret' }));
    expect(component.selectedTab).toBe('Overview');
    expect(get).not.toHaveBeenCalledWith('docs/../secret.md', jasmine.anything());

    const before = navigate.calls.count();
    component.selectTab('../secret');
    expect(navigate.calls.count()).toBe(before);

    component.selectTab('Overview');
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({
      queryParams: { section: null }
    }));
  });
});
