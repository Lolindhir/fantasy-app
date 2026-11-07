import { TestBed } from '@angular/core/testing';

import { GlyphComponent } from './glyph';

describe('GlyphComponent', () => {
  function render(glyph: string): HTMLElement {
    const fixture = TestBed.createComponent(GlyphComponent);
    fixture.componentInstance.glyph = glyph;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('renders the championship ring instead of the trophy emoji', () => {
    const el = render('🏆');
    expect(el.querySelector('img')).not.toBeNull();
    expect(el.textContent).not.toContain('🏆');
  });

  it('renders other glyphs as text', () => {
    const el = render('👑');
    expect(el.querySelector('img')).toBeNull();
    expect(el.textContent).toContain('👑');
  });
});
