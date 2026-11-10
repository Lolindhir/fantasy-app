import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit, ViewEncapsulation, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule, type MatTabChangeEvent } from '@angular/material/tabs';
import { Chart, Filler, BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Title, Tooltip, Legend } from 'chart.js';
import type { ChartConfiguration, ChartOptions } from 'chart.js';

import type { Player, PointHistorySeason, PlayerStats } from '../../../core/models/fantasy.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { DataService } from '../../../core/services/data.service';
import { formatPlayerPositionDepth } from '../../utils/player-sort.util';
import { buildPlayerJourney, type PlayerJourney, type PlayerJourneyEvent } from '../../utils/player-journey.util';
import { resolveWeekResult, type PlayerWeekProjectionView, type PlayerWeekResultView } from '../../utils/player-week-projection.util';
import { PlayerProjectionComponent } from '../projection-range/player-projection';

// Registrierung
Chart.register(LineController, Filler, LineElement, PointElement, LinearScale, CategoryScale, BarController, BarElement, Title, Tooltip, Legend);

@Component({
  selector: 'app-player-detail-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule,
    MatDialogModule,
    MatTabsModule,
    MatTableModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    PositionStylePipe,
    PlayerProjectionComponent
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

  private readonly dataService = inject(DataService);

  /** Published projection of the current App week; null while loading or when the player has no record. */
  weekProjection: PlayerWeekProjectionView | null = null;
  /** Real points of that week: the published Actual, else the Game Log entry of the same week. */
  weekResult: PlayerWeekResultView | null = null;
  journey: PlayerJourney | null = null;
  journeyState: 'idle' | 'loading' | 'ready' | 'error' = 'idle';

  constructor(
    @Inject(MAT_DIALOG_DATA) public player: Player,
    private dialogRef: MatDialogRef<PlayerDetailDialogComponent>
  ) {}

  ngOnInit(): void {
    this.prepareChart();
    this.dataService.getPlayerWeekProjections().subscribe(projections => {
      this.weekProjection = projections.get(String(this.player.ID)) ?? null;
      this.weekResult = resolveWeekResult(this.weekProjection, this.player.GameHistory);
    });
  }

  onTabChange(event: MatTabChangeEvent): void {
    if (event.tab.textLabel === 'Moves') this.loadJourney();
  }

  private loadJourney(): void {
    if (this.journeyState !== 'idle') return;
    this.journeyState = 'loading';
    this.dataService.getPlayerJourneySources().subscribe({
      next: ({ transactions, drafts, teams }) => {
        this.journey = buildPlayerJourney(this.player.ID, transactions, drafts, teams);
        this.journeyState = 'ready';
      },
      error: () => {
        this.journeyState = 'error';
      }
    });
  }

  journeyIcon(event: PlayerJourneyEvent): string {
    switch (event.kind) {
      case 'drafted': return 'emoji_events';
      case 'traded': return 'swap_horiz';
      case 'added': return 'person_add';
      case 'dropped': return 'person_remove';
    }
  }

  journeyTitle(event: PlayerJourneyEvent): string {
    switch (event.kind) {
      case 'drafted': return 'Drafted';
      case 'traded': return 'Traded';
      case 'added': return 'Added';
      case 'dropped': return 'Dropped';
    }
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

  get positionDepthLabel(): string {
    return formatPlayerPositionDepth(this.player);
  }

  get teamLogo(): string {
    return this.player.TeamNFL?.Logo || 'assets/nfl-logo.svg';
  }

  getDefinedSeasons(stats: PlayerStats | undefined): PointHistorySeason[] {
    if (!stats) return [];

    const seasons: (PointHistorySeason | undefined)[] = [
      {
        Season: stats.PointHistory.SeasonMinus1.Season + 1,
        GamesPlayed: stats.GamesPlayed,
        PotentialGames: stats.GamesPotential,
        Total: stats.FantasyPointsTotal,
        AvgGame: stats.FantasyPointsAvgGame,
        AvgPotentialGame: stats.FantasyPointsAvgPotentialGame
        // ggf. weitere Werte übernehmen
      },
      stats.PointHistory.SeasonMinus1,
      stats.PointHistory.SeasonMinus2,
      stats.PointHistory.SeasonMinus3,
    ];

    // Filtert undefined raus
    return seasons.filter((s): s is PointHistorySeason => !!s);
  }
}
