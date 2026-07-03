import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import type { DraftPick, FantasyTeam, League, Player, RawDraft } from '../../core/models/fantasy.models';
import { DataService } from '../../core/services/data.service';
import { AllTimeStandingsComponent } from '../../shared/components/all-time-standings/all-time-standings';
import { SeasonResultsComponent } from '../../shared/components/season-results/season-results';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { getDraftRoundColor } from '../../shared/utils/draft-ui.util';
import {
  buildAllTimeStandings,
  buildCurrentStandings,
  buildSeasonResults,
  getCurrentSeasonAwards,
  getPreviousChampion
} from '../../shared/utils/league-standings-view.util';

type DraftSeasonStatusClass = 'live' | 'upcoming' | 'completed';

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
  details: string;
  status: string;
  statusClass: DraftSeasonStatusClass;
}

interface DraftCapitalRow {
  team: FantasyTeam;
  teamName: string;
  rookieCount: number;
  freeAgentCount: number;
  bestPick: string;
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
  playerDisplay: string | null;
}

interface DraftSeasonDashboard {
  drafts: DraftSeasonDraftRow[];
  draftCapital: DraftCapitalRow[];
  nextPicks: DraftPickOverviewRow[];
  recentPicks: DraftPickOverviewRow[];
}

interface SalaryTeamSummary {
  total: number;
}

@Component({
  selector: 'app-overview',
  imports: [
    CommonModule,
    SharedMaterialImports,
    SeasonResultsComponent,
    AllTimeStandingsComponent
  ],
  standalone: true,
  templateUrl: './overview.html',
  styleUrl: './overview.scss'
})
export class OverviewComponent {

  private dataService = inject(DataService);
  expandedTeamId: number | null = null;

