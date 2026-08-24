import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-cap-usage-bar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cap-usage-bar.html',
  styleUrl: './cap-usage-bar.scss'
})
export class CapUsageBarComponent {
  @Input() label = '';
  @Input() value = 0;
  @Input() cap = 0;
  @Input() compact = false;
  @Input() showSpace = true;

  get utilization(): number {
    return this.cap > 0 ? (this.value / this.cap) * 100 : 0;
  }

  get barWidth(): number {
    return Math.max(0, Math.min(this.utilization, 100));
  }

  get capSpace(): number {
    return this.cap - this.value;
  }

  get isOverCap(): boolean {
    return this.capSpace < 0;
  }

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    const prefix = value < 0 ? '-' : '';
    if (absolute >= 1_000_000) {
      return `${prefix}$${(absolute / 1_000_000).toFixed(1)}m`;
    }
    if (absolute >= 1_000) {
      return `${prefix}$${(absolute / 1_000).toFixed(1)}k`;
    }
    return `${prefix}$${absolute.toFixed(0)}`;
  }
}
