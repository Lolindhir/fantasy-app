import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';
import { DataService, DraftPick, FantasyTeam, League, RawDraft } from '../../services/data-service';
import { SharedMaterialImports } from '../../shared/shared-material-imports';

type LeagueActivityTab = 'drafts' | 'moves';

interface TeamDisplayViewModel {
  id: number;
  name: string;
  avatar: string;
}

interface DraftPickViewModel {
  pick: DraftPick;
  currentOwner: TeamDisplayViewModel;
  originalOwner: TeamDisplayViewModel;
  isCurrentlyTraded: boolean;
  roundColor: string;
}

interface DraftRoundViewModel {
  round: number;
  label: string;
  picks: DraftPickViewModel[];
}

interface CompactRoundPickViewModel {
  label: string;
  color: string;
}

interface CompactOwnerPickGroupViewModel {
  owner: TeamDisplayViewModel;
  picks: CompactRoundPickViewModel[];
  pickCount: number;
  roundCounts: number[];
}

interface DraftViewModel {
  draft: RawDraft;
  statusLabel: string;
  statusClass: string;
  pickCount: number;
  tradedPickCount: number;
  pickedCount: number;
  rounds: DraftRoundViewModel[];
  ownerPickGroups: CompactOwnerPickGroupViewModel[];
}

interface LeagueActivityViewModel {
  currentSeason: string;
  currentSeasonDrafts: DraftViewModel[];
  upcomingDrafts: DraftViewModel[];
  draftCount: number;
  tradedPickCount: number;
  pickCount: number;
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
  activeTab: LeagueActivityTab = 'drafts';

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, drafts, teams }) => this.createViewModel(league, drafts, teams))
  );

  setActiveTab(tab: LeagueActivityTab): void {
    this.activeTab = tab;
  }

  private createViewModel(league: League, drafts: RawDraft[], teams: FantasyTeam[]): LeagueActivityViewModel {
    const teamByRosterId = new Map<number, TeamDisplayViewModel>();

    teams.forEach(team => {
      teamByRosterId.set(team.TeamID, {
        id: team.TeamID,
        name: team.Team || `Team ${team.Owner}`,
        avatar: team.Avatar
      });
    });

    const maxRound = this.getMaxRound(drafts);

    const draftViewModels = [...drafts]
      .sort((a, b) => {
        const seasonDiff = Number(a.Season) - Number(b.Season);
        if (seasonDiff !== 0) return seasonDiff;
        return (a.DraftNo ?? 999) - (b.DraftNo ?? 999);
      })
      .map(draft => this.createDraftViewModel(draft, teamByRosterId, maxRound));

    const currentSeasonDrafts = draftViewModels.filter(draft => draft.draft.Season === league.Season);
    const upcomingDrafts = draftViewModels.filter(draft => draft.draft.Season !== league.Season);

    return {
      currentSeason: league.Season,
      currentSeasonDrafts,
      upcomingDrafts,
      draftCount: draftViewModels.length,
      tradedPickCount: draftViewModels.reduce((sum, draft) => sum + draft.tradedPickCount, 0),
      pickCount: draftViewModels.reduce((sum, draft) => sum + draft.pickCount, 0),
      pickedCount: draftViewModels.reduce((sum, draft) => sum + draft.pickedCount, 0)
    };
  }

  private createDraftViewModel(
    draft: RawDraft,
    teamByRosterId: Map<number, TeamDisplayViewModel>,
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
      .map(pick => this.createPickViewModel(pick, teamByRosterId, maxRound));

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
    const draftMaxRound = this.getDraftMaxRound(draft);
    const rawStatus = draft.Status || draft.SleeperStatus || 'Unknown';
    const displayStatus = (draft as RawDraft & { DisplayStatus?: string }).DisplayStatus;

    return {
      draft,
      statusLabel: displayStatus || rawStatus,
      statusClass: this.getStatusClass(rawStatus),
      pickCount: picks.length,
      tradedPickCount,
      pickedCount,
      rounds: roundGroups,
      ownerPickGroups: this.createOwnerPickGroups(picks, draftMaxRound)
    };
  }

  private createPickViewModel(
    pick: DraftPick,
    teamByRosterId: Map<number, TeamDisplayViewModel>,
    maxRound: number
  ): DraftPickViewModel {
    return {
      pick,
      currentOwner: this.getTeamDisplay(teamByRosterId, pick.CurrentOwnerRosterID),
      originalOwner: this.getTeamDisplay(teamByRosterId, pick.OriginalOwnerRosterID),
      isCurrentlyTraded: pick.IsCurrentlyTraded || pick.CurrentOwnerRosterID !== pick.OriginalOwnerRosterID,
      roundColor: this.getRoundColor(pick.Round, maxRound)
    };
  }

  private createOwnerPickGroups(
    picks: DraftPickViewModel[],
    draftMaxRound: number
  ): CompactOwnerPickGroupViewModel[] {
    const groups = new Map<number, DraftPickViewModel[]>();

    picks.forEach(pick => {
      const ownerId = pick.currentOwner.id;
      if (!groups.has(ownerId)) {
        groups.set(ownerId, []);
      }
      groups.get(ownerId)!.push(pick);
    });

    return [...groups.values()]
      .map(ownerPicks => {
        const sortedPicks = [...ownerPicks].sort((a, b) => {
          const roundDiff = a.pick.Round - b.pick.Round;
          if (roundDiff !== 0) return roundDiff;
          return (a.pick.OverallPick ?? 9999) - (b.pick.OverallPick ?? 9999);
        });

        return {
          owner: sortedPicks[0].currentOwner,
          picks: sortedPicks.map(pick => ({
            label: `R${pick.pick.Round}`,
            color: pick.roundColor
          })),
          pickCount: sortedPicks.length,
          roundCounts: this.getRoundCounts(sortedPicks, draftMaxRound)
        };
      })
      .sort((a, b) => this.compareOwnerPickGroupsByPickStrength(a, b));
  }

  private getRoundCounts(picks: DraftPickViewModel[], maxRound: number): number[] {
    const roundCounts = Array.from({ length: maxRound }, () => 0);

    picks.forEach(pick => {
      const roundIndex = pick.pick.Round - 1;
      if (roundIndex >= 0 && roundIndex < maxRound) {
        roundCounts[roundIndex] += 1;
      }
    });

    return roundCounts;
  }

  private compareOwnerPickGroupsByPickStrength(
    a: CompactOwnerPickGroupViewModel,
    b: CompactOwnerPickGroupViewModel
  ): number {
    const maxRound = Math.max(a.roundCounts.length, b.roundCounts.length);

    for (let index = 0; index < maxRound; index++) {
      const diff = (b.roundCounts[index] ?? 0) - (a.roundCounts[index] ?? 0);
      if (diff !== 0) {
        return diff;
      }
    }

    return a.owner.name.localeCompare(b.owner.name, 'en', { sensitivity: 'base' });
  }

  private getTeamDisplay(teamByRosterId: Map<number, TeamDisplayViewModel>, rosterId: number): TeamDisplayViewModel {
    return teamByRosterId.get(rosterId) ?? {
      id: rosterId,
      name: `Roster ${rosterId}`,
      avatar: 'assets/default-team-avatar.png'
    };
  }

  private getDraftMaxRound(draft: RawDraft): number {
    const configuredRounds = Number(draft.Settings?.Rounds) || 0;
    const maxPickRound = (draft.Picks ?? [])
      .map(pick => Number(pick.Round) || 0)
      .reduce((max, round) => Math.max(max, round), 0);

    return Math.max(configuredRounds, maxPickRound, 1);
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
