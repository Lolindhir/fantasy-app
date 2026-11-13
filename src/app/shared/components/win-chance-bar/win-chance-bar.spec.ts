import { TestBed } from '@angular/core/testing';

import { WinChanceBarComponent } from './win-chance-bar';

describe('WinChanceBarComponent', () => {
  function create(inputs: Partial<Pick<WinChanceBarComponent, 'left' | 'right'>>): HTMLElement {
    const fixture = TestBed.createComponent(WinChanceBarComponent);
    Object.assign(fixture.componentInstance, { left: 0, right: 0, ...inputs });
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('displays exactly the delivered percents and highlights the favorite', () => {
    const host = create({ left: 64, right: 36 });

    expect(host.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('64%');
    expect(host.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('36%');
    expect(host.querySelector('.win-chance-value--left')?.classList).toContain('win-chance-value--lead');
    expect(host.querySelector('.win-chance-value--right')?.classList).not.toContain('win-chance-value--lead');
    expect(host.querySelector('.win-chance')?.getAttribute('aria-label')).toContain('64 percent');
  });
});
