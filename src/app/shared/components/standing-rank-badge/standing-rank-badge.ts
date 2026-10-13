import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-standing-rank-badge',
  standalone: true,
  templateUrl: './standing-rank-badge.html',
  styleUrl: './standing-rank-badge.scss'
})
export class StandingRankBadgeComponent {
  @Input({ required: true }) rank!: number;
}
