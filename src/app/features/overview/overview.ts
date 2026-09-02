import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RouterLink } from '@angular/router';
import { map } from 'rxjs/operators';

import type {
  DraftPick,
  FantasyTeam,
  League,
  Player,
  RawDraft,
  Transaction
} from '../../core/models/fantasy.models';
import { DataService } from '../../core/services/data.service';
import { AllTimeStandingsComponent } from '../../shared/components/all-time-standings/all-time-standings';
import { CurrentStandingsComponent } from '../../shared/components/current-standings/current-standings';
import { PlayerDetailDialogComponent } from '../../shared/components/player-detail-dialog/player-detail-dialog';
import { SeasonResultsComponent } from '../../shared/components/season-results/season-results';
import { PositionStylePipe } from '../../shared/pipes/position-style.pipe';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import {
  compareDraftPicksByDraftOrder,
  compareDraftPicksByDraftThenOrder
} from '../../shared/utils/draft-capital.util';
import { getDraftRoundColor } from '../../shared/utils/draft-ui.util';
import {
  buildAllTimeStandings,
  buildCurrentStandings,
  buildSeasonResults,
  getCurrentSeasonAwards,
  getPreviousChampion
} from '../../shared/utils/league-standings-view.util';

type DraftSeasonStatusClass = 'live' | 'upcoming' | 'completed';
type RecentMoveCategory = 'trade' | 'add' | 'cut' | 'other';

interface DraftPickDisplayItem {
  display: string;
  round: number;
  backgroundColor: string;
}

interface DraftPickDisplayGroup {
  draftKey: string;
  label: string;
  count: number;
  picks: DraftPickDisplayItem[];
  sortOrder: number;
}

interface DeadlineDisplayInfo {
  displayText: string;
}

interface CapCheckSummary {
  title: string;
  summaryText: string;
  detailText: string;
  allCompliant: boolean;
}

interface DraftSeasonDraftRow {
  name: string;
  detailsPrimary: string;
  detailsSecondary: string;
  status: string;
  statusClass: DraftSeasonStatusClass;
  startDisplay: string | null;
}

interface DraftPickOverviewEntry {
  draft: RawDraft;
  pick: DraftPick;
}

interface DraftPickOverviewRow {
  displayPick: string;
  owner: string;
  ownerAbbr: string;
  ownerAvatar: string | null;
  ownerFallback: string;
  player: Player | null;
  playerDisplay: string | null;
}

interface DraftSeasonDashboard {
  drafts: DraftSeasonDraftRow[];
  nextPicks: DraftPickOverviewRow[];
  recentPicks: DraftPickOverviewRow[];
}

interface SalaryTeamSummary {
  total: number;
}

interface SeasonPulseMetric {
  label: string;
  value: string;
}

interface SeasonPulse {
  eyebrow: string;
  title: string;
  subtitle: string;
  metrics: SeasonPulseMetric[];
}

interface SeasonLeaderCard {
  icon: string;
  label: string;
  team: string;
  avatar: string | null;
  fallback: string;
  value: string;
  detail: string;
}

interface RecentMoveRow {
  id: string;
  category: RecentMoveCategory;
  icon: string;
  typeLabel: string;
  dateLabel: string;
  teamLabel: string;
  summary: string;
}

@Component({
  selector: 'app-overview',
  imports: [
    CommonModule,
    RouterLink,
    SharedMaterialImports,
    SeasonResultsComponent,
    AllTimeStandingsComponent,
    CurrentStandingsComponent,
    PositionStylePipe
  ],
  standalone: true,
  templateUrl: './overview.html',
  styleUrls: ['./overview.scss', './active-overview.scss']
})
export class OverviewComponent {

  private dataService = inject(DataService);
  private dialog = inject(MatDialog);
  expandedTeamId: number | null = null;

  toggleTeam(teamId: number): void {
    this.expandedTeamId =
      this.expandedTeamId === teamId ? null : teamId;
  }

