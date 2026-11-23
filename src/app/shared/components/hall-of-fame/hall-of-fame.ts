import { NgFor, NgIf } from '@angular/common';
import { Component, Input } from '@angular/core';

import { GlyphComponent } from '../glyph/glyph';
import { SharedMaterialImports } from '../../shared-material-imports';
import type { LeagueLegacyHighlight } from '../../utils/league-standings-view.util';

/**
 * Hall of Fame block: compact record cards that never break mid-word.
 * Reusable on its own (Stats today, possibly a dedicated page later, Issue #1621); it only renders the tiles it is given.
 */
@Component({
  selector: 'app-hall-of-fame',
  standalone: true,
  imports: [NgFor, NgIf, SharedMaterialImports, GlyphComponent],
  templateUrl: './hall-of-fame.html',
  styleUrl: './hall-of-fame.scss'
})
export class HallOfFameComponent {
  @Input({ required: true }) highlights: readonly LeagueLegacyHighlight[] | null | undefined;

  trackHighlight = (_: number, item: LeagueLegacyHighlight): string => item.key;
}
