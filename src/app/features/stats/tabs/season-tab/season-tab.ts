import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../../../core/models/season-statistics.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement, type TeamIdentitySubject } from '../../../../shared/components/team-identity/team-identity';
import { TeamSeasonService } from '../../../../shared/services/team-season.service';
import { PositionStylePipe } from '../../../../shared/pipes/position-style.pipe';
import { buildInjuryImpactByTeam, type TeamInjuryImpactView } from '../../../../shared/utils/injury-impact-view.util';
import { buildSeasonHistory } from '../../../../shared/utils/league-standings-view.util';
import {
  buildSeasonUpsetCard,
  formatAllPlay,
  formatDecimal,
  formatPercent,
  formatSigned,
  signClass,
  statisticsByTeam,
  type SeasonUpsetCard
} from '../../../../shared/utils/season-statistics-view.util';

export interface SeasonStatsRow {
  teamId: string;
  place: number;
  identity: TeamIdentitySubject;
  record: string | null;
  stats: SeasonStatisticsTeam | null;
  injury: TeamInjuryImpactView | null;
}

/** Column groups of the table; on small screens one group is shown at a time (Issue #1621). */
export type StatsGroup = 'record' | 'injury' | 'efficiency';

export type SortKey = 'place' | 'record' | 'expected' | 'luck' | 'hurt' | 'lost' | 'lineup' | 'delta';

interface GroupOption {
  id: StatsGroup;
  label: string;
}

interface SeasonStatsViewModel {
  seasons: string[];
  defaultSeason: string | null;
  /** True when at least one season has Injury Impact; otherwise the group is hidden. */
  hasInjuryImpact: boolean;
  /** True when any season carries lineup efficiency; otherwise the group is hidden. */
  hasEfficiency: boolean;
  upset(season: string): SeasonUpsetCard | null;
  rows(season: string): SeasonStatsRow[];
  /** NFL team logo by canonical abbreviation. */
  nflLogos: ReadonlyMap<string, string>;
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
  private readonly teamSeasons = inject(TeamSeasonService);

  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly formatSigned = formatSigned;
  readonly formatDecimal = formatDecimal;
  readonly formatAllPlay = formatAllPlay;
  readonly formatPercent = formatPercent;
  readonly signClass = signClass;

  selectedSeason: string | null = null;
  expandedTeamId: string | null = null;
  sortKey: SortKey = 'place';
  sortDescending = false;
  /** Group shown on small screens; wide screens show all groups. */
  group: StatsGroup = 'record';

  readonly vm$ = forkJoin({
    league: this.dataService.getLeagueSummary(),
    injury: this.dataService.getInjuryImpact(),
    nflTeams: this.dataService.getNflTeams(),
    stats: this.dataService.getAllSeasonStatistics(),
    teamSeasons: this.teamSeasons.getLookup().pipe(catchError(() => of(null)))
  }).pipe(
    map(({ league, injury, nflTeams, stats, teamSeasons }): SeasonStatsViewModel => {
      const history = buildSeasonHistory(league).seasons.filter(season => season.regularSeasonStandings.length > 0);
      const statsDocs = new Map<string, SeasonStatisticsReadModel>(stats.bySeason);
      if (stats.current) statsDocs.set(String(stats.current.Season), stats.current);
      const injurySeasons = new Map((injury?.Seasons ?? []).map(season => [String(season.Season), season]));
      const seasons = history.map(season => season.season).filter(season => statsDocs.has(season) || injurySeasons.has(season));
      const cache = new Map<string, SeasonStatsRow[]>();
      const currentTeams = new Map(league.Teams.map(team => [String(team.TeamID), team]));

      return {
        seasons,
        defaultSeason: seasons.includes(String(league.Season)) ? String(league.Season) : (seasons[0] ?? null),
        hasInjuryImpact: injurySeasons.size > 0,
        hasEfficiency: [...statsDocs.values()].some(doc => doc.Teams.some(team => team.LineupEfficiencyActual != null || team.ProjectionDelta != null)),
        upset: season => buildSeasonUpsetCard(statsDocs.get(season)),
        nflLogos: new Map(nflTeams.filter(team => team.Logo).map(team => [team.ID, team.Logo])),
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
              // Identity of that season from the league-teams product; the standings snapshot is only the fallback while the product is unavailable.
              identity: teamSeasons?.identity(season, teamId) ?? {
                TeamID: Number(row.teamId),
                Team: row.teamName ?? '',
                // Season-specific abbreviation from the generator; the running season may also use the league abbreviation.
                TeamAbbr: stat?.TeamAbbr ?? (isCurrent ? currentTeams.get(teamId)?.TeamAbbr : undefined),
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
  }

  groupOptions(vm: SeasonStatsViewModel): GroupOption[] {
    return [
      { id: 'record', label: 'Record' },
      ...(vm.hasInjuryImpact ? [{ id: 'injury' as const, label: 'Injuries' }] : []),
      ...(vm.hasEfficiency ? [{ id: 'efficiency' as const, label: 'Efficiency' }] : [])
    ];
  }

  /** The group a small screen shows; falls back to Record when the chosen group is not available. */
  activeGroup(vm: SeasonStatsViewModel): StatsGroup {
    return this.groupOptions(vm).some(option => option.id === this.group) ? this.group : 'record';
  }

  selectGroup(group: StatsGroup): void {
    this.group = group;
  }

  sortedRows(vm: SeasonStatsViewModel): SeasonStatsRow[] {
    const season = this.activeSeason(vm);
    if (!season) return [];
    const direction = this.sortDescending ? -1 : 1;
    // Rows without a value always sort last, never as zero.
    return [...vm.rows(season)].sort((a, b) => {
      const left = this.sortValue(a);
      const right = this.sortValue(b);
      if (left === null && right === null) return a.place - b.place;
      if (left === null) return 1;
      if (right === null) return -1;
      return (left - right) * direction || a.place - b.place;
    });
  }

  private sortValue(row: SeasonStatsRow): number | null {
    switch (this.sortKey) {
      case 'record': return row.stats ? row.stats.Wins + row.stats.Ties / 2 : null;
      case 'expected': return row.stats?.ExpectedWins ?? null;
      case 'luck': return row.stats?.Luck ?? null;
      case 'hurt': return row.injury?.hurt ?? null;
      case 'lost': return row.injury?.total ?? null;
      case 'lineup': return row.stats?.LineupEfficiencyActual ?? null;
      case 'delta': return row.stats?.ProjectionDelta ?? null;
      default: return row.place;
    }
  }

  sortBy(key: SortKey): void {
    if (this.sortKey === key) {
      this.sortDescending = !this.sortDescending;
      return;
    }
    this.sortKey = key;
    // The place starts with the best (lowest) one, every other column with the largest value.
    this.sortDescending = key !== 'place';
  }

  ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
    return this.sortKey !== key ? 'none' : this.sortDescending ? 'descending' : 'ascending';
  }

  toggle(row: SeasonStatsRow): void {
    this.expandedTeamId = this.expandedTeamId === row.teamId ? null : row.teamId;
  }

  isExpanded(row: SeasonStatsRow): boolean {
    return this.expandedTeamId === row.teamId;
  }

  nflLogo(vm: SeasonStatsViewModel, team: string | null): string | null {
    return team ? (vm.nflLogos.get(team) ?? null) : null;
  }

  trackRow = (_: number, row: SeasonStatsRow): string => row.teamId;

  expectedWins(stat: SeasonStatisticsTeam | null): string {
    return formatDecimal(stat?.ExpectedWins ?? null);
  }
}
