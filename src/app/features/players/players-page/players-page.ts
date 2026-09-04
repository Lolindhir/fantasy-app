import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { DataService } from '../../../core/services/data.service';
import type { Player } from '../../../core/models/fantasy.models';
import { SharedMaterialImports } from '../../../shared/shared-material-imports';
import { PlayerListColumn, PlayerListComponent } from '../../../shared/components/player-list/player-list';
import { comparePlayersByDepthChart } from '../../../shared/utils/player-sort.util';

type PlayerMarketFilter =
  | 'all'
  | 'available'
  | 'freeAgents'
  | 'projectedCapCuts'
  | 'rostered';

type PlayerSortOption =
  | 'salaryDesc'
  | 'salaryProjectedDesc'
  | 'pointsDesc'
  | 'lastYearPointsDesc'
  | 'avgPointsDesc'
  | 'lastYearAvgPointsDesc'
  | 'depthAsc'
  | 'ageAsc'
  | 'ageDesc'
  | 'nameAsc'
  | 'nameDesc';

@Component({
  selector: 'app-players-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SharedMaterialImports,
    PlayerListComponent
  ],
  templateUrl: './players-page.html',
  styleUrls: ['./players-page.scss']
})
export class PlayersPageComponent implements OnInit {

  isMobile = window.innerWidth <= 600;

  allPlayers: Player[] = [];
  filteredPlayers: Player[] = [];
  players: Player[] = [];

  timestamp: string | undefined;

  searchText = '';
  selectedPosition = 'ALL';

  // Default: All Players
  marketFilter: PlayerMarketFilter = 'all';

  // Default: Salary
  sortOption: PlayerSortOption = 'salaryDesc';

  showProjectedSalary = false;
  showProjectedMarket = false;

  visibleCount = 100;
  visibleStep = 100;

  positions: string[] = ['ALL', 'FLEX', 'QB', 'RB', 'WR', 'TE', 'K'];

  desktopColumns: PlayerListColumn[] = [
    'rank',
    'picture',
    'name',
    'position',
    'team',
    'salary',
    'salaryProjected',
    'dynamicStat',
    'fantasyTeam'
  ];

  // Mobile: Owner statt Market
  mobileColumns: PlayerListColumn[] = [
    'rank',
    'name',
    'salary',
    'dynamicStat',
    'fantasyTeam'
  ];

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    this.dataService.getLeagueWithPlayers(['Salary']).subscribe(({ players }) => {
      this.allPlayers = players;
      this.applyFilters();
    });

