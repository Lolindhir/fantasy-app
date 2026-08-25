import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewEncapsulation, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { forkJoin } from 'rxjs';

import type { DraftPick, FantasyTeam, League, Player, RawDraft } from '../../../core/models/fantasy.models';
import { DataService } from '../../../core/services/data.service';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { SharedMaterialImports } from '../../shared-material-imports';
import { getDraftRoundColor } from '../../utils/draft-ui.util';
import {
  buildRosterPlayerGroups,
  getCombinedRanking,
  getPreviousCombinedRanking,
  isCombinedRankingAvailable,
  type RosterGroupMode,
  type RosterPlayerGroup,
  type RosterSortMode
} from '../../utils/team-roster-view.util';
import { CapUsageBarComponent } from '../cap-usage-bar/cap-usage-bar';
import { PlayerListComponent, type PlayerListColumn } from '../player-list/player-list';
import { SalaryAssetLeaderboardComponent } from '../salary-asset-leaderboard/salary-asset-leaderboard';
import { SalaryHealthIndicatorComponent } from '../salary-health-indicator/salary-health-indicator';
import { SalaryPositionDonutComponent } from '../salary-position-donut/salary-position-donut';
import {
  buildTeamSalarySummary,
  getEarliestOpenPicks,
  getPositionCounts,
  getTeamRosterLimits,
  getTeamSeasonSummary,
  splitTeamRoster,
  type SalaryLens,
  type TeamSalaryLensSummary
} from '../../utils/team-salary.util';

export interface TeamDetailDialogData {
  team: FantasyTeam;
  league: League;
  players: Player[];
  drafts: RawDraft[];
}

interface TeamDraftGroup {
  title: string;
  season: number;
  draftType: string;
  picks: DraftPick[];
}

interface HistoricalDraftGroup {
  title: string;
  season: number;
  picks: DraftPick[];
}

interface TeamHistoryRow {
  season: string;
  record: string;
  regularPlace: string;
  finalPlace: string;
  awards: string[];
}

