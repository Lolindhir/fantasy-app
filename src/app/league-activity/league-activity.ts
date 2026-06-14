import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';
import { DataService, DraftPick, FantasyTeam, RawDraft } from '../services/data-service';
import { SharedMaterialImports } from '../shared/shared-material-imports';

interface DraftPickViewModel {
  pick: DraftPick;
  currentOwnerName: string;
  originalOwnerName: string;
  isCurrentlyTraded: boolean;
  roundColor: string;
}

interface DraftRoundViewModel {
  round: number;
  label: string;
  picks: DraftPickViewModel[];
}

interface DraftViewModel {
  draft: RawDraft;
  statusLabel: string;
  statusClass: string;
  subtitle: string;
  pickCount: number;
  tradedPickCount: number;
  pickedCount: number;
  rounds: DraftRoundViewModel[];
}

interface LeagueActivityViewModel {
  drafts: DraftViewModel[];
  nextDraft?: DraftViewModel;
  draftCount: number;
  tradedPickCount: number;
  pickedCount: number;
}

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports
  ],
  templateUrl: './league-activity.html',
  styleUrl: './league-activity.scss'
})
export class LeagueActivityComponent {

  private dataService = inject(DataService);

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ drafts, teams }) => this.createViewModel(drafts, teams))
  );

  private createViewModel(drafts: RawDraft[], teams: FantasyTeam[]): LeagueActivityViewModel {
    const teamNameByRosterId = new Map<number, string>();

    teams.forEach(team => {
      teamNameByRosterId.set(team.TeamID, team.Team || `Team ${team.Owner}`);
    });

    const maxRound = this.getMaxRound(drafts);

    const draftViewModels = [...drafts]
      .sort((a, b) => {
        const seasonDiff = Number(a.Season) - Number(b.Season);
        if (seasonDiff !== 0) return seasonDiff;
        return (a.DraftNo ?? 999) - (b.DraftNo ?? 999);
      })
      .map(draft => this.createDraftViewModel(draft, teamNameByRosterId, maxRound));

    return {
      drafts: draftViewModels,
      nextDraft: draftViewModels[0],
      draftCount: draftViewModels.length,
      tradedPickCount: draftViewModels.reduce((sum, draft) => sum + draft.tradedPickCount, 0),
      pickedCount: draftViewModels.reduce((sum, draft) => sum + draft.pickedCount, 0)
    };
  }

  private createDraftViewModel(
    draft: RawDraft,
    teamNameByRosterId: Map<number, string>,
    maxRound: number
  ): DraftViewModel {
    const picks = [...(draft.Picks ?? [])]
      .sort((a, b) => {
        const roundDiff = (a.Round ?? 999) - (b.Round ?? 999);
        if (roundDiff !== 0) return roundDiff;

        const positionDiff = (a.PositionInRound ?? 999) - (b.PositionInRound ?? 999);
        if (positionDiff !== 0) return positionDiff;

        return (a.OverallPick ?? 9999) - (b.OverallPick ?? 9999);
      })
      .map(pick => this.createPickViewModel(pick, teamNameByRosterId, maxRound));

    const rounds = new Map<number, DraftPickViewModel[]>();
    picks.forEach(pick => {
      const round = pick.pick.Round;
      if (!rounds.has(round)) {
        rounds.set(round, []);
      }
      rounds.get(round)!.push(pick);
    });

    const roundGroups = [...rounds.entries()]
      .sort(([a], [b]) => a - b)
      .map(([round, roundPicks]) => ({
        round,
        label: `Round ${round}`,
        picks: roundPicks
      }));

    const pickedCount = picks.filter(item => item.pick.Status === 'Picked' || !!item.pick.PlayerName).length;
    const tradedPickCount = picks.filter(item => item.isCurrentlyTraded).length;

    return {
      draft,
      statusLabel: draft.Status || draft.SleeperStatus || 'Unknown',
      statusClass: this.getStatusClass(draft.Status || draft.SleeperStatus || 'Unknown'),
      subtitle: this.getDraftSubtitle(draft),
      pickCount: picks.length,
      tradedPickCount,
      pickedCount,
      rounds: roundGroups
    };
  }

  private createPickViewModel(
    pick: DraftPick,
    teamNameByRosterId: Map<number, string>,
    maxRound: number
  ): DraftPickViewModel {
    return {
      pick,
      currentOwnerName: this.getTeamName(teamNameByRosterId, pick.CurrentOwnerRosterID),
      originalOwnerName: this.getTeamName(teamNameByRosterId, pick.OriginalOwnerRosterID),
      isCurrentlyTraded: pick.IsCurrentlyTraded || pick.CurrentOwnerRosterID !== pick.OriginalOwnerRosterID,
      roundColor: this.getRoundColor(pick.Round, maxRound)
    };
  }

  private getTeamName(teamNameByRosterId: Map<number, string>, rosterId: number): string {
    return teamNameByRosterId.get(rosterId) ?? `Roster ${rosterId}`;
  }

  private getDraftSubtitle(draft: RawDraft): string {
    const parts = [
      `${draft.Settings?.Rounds ?? 0} Rounds`,
      draft.OrderMode,
      draft.OrderSource
    ].filter(Boolean);

    return parts.join(' · ');
  }

  private getMaxRound(drafts: RawDraft[]): number {
    const rounds = drafts
      .flatMap(draft => draft.Picks ?? [])
      .map(pick => Number(pick.Round) || 0)
      .filter(round => round > 0);

    return rounds.length ? Math.max(...rounds) : 1;
  }

  private getRoundColor(round: number, maxRound: number): string {
    if (!round || maxRound <= 1) {
      return 'hsl(35, 55%, 84%)';
    }

    const ratio = (round - 1) / (maxRound - 1);
    const startHue = 35;
    const endHue = 205;
    const hue = startHue + ratio * (endHue - startHue);

    return `hsl(${hue}, 55%, 84%)`;
  }

  private getStatusClass(status: string): string {
    return status.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }
}
