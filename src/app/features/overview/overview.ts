import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import type { DraftPick, FantasyTeam, League, Player } from '../../core/models/fantasy.models';
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
    map(({ league, teams }: { league: League; teams: FantasyTeam[] }) => {

      const offSeason = league.Status === 'Off-Season';
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
        awards,
        deadlineDisplay,
        deadlineInfo,
        offSeason
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
        title: '✅ Cap Check bestanden',
        summaryText: 'Alle Teams sind unter dem Salary Cap.',
        detailText: `${compliantTeams} von ${salaryByTeam.length} Teams compliant`,
        allCompliant: true
      };
    }

    const worstOverage = Math.max(...overCapTeams.map(team => team.total - league.SalaryCap));
    const teamLabel = overCapTeams.length === 1 ? 'Team muss' : 'Teams müssen';

    return {
      title: '🚨 Cap Check offen',
      summaryText: `${overCapTeams.length} ${teamLabel} noch Cap freimachen.`,
      detailText: `${compliantTeams} compliant · größter Fehlbetrag ${this.formatSalaryDollars(worstOverage, false, 1)}`,
      allCompliant: false
    };
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
        return (b.SalaryProjected ?? 0) - (a.Salary ?? 0);
      }
    });
    return sorted;
  }

}