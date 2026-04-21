import { Component, OnInit, inject } from '@angular/core';
import { DataService, League, FantasyTeam, AwardInStanding } from '../services/data-service';
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

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams }: { league: League; teams: FantasyTeam[] }) => {

      const isFinished =
        league.IsFinished;

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
      const salaryByTeam = teams.map(t => ({
        team: t,
        total: t.Roster.reduce((sum, p) => sum + p.Salary, 0)
      }));

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
        deadlineInfo
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
    if (count <= 3) return Array(count).fill(emoji).join('');
    return Array(3).fill(emoji).join('') + ` +${count - 3}`;
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

}
