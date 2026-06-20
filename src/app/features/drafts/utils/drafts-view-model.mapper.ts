import type { DraftPick, FantasyTeam, League, RawDraft } from '../../../core/models/fantasy.models';
import type {
  CompactOwnerPickGroupViewModel,
  DraftPickViewModel,
  DraftRoundViewModel,
  DraftsViewModel,
  DraftViewModel,
  TeamDisplayViewModel
} from '../models/drafts-view.models';

export function createDraftsViewModel(
  league: League,
  drafts: RawDraft[],
  teams: FantasyTeam[]
): DraftsViewModel {
  const teamByRosterId = createTeamDisplayMap(teams);
  const maxRound = getMaxRound(drafts);

  const draftViewModels = [...drafts]
    .sort(compareDraftsBySeasonAndNumber)
    .map(draft => createDraftViewModel(draft, teamByRosterId, maxRound));

  return {
    currentSeason: league.Season,
    currentSeasonDrafts: draftViewModels.filter(draft => draft.draft.Season === league.Season),
    futureDrafts: draftViewModels.filter(draft => draft.draft.Season !== league.Season),
    draftCount: draftViewModels.length,
    tradedPickCount: draftViewModels.reduce((sum, draft) => sum + draft.tradedPickCount, 0),
    pickCount: draftViewModels.reduce((sum, draft) => sum + draft.pickCount, 0),
    pickedCount: draftViewModels.reduce((sum, draft) => sum + draft.pickedCount, 0)
  };
}

function createTeamDisplayMap(teams: FantasyTeam[]): Map<number, TeamDisplayViewModel> {
  const teamByRosterId = new Map<number, TeamDisplayViewModel>();

  teams.forEach(team => {
    teamByRosterId.set(team.TeamID, {
      id: team.TeamID,
      name: team.Team || `Team ${team.Owner}`,
      avatar: team.Avatar
    });
  });

  return teamByRosterId;
}

function compareDraftsBySeasonAndNumber(a: RawDraft, b: RawDraft): number {
  const seasonDiff = Number(a.Season) - Number(b.Season);
  if (seasonDiff !== 0) return seasonDiff;
  return (a.DraftNo ?? 999) - (b.DraftNo ?? 999);
}

function createDraftViewModel(
  draft: RawDraft,
  teamByRosterId: Map<number, TeamDisplayViewModel>,
  maxRound: number
): DraftViewModel {
  const picks = [...(draft.Picks ?? [])]
    .sort(comparePicksByDraftOrder)
    .map(pick => createPickViewModel(pick, teamByRosterId, maxRound));

  const pickedCount = picks.filter(item => item.pick.Status === 'Picked' || !!item.pick.PlayerName).length;
  const rawStatus = draft.Status || draft.SleeperStatus || 'Unknown';

  return {
    draft,
    statusLabel: draft.DisplayStatus || rawStatus,
    statusClass: getStatusClass(rawStatus),
    pickCount: picks.length,
    tradedPickCount: picks.filter(item => item.isCurrentlyTraded).length,
    pickedCount,
    rounds: createRoundGroups(picks),
    ownerPickGroups: createOwnerPickGroups(picks, getDraftMaxRound(draft))
  };
}

function comparePicksByDraftOrder(a: DraftPick, b: DraftPick): number {
  const roundDiff = (a.Round ?? 999) - (b.Round ?? 999);
  if (roundDiff !== 0) return roundDiff;

  const positionDiff = (a.PositionInRound ?? 999) - (b.PositionInRound ?? 999);
  if (positionDiff !== 0) return positionDiff;

  return (a.OverallPick ?? 9999) - (b.OverallPick ?? 9999);
}

