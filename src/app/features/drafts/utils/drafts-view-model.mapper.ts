import type { DraftPick, FantasyTeam, League, Player, RawDraft } from '../../../core/models/fantasy.models';
import {
  compareDraftPickCollectionsByStrength,
  compareDraftPicksByDraftOrder,
  getDraftPickRoundCounts
} from '../../../shared/utils/draft-capital.util';
import { getDraftRoundColor, getDraftStatusClass } from '../../../shared/utils/draft-ui.util';
import type {
  CompactOwnerPickGroupViewModel,
  CurrentOwnerPickGroupViewModel,
  DraftPickViewModel,
  DraftRoundViewModel,
  DraftsViewModel,
  DraftViewModel,
  TeamDisplayViewModel
} from '../models/drafts-view.models';

export function createDraftsViewModel(
  league: League,
  drafts: RawDraft[],
  teams: FantasyTeam[],
  players: Player[] = []
): DraftsViewModel {
  const draftViewModels = createDraftViewModels(drafts, teams, players);

  return {
    currentSeason: league.Season,
    currentSeasonDrafts: draftViewModels.filter(draft => draft.draft.Season === league.Season),
    futureDrafts: draftViewModels.filter(draft => Number(draft.draft.Season) > Number(league.Season)),
    draftCount: draftViewModels.length,
    tradedPickCount: draftViewModels.reduce((sum, draft) => sum + draft.tradedPickCount, 0),
    pickCount: draftViewModels.reduce((sum, draft) => sum + draft.pickCount, 0),
    pickedCount: draftViewModels.reduce((sum, draft) => sum + draft.pickedCount, 0)
  };
}

export function createDraftViewModels(
  drafts: RawDraft[],
  teams: FantasyTeam[],
  players: Player[] = []
): DraftViewModel[] {
  const teamByRosterId = createTeamDisplayMap(teams);
  const playerById = createPlayerMap(players);
  const maxRound = getMaxRound(drafts);

  return [...drafts]
    .sort(compareDraftsBySeasonAndNumber)
    .map(draft => createDraftViewModel(draft, teamByRosterId, playerById, maxRound));
}

function createTeamDisplayMap(teams: FantasyTeam[]): Map<number, TeamDisplayViewModel> {
  const teamByRosterId = new Map<number, TeamDisplayViewModel>();

  teams.forEach(team => {
    const rosterId = normalizeRosterId(team.TeamID);
    const teamName = team.Team || `Team ${team.Owner}`;

    const teamDisplay: TeamDisplayViewModel = {
      id: rosterId,
      name: teamName,
      abbr: team.TeamAbbr || teamName,
      avatar: team.Avatar
    };

    teamByRosterId.set(rosterId, teamDisplay);
  });

  return teamByRosterId;
}

function createPlayerMap(players: Player[]): Map<string, Player> {
  const playerById = new Map<string, Player>();

  players.forEach(player => {
    playerById.set(player.ID, player);
  });

  return playerById;
}

function compareDraftsBySeasonAndNumber(a: RawDraft, b: RawDraft): number {
  const seasonDiff = Number(a.Season) - Number(b.Season);
  if (seasonDiff !== 0) return seasonDiff;
  return (a.DraftNo ?? 999) - (b.DraftNo ?? 999);
}

function createDraftViewModel(
  draft: RawDraft,
  teamByRosterId: Map<number, TeamDisplayViewModel>,
  playerById: Map<string, Player>,
  maxRound: number
): DraftViewModel {
  const orderedPicks = [...(draft.Picks ?? [])]
    .sort(compareDraftPicksByDraftOrder)
    .map(pick => createPickViewModel(pick, teamByRosterId, playerById, maxRound));

  const pickedCount = orderedPicks.filter(item => item.isPicked).length;
  const rawStatus = draft.Status || draft.SleeperStatus || 'Unknown';

  return {
    draft,
    statusLabel: draft.DisplayStatus || rawStatus,
    statusClass: getDraftStatusClass(rawStatus),
    pickCount: orderedPicks.length,
    tradedPickCount: orderedPicks.filter(item => item.isCurrentlyTraded).length,
    pickedCount,
    orderedPicks,
    rounds: createRoundGroups(orderedPicks),
    currentOwnerPickGroups: createCurrentOwnerPickGroups(orderedPicks, getDraftMaxRound(draft)),
    ownerPickGroups: createOwnerPickGroups(orderedPicks, getDraftMaxRound(draft))
  };
}

function comparePickViewModelsByDraftOrder(a: DraftPickViewModel, b: DraftPickViewModel): number {
  return compareDraftPicksByDraftOrder(a.pick, b.pick);
}

