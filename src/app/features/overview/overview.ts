import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import type { AwardInStanding, DraftPick, FantasyTeam, League, Player } from '../../core/models/fantasy.models';
import { DataService } from '../../core/services/data.service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { getDraftRoundColor } from '../../shared/utils/draft-ui.util';

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

@Component({
  selector: 'app-overview',
  imports: [
    CommonModule,
    SharedMaterialImports
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

      const isFinished = league.IsFinished;
      const offSeason = league.Status === 'Off-Season';
      const currentSeason = league.Season;
      const maxDisplayedDraftRound = this.getMaxDisplayedDraftRound(teams, currentSeason);

      // 🏆 Champion
      const champion = teams.find(t =>
        t.Placements.Previous.Playoffs?.Place === 1
      );

      // 📊 Standings
      const standings = [...teams].map(t => ({
        ...t,
        DisplayPlace: isFinished
          ? t.Placements.Previous.Playoffs?.Place ?? t.Placements.Previous.Regular.Place
          : t.Standing
      })).sort((a, b) => a.DisplayPlace - b.DisplayPlace);

      // 🏛️ All-Time
      const allTime = [...teams].sort((a, b) =>
        a.Placements.AllTime.Playoffs.Place - b.Placements.AllTime.Playoffs.Place
      );

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

      // 🔥 Awards
      const currentStanding = league.Standings.find(s => s.Season === currentSeason);
      // Awards aus dem Standing extrahieren oder leeres Array setzen
      const awards: AwardInStanding[] = currentStanding?.Awards
        ? currentStanding.Awards.map(a => ({
            ...a,
          }))
        : [];

      // ⏱️ Deadline
      const deadline = new Date(league.CapDeadline);
      const deadlineDisplay = deadline.toLocaleDateString();
      const now = new Date();
      const msLeft = deadline.getTime() - now.getTime();

      const deadlineInfo = msLeft > 0 ? {
        days: Math.floor(msLeft / (1000 * 60 * 60 * 24)),
        hours: Math.floor((msLeft / (1000 * 60 * 60)) % 24)
      } : null;

      return {
        league,
        champion,
        standings,
        allTime,
        salaryByTeam,
        awards,
        deadlineDisplay,
        deadlineInfo,
        offSeason
      };
    })
  );

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
