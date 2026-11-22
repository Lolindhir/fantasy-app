import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { map } from 'rxjs/operators';

import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../../../core/models/season-statistics.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement, type TeamIdentitySubject } from '../../../../shared/components/team-identity/team-identity';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import { buildInjuryImpactByTeam, type InjuryImpactWeekBar, type TeamInjuryImpactView } from '../../../../shared/utils/injury-impact-view.util';
import { buildSeasonHistory } from '../../../../shared/utils/league-standings-view.util';
import {
  formatAllPlay,
  formatDecimal,
  formatSigned,
  signClass,
  statisticsByTeam
} from '../../../../shared/utils/season-statistics-view.util';

export interface SeasonStatsRow {
  teamId: string;
  place: number;
  identity: TeamIdentitySubject;
  record: string | null;
  stats: SeasonStatisticsTeam | null;
  injury: TeamInjuryImpactView | null;
}

type SortKey = 'place' | 'luck' | 'impact';

interface SeasonStatsViewModel {
  seasons: string[];
  defaultSeason: string | null;
  /** True when at least one season has Injury Impact; otherwise the column is hidden. */
  hasInjuryImpact: boolean;
  rows(season: string): SeasonStatsRow[];
}

const DEFAULT_AVATAR = 'assets/default-team-avatar.png';

/** Stats > Season: one row per team of the selected season (Issue #1621). Display only; every value comes from a data product. */
@Component({
  selector: 'app-stats-season-tab',
  standalone: true,
  imports: [CommonModule, RouterLink, TeamIdentityComponent, PositionStylePipe],
  templateUrl: './season-tab.html',
  styleUrl: './season-tab.scss'
})
export class SeasonTabComponent {
  private readonly dataService = inject(DataService);

  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'name'];
  readonly formatSigned = formatSigned;
  readonly formatDecimal = formatDecimal;
  readonly formatAllPlay = formatAllPlay;
  readonly signClass = signClass;

  selectedSeason: string | null = null;
  expandedTeamId: string | null = null;
  sortKey: SortKey = 'place';
  sortDescending = false;

  readonly vm$ = forkJoin({
    data: this.dataService.getLeagueWithPlayers(),
    injury: this.dataService.getInjuryImpact(),
    stats: this.dataService.getAllSeasonStatistics()
  }).pipe(
    map(({ data: { league, teams }, injury, stats }): SeasonStatsViewModel => {
      const history = buildSeasonHistory(league).seasons.filter(season => season.regularSeasonStandings.length > 0);
      const statsDocs = new Map<string, SeasonStatisticsReadModel>(stats.bySeason);
      if (stats.current) statsDocs.set(String(stats.current.Season), stats.current);
      const injurySeasons = new Map((injury?.Seasons ?? []).map(season => [String(season.Season), season]));
      const seasons = history.map(season => season.season).filter(season => statsDocs.has(season) || injurySeasons.has(season));
      const cache = new Map<string, SeasonStatsRow[]>();
      const currentTeams = new Map(teams.map(team => [String(team.TeamID), team]));

      return {
        seasons,
        defaultSeason: seasons.includes(String(league.Season)) ? String(league.Season) : (seasons[0] ?? null),
        hasInjuryImpact: injurySeasons.size > 0,
        rows: season => {
          const cached = cache.get(season);
          if (cached) return cached;
          const standings = history.find(item => item.season === season)?.regularSeasonStandings ?? [];
          const statsByTeam = statisticsByTeam(statsDocs.get(season)?.Teams);
          const injuryByTeam = buildInjuryImpactByTeam(injurySeasons.get(season));
          const isCurrent = season === String(league.Season);
          const rows = standings.map((row): SeasonStatsRow => {
            const teamId = String(row.teamId);
            const stat = statsByTeam.get(teamId) ?? null;
            return {
              teamId,
              place: row.place,
              // Season-specific identity; the current logo is only a fallback for the running season.
              identity: {
                TeamID: Number(row.teamId),
                Team: row.teamName ?? '',
                Owner: row.owner,
                Avatar: row.teamAvatar || (isCurrent ? currentTeams.get(teamId)?.Avatar : null) || DEFAULT_AVATAR
              },
              record: row.record,
              stats: stat && stat.Games > 0 ? stat : null,
              injury: injuryByTeam.get(teamId) ?? null
            };
          });
          cache.set(season, rows);
          return rows;
        }
      };
    })
  );

  activeSeason(vm: SeasonStatsViewModel): string | null {
    return this.selectedSeason && vm.seasons.includes(this.selectedSeason) ? this.selectedSeason : vm.defaultSeason;
  }

  selectSeason(season: string): void {
    this.selectedSeason = season;
    this.expandedTeamId = null;
    this.activeBar = null;
  }

  sortedRows(vm: SeasonStatsViewModel): SeasonStatsRow[] {
    const season = this.activeSeason(vm);
    if (!season) return [];
    const value = (row: SeasonStatsRow): number | null => {
      if (this.sortKey === 'luck') return row.stats?.Luck ?? null;
      if (this.sortKey === 'impact') return row.injury?.hurt ?? null;
      return row.place;
    };
    const direction = this.sortDescending ? -1 : 1;
    // Rows without a value always sort last, never as zero.
    return [...vm.rows(season)].sort((a, b) => {
      const left = value(a);
      const right = value(b);
      if (left === null && right === null) return a.place - b.place;
      if (left === null) return 1;
      if (right === null) return -1;
      return (left - right) * direction || a.place - b.place;
    });
  }

  sortBy(key: SortKey): void {
    if (this.sortKey === key) {
      this.sortDescending = !this.sortDescending;
      return;
    }
    this.sortKey = key;
    // Luck and Injury Impact start with the largest value, the place with the best (lowest) one.
    this.sortDescending = key !== 'place';
  }

  ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
    return this.sortKey !== key ? 'none' : this.sortDescending ? 'descending' : 'ascending';
  }

  toggle(row: SeasonStatsRow): void {
    this.expandedTeamId = this.expandedTeamId === row.teamId ? null : row.teamId;
    this.activeBar = null;
  }

  isExpanded(row: SeasonStatsRow): boolean {
    return this.expandedTeamId === row.teamId;
  }

  activeBar: InjuryImpactWeekBar | null = null;

  trackRow = (_: number, row: SeasonStatsRow): string => row.teamId;

  pickBar(bar: InjuryImpactWeekBar): void {
    this.activeBar = bar;
  }

  expectedWins(stat: SeasonStatisticsTeam | null): string {
    return formatDecimal(stat?.ExpectedWins ?? null);
  }
}
