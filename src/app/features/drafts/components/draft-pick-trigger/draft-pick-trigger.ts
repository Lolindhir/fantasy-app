import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { DraftPickPillComponent } from '../../../../shared/components/draft-pick-pill/draft-pick-pill';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import { DraftPickPopoverComponent } from '../draft-pick-popover/draft-pick-popover';
import type {
  CompactRoundPickViewModel,
  DraftPickViewModel,
  DraftViewModel,
  TeamDisplayViewModel
} from '../../models/drafts-view.models';

export type DraftPickTriggerVariant = 'chip' | 'round-pill';

@Component({
  selector: 'app-draft-pick-trigger',
  standalone: true,
  imports: [CommonModule, MatMenuModule, DraftPickPillComponent, PositionStylePipe, DraftPickPopoverComponent],
  templateUrl: './draft-pick-trigger.html',
  styleUrl: './draft-pick-trigger.scss'
})
export class DraftPickTriggerComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input() item?: DraftPickViewModel;
  @Input() compactPick?: CompactRoundPickViewModel;
  @Input() currentOwner?: TeamDisplayViewModel;
  @Input() variant: DraftPickTriggerVariant = 'chip';
  @Input() usePickedPositionColor = false;

  get label(): string {
    return this.item?.pick.DisplayPick ?? this.compactPick?.label ?? 'Pick';
  }

  get isTradedPick(): boolean {
    return this.item?.isCurrentlyTraded ?? this.compactPick?.isCurrentlyTraded ?? false;
  }

  get roundColor(): string | undefined {
    return this.item?.roundColor ?? this.compactPick?.color;
  }

  get selectedPlayerPosition(): string | null | undefined {
    return this.item?.selectedPlayer?.Position;
  }

  get usePositionColor(): boolean {
    return this.usePickedPositionColor && !!this.selectedPlayerPosition;
  }
}
