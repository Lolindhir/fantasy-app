import { TestBed } from '@angular/core/testing';

import { WinChanceBarComponent } from './win-chance-bar';

describe('WinChanceBarComponent', () => {
  function create(inputs: Partial<Pick<WinChanceBarComponent, 'left' | 'right' | 'leftRaw' | 'rightRaw' | 'deterministic' | 'estimated'>>): HTMLElement {
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

  it('distinguishes an extremely unlikely open comeback from a guaranteed result', () => {
    const host = create({
      left: 0, right: 100,
      leftRaw: 0.00000000806, rightRaw: 0.99999999194,
      deterministic: false
    });
    expect(host.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('<1%');
    expect(host.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('>99%');
    expect(host.querySelector('.win-chance')?.getAttribute('aria-label')).toContain('less than 1 percent');
    expect(host.querySelector('.win-chance')?.getAttribute('aria-label')).toContain('greater than 99 percent');
  });

  it('keeps exact 0/100 when no scoring variance remains', () => {
    const host = create({ left: 0, right: 100, leftRaw: 0, rightRaw: 1, deterministic: true });
    expect(host.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('0%');
    expect(host.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('100%');
  });

  it('uses the raw tails even when floating-point rounding saturates to 0/1', () => {
    const host = create({ left: 0, right: 100, leftRaw: 0, rightRaw: 1, deterministic: false });
    expect(host.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('<1%');
    expect(host.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('>99%');
  });

  it('keeps whole percentages for ordinary chances', () => {
    const host = create({ left: 64, right: 36, leftRaw: 0.643, rightRaw: 0.357 });
    expect(host.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('64%');
    expect(host.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('36%');
  });

  it('labels a fallback chance as estimated without altering delivered percentages', () => {
    const estimate = create({ left: 59, right: 41, estimated: true });
    expect(estimate.querySelector('.win-chance-estimate')?.textContent?.trim()).toBe('EST.');
    expect(estimate.querySelector('.win-chance-value--left')?.textContent?.trim()).toBe('59%');
    expect(estimate.querySelector('.win-chance-value--right')?.textContent?.trim()).toBe('41%');
    expect(estimate.querySelector('.win-chance')?.getAttribute('aria-label')).toContain('Estimated win chance');

    const lineup = create({ left: 59, right: 41 });
    expect(lineup.querySelector('.win-chance-estimate')).toBeNull();
    expect(lineup.querySelector('.win-chance')?.getAttribute('aria-label')).toContain('Win chance:');
  });

  it('colors the side with the higher chance and keeps the sides fixed', () => {
    const left = create({ left: 30, right: 70 });
    expect(left.querySelector('.win-chance-fill--left')?.classList).not.toContain('win-chance-fill--lead');
    expect(left.querySelector('.win-chance-fill--right')?.classList).toContain('win-chance-fill--lead');
    const right = create({ left: 62, right: 38 });
    expect(right.querySelector('.win-chance-fill--left')?.classList).toContain('win-chance-fill--lead');
    const even = create({ left: 50, right: 50 });
    expect(even.querySelectorAll('.win-chance-fill--lead').length).toBe(0);
  });
});
