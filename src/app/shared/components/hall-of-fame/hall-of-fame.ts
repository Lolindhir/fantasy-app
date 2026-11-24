import { NgFor, NgIf } from '@angular/common';
import { Component, Input } from '@angular/core';

import { GlyphComponent } from '../glyph/glyph';
import { MatTooltipModule } from '@angular/material/tooltip';
import type { LeagueLegacyHighlight } from '../../utils/league-standings-view.util';

/**
 * Hall of Fame block: compact record cards that never break mid-word.
 * Used by the Hall of Fame page (Issue #1621) once per record group; it only renders the tiles it is given.
 */
@Component({
  selector: 'app-hall-of-fame',
  standalone: true,
  imports: [NgFor, NgIf, MatTooltipModule, GlyphComponent],
  templateUrl: './hall-of-fame.html',
  styleUrl: './hall-of-fame.scss'
})
export class HallOfFameComponent {
  @Input() heading = 'Hall of Fame';
  @Input() crest = '🏛️';
  @Input({ required: true }) highlights: readonly LeagueLegacyHighlight[] | null | undefined;

  trackHighlight = (_: number, item: LeagueLegacyHighlight): string => item.key;
}