  toggleTeam(teamId: number): void {
    this.expandedTeamId =
      this.expandedTeamId === teamId ? null : teamId;
  }

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams, drafts }: { league: League; teams: FantasyTeam[]; drafts: RawDraft[] }) => {

      const offSeason = league.Status === 'Off-Season';
      const draftSeason = league.Status === 'Draft-Season';
      const currentSeason = league.Season;
      const maxDisplayedDraftRound = this.getMaxDisplayedDraftRound(teams, currentSeason);

      // 🏆 Champion / Standings / Results
      const champion = getPreviousChampion(teams);
      const currentStandings = buildCurrentStandings(league, teams);
      const standings = currentStandings.map(row => ({
        ...row.team,
        DisplayPlace: row.displayPlace
      }));
      const seasonResults = buildSeasonResults(teams);
      const allTimeStandings = buildAllTimeStandings(teams);
      const allTime = allTimeStandings.map(row => row.team);

      // 💰 Salary je Team
      const salaryByTeam = teams.map(t => {

        const playerCount = Math.min(
          league.SalaryRelevantTeamSize, // 👈 aus League!
          t.Roster.length
        );

        // sort aus DataService nutzen
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

        // Draft Picks
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

      const draftSeasonDashboard = this.buildDraftSeasonDashboard(drafts, teams, currentSeason, draftSeason);

      // 🔥 Awards
      const awards = getCurrentSeasonAwards(league);

      // ⏱️ Deadline
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
        awards,
        deadlineDisplay,
        deadlineInfo,
        offSeason,
        draftSeason
      };
    })
  );

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
    season: string,
    draftSeason: boolean
  ): DraftSeasonDashboard | null {
    if (!draftSeason) return null;

    const seasonDrafts = this.getSeasonDrafts(drafts, season);
    if (seasonDrafts.length === 0) return null;

    const teamById = this.buildTeamById(teams);

    return {
      drafts: seasonDrafts.map(draft => this.buildDraftSeasonDraftRow(draft)),
      draftCapital: this.buildDraftCapitalRows(teams, season),
      nextPicks: this.getNextDraftPickEntries(seasonDrafts)
        .slice(0, 3)
        .map(entry => this.buildDraftPickOverviewRow(entry.pick, entry.draft, teamById, false)),
      recentPicks: this.getRecentDraftPickEntries(seasonDrafts)
        .slice(0, 2)
        .map(entry => this.buildDraftPickOverviewRow(entry.pick, entry.draft, teamById, true))
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
    const details = [
      `${draft.Settings.Rounds} rounds`,
      `${total} picks`,
      `${selected} selected`,
      `${remaining} remaining`
    ];
    const startDisplay = this.formatDraftStartTime(draft);

    if (startDisplay) {
      details.push(`starts ${startDisplay}`);
    }

    return {
      name: `${draft.DisplayDraftType} Draft`,
      details: details.join(' · '),
      status: this.formatDraftSummaryStatus(statusClass),
      statusClass
    };
  }

  private buildDraftCapitalRows(teams: FantasyTeam[], season: string): DraftCapitalRow[] {
    return teams
      .map(team => {
        const currentSeasonPicks = team.DraftPicks.filter(pick => pick.Season === season);
        const bestPick = [...currentSeasonPicks]
          .filter(pick => pick.OverallPick !== null)
          .sort((a, b) => {
            const draftNoDiff = (a.Draft?.DraftNo ?? 999) - (b.Draft?.DraftNo ?? 999);
            if (draftNoDiff !== 0) return draftNoDiff;
            return (a.OverallPick ?? 9999) - (b.OverallPick ?? 9999);
          })[0];

        return {
          team,
          teamName: team.Team ?? team.Owner,
          rookieCount: currentSeasonPicks.filter(pick => pick.DraftType === 'Rookie').length,
          freeAgentCount: currentSeasonPicks.filter(pick => pick.DraftType === 'Free_Agent').length,
          bestPick: bestPick ? this.formatBestDraftPick(bestPick) : '—'
        };
      })
      .sort((a, b) => {
        const totalDiff = (b.rookieCount + b.freeAgentCount) - (a.rookieCount + a.freeAgentCount);
        if (totalDiff !== 0) return totalDiff;
        return a.teamName.localeCompare(b.teamName);
      });
  }

  private formatBestDraftPick(pick: DraftPick): string {
    const prefix = pick.DraftType === 'Free_Agent' ? 'FA' : 'R';
    return `${prefix} ${pick.DisplayPick}`;
  }

  private buildDraftPickOverviewRow(
    pick: DraftPick,
    draft: RawDraft,
    teamById: Map<number, FantasyTeam>,
    includePlayer: boolean
  ): DraftPickOverviewRow {
    const owner = teamById.get(pick.CurrentOwnerRosterID);
    const ownerName = owner?.Team ?? owner?.Owner ?? `Team ${pick.CurrentOwnerRosterID}`;

    return {
      displayPick: this.formatDraftPickOverviewChip(draft, pick),
      owner: ownerName,
      ownerAbbr: owner?.TeamAbbr ?? this.formatOwnerFallback(ownerName),
      ownerAvatar: owner?.Avatar ?? null,
      ownerFallback: this.formatOwnerFallback(ownerName),
      playerDisplay: includePlayer ? pick.PlayerName ?? 'Selected' : null
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

    return (a.pick.OverallPick ?? 9999) - (b.pick.OverallPick ?? 9999);
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
      .sort((a, b) => (a.OverallPick ?? 9999) - (b.OverallPick ?? 9999));
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
      .sort((a, b) => {
        const draftNoDiff = (a.Draft?.DraftNo ?? 999) - (b.Draft?.DraftNo ?? 999);
        if (draftNoDiff !== 0) return draftNoDiff;

        const roundDiff = (a.Round ?? 999) - (b.Round ?? 999);
        if (roundDiff !== 0) return roundDiff;

        return (a.OverallPick ?? 9999) - (b.OverallPick ?? 9999);
      });

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
      case 1: return '🏆';   // Pokal für Champion
      case 2: return '🥈';   // Silbermedaille
      case 3: return '🥉';   // Bronzemedaille
      case 4: return '4️⃣';   // Zahlen-Emoji ab 4
      case 5: return '5️⃣';   // Zahlen-Emoji ab 5
      case 6: return '6️⃣';   // Zahlen-Emoji ab 6
      case 7: return '7️⃣';   // Zahlen-Emoji ab 7
      case 8: return '8️⃣';   // Zahlen-Emoji ab 8
      case 9: return '9️⃣';   // Zahlen-Emoji ab 9
      case 10: return '🔟';   // Zahlen-Emoji ab 10
      default:
        return place.toString(); // fallback auf normale Zahl, wenn >10
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
        // Primär: SalaryProjected, Sekundär: Salary
        const diff = (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
        if (diff !== 0) return diff;
        return (b.Salary ?? 0) - (a.Salary ?? 0);
      } else {
        // Primär: Salary, Sekundär: SalaryProjected
        const diff = (b.Salary ?? 0) - (a.Salary ?? 0);
        if (diff !== 0) return diff;
        return (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
      }
    });
    return sorted;
  }

}
