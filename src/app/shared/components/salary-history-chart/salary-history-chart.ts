import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import type { SalaryHistoryEntry } from '../../../core/models/player.models';

interface ChartPoint {
  week: number;
  x: number;
  y: number;
  value: number;
}

interface ChartLine {
  /** Consecutive known weeks; an unknown week breaks the line. */
  segments: ChartPoint[][];
  points: ChartPoint[];
}

const WIDTH = 560;
const HEIGHT = 220;
const PAD = { left: 52, right: 14, top: 14, bottom: 30 };

/** Salary curve of the current season from the generator-owned weekly history (presentation only). */
@Component({
  selector: 'app-salary-history-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './salary-history-chart.html',
  styleUrl: './salary-history-chart.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SalaryHistoryChartComponent {
  readonly width = WIDTH;
  readonly height = HEIGHT;
  readonly plotBottom = HEIGHT - PAD.bottom;
  readonly plotLeft = PAD.left;
  readonly plotRight = WIDTH - PAD.right;

  projected: ChartLine = { segments: [], points: [] };
  current: ChartLine = { segments: [], points: [] };
  yTicks: { y: number; label: string }[] = [];
  xTicks: { x: number; label: string }[] = [];
  hasData = false;

  @Input() set history(value: readonly SalaryHistoryEntry[] | null | undefined) {
    this.build(value ?? []);
  }

  path(segment: ChartPoint[]): string {
    return segment.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  }

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    if (absolute >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}m`;
    if (absolute >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
    return `$${value.toFixed(0)}`;
  }

  private build(history: readonly SalaryHistoryEntry[]): void {
    const values = history.flatMap(h => [h.Salary, h.SalaryProjected]).filter((v): v is number => v != null);
    this.hasData = values.length > 0 && history.length > 1;
    if (!this.hasData) {
      this.projected = { segments: [], points: [] };
      this.current = { segments: [], points: [] };
      this.yTicks = [];
      this.xTicks = [];
      return;
    }
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const span = maxValue - minValue || Math.max(maxValue, 1) * 0.1;
    const low = minValue - span * 0.1;
    const high = maxValue + span * 0.1;
    const firstWeek = history[0].Week;
    const lastWeek = history[history.length - 1].Week;
    const xOf = (week: number) => PAD.left + ((week - firstWeek) / Math.max(lastWeek - firstWeek, 1)) * (WIDTH - PAD.left - PAD.right);
    const yOf = (value: number) => PAD.top + (1 - (value - low) / (high - low)) * (HEIGHT - PAD.top - PAD.bottom);

    const line = (pick: (h: SalaryHistoryEntry) => number | null): ChartLine => {
      const segments: ChartPoint[][] = [];
      const points: ChartPoint[] = [];
      let open: ChartPoint[] | null = null;
      for (const h of history) {
        const value = pick(h);
        if (value == null) {
          open = null;
          continue;
        }
        const point = { week: h.Week, x: xOf(h.Week), y: yOf(value), value };
        points.push(point);
        if (!open) {
          open = [];
          segments.push(open);
        }
        open.push(point);
      }
      return { segments, points };
    };

    this.projected = line(h => h.SalaryProjected);
    this.current = line(h => h.Salary);
    this.yTicks = [low + (high - low) * 0.1, (low + high) / 2, high - (high - low) * 0.1]
      .map(v => ({ y: yOf(v), label: this.formatMoney(v) }));
    this.xTicks = history.map(h => ({ x: xOf(h.Week), label: h.Week === 0 ? 'Start' : `W${h.Week}` }));
  }
}
