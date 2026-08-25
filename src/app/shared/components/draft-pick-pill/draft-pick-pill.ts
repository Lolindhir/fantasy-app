import { Component, Input } from '@angular/core';

export type DraftPickPillVariant = 'chip' | 'round-pill';

@Component({
  selector: 'app-draft-pick-pill',
  standalone: true,
  templateUrl: './draft-pick-pill.html',
  styleUrl: './draft-pick-pill.scss'
})
export class DraftPickPillComponent {
  @Input({ required: true }) label!: string;
  @Input() variant: DraftPickPillVariant = 'chip';
  @Input() isTradedPick = false;
  @Input() interactive = false;
}
