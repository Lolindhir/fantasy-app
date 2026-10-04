import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../core/models/fantasy-game-context.models';
import type {
  DecisionWindowsReadModel,
  FantasyRelevanceSlotState,
  FantasyRelevanceTeamState
} from '../../core/models/decision-window.models';
import type { MatchupCompletionState } from '../../core/models/matchup.models';

export type MatchupProgressSide = 'left' | 'right';
export type MatchupProgressKind =
  | 'irreparable'
  | 'final'
  | 'locked'
  | 'next'
  | 'future'
  | 'repairable'
  | 'questionable'
  | 'unknown';
export type MatchupProgressOutline = 'next' | 'repairable' | 'questionable' | 'unknown' | null;
export type MatchupScoringWindowDensity = 'rich' | 'compact' | 'dense';
export type MatchupScoreboardState = 'neutral' | 'active' | 'final' | 'unknown';

export interface MatchupProgressSegmentView {
  slotID: string;
  slotType: string;
  kind: MatchupProgressKind;
  ariaLabel: string;
}

export interface MatchupProgressGroupView {
  kind: MatchupProgressKind;
  outline: MatchupProgressOutline;
  segments: MatchupProgressSegmentView[];
  ariaLabel: string;
}

export interface MatchupStarterProgressView {
  side: MatchupProgressSide;
  slotCount: number;
  showFinalMarker: boolean;
  groups: MatchupProgressGroupView[];
}

export interface MatchupScoringWindowHorizonView {
  decisionWindowID: string;
  startsAtUtc: string;
  gameCount: number;
  games: FantasyGameContextGame[];
  mobileVisibleGames: FantasyGameContextGame[];
  mobileOverflowCount: number;
  density: MatchupScoringWindowDensity;
}

export interface MatchupScoringWindowView extends MatchupScoringWindowHorizonView {
  active: MatchupScoringWindowHorizonView | null;
  next: MatchupScoringWindowHorizonView | null;
  liveIsFinalScoringWindow: boolean;
  isLive: boolean;
}

// Within one time phase: red (problems), yellow (questionable), blue (live/next), green (final), then neutral/unknown.
const kindOrder: Record<MatchupProgressKind, number> = {
  irreparable: 0,
  repairable: 1,
  questionable: 2,
  locked: 3,
  next: 4,
  final: 5,
  future: 6,
  unknown: 7
};

// Time phase, outer edge first: started starters (locked or final), then next-window starters, then still-open ones.
function timePhase(
  slot: FantasyRelevanceSlotState,
  nextScoringWindowID: string | null | undefined
): number {
  if (slot.State === 'completed' || slot.State === 'locked-active') return 0;
  if (slot.State === 'unlocked' && nextScoringWindowID && slot.DecisionWindowID === nextScoringWindowID) return 1;
  return 2;
}

const kindLabel: Record<MatchupProgressKind, string> = {
  irreparable: 'irreparable starter problem',
  final: 'final starter',
  locked: 'locked active starter',
  next: 'starter in the next scoring window',
  future: 'later unlocked starter',
  repairable: 'repairable starter problem',
  questionable: 'questionable starter',
  unknown: 'starter state requiring review'
};

export function findFantasyRelevanceTeam(
  readModel: DecisionWindowsReadModel | null | undefined,
  fantasyTeamID: string | number
): FantasyRelevanceTeamState | null {
  return readModel?.FantasyRelevance?.Teams.find(team =>
    String(team.FantasyTeamID) === String(fantasyTeamID)
  ) ?? null;
}

export function buildMatchupScoreboardState(
  completionState: MatchupCompletionState,
  teams: ReadonlyArray<FantasyRelevanceTeamState | null | undefined>
): MatchupScoreboardState {
  if (completionState === 'final') return 'final';
  if (completionState === 'unknown') return 'unknown';

  const scoringHasStarted = teams.some(team => team?.Slots?.some(slot =>
    slot.State === 'locked-active' || slot.State === 'completed'
  ));

  return scoringHasStarted ? 'active' : 'neutral';
}

export function buildMatchupStarterProgress(
  team: FantasyRelevanceTeamState | null | undefined,
  nextScoringWindowID: string | null | undefined,
  side: MatchupProgressSide
): MatchupStarterProgressView | null {
  if (!team?.Slots?.length) return null;

  const sorted = team.Slots
    .map(slot => ({ segment: toSegment(slot, nextScoringWindowID), phase: timePhase(slot, nextScoringWindowID) }))
    .sort((left, right) => left.phase - right.phase
      || kindOrder[left.segment.kind] - kindOrder[right.segment.kind]
      || slotIndex(team.Slots, left.segment.slotID) - slotIndex(team.Slots, right.segment.slotID))
    .map(item => item.segment);

  const groups: MatchupProgressGroupView[] = [];
  for (const segment of sorted) {
    const current = groups[groups.length - 1];
    if (current?.kind === segment.kind) {
      current.segments.push(segment);
      current.ariaLabel = groupAriaLabel(current.kind, current.segments.length);
      continue;
    }

    groups.push({
      kind: segment.kind,
      outline: outlineFor(segment.kind),
      segments: [segment],
      ariaLabel: groupAriaLabel(segment.kind, 1)
    });
  }

  return {
    side,
    slotCount: team.Slots.length,
    showFinalMarker: team.RemainingScoringPathState === 'none',
    groups: side === 'right' ? [...groups].reverse() : groups
  };
}

