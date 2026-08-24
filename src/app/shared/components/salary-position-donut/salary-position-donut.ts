import { Component, Input } from '@angular/core';
import type { SalaryPositionBreakdown } from '../../utils/team-salary.util';

@Component({
  selector: 'app-salary-position-donut',
  standalone: true,
  templateUrl: './salary-position-donut.html',
  styleUrl: './salary-position-donut.scss'
})
export class SalaryPositionDonutComponent {
  @Input() segments: SalaryPositionBreakdown[] = [];
  @Input() total = 0;
  @Input() centerLabel = 'Team Salary';

  get gradient(): string {
    if (!this.segments.length || this.total <= 0) {
      return 'conic-gradient(#e5e7eb 0 100%)';
    }

    let cursor = 0;
    const stops = this.segments.map(segment => {
      const start = cursor;
      cursor += segment.percentage;
      return `${segment.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
    });
    return `conic-gradient(${stops.join(', ')})`;
  }

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    const prefix = value < 0 ? '-' : '';
    if (absolute >= 1_000_000) return `${prefix}$${(absolute / 1_000_000).toFixed(1)}m`;
    if (absolute >= 1_000) return `${prefix}$${(absolute / 1_000).toFixed(1)}k`;
    return `${prefix}$${absolute.toFixed(0)}`;
  }
}