function createPickViewModel(
  pick: DraftPick,
  teamByRosterId: Map<number, TeamDisplayViewModel>,
  maxRound: number
): DraftPickViewModel {
  return {
    pick,
    currentOwner: getTeamDisplay(teamByRosterId, pick.CurrentOwnerRosterID),
    originalOwner: getTeamDisplay(teamByRosterId, pick.OriginalOwnerRosterID),
    isCurrentlyTraded: pick.IsCurrentlyTraded || pick.CurrentOwnerRosterID !== pick.OriginalOwnerRosterID,
    roundColor: getRoundColor(pick.Round, maxRound)
  };
}

function createRoundGroups(picks: DraftPickViewModel[]): DraftRoundViewModel[] {
  const rounds = new Map<number, DraftPickViewModel[]>();

  picks.forEach(pick => {
    const round = pick.pick.Round;
    if (!rounds.has(round)) rounds.set(round, []);
    rounds.get(round)!.push(pick);
  });

  return [...rounds.entries()]
    .sort(([a], [b]) => a - b)
    .map(([round, roundPicks]) => ({
      round,
      label: `Round ${round}`,
      picks: roundPicks
    }));
}

function createOwnerPickGroups(
  picks: DraftPickViewModel[],
  draftMaxRound: number
): CompactOwnerPickGroupViewModel[] {
  const groups = new Map<number, DraftPickViewModel[]>();

  picks.forEach(pick => {
    const ownerId = pick.currentOwner.id;
    if (!groups.has(ownerId)) groups.set(ownerId, []);
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
          color: pick.roundColor,
          originalOwner: pick.originalOwner,
          isCurrentlyTraded: pick.isCurrentlyTraded
        })),
        pickCount: sortedPicks.length,
        roundCounts: getRoundCounts(sortedPicks, draftMaxRound)
      };
    })
    .sort(compareOwnerPickGroupsByPickStrength);
}

function getRoundCounts(picks: DraftPickViewModel[], maxRound: number): number[] {
  const roundCounts = Array.from({ length: maxRound }, () => 0);

  picks.forEach(pick => {
    const roundIndex = pick.pick.Round - 1;
    if (roundIndex >= 0 && roundIndex < maxRound) roundCounts[roundIndex] += 1;
  });

  return roundCounts;
}

function compareOwnerPickGroupsByPickStrength(
  a: CompactOwnerPickGroupViewModel,
  b: CompactOwnerPickGroupViewModel
): number {
  const maxRound = Math.max(a.roundCounts.length, b.roundCounts.length);

  for (let index = 0; index < maxRound; index++) {
    const diff = (b.roundCounts[index] ?? 0) - (a.roundCounts[index] ?? 0);
    if (diff !== 0) return diff;
  }

  return a.owner.name.localeCompare(b.owner.name, 'en', { sensitivity: 'base' });
}

function getTeamDisplay(teamByRosterId: Map<number, TeamDisplayViewModel>, rosterId: number): TeamDisplayViewModel {
  return teamByRosterId.get(rosterId) ?? {
    id: rosterId,
    name: `Roster ${rosterId}`,
    avatar: 'assets/default-team-avatar.png'
  };
}

function getDraftMaxRound(draft: RawDraft): number {
  const configuredRounds = Number(draft.Settings?.Rounds) || 0;
  const maxPickRound = (draft.Picks ?? [])
    .map(pick => Number(pick.Round) || 0)
    .reduce((max, round) => Math.max(max, round), 0);

  return Math.max(configuredRounds, maxPickRound, 1);
}

function getMaxRound(drafts: RawDraft[]): number {
  const rounds = drafts
    .flatMap(draft => draft.Picks ?? [])
    .map(pick => Number(pick.Round) || 0)
    .filter(round => round > 0);

  return rounds.length ? Math.max(...rounds) : 1;
}

function getRoundColor(round: number, maxRound: number): string {
  if (!round || maxRound <= 1) return 'hsl(35, 55%, 84%)';

  const ratio = (round - 1) / (maxRound - 1);
  const hue = 35 + ratio * (205 - 35);

  return `hsl(${hue}, 55%, 84%)`;
}

function getStatusClass(status: string): string {
  return status.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}
