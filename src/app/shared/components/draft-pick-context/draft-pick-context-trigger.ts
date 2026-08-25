import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';

import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { DraftPickPillComponent, type DraftPickPillVariant } from '../draft-pick-pill/draft-pick-pill';
import type { DraftPickContext } from './draft-pick-context.models';
import { DraftPickContextPopoverComponent } from './draft-pick-context-popover';

@Component({
  selector: 'app-draft-pick-context-trigger',
  standalone: true,
  imports: [MatMenuModule, PositionStylePipe, DraftPickPillComponent, DraftPickContextPopoverComponent],
  templateUrl: './draft-pick-context-trigger.html',
  styleUrl: './draft-pick-context-trigger.scss'
})
export class DraftPickContextTriggerComponent {
  @Input({ required: true }) context!: DraftPickContext;
  @Input() variant: DraftPickPillVariant = 'chip';
  @Input() usePickedPositionColor = false;

  get usePositionColor(): boolean {
    return this.usePickedPositionColor && !!this.context.selectedPlayer?.Position;
  }
}
