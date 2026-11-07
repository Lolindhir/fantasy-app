import { Component, Input } from '@angular/core';

import { GENERIC_CHAMPIONSHIP_RING_SRC } from '../../utils/championship.util';

/** Emoji glyph that renders the championship ring instead of the trophy emoji (#662). */
@Component({
  selector: 'app-glyph',
  standalone: true,
  template: `@if (isTrophy) {<img [src]="ring" alt="" aria-hidden="true" />} @else {{{ glyph }}}`,
  styles: [`
    :host { display: inline-flex; align-items: center; justify-content: center; vertical-align: middle; }
    img { width: 1.15em; height: 1.15em; object-fit: contain; display: block; }
  `]
})
export class GlyphComponent {
  @Input() glyph = '';
  readonly ring = GENERIC_CHAMPIONSHIP_RING_SRC;
  get isTrophy(): boolean { return this.glyph === '🏆'; }
}