  vm$ = this.dataService.getLeagueWithPlayersAndTransactions().pipe(
    map(({ league, teams, drafts, players, transactions }) => {

      const offSeason = league.Status === 'Off-Season';
      const draftSeason = league.Status === 'Draft-Season';
      const activeLeague = this.isActiveLeagueStatus(league.Status);
      const currentSeason = league.Season;
      const maxDisplayedDraftRound = this.getMaxDisplayedDraftRound(teams, currentSeason);

      const champion = getPreviousChampion(teams);
      const currentStandings = buildCurrentStandings(league, teams);
      const standings = currentStandings.map(row => ({
        ...row.team,
        DisplayPlace: row.displayPlace
      }));
      const seasonResults = buildSeasonResults(teams);
      const allTimeStandings = buildAllTimeStandings(teams);
      const allTime = allTimeStandings.map(row => row.team);

      const salaryByTeam = teams.map(t => {

        const playerCount = Math.min(
          league.SalaryRelevantTeamSize,
          t.Roster.length
        );

        const sortedSalary = this.sortPlayersBySalary(t.Roster, false);
        const sortedProjected = this.sortPlayersBySalary(t.Roster, true);

        const topPlayers = sortedSalary.slice(0, playerCount);
        const topPlayersProjected = sortedProjected.slice(0, playerCount);

        const total = topPlayers.reduce((sum, p) => sum + p.Salary, 0);
        const totalProjected = topPlayersProjected.reduce((sum, p) => sum + p.SalaryProjected, 0);

        const totalAll = sortedSalary.reduce((sum, p) => sum + p.Salary, 0);
        const totalAllProjected = sortedProjected.reduce((sum, p) => sum + p.SalaryProjected, 0);

        const top5Players = sortedSalary.slice(0, 5);
        const top5PlayersProjected = sortedProjected.slice(0, 5);

        const totalTop5 = top5Players.reduce((sum, p) => sum + p.Salary, 0);
        const totalTop5Projected = top5PlayersProjected.reduce((sum, p) => sum + p.SalaryProjected, 0);

        const currentSeasonDraftPickGroups = this.getCurrentSeasonDraftPickGroups(
          t.DraftPicks ?? [],
          currentSeason,
          maxDisplayedDraftRound
        );

        return {
          team: t,
          total,
          totalProjected,
          totalAll,
          totalAllProjected,
          totalTop5,
          totalTop5Projected,
          topPlayers,
          topPlayersProjected,
          countedPlayers: playerCount,
          draftPickGroups: currentSeasonDraftPickGroups
        };

      }).sort((a, b) => a.total - b.total);

      const capCheckSummary = offSeason && league.Phase === 'Cap Check'
        ? this.buildCapCheckSummary(league, salaryByTeam)
        : null;

      const draftSeasonDashboard = this.buildDraftSeasonDashboard(drafts, teams, players, currentSeason, draftSeason);
      const seasonPulse = activeLeague ? this.buildSeasonPulse(league) : null;
      const seasonLeaders = activeLeague ? this.buildSeasonLeaders(league, teams) : [];
      const recentMoves = activeLeague ? this.buildRecentMoves(transactions, currentSeason) : [];
      const awards = getCurrentSeasonAwards(league);
      const deadline = this.parseDeadline(league.CapDeadline);
      const deadlineDisplay = deadline.toLocaleDateString();
      const now = new Date();
      const msLeft = deadline.getTime() - now.getTime();

      const deadlineInfo: DeadlineDisplayInfo | null = msLeft > 0
        ? { displayText: this.formatDeadlineCountdown(msLeft) }
        : null;

      return {
        league,
        champion,
        currentStandings,
        standings,
        seasonResults,
        allTime,
        allTimeStandings,
        salaryByTeam,
        capCheckSummary,
        draftSeasonDashboard,
        seasonPulse,
        seasonLeaders,
        recentMoves,
        awards,
        deadlineDisplay,
        deadlineInfo,
        offSeason,
        draftSeason,
        activeLeague
      };
    })
  );

