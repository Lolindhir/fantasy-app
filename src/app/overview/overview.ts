import { Component, OnInit, inject } from '@angular/core';
import { DataService, League, FantasyTeam, AwardInStanding, Player } from '../services/data-service';
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { map } from 'rxjs/operators';
import { CommonModule } from '@angular/common';

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
export class OverviewComponent implements OnInit {

  private dataService = inject(DataService);
  expandedTeamId: number | null = null;

  toggleTeam(teamId: number) {
    this.expandedTeamId =
      this.expandedTeamId === teamId ? null : teamId;
  }

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams }: { league: League; teams: FantasyTeam[] }) => {

      const isFinished = league.IsFinished;
      const offSeason = league.Status == "Off-Season"
      //const offSeason = true;

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
          countedPlayers: playerCount
        };

      }).sort((a, b) => a.total - b.total);

      // 🔥 Awards
      const currentSeason = league.Season; // z. B. "2026"
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

  constructor() {}

  ngOnInit(): void {
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