@Component({
  selector: 'app-team-detail-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule,
    MatDialogModule,
    MatTabsModule,
    MatButtonToggleModule,
    SharedMaterialImports,
    PositionStylePipe,
    PlayerListComponent,
    CapUsageBarComponent,
    SalaryAssetLeaderboardComponent,
    SalaryHealthIndicatorComponent,
    SalaryPositionDonutComponent
  ],
  templateUrl: './team-detail-dialog.html',
  styleUrl: './team-detail-dialog.scss'
})
export class TeamDetailDialogComponent implements OnInit {
  readonly data = inject<TeamDetailDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<TeamDetailDialogComponent>);
  private readonly dataService = inject(DataService);

  readonly team = this.data.team;
  readonly league = this.data.league;
  readonly salary = buildTeamSalarySummary(this.data.team, this.data.league);
  readonly roster = splitTeamRoster(this.data.team);
  readonly limits = getTeamRosterLimits(this.data.league);
  readonly seasonSummary = getTeamSeasonSummary(this.data.team, this.data.league);
  readonly earliestOpenPicks = getEarliestOpenPicks(this.data.team, this.data.league.SeasonAsNumber);
  readonly positionCounts = getPositionCounts(this.data.team.Roster);
  readonly combinedRankingAvailable = isCombinedRankingAvailable(this.data.league.FinalScoredWeek);

  salaryLens: SalaryLens = 'current';
  rosterGroup: RosterGroupMode = 'none';
  rosterSort: RosterSortMode = 'salary';
  isMobile = window.innerWidth <= 600;
  historicalDraftGroups: HistoricalDraftGroup[] = [];
  draftHistoryLoading = false;

  ngOnInit(): void {
    this.loadDraftHistory();
  }

  get playerColumns(): PlayerListColumn[] {
    const sortColumn: PlayerListColumn[] = this.showsRosterSortColumn ? ['dynamicStat'] : [];

    return this.isMobile
      ? ['rank', 'name', ...sortColumn, 'salary', 'salaryProjected']
      : ['rank', 'picture', 'name', 'position', 'team', ...sortColumn, 'salary', 'salaryProjected'];
  }

  get rosterDynamicColumnHeader(): string {
    switch (this.rosterSort) {
      case 'ageAsc':
      case 'ageDesc':
        return 'Age';
      case 'ranking':
        return 'Rank';
      default:
        return '';
    }
  }

  get rosterGroups(): RosterPlayerGroup[] {
    const groupMode = this.rosterGroup === 'rankingStatus' && !this.combinedRankingAvailable
      ? 'none'
      : this.rosterGroup;
    const sortMode = this.rosterSort === 'ranking' && !this.combinedRankingAvailable
      ? 'salary'
      : this.rosterSort;

    return buildRosterPlayerGroups(this.team.Roster, groupMode, sortMode, this.roster);
  }

  get selectedSalary(): TeamSalaryLensSummary {
    return this.salary[this.salaryLens];
  }

  get comparisonSalary(): TeamSalaryLensSummary {
    return this.salary[this.salaryLens === 'current' ? 'projected' : 'current'];
  }

  get selectedSeasonLabel(): string {
    return this.salaryLens === 'current'
      ? `Current ${this.league.Season}`
      : `Projected ${this.league.SeasonAsNumber + 1}`;
  }

  get comparisonSeasonLabel(): string {
    return this.salaryLens === 'current'
      ? `Projected ${this.league.SeasonAsNumber + 1}`
      : `Current ${this.league.Season}`;
  }

  get coreAssets(): Player[] {
    return this.salary.current.mostExpensive;
  }

  get allTimeRecord(): string {
    const regular = this.team.Placements.AllTime.Regular;
    return regular.Ties > 0
      ? `${regular.Wins}-${regular.Losses}-${regular.Ties}`
      : `${regular.Wins}-${regular.Losses}`;
  }

  get futureDraftGroups(): TeamDraftGroup[] {
    const groups = new Map<string, TeamDraftGroup>();
    this.team.DraftPicks
      .filter(pick => Number(pick.Season) >= this.league.SeasonAsNumber && pick.Status !== 'Picked' && !pick.PlayerID)
      .forEach(pick => {
        const season = Number(pick.Season);
        const draftType = pick.DraftType || 'Draft';
        const key = `${season}|${draftType}`;
        const group = groups.get(key) ?? {
          title: `${season} ${this.displayDraftType(draftType)}`,
          season,
          draftType,
          picks: []
        };
        group.picks.push(pick);
        groups.set(key, group);
      });

    return [...groups.values()]
      .map(group => ({ ...group, picks: [...group.picks].sort(this.comparePicks) }))
      .sort((a, b) => a.season - b.season || a.draftType.localeCompare(b.draftType));
  }

  get historyRows(): TeamHistoryRow[] {
    return this.league.Standings
      .map(standing => {
        const regular = standing.RegularSeason.find(row => String(row.TeamID) === String(this.team.TeamID));
        if (!regular) return undefined;
        const playoff = standing.Playoffs?.find(row => String(row.TeamID) === String(this.team.TeamID));
        const awards = (standing.Awards ?? [])
          .filter(award => String(award.TeamID) === String(this.team.TeamID))
          .map(award => award.Type.DisplayText || award.Name);
        return {
          season: standing.Season,
          record: `${regular.Wins ?? 0}-${regular.Losses ?? 0}${regular.Ties ? `-${regular.Ties}` : ''}`,
          regularPlace: regular.PlaceOrdinal || this.ordinal(regular.Place),
          finalPlace: playoff?.PlaceOrdinal || regular.PlaceOrdinal || this.ordinal(playoff?.Place ?? regular.Place),
          awards
        } satisfies TeamHistoryRow;
      })
      .filter((row): row is TeamHistoryRow => !!row)
      .sort((a, b) => Number(b.season) - Number(a.season));
  }

  close(): void {
    this.dialogRef.close();
  }

  displayTeamName(): string {
    return this.team.Team || `Team ${this.team.TeamID}`;
  }

  displayLimit(value: number, limit?: number): string {
    return limit ? `${value} / ${limit}` : `${value}`;
  }

  rosterGroupCount(group: RosterPlayerGroup): string {
    switch (group.key) {
      case 'roster': return this.displayLimit(group.players.length, this.limits.roster);
      case 'taxi': return this.displayLimit(group.players.length, this.limits.taxi);
      case 'ir': return this.displayLimit(group.players.length, this.limits.ir);
      default: return `${group.players.length}`;
    }
  }

  rosterGroupEmptyText(group: RosterPlayerGroup): string {
    switch (group.key) {
      case 'taxi': return 'No players on Taxi.';
      case 'ir': return 'No players on IR.';
      case 'ranked': return 'No players have a current Combined Ranking.';
      case 'unranked': return 'All players currently have a Combined Ranking.';
      default: return `No players in ${group.label}.`;
    }
  }

  getRosterDynamicColumnValue = (player: Player): string => {
    switch (this.rosterSort) {
      case 'ageAsc':
      case 'ageDesc':
        return `${player.Age}`;
      case 'ranking': {
        const currentRank = getCombinedRanking(player);
        if (currentRank !== undefined) return `#${currentRank}`;
        const previousRank = getPreviousCombinedRanking(player);
        return previousRank !== undefined ? `Prev #${previousRank}` : '—';
      }
      default:
        return '';
    }
  };

  formatMoney(value: number): string {
    const absolute = Math.abs(value);
    const prefix = value < 0 ? '-' : '';
    if (absolute >= 1_000_000) return `${prefix}$${(absolute / 1_000_000).toFixed(1)}m`;
    if (absolute >= 1_000) return `${prefix}$${(absolute / 1_000).toFixed(1)}k`;
    return `${prefix}$${absolute.toFixed(0)}`;
  }

  ordinal(value: number): string {
    const mod100 = value % 100;
    if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
    switch (value % 10) {
      case 1: return `${value}st`;
      case 2: return `${value}nd`;
      case 3: return `${value}rd`;
      default: return `${value}th`;
    }
  }

  draftRoundColor(pick: DraftPick): string {
    return getDraftRoundColor(pick.Round, pick.Draft?.Settings.Rounds);
  }

  historicalPlayer(pick: DraftPick): Player | undefined {
    if (!pick.PlayerID) return undefined;
    return this.data.players.find(candidate => candidate.ID === pick.PlayerID);
  }

  historicalPlayerName(pick: DraftPick): string {
    return this.historicalPlayer(pick)?.Name || pick.PlayerName || 'Unknown player';
  }

  private get showsRosterSortColumn(): boolean {
    return this.rosterSort === 'ranking' || this.rosterSort === 'ageAsc' || this.rosterSort === 'ageDesc';
  }

  private loadDraftHistory(): void {
    this.draftHistoryLoading = true;
    this.dataService.getPastSeasonsIndex().subscribe(index => {
      const paths = index.Seasons
        .filter(season => Number(season.Season) < this.league.SeasonAsNumber)
        .map(season => season.Resources['Drafts'])
        .filter((resource): resource is { Path: string; Exists: boolean } =>
          !!resource && resource.Exists && typeof resource.Path === 'string' && resource.Path.length > 0
        )
        .map(resource => resource.Path);

      if (!paths.length) {
        this.draftHistoryLoading = false;
        return;
      }

      forkJoin(paths.map(path => this.dataService.getPastDraftsRaw(path))).subscribe(draftLists => {
        this.historicalDraftGroups = draftLists
          .flat()
          .map(draft => this.buildHistoricalDraftGroup(draft))
          .filter((group): group is HistoricalDraftGroup => !!group && group.picks.length > 0)
          .sort((a, b) => b.season - a.season || a.title.localeCompare(b.title));
        this.draftHistoryLoading = false;
      });
    });
  }

  private buildHistoricalDraftGroup(draft: RawDraft): HistoricalDraftGroup | undefined {
    const picks = draft.Picks
      .filter(pick => pick.Status === 'Picked' && this.wasDraftedByTeam(pick))
      .sort(this.comparePicks);
    if (!picks.length) return undefined;

    return {
      title: draft.DisplayDraftKey || `${draft.Season} ${this.displayDraftType(draft.DraftType)}`,
      season: Number(draft.Season),
      picks
    };
  }

  private wasDraftedByTeam(pick: DraftPick): boolean {
    if (pick.SleeperPickedBy != null) {
      return String(pick.SleeperPickedBy) === String(this.team.TeamID);
    }
    return String(pick.CurrentOwnerRosterID) === String(this.team.TeamID);
  }

  private comparePicks = (a: DraftPick, b: DraftPick): number =>
    (a.OverallPick ?? Number.MAX_SAFE_INTEGER) - (b.OverallPick ?? Number.MAX_SAFE_INTEGER)
    || (a.PositionInRound ?? Number.MAX_SAFE_INTEGER) - (b.PositionInRound ?? Number.MAX_SAFE_INTEGER)
    || a.Round - b.Round;

  private displayDraftType(value: string): string {
    return value.replaceAll('_', ' ');
  }
}
