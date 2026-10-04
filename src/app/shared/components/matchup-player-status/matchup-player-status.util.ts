import type { FantasyRelevanceTeamState } from '../../../core/models/decision-window.models';
import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';

export type MatchupPlayerProblemKind = 'out' | 'questionable';

export interface MatchupPlayerStatusPlayerInfo {
  name: string;
  picture: string | null;
  position: string | null;
  nflLogo: string | null;
}

export interface MatchupPlayerStatusLookups {
  teamName(teamID: string | number): string;
  teamAvatar(teamID: string | number): string | null;
  player(playerID: string): MatchupPlayerStatusPlayerInfo;
  decisionTeam(teamID: string | number): FantasyRelevanceTeamState | null;
}

export interface MatchupPlayerStatusPlayerView extends MatchupPlayerStatusPlayerInfo {
  playerID: string;
}

export interface MatchupPlayerStatusProblemView extends MatchupPlayerStatusPlayerView {
  kind: MatchupPlayerProblemKind;
  slot: string | null;
  gameLabel: string | null;
  benchOptionCount: number | null;
}

export interface MatchupPlayerStatusNextWindowView {
  gameLabel: string;
  playerName: string;
  extraPlayerCount: number;
}

export interface MatchupPlayerStatusTeamView {
  teamID: string | number;
  name: string;
  avatar: string | null;
  openCount: number;
  problems: MatchupPlayerStatusProblemView[];
  nextWindow: MatchupPlayerStatusNextWindowView | null;
}

interface StarterEntry {
  playerID: string;
  game: FantasyGameContextGame;
  points: number | null;
}

export function fantasyGameLabel(game: FantasyGameContextGame): string {
  return `${game.AwayTeamAbbr || game.AwayTeamID} @ ${game.HomeTeamAbbr || game.HomeTeamID}`;
}

function isFinalGame(game: FantasyGameContextGame): boolean {
  return /^Final/i.test(game.Status ?? '');
}

function toInfoView(playerID: string, lookups: MatchupPlayerStatusLookups): MatchupPlayerStatusPlayerView {
  return { playerID, ...lookups.player(playerID) };
}

function starterEntries(
  context: FantasyGameContextReadModel,
  teamID: string | number
): Map<string, StarterEntry> {
  const entries = new Map<string, StarterEntry>();
  for (const game of context.Games) {
    const team = game.FantasyTeams.find(candidate => String(candidate.FantasyTeamID) === String(teamID));
    for (const player of team?.Players ?? []) {
      if (!player.IsStarter) continue;
      entries.set(String(player.PlayerID), {
        playerID: String(player.PlayerID),
        game,
        points: player.Points ?? null
      });
    }
  }
  return entries;
}

function problemSlot(
  decisionTeam: FantasyRelevanceTeamState | null,
  playerID: string,
  position: string | null
): { slot: string | null; benchOptionCount: number | null } {
  const state = decisionTeam?.Players.find(candidate => String(candidate.PlayerID) === playerID);
  if (!state) return { slot: null, benchOptionCount: null };

  const natural = (position ?? '').trim().toUpperCase();
  const slotType = state.LineupSlotType?.trim().toUpperCase() ?? '';
  const slotID = state.LineupSlotID;
  const benchOptionCount = slotID
    ? decisionTeam!.Players.filter(
        candidate => candidate.IsBenchCandidate && candidate.EligibleUnlockedSlotIDs.includes(slotID)
      ).length
    : null;

  return {
    slot: slotType && slotType !== natural ? slotType : null,
    benchOptionCount
  };
}

/**
 * Presentation-only grouping of generated facts for the matchup dialog: starters flagged OUT or
 * questionable by MatchupProjections, and a count of the remaining open starters.
 * Availability, scoring and next-window membership all come from generated fields.
 */
export function buildMatchupPlayerStatus(
  matchup: FantasyGameContextMatchup,
  displayTeamIDs: readonly [string | number, string | number],
  context: FantasyGameContextReadModel,
  lookups: MatchupPlayerStatusLookups
): MatchupPlayerStatusTeamView[] {
  const nextGameIDs = new Set(matchup.RemainingRelevance?.NextScoringGameIDs ?? []);

  return displayTeamIDs.map(teamID => {
    const projection = matchup.Projection?.Teams.find(team => String(team.FantasyTeamID) === String(teamID));
    const decisionTeam = lookups.decisionTeam(teamID);
    const starters = starterEntries(context, teamID);

    const sortedStarters = [...starters.values()].sort(
      (left, right) => Date.parse(left.game.StartsAtUtc) - Date.parse(right.game.StartsAtUtc)
        || left.game.GameID.localeCompare(right.game.GameID)
    );
    // Starters from finished NFL games are not listed here; the matchup timeline already shows them.
    const playedIDs = new Set(
      sortedStarters
        .filter(entry => isFinalGame(entry.game) && entry.points !== null && Number.isFinite(entry.points))
        .map(entry => entry.playerID)
    );

    const problems: MatchupPlayerStatusProblemView[] = [];
    const problemIDs = new Set<string>();
    const flagged: Array<[MatchupPlayerProblemKind, string[]]> = [
      ['out', projection?.OutStarterPlayerIDs ?? []],
      ['questionable', projection?.UncertainStarterPlayerIDs ?? []]
    ];
    for (const [kind, playerIDs] of flagged) {
      for (const rawID of playerIDs) {
        const playerID = String(rawID);
        if (playedIDs.has(playerID) || problemIDs.has(playerID)) continue;
        problemIDs.add(playerID);
        const info = toInfoView(playerID, lookups);
        const { slot, benchOptionCount } = problemSlot(decisionTeam, playerID, info.position);
        const game = starters.get(playerID)?.game;
        problems.push({
          ...info,
          kind,
          slot,
          gameLabel: game ? fantasyGameLabel(game) : null,
          benchOptionCount: kind === 'out' ? benchOptionCount : null
        });
      }
    }

    const byeIDs = new Set((projection?.ByeStarterPlayerIDs ?? []).map(String));
    const starterCount = projection?.StarterCount ?? starters.size;
    const finalCount = playedIDs.size;
    const openCount = Math.max(
      0,
      starterCount - finalCount - problemIDs.size
        - [...byeIDs].filter(id => !playedIDs.has(id) && !problemIDs.has(id)).length
    );

    const nextEntries = sortedStarters
      .filter(entry => !playedIDs.has(entry.playerID) && nextGameIDs.has(entry.game.GameID))
      .map(entry => ({ entry, name: lookups.player(entry.playerID).name }))
      .sort((left, right) => left.name.localeCompare(right.name));
    const nextWindow = nextEntries.length > 0
      ? {
          gameLabel: fantasyGameLabel(nextEntries[0].entry.game),
          playerName: nextEntries[0].name,
          extraPlayerCount: nextEntries.length - 1
        }
      : null;

    return {
      teamID,
      name: lookups.teamName(teamID),
      avatar: lookups.teamAvatar(teamID),
      openCount,
      problems,
      nextWindow
    };
  });
}

export function hasMatchupPlayerStatus(teams: readonly MatchupPlayerStatusTeamView[]): boolean {
  return teams.some(team => team.problems.length > 0);
}
