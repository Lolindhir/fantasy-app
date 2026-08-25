import { NgStyle } from '@angular/common';
import { Component, Input } from '@angular/core';

export type DraftPickPillVariant = 'chip' | 'round-pill';
export type DraftPickPillStyle = Record<string, any>;

@Component({
  selector: 'app-draft-pick-pill',
  standalone: true,
  imports: [NgStyle],
  templateUrl: './draft-pick-pill.html',
  styleUrl: './draft-pick-pill.scss'
})
export class DraftPickPillComponent {
  @Input({ required: true }) label!: string;
  @Input() variant: DraftPickPillVariant = 'chip';
  @Input() isTradedPick = false;
  @Input() interactive = false;
  @Input() pillStyle: DraftPickPillStyle = {};
}
