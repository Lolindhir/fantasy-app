import { Component, Inject, OnInit, ViewEncapsulation, importProvidersFrom } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Player, PointHistory, PointHistorySeason } from '../services/data-service'; // Pfad ggf. anpassen
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartOptions } from 'chart.js';
import { Chart, Filler, BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Title, Tooltip, Legend } from 'chart.js';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';

// Registrierung
Chart.register(LineController, Filler, LineElement, PointElement, LinearScale, CategoryScale, BarController, BarElement, Title, Tooltip, Legend);

@Component({
  selector: 'app-player-detail-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule,
    BaseChartDirective,
    MatDialogModule,
    MatTabsModule,
    MatTableModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    SharedMaterialImports
  ],
  templateUrl: './player-detail-dialog.html',
  styleUrls: ['./player-detail-dialog.scss']
})
export class PlayerDetailDialogComponent implements OnInit {
  chartData?: ChartConfiguration<'line'>['data'];
  chartOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: { mode: 'index', intersect: false },
      title: { display: true, text: 'Fantasy Points Entwicklung' }
    },
    elements: { line: { tension: 0.3 } },
    scales: {
      x: { title: { display: true, text: 'Season' } },
      y: { title: { display: true, text: 'Fantasy Points / Game' }, beginAtZero: true }
    }
  };

  constructor(
    @Inject(MAT_DIALOG_DATA) public player: Player,
    private dialogRef: MatDialogRef<PlayerDetailDialogComponent>
  ) {}

  ngOnInit(): void {
    this.prepareChart();
  }

  close(): void {
    this.dialogRef.close();
  }

  private prepareChart(): void {
    const hist = this.player.Stats?.PointHistory;
    if (!hist) return;

    const seasons = Object.values(hist)
      .filter((s): s is { Season: number } => !!s?.Season)
      .map(s => s.Season.toString())
      .reverse();

    const avgGames = Object.values(hist)
      .filter((s): s is { AvgGame: number } => s != null)
      .map(s => s.AvgGame)
      .reverse();

    this.chartData = {
      labels: seasons,
      datasets: [
        {
          data: avgGames,
          borderColor: '#3f51b5',
          backgroundColor: 'rgba(63,81,181,0.1)',
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.3
        }
      ]
    };
  }

  get rankingTotal(): number | undefined {
    return this.player.Stats?.Ranking.find(r => r.Type === 'Total')?.Value;
  }

  get rankingCombined(): number | undefined {
    return this.player.Stats?.Ranking.find(r => r.Type === 'Combined')?.Value;
  }

  get rankingCombinedPosition(): number | undefined {
    return this.player.Stats?.Ranking.find(r => r.Type === 'Combined_Pos')?.Value;
  }

  get teamLogo(): string {
    return this.player.TeamNFL?.Logo || 'assets/nfl-logo.svg';
  }

  getDefinedSeasons(hist: PointHistory | undefined): PointHistorySeason[] {
    if (!hist) return [];
    return [hist.SeasonMinus1, hist.SeasonMinus2, hist.SeasonMinus3].filter(
      (s): s is PointHistorySeason => !!s
    );
  }

}