  openPlayerDetail(player: Player | null): void {
    if (!player) return;

    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

  private isActiveLeagueStatus(status: string): boolean {
    return ['Pre-Season', 'In-Season', 'Playoffs'].includes(status);
  }

  private buildSeasonPulse(league: League): SeasonPulse {
    const currentWeek = league.CurrentWeek
      ?? Math.min(Math.max(league.FinalScoredWeek + 1, 1), league.LastLeagueWeek);
    const commonMetrics: SeasonPulseMetric[] = [
      { label: 'Current', value: `Week ${currentWeek}` },
      { label: 'Trade deadline', value: `Week ${league.TradeDeadlineWeek}` },
      { label: 'Playoffs start', value: `Week ${league.PlayoffStartWeek}` }
    ];

    if (league.Status === 'Pre-Season') {
      return {
        eyebrow: 'Season Pulse',
        title: `Season ${league.Season} is ready`,
        subtitle: `Week ${currentWeek} is next · regular season ahead`,
        metrics: commonMetrics
      };
    }

    if (league.Status === 'Playoffs') {
      return {
        eyebrow: 'Playoff Pulse',
        title: `Playoffs · Week ${currentWeek}`,
        subtitle: `Postseason started in Week ${league.PlayoffStartWeek}`,
        metrics: [
          { label: 'Current', value: `Week ${currentWeek}` },
          { label: 'Last scored', value: `Week ${league.FinalScoredWeek}` },
          { label: 'League season', value: league.Season }
        ]
      };
    }

    const scoredWeeks = league.FinalScoredWeek;
    const scoredWeekLabel = scoredWeeks === 1 ? 'week scored' : 'weeks scored';

    return {
      eyebrow: 'Season Pulse',
      title: `Week ${currentWeek}`,
      subtitle: scoredWeeks > 0
        ? `Regular season · ${scoredWeeks} ${scoredWeekLabel}`
        : 'Regular season is underway',
      metrics: commonMetrics
    };
  }

  private buildSeasonLeaders(league: League, teams: FantasyTeam[]): SeasonLeaderCard[] {
    if (league.FinalScoredWeek <= 0 || teams.length === 0) {
      return [];
    }

    const bestRecord = [...teams].sort((left, right) =>
      right.Wins - left.Wins
      || left.Losses - right.Losses
      || right.Ties - left.Ties
      || right.Points - left.Points
    )[0];
    const pointsLeader = [...teams].sort((left, right) => right.Points - left.Points)[0];
    const streakLeader = teams
      .map(team => ({ team, wins: this.getWinningStreakLength(team.Streak) }))
      .filter(entry => entry.wins > 0)
      .sort((left, right) => right.wins - left.wins || right.team.Points - left.team.Points)[0];

    const leaders: SeasonLeaderCard[] = [
      this.buildSeasonLeaderCard(
        'emoji_events',
        'Best Record',
        bestRecord,
        bestRecord.Record || `${bestRecord.Wins}-${bestRecord.Losses}-${bestRecord.Ties}`,
        `${bestRecord.Points.toFixed(1)} PF`
      ),
      this.buildSeasonLeaderCard(
        'leaderboard',
        'Points Leader',
        pointsLeader,
        `${pointsLeader.Points.toFixed(1)} pts`,
        pointsLeader.Record || `${pointsLeader.Wins}-${pointsLeader.Losses}-${pointsLeader.Ties}`
      )
    ];

    if (streakLeader) {
      leaders.push(this.buildSeasonLeaderCard(
        'local_fire_department',
        'Hot Streak',
        streakLeader.team,
        streakLeader.team.Streak,
        `${streakLeader.team.Points.toFixed(1)} PF`
      ));
    } else {
      const pointDiffLeader = [...teams].sort(
        (left, right) => (right.Points - right.PointsAgainst) - (left.Points - left.PointsAgainst)
      )[0];
      const pointDiff = pointDiffLeader.Points - pointDiffLeader.PointsAgainst;

      leaders.push(this.buildSeasonLeaderCard(
        'compare_arrows',
        'Point Differential',
        pointDiffLeader,
        `${pointDiff >= 0 ? '+' : ''}${pointDiff.toFixed(1)}`,
        `${pointDiffLeader.Points.toFixed(1)} PF · ${pointDiffLeader.PointsAgainst.toFixed(1)} PA`
      ));
    }

    return leaders;
  }

  private buildSeasonLeaderCard(
    icon: string,
    label: string,
    team: FantasyTeam,
    value: string,
    detail: string
  ): SeasonLeaderCard {
    const teamName = team.Team || team.Owner || `Team ${team.TeamID}`;

    return {
      icon,
      label,
      team: teamName,
      avatar: team.Avatar || null,
      fallback: this.formatOwnerFallback(teamName),
      value,
      detail
    };
  }

  private getWinningStreakLength(streak: string): number {
    const match = /^W(\d+)$/i.exec(streak?.trim() ?? '');
    return match ? Number(match[1]) : 0;
  }

  private buildRecentMoves(transactions: Transaction[], season: string): RecentMoveRow[] {
    return [...transactions]
      .filter(transaction => transaction.Season === season)
      .sort((left, right) => right.CreatedAt - left.CreatedAt)
      .slice(0, 4)
      .map(transaction => {
        const category = this.getRecentMoveCategory(transaction);

        return {
          id: transaction.TransactionID,
          category,
          icon: this.getRecentMoveIcon(category),
          typeLabel: this.getRecentMoveTypeLabel(transaction, category),
          dateLabel: this.formatRecentMoveDate(transaction),
          teamLabel: this.getRecentMoveTeamLabel(transaction, category),
          summary: this.getRecentMoveSummary(transaction, category)
        };
      });
  }

  private getRecentMoveCategory(transaction: Transaction): RecentMoveCategory {
    if (transaction.Type === 'trade') {
      return 'trade';
    }

    if (this.getTransactionPlayerNames(transaction, 'added').length > 0 || transaction.Type === 'add') {
      return 'add';
    }

    if (
      this.getTransactionPlayerNames(transaction, 'dropped').length > 0
      || transaction.Type === 'cut'
      || transaction.Type === 'drop'
    ) {
      return 'cut';
    }

    return 'other';
  }

  private getRecentMoveTypeLabel(transaction: Transaction, category: RecentMoveCategory): string {
    switch (category) {
      case 'trade': return 'Trade';
      case 'add': return 'Add';
      case 'cut': return 'Cut';
      default:
        return transaction.Type === 'commissioner'
          ? 'Commissioner move'
          : this.toTitleCase(transaction.Type);
    }
  }

  private getRecentMoveIcon(category: RecentMoveCategory): string {
    switch (category) {
      case 'trade': return 'swap_horiz';
      case 'add': return 'person_add';
      case 'cut': return 'person_remove';
      default: return 'sync_alt';
    }
  }

  private getRecentMoveTeamLabel(transaction: Transaction, category: RecentMoveCategory): string {
    const teamLabels = Array.from(new Set(transaction.Participants.map(participant =>
      participant.Team?.Team
      || participant.Team?.Owner
      || `Team ${participant.RosterID}`
    )));

    if (teamLabels.length === 0) {
      return 'League';
    }

    if (category === 'trade') {
      return teamLabels.join(' ↔ ');
    }

    return teamLabels.join(' · ');
  }

  private getRecentMoveSummary(transaction: Transaction, category: RecentMoveCategory): string {
    const addedPlayers = this.getTransactionPlayerNames(transaction, 'added');
    const droppedPlayers = this.getTransactionPlayerNames(transaction, 'dropped');

    if (category === 'trade') {
      const playerIDs = new Set<string>();
      for (const participant of transaction.Participants) {
        participant.AddedPlayers.forEach(asset => playerIDs.add(asset.PlayerID));
        participant.DroppedPlayers.forEach(asset => playerIDs.add(asset.PlayerID));
      }

      const parts: string[] = [];
      if (playerIDs.size > 0) {
        parts.push(`${playerIDs.size} ${playerIDs.size === 1 ? 'player' : 'players'}`);
      }
      if (transaction.DraftPicks.length > 0) {
        parts.push(`${transaction.DraftPicks.length} ${transaction.DraftPicks.length === 1 ? 'draft pick' : 'draft picks'}`);
      }

      return parts.length > 0 ? parts.join(' · ') : 'Trade completed';
    }

    const parts: string[] = [];
    if (addedPlayers.length > 0) {
      parts.push(`Added ${this.summarizePlayerNames(addedPlayers)}`);
    }
    if (droppedPlayers.length > 0) {
      parts.push(`Dropped ${this.summarizePlayerNames(droppedPlayers)}`);
    }

    if (parts.length > 0) {
      return parts.join(' · ');
    }

    return transaction.Notes || 'League move completed';
  }

  private getTransactionPlayerNames(
    transaction: Transaction,
    direction: 'added' | 'dropped'
  ): string[] {
    const names = new Map<string, string>();

    for (const participant of transaction.Participants) {
      const assets = direction === 'added'
        ? participant.AddedPlayers
        : participant.DroppedPlayers;

      for (const asset of assets) {
        names.set(asset.PlayerID, asset.Player?.NameShort || asset.Player?.Name || asset.PlayerID);
      }
    }

    return [...names.values()];
  }

  private summarizePlayerNames(names: string[]): string {
    if (names.length <= 2) {
      return names.join(', ');
    }

    return `${names.slice(0, 2).join(', ')} +${names.length - 2}`;
  }

  private formatRecentMoveDate(transaction: Transaction): string {
    const date = transaction.CreatedAtDate
      ?? (transaction.CreatedDate ? new Date(`${transaction.CreatedDate}T12:00:00Z`) : null);

    if (!date || Number.isNaN(date.getTime())) {
      return transaction.CreatedDate || '';
    }

    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric'
    }).format(date);
  }

  private toTitleCase(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, character => character.toUpperCase());
  }

  private buildCapCheckSummary(
    league: League,
    salaryByTeam: SalaryTeamSummary[]
  ): CapCheckSummary {
    const overCapTeams = salaryByTeam.filter(team => team.total > league.SalaryCap);
    const compliantTeams = salaryByTeam.length - overCapTeams.length;

    if (overCapTeams.length === 0) {
      return {
        title: '✅ Cap Check Passed',
        summaryText: 'All teams are under the salary cap.',
        detailText: `${compliantTeams} of ${salaryByTeam.length} teams compliant`,
        allCompliant: true
      };
    }

    const worstOverage = Math.max(...overCapTeams.map(team => team.total - league.SalaryCap));
    const teamLabel = overCapTeams.length === 1 ? 'team still needs' : 'teams still need';

    return {
      title: '🚨 Cap Check Open',
      summaryText: `${overCapTeams.length} ${teamLabel} to clear cap.`,
      detailText: `${compliantTeams} compliant · largest overage ${this.formatSalaryDollars(worstOverage, false, 1)}`,
      allCompliant: false
    };
  }

  private buildDraftSeasonDashboard(
    drafts: RawDraft[],
    teams: FantasyTeam[],
    players: Player[],
    season: string,
    draftSeason: boolean
  ): DraftSeasonDashboard | null {
    if (!draftSeason) return null;

    const seasonDrafts = this.getSeasonDrafts(drafts, season);
    if (seasonDrafts.length === 0) return null;

    const teamById = this.buildTeamById(teams);
    const playerById = this.buildPlayerById(players);

    return {
      drafts: seasonDrafts.map(draft => this.buildDraftSeasonDraftRow(draft)),
      nextPicks: this.getNextDraftPickEntries(seasonDrafts)
        .slice(0, 3)
        .map(entry => this.buildDraftPickOverviewRow(entry.pick, entry.draft, teamById, playerById, false)),
      recentPicks: this.getRecentDraftPickEntries(seasonDrafts)
        .slice(0, 3)
        .map(entry => this.buildDraftPickOverviewRow(entry.pick, entry.draft, teamById, playerById, true))
    };
  }

  private getSeasonDrafts(drafts: RawDraft[], season: string): RawDraft[] {
    return drafts
      .filter(draft => draft.Season === season)
      .sort((a, b) => a.DraftNo - b.DraftNo);
  }

  private buildDraftSeasonDraftRow(draft: RawDraft): DraftSeasonDraftRow {
    const statusClass = this.getDraftSummaryStatusClass(draft);
    const total = draft.Picks.length;
    const selected = draft.Picks.filter(pick => this.isDraftPickSelected(pick)).length;
    const remaining = total - selected;
    const startDisplay = statusClass === 'upcoming'
      ? this.formatDraftStartTime(draft) ?? 'not scheduled'
      : null;

    return {
      name: `${draft.DisplayDraftType} Draft`,
      detailsPrimary: [`${draft.Settings.Rounds} rounds`, `${total} picks`].join(' · '),
      detailsSecondary: [`${selected} selected`, `${remaining} remaining`].join(' · '),
      status: this.formatDraftSummaryStatus(statusClass),
      statusClass,
      startDisplay
    };
  }

  private buildDraftPickOverviewRow(
    pick: DraftPick,
    draft: RawDraft,
    teamById: Map<number, FantasyTeam>,
    playerById: Map<string, Player>,
    includePlayer: boolean
  ): DraftPickOverviewRow {
    const owner = teamById.get(pick.CurrentOwnerRosterID);
    const ownerName = owner?.Team ?? owner?.Owner ?? `Team ${pick.CurrentOwnerRosterID}`;
    const player = includePlayer && pick.PlayerID
      ? playerById.get(pick.PlayerID) ?? null
      : null;

    return {
      displayPick: this.formatDraftPickOverviewChip(draft, pick),
      owner: ownerName,
      ownerAbbr: owner?.TeamAbbr ?? this.formatOwnerFallback(ownerName),
      ownerAvatar: owner?.Avatar ?? null,
      ownerFallback: this.formatOwnerFallback(ownerName),
      player,
      playerDisplay: includePlayer ? player?.NameShort ?? pick.PlayerName ?? 'Selected' : null
    };
  }

  private formatDraftPickOverviewChip(draft: RawDraft, pick: DraftPick): string {
    return `${draft.DisplayDraftType} ${pick.DisplayPick}`;
  }

  private formatOwnerFallback(ownerName: string): string {
    return ownerName.trim().charAt(0).toUpperCase() || '?';
  }

  private buildTeamById(teams: FantasyTeam[]): Map<number, FantasyTeam> {
    return new Map(teams.map(team => [team.TeamID, team]));
  }

  private buildPlayerById(players: Player[]): Map<string, Player> {
    return new Map(players.map(player => [player.ID, player]));
  }

  private getNextDraftPickEntries(drafts: RawDraft[]): DraftPickOverviewEntry[] {
    return drafts
      .flatMap(draft => this.getOpenDraftPicks(draft).map(pick => ({ draft, pick })))
      .sort((a, b) => this.compareNextDraftPickEntries(a, b));
  }

  private getRecentDraftPickEntries(drafts: RawDraft[]): DraftPickOverviewEntry[] {
    return drafts
      .flatMap(draft => this.getSelectedDraftPicks(draft).map(pick => ({ draft, pick })))
      .sort((a, b) => this.compareRecentDraftPickEntries(a, b));
  }

  private compareNextDraftPickEntries(a: DraftPickOverviewEntry, b: DraftPickOverviewEntry): number {
    const liveDiff = Number(this.isDraftLive(b.draft)) - Number(this.isDraftLive(a.draft));
    if (liveDiff !== 0) return liveDiff;

    const draftNoDiff = (a.draft.DraftNo ?? 999) - (b.draft.DraftNo ?? 999);
    if (draftNoDiff !== 0) return draftNoDiff;

    return compareDraftPicksByDraftOrder(a.pick, b.pick);
  }

  private compareRecentDraftPickEntries(a: DraftPickOverviewEntry, b: DraftPickOverviewEntry): number {
    const liveDiff = Number(this.isDraftLive(b.draft)) - Number(this.isDraftLive(a.draft));
    if (liveDiff !== 0) return liveDiff;

    const draftNoDiff = (b.draft.DraftNo ?? 0) - (a.draft.DraftNo ?? 0);
    if (draftNoDiff !== 0) return draftNoDiff;

    return (b.pick.SleeperPickNo ?? b.pick.OverallPick ?? 0) - (a.pick.SleeperPickNo ?? a.pick.OverallPick ?? 0);
  }

  private formatDraftSummaryStatus(statusClass: DraftSeasonStatusClass): string {
    switch (statusClass) {
      case 'live': return 'Live';
      case 'completed': return 'Completed';
      default: return 'Upcoming';
    }
  }

  private getDraftSummaryStatusClass(draft: RawDraft): DraftSeasonStatusClass {
    if (this.isDraftLive(draft)) return 'live';

    return this.getOpenDraftPicks(draft).length > 0 ? 'upcoming' : 'completed';
  }

  private isDraftLive(draft: RawDraft): boolean {
    const status = draft.Status?.toLowerCase() ?? '';
    const displayStatus = draft.DisplayStatus?.toLowerCase() ?? '';
    const sleeperStatus = draft.SleeperStatus?.toLowerCase() ?? '';

    return status === 'live'
      || status === 'in_draft'
      || status === 'indraft'
      || displayStatus === 'live'
      || sleeperStatus === 'drafting';
  }

  private getOpenDraftPicks(draft: RawDraft): DraftPick[] {
    return draft.Picks
      .filter(pick => !this.isDraftPickSelected(pick))
      .sort(compareDraftPicksByDraftOrder);
  }

  private getSelectedDraftPicks(draft: RawDraft): DraftPick[] {
    return draft.Picks
      .filter(pick => this.isDraftPickSelected(pick))
      .sort((a, b) => (b.SleeperPickNo ?? b.OverallPick ?? 0) - (a.SleeperPickNo ?? a.OverallPick ?? 0));
  }

  private isDraftPickSelected(pick: DraftPick): boolean {
    return pick.Status === 'Picked'
      || !!pick.PlayerID
      || !!pick.PlayerName
      || pick.SleeperPickNo !== null;
  }

  private getCurrentSeasonDraftPickGroups(
    picks: DraftPick[],
    season: string,
    maxRound: number
  ): DraftPickDisplayGroup[] {
    const currentSeasonPicks = picks
      .filter(pick => pick.Season === season)
      .sort(compareDraftPicksByDraftThenOrder);

    const groups = new Map<string, DraftPickDisplayGroup>();

    for (const pick of currentSeasonPicks) {
      const draftKey = pick.DraftKey;
      const label =
        pick.Draft?.DisplayDraftType ??
        pick.Draft?.DisplayAbrDraftKey ??
        pick.Draft?.DisplayDraftKey ??
        pick.DraftKey;

      const sortOrder = pick.Draft?.DraftNo ?? 999;

      if (!groups.has(draftKey)) {
        groups.set(draftKey, {
          draftKey,
          label,
          count: 0,
          picks: [],
          sortOrder
        });
      }

      const group = groups.get(draftKey)!;
      group.count += 1;
      group.picks.push({
        display: pick.DisplayPick,
        round: pick.Round,
        backgroundColor: getDraftRoundColor(pick.Round, maxRound)
      });
    }

    return [...groups.values()]
      .sort((a, b) => a.sortOrder - b.sortOrder);
  }

  private getMaxDisplayedDraftRound(teams: FantasyTeam[], season: string): number {
    const rounds = teams
      .flatMap(team => team.DraftPicks ?? [])
      .filter(pick => pick.Season === season)
      .map(pick => Number(pick.Round) || 0)
      .filter(round => round > 0);

    return rounds.length ? Math.max(...rounds) : 1;
  }

  private formatDraftStartTime(draft: RawDraft): string | null {
    const startTime = this.getDraftStartDate(draft);
    if (!startTime) return null;

    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(startTime);
  }

  private getDraftStartDate(draft: RawDraft): Date | null {
    const rawStart = draft.DraftStartTimeUtc ?? draft.SleeperStartTime;
    if (rawStart === null || rawStart === undefined || rawStart === '') return null;

    const startTime = typeof rawStart === 'number'
      ? new Date(rawStart)
      : new Date(rawStart);

    return Number.isNaN(startTime.getTime()) ? null : startTime;
  }

  private parseDeadline(deadlineValue: string): Date {
    if (/^\d{4}-\d{2}-\d{2}$/.test(deadlineValue)) {
      return new Date(`${deadlineValue}T23:59:59Z`);
    }

    return new Date(deadlineValue);
  }

  private formatDeadlineCountdown(msLeft: number): string {
    const minuteMs = 1000 * 60;
    const hourMs = minuteMs * 60;
    const dayMs = hourMs * 24;
    const dayHourThresholdMs = dayMs * 4;

    if (msLeft >= dayMs) {
      const totalHours = Math.floor(msLeft / hourMs);
      const days = Math.floor(totalHours / 24);
      const hours = totalHours % 24;

      if (msLeft < dayHourThresholdMs) {
        return `${days} ${days === 1 ? 'day' : 'days'} ${hours} h`;
      }

      return `${days} ${days === 1 ? 'day' : 'days'}`;
    }

    const totalMinutes = Math.max(1, Math.floor(msLeft / minuteMs));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours === 0) {
      return `${minutes} min`;
    }

    if (minutes === 0) {
      return `${hours} h`;
    }

    return `${hours} h ${minutes} min`;
  }

  standingEmoji(place: number): string {
    switch (place) {
      case 1: return '🏆';
      case 2: return '🥈';
      case 3: return '🥉';
      case 4: return '4️⃣';
      case 5: return '5️⃣';
      case 6: return '6️⃣';
      case 7: return '7️⃣';
      case 8: return '8️⃣';
      case 9: return '9️⃣';
      case 10: return '🔟';
      default:
        return place.toString();
    }
  }

  repeatEmoji(emoji: string, count: number): string {
    return Array(count).fill(emoji).join('');
  }

  repeatEmojiLimited(emoji: string, count: number): string {
    if (count <= 2) return Array(count).fill(emoji).join('');
    return `${count}` + Array(1).fill(emoji).join('');
  }

  formatSalaryDollars(amount: number, plus: boolean, afterPoint: number): string {
    if(amount >= 0){
      if (plus) {
        return `+ $${(amount / 1_000_000).toFixed(afterPoint)} Mio.`;
      } else {
        return `$${(amount / 1_000_000).toFixed(afterPoint)} Mio.`;
      }
    } else {
      return `- $${(-amount / 1_000_000).toFixed(afterPoint)} Mio.`;
    }
  }

  sortPlayersBySalary(players: Player[], useProjected: boolean): Player[] {
    const sorted = [...players].sort((a, b) => {
      if (useProjected) {
        const diff = (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
        if (diff !== 0) return diff;
        return (b.Salary ?? 0) - (a.Salary ?? 0);
      } else {
        const diff = (b.Salary ?? 0) - (a.Salary ?? 0);
        if (diff !== 0) return diff;
        return (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
      }
    });
    return sorted;
  }

}