    this.dataService.getLatestTimestamp().subscribe(ts => {
      this.timestamp = ts;
    });
  }

  @HostListener('window:resize')
  onResize(): void {
    const newIsMobile = window.innerWidth <= 600;

    if (newIsMobile !== this.isMobile) {
      this.isMobile = newIsMobile;
    }
  }

  get columns(): PlayerListColumn[] {
    if (this.isMobile) {
      return this.showProjectedSalary
        ? ['rank', 'name', 'salaryProjected', 'dynamicStat', 'fantasyTeam']
        : this.mobileColumns;
    }

    if (this.showProjectedSalary) {
      return [
        'rank',
        'picture',
        'name',
        'position',
        'team',
        'salaryProjected',
        'salary',
        'dynamicStat',
        'fantasyTeam'
      ];
    }

    return this.desktopColumns;
  }

  get hasMorePlayers(): boolean {
    return this.players.length < this.filteredPlayers.length;
  }

  get remainingPlayersCount(): number {
    return Math.max(this.filteredPlayers.length - this.players.length, 0);
  }

  applyFilters(): void {
    this.visibleCount = 100;

    let result = [...this.allPlayers];

    result = this.applySearchFilter(result);
    result = this.applyPositionFilter(result);
    result = this.applyMarketFilter(result);
    result = this.applySort(result);

    this.filteredPlayers = result;
    this.refreshVisiblePlayers();
  }

  showMore(): void {
    this.visibleCount += this.visibleStep;
    this.refreshVisiblePlayers();
  }

  resetFilters(): void {
    this.searchText = '';
    this.selectedPosition = 'ALL';
    this.marketFilter = 'all';
    this.sortOption = 'salaryDesc';
    this.showProjectedSalary = false;
    this.showProjectedMarket = false;

    this.applyFilters();
  }

  get dynamicColumnHeader(): string {
    switch (this.sortOption) {

      case 'salaryProjectedDesc':
        return 'Proj.';

      case 'pointsDesc':
        return 'Pts';

      case 'avgPointsDesc':
        return 'Avg';

      case 'lastYearPointsDesc':
        return 'LS Pts';

      case 'lastYearAvgPointsDesc':
        return 'LS Avg';

      case 'ageAsc':
      case 'ageDesc':
        return 'Age';

      default:
        return 'Age';
    }
  }

  getDynamicColumnValue = (player: Player): string => {
    switch (this.sortOption) {
      
      case 'salaryProjectedDesc':
        return player.SalaryProjectedDisplay;

      case 'pointsDesc':
        return `${player.Stats.FantasyPointsTotal.toFixed(1)} pts`;

      case 'avgPointsDesc':
        return `${player.Stats.FantasyPointsAvgGame.toFixed(1)} pts/g`;

      case 'lastYearPointsDesc':
        return `${this.getLastYearPoints(player).toFixed(1)} pts`;

      case 'lastYearAvgPointsDesc':
        return `${this.getLastYearAvgPoints(player).toFixed(1)} pts/g`;

      case 'ageAsc':
      case 'ageDesc':
        return `${player.Age}`;

      default:
        return `${player.Age}`;
    }
  };

  private refreshVisiblePlayers(): void {
    this.players = this.filteredPlayers.slice(0, this.visibleCount);
  }

  private applySearchFilter(players: Player[]): Player[] {
    const search = this.searchText.trim().toLowerCase();

    if (!search) {
      return players;
    }

    return players.filter(player =>
      player.Name.toLowerCase().includes(search) ||
      player.NameShort.toLowerCase().includes(search) ||
      player.Position.toLowerCase().includes(search) ||
      player.TeamNFL?.Abv?.toLowerCase().includes(search) ||
      player.TeamFantasy?.Owner?.toLowerCase().includes(search) ||
      player.TeamFantasy?.Team?.toLowerCase().includes(search)
    );
  }

  private applyPositionFilter(players: Player[]): Player[] {
    if (this.selectedPosition === 'ALL') {
      return players;
    }

    if (this.selectedPosition === 'FLEX') {
      return players.filter(player =>
        player.Position === 'RB' ||
        player.Position === 'WR' ||
        player.Position === 'TE'
      );
    }

    return players.filter(player => player.Position === this.selectedPosition);
  }

  private applyMarketFilter(players: Player[]): Player[] {
    switch (this.marketFilter) {
      case 'available':
        return players.filter(player =>
          this.showProjectedMarket
            ? player.IsFreeAgentDraftAvailableProjected
            : player.IsFreeAgentDraftAvailable
        );

      case 'freeAgents':
        return players.filter(player => player.IsFantasyFreeAgent);

      case 'projectedCapCuts':
        return players.filter(player =>
          this.showProjectedMarket
            ? player.FreeAgentMarketInfoProjected?.Status === 'ProjectedCapCut'
            : player.FreeAgentMarketInfo?.Status === 'ProjectedCapCut'
        );

      case 'rostered':
        return players.filter(player => !player.IsFantasyFreeAgent);

      case 'all':
      default:
        return players;
    }
  }

  private applySort(players: Player[]): Player[] {
    return [...players].sort((a, b) => {
      switch (this.sortOption) {
        case 'salaryProjectedDesc':
          return (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);

        case 'pointsDesc':
          return this.getPoints(b) - this.getPoints(a);

        case 'lastYearPointsDesc':
          return this.getLastYearPoints(b) - this.getLastYearPoints(a);

        case 'avgPointsDesc':
          return this.getAvgPoints(b) - this.getAvgPoints(a);

        case 'lastYearAvgPointsDesc':
          return this.getLastYearAvgPoints(b) - this.getLastYearAvgPoints(a);

        case 'depthAsc':
          return comparePlayersByDepthChart(a, b);

        case 'ageAsc':
          return this.compareAge(a, b);

        case 'ageDesc':
          return this.compareAge(b, a);

        case 'nameAsc':
          return this.compareName(a, b);

        case 'nameDesc':
          return this.compareName(b, a);

        case 'salaryDesc':
        default:
          return (b.Salary ?? 0) - (a.Salary ?? 0);
      }
    });
  }

  private compareName(a: Player, b: Player): number {
    return a.NameLast.localeCompare(b.NameLast, 'en', { sensitivity: 'base' }) ||
      a.NameFirst.localeCompare(b.NameFirst, 'en', { sensitivity: 'base' }) ||
      a.ID.localeCompare(b.ID);
  }

  private compareAge(a: Player, b: Player): number {
    return (a.Age ?? 999) - (b.Age ?? 999) ||
      this.compareName(a, b);
  }

  private getPoints(player: Player): number {
    return player.Stats?.FantasyPointsTotal ?? 0;
  }

  private getLastYearPoints(player: Player): number {
    return player.Stats?.PointHistory?.SeasonMinus1?.Total ?? 0;
  }

  private getAvgPoints(player: Player): number {
    return player.Stats?.FantasyPointsAvgGame ?? 0;
  }

  private getLastYearAvgPoints(player: Player): number {
    return player.Stats?.PointHistory?.SeasonMinus1?.AvgGame ?? 0;
  }
}