export function buildMatchupScoringWindow(
  matchup: FantasyGameContextMatchup | null | undefined,
  context: FantasyGameContextReadModel | null | undefined
): MatchupScoringWindowView | null {
  const remaining = matchup?.RemainingRelevance;
  if (!matchup || !context || !remaining) return null;

  if (context.SchemaVersion >= 5) {
    const active = buildGeneratedScoringWindow(
      matchup,
      context,
      remaining.ActiveScoringWindowID,
      remaining.ActiveScoringGameIDs
    );
    const next = buildGeneratedScoringWindow(
      matchup,
      context,
      remaining.NextScoringWindowID,
      remaining.NextScoringGameIDs
    );

    return combineScoringHorizons(active, next, !!active && !next);
  }

  // Schema-v4 compatibility: NextScoringWindow could itself be the live window.
  // Render that known horizon, but do not claim FINAL SCORING WINDOW because older
  // data cannot prove that no future direct-Starter window exists.
  const legacy = buildGeneratedScoringWindow(
    matchup,
    context,
    remaining.NextScoringWindowID,
    remaining.NextScoringGameIDs
  );
  if (!legacy) return null;

  const legacyIsLive = (remaining.NextScoringLockedActiveStarterCount ?? 0) > 0
    || legacy.games.some(game => !/^Final/i.test(game.Status ?? '')
      && (game.RemainingRelevance?.LockedActiveStarterCount ?? 0) > 0);

  return combineScoringHorizons(
    legacyIsLive ? legacy : null,
    legacyIsLive ? null : legacy,
    false
  );
}

function combineScoringHorizons(
  active: MatchupScoringWindowHorizonView | null,
  next: MatchupScoringWindowHorizonView | null,
  liveIsFinalScoringWindow: boolean
): MatchupScoringWindowView | null {
  const primary = next ?? active;
  if (!primary) return null;

  return {
    ...primary,
    active,
    next,
    liveIsFinalScoringWindow,
    isLive: !!active
  };
}

function buildGeneratedScoringWindow(
  matchup: FantasyGameContextMatchup,
  context: FantasyGameContextReadModel,
  decisionWindowID: string | null | undefined,
  generatedGameIDs: string[] | string | null | undefined
): MatchupScoringWindowHorizonView | null {
  if (!decisionWindowID) return null;

  const gameIDs = normalizeIDs(generatedGameIDs);
  if (gameIDs.length === 0) return null;

  const gameByID = new Map(context.Games.map(game => [game.GameID, game]));
  const games = gameIDs
    .map(gameID => gameByID.get(gameID) ?? null)
    .filter((game): game is FantasyGameContextGame => !!game);
  if (games.length === 0) return null;

  const startsAtUtc = games[0].StartsAtUtc
    || matchup.Games.find(game => game.DecisionWindowID === decisionWindowID)?.StartsAtUtc;
  if (!startsAtUtc) return null;

  const density: MatchupScoringWindowDensity = gameIDs.length === 1
    ? 'rich'
    : gameIDs.length <= 4
      ? 'compact'
      : 'dense';

  // #507: the complete generated game count is the breadth signal. Overview only
  // previews the first three already ordered identities; Matchup Detail is drilldown.
  const mobileVisibleGames = games.slice(0, 3);

  return {
    decisionWindowID,
    startsAtUtc,
    gameCount: gameIDs.length,
    games,
    mobileVisibleGames,
    mobileOverflowCount: Math.max(0, gameIDs.length - mobileVisibleGames.length),
    density
  };
}

function toSegment(
  slot: FantasyRelevanceSlotState,
  nextScoringWindowID: string | null | undefined
): MatchupProgressSegmentView {
  const kind = classifySlot(slot, nextScoringWindowID);
  return {
    slotID: slot.SlotID,
    slotType: slot.SlotType,
    kind,
    ariaLabel: `${slot.SlotType}: ${kindLabel[kind]}`
  };
}

function classifySlot(
  slot: FantasyRelevanceSlotState,
  nextScoringWindowID: string | null | undefined
): MatchupProgressKind {
  if (slot.Repairability?.State === 'irreparable') return 'irreparable';
  if (slot.State === 'completed') return 'final';
  if (slot.State === 'locked-active') return 'locked';
  if (slot.Repairability?.State === 'repairable') return 'repairable';
  if (slot.Repairability?.State === 'unknown' || slot.State === 'unknown') return 'unknown';
  // Known status: ESPN lists the starter as questionable. Distinct from the unknown-state review marker.
  if (slot.ScoringAvailability?.State === 'uncertain') return 'questionable';
  if (slot.State === 'unlocked' && nextScoringWindowID && slot.DecisionWindowID === nextScoringWindowID) {
    return 'next';
  }
  return 'future';
}

function outlineFor(kind: MatchupProgressKind): MatchupProgressOutline {
  if (kind === 'next') return 'next';
  if (kind === 'repairable') return 'repairable';
  if (kind === 'questionable') return 'questionable';
  if (kind === 'unknown') return 'unknown';
  return null;
}

function groupAriaLabel(kind: MatchupProgressKind, count: number): string {
  return `${count} ${kindLabel[kind]}${count === 1 ? '' : 's'}`;
}

function slotIndex(slots: FantasyRelevanceSlotState[], slotID: string): number {
  return slots.find(slot => slot.SlotID === slotID)?.SlotIndex ?? Number.MAX_SAFE_INTEGER;
}

function normalizeIDs(value: string[] | string | null | undefined): string[] {
  if (Array.isArray(value)) return value;
  return typeof value === 'string' && value.length > 0 ? [value] : [];
}
