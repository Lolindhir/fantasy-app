import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import type { SalaryHistoryEntry } from '../../../core/models/player.models';

interface ChartPoint {
  label: string;
  x: number;
  y: number;
  value: number;
}

const WIDTH = 560;
const HEIGHT = 220;
const PAD = { left: 52, right: 20, top: 14, bottom: 30 };

/** Salary per league season (plus the projection for the next season) from the generator-owned history; presentation only. */
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

  /** Salary points; an unknown season breaks the line. */
  segments: ChartPoint[][] = [];
  points: ChartPoint[] = [];
  /** Dashed connection from the latest known salary to the projection. */
  projectionLine: ChartPoint[] = [];
  yTicks: { y: number; label: string }[] = [];
  xTicks: { x: number; label: string }[] = [];
  hasData = false;

  @Input() set history(value: readonly SalaryHistoryEntry[] | null | undefined) {
    this.build(value ?? []);
  }

  path(points: ChartPoint[]): string {
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  }

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    if (absolute >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}m`;
    if (absolute >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
    return `$${value.toFixed(0)}`;
  }

  private build(history: readonly SalaryHistoryEntry[]): void {
    const latest = history.length ? history[history.length - 1] : null;
    const projected = latest?.SalaryProjected ?? null;
    const known = history.filter(h => h.Salary != null);
    this.hasData = known.length > 0 && history.length + (projected != null ? 1 : 0) > 1;
    this.segments = [];
    this.points = [];
    this.projectionLine = [];
    this.yTicks = [];
    this.xTicks = [];
    if (!this.hasData || !latest) return;

    const slots = history.length + (projected != null ? 1 : 0);
    const values = [...known.map(h => h.Salary as number), ...(projected != null ? [projected] : [])];
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const span = maxValue - minValue || Math.max(maxValue, 1) * 0.1;
    const low = minValue - span * 0.15;
    const high = maxValue + span * 0.15;
    const xOf = (index: number) => PAD.left + (index / Math.max(slots - 1, 1)) * (WIDTH - PAD.left - PAD.right);
    const yOf = (value: number) => PAD.top + (1 - (value - low) / (high - low)) * (HEIGHT - PAD.top - PAD.bottom);

    let open: ChartPoint[] | null = null;
    history.forEach((h, index) => {
      this.xTicks.push({ x: xOf(index), label: String(h.Season) });
      if (h.Salary == null) {
        open = null;
        return;
      }
      const point = { label: String(h.Season), x: xOf(index), y: yOf(h.Salary), value: h.Salary };
      this.points.push(point);
      if (!open) {
        open = [];
        this.segments.push(open);
      }
      open.push(point);
    });

    if (projected != null) {
      const point = { label: `${latest.Season + 1} proj.`, x: xOf(slots - 1), y: yOf(projected), value: projected };
      this.xTicks.push({ x: point.x, label: point.label });
      const last = this.points.length && this.points[this.points.length - 1].label === String(latest.Season)
        ? this.points[this.points.length - 1]
        : null;
      this.projectionLine = last ? [last, point] : [point];
      this.points.push(point);
    }
    this.yTicks = [low + (high - low) * 0.1, (low + high) / 2, high - (high - low) * 0.1]
      .map(v => ({ y: yOf(v), label: this.formatMoney(v) }));
  }
}