function createPickViewModel(
  pick: DraftPick,
  teamByRosterId: Map<number, TeamDisplayViewModel>,
  playerById: Map<string, Player>,
  maxRound: number
): DraftPickViewModel {
  const selectedPlayer = pick.PlayerID ? playerById.get(pick.PlayerID) : undefined;
  const selectedPlayerName = selectedPlayer?.NameShort || selectedPlayer?.Name || pick.PlayerName || undefined;
  const currentOwnerRosterId = normalizeRosterId(pick.CurrentOwnerRosterID);
  const originalOwnerRosterId = normalizeRosterId(pick.OriginalOwnerRosterID);

  return {
    pick,
    currentOwner: getTeamDisplay(teamByRosterId, currentOwnerRosterId),
    originalOwner: getTeamDisplay(teamByRosterId, originalOwnerRosterId),
    isCurrentlyTraded: wasPickTraded(pick),
    roundColor: getDraftRoundColor(pick.Round, maxRound),
    isPicked: pick.Status === 'Picked' || !!pick.PlayerName || !!selectedPlayer,
    selectedPlayerName,
    selectedPlayerPosition: selectedPlayer?.Position,
    selectedPlayer
  };
}

function wasPickTraded(pick: DraftPick): boolean {
  return (pick.TradeHistory?.length ?? 0) > 0;
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

function createCurrentOwnerPickGroups(
  picks: DraftPickViewModel[],
  draftMaxRound: number
): CurrentOwnerPickGroupViewModel[] {
  const groups = new Map<number, DraftPickViewModel[]>();

  picks.forEach(pick => {
    const ownerId = pick.currentOwner.id;
    if (!groups.has(ownerId)) groups.set(ownerId, []);
    groups.get(ownerId)!.push(pick);
  });

  return [...groups.values()]
    .map(ownerPicks => {
      const sortedPicks = [...ownerPicks].sort(comparePickViewModelsByDraftOrder);

      return {
        group: {
          owner: sortedPicks[0].currentOwner,
          picks: sortedPicks,
          pickCount: sortedPicks.length
        },
        sortPicks: sortedPicks.map(pick => pick.pick)
      };
    })
    .sort((a, b) => compareOwnerPickGroupSortItemsByPickStrength(a, b, draftMaxRound))
    .map(item => item.group);
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
      const sortedPicks = [...ownerPicks].sort(comparePickViewModelsByDraftOrder);
      const sortPicks = sortedPicks.map(pick => pick.pick);

      return {
        group: {
          owner: sortedPicks[0].currentOwner,
          picks: sortedPicks.map(pick => ({
            label: `R${pick.pick.Round}`,
            color: pick.roundColor,
            originalOwner: pick.originalOwner,
            isCurrentlyTraded: pick.isCurrentlyTraded
          })),
          pickCount: sortedPicks.length,
          roundCounts: getDraftPickRoundCounts(sortPicks, draftMaxRound)
        },
        sortPicks
      };
    })
    .sort((a, b) => compareOwnerPickGroupSortItemsByPickStrength(a, b, draftMaxRound))
    .map(item => item.group);
}

function compareOwnerPickGroupSortItemsByPickStrength(
  a: { group: CurrentOwnerPickGroupViewModel | CompactOwnerPickGroupViewModel; sortPicks: DraftPick[] },
  b: { group: CurrentOwnerPickGroupViewModel | CompactOwnerPickGroupViewModel; sortPicks: DraftPick[] },
  maxRound: number
): number {
  const strengthDiff = compareDraftPickCollectionsByStrength(a.sortPicks, b.sortPicks, maxRound);
  if (strengthDiff !== 0) return strengthDiff;

  return a.group.owner.name.localeCompare(b.group.owner.name, 'en', { sensitivity: 'base' });
}

function getTeamDisplay(teamByRosterId: Map<number, TeamDisplayViewModel>, rosterId: number | string): TeamDisplayViewModel {
  const normalizedRosterId = normalizeRosterId(rosterId);

  return teamByRosterId.get(normalizedRosterId) ?? {
    id: normalizedRosterId,
    name: `Roster ${normalizedRosterId}`,
    abbr: `R${normalizedRosterId}`,
    avatar: 'assets/default-team-avatar.png'
  };
}

function normalizeRosterId(rosterId: number | string | null | undefined): number {
  const normalized = Number(rosterId);
  return Number.isFinite(normalized) ? normalized : 0;
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
    .map(pick => Number(pick.Round) || 0);

  return Math.max(...rounds, 1);
}
