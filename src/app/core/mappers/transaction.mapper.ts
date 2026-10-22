import type { FantasyTeam } from '../models/league.models';
import type { Player } from '../models/player.models';
import type {
  RawTransaction,
  RawTransactionDraftPick,
  Transaction,
  TransactionDraftPick,
  TransactionParticipant,
  TransactionPlayerAsset,
  TransactionPlayerRosterMap
} from '../models/transaction.models';

export function mapRawTransactions(
  rawTransactions: RawTransaction[],
  teams: FantasyTeam[],
  players: Player[]
): Transaction[] {
  return (rawTransactions ?? [])
    .map(raw => mapRawTransaction(raw, teams, players))
    .sort((a, b) => {
      const effectiveAtDifference = b.EffectiveAt - a.EffectiveAt;
      return effectiveAtDifference !== 0
        ? effectiveAtDifference
        : b.TransactionID.localeCompare(a.TransactionID);
    });
}

export function mapRawTransaction(
  raw: RawTransaction,
  teams: FantasyTeam[],
  players: Player[]
): Transaction {
  const teamByRosterId = new Map(teams.map(team => [team.TeamID, team]));
  const playerById = new Map(players.map(player => [player.ID, player]));
  const adds = raw.Adds ?? {};
  const drops = raw.Drops ?? {};
  const draftPicks = (raw.DraftPicks ?? []).map(pick => mapDraftPick(
    pick,
    teamByRosterId,
    playerById
  ));
  const rosterIDs = collectRosterIDs(raw, adds, drops, draftPicks);
  // Transitional fallback for old published JSON while the canonical source and
  // Shared Derived artifacts are being re-materialized. The generator owns EffectiveAt.
  const effectiveAt = Number.isFinite(raw.EffectiveAt) && (raw.EffectiveAt ?? 0) > 0
    ? raw.EffectiveAt!
    : raw.CreatedAt;

  return {
    ...raw,
    EffectiveAt: effectiveAt,
    CreatedAtDate: Number.isFinite(raw.CreatedAt) ? new Date(raw.CreatedAt) : null,
    EffectiveAtDate: Number.isFinite(effectiveAt) ? new Date(effectiveAt) : null,
    RosterIDs: rosterIDs,
    Participants: rosterIDs.map(rosterID => mapParticipant(
      rosterID,
      teamByRosterId,
      playerById,
      adds,
      drops,
      raw.PlayerRefs,
      draftPicks
    )),
    DraftPicks: draftPicks
  };
}

function mapParticipant(
  rosterID: number,
  teamByRosterId: Map<number, FantasyTeam>,
  playerById: Map<string, Player>,
  adds: TransactionPlayerRosterMap,
  drops: TransactionPlayerRosterMap,
  historicalRefs: RawTransaction['PlayerRefs'],
  draftPicks: TransactionDraftPick[]
): TransactionParticipant {
  return {
    RosterID: rosterID,
    Team: teamByRosterId.get(rosterID),
    AddedPlayers: mapPlayerAssets(adds, rosterID, playerById, historicalRefs),
    DroppedPlayers: mapPlayerAssets(drops, rosterID, playerById, historicalRefs),
    AcquiredDraftPicks: draftPicks.filter(pick => pick.NewOwnerRosterID === rosterID),
    SentDraftPicks: draftPicks.filter(pick => pick.PreviousOwnerRosterID === rosterID)
  };
}

function mapPlayerAssets(
  playerRosterMap: TransactionPlayerRosterMap,
  rosterID: number,
  playerById: Map<string, Player>,
  historicalRefs: RawTransaction['PlayerRefs']
): TransactionPlayerAsset[] {
  return Object.entries(playerRosterMap)
    .filter(([, targetRosterID]) => normalizeRosterID(targetRosterID) === rosterID)
    .map(([playerID]) => ({
      PlayerID: playerID,
      Player: playerById.get(playerID),
      ...(historicalRefs?.[playerID] ? { PlayerRef: historicalRefs[playerID] } : {})
    }))
    .sort((a, b) => {
      const aName = a.Player?.Name ?? a.PlayerID;
      const bName = b.Player?.Name ?? b.PlayerID;
      return aName.localeCompare(bName);
    });
}

function mapDraftPick(
  raw: RawTransactionDraftPick,
  teamByRosterId: Map<number, FantasyTeam>,
  playerById: Map<string, Player>
): TransactionDraftPick {
  const originalOwnerRosterID = normalizeRosterID(raw.OriginalOwnerRosterID) ?? 0;
  const previousOwnerRosterID = normalizeRosterID(raw.PreviousOwnerRosterID) ?? 0;
  const newOwnerRosterID = normalizeRosterID(raw.NewOwnerRosterID) ?? 0;
  const playerID = raw.PlayerID ?? null;

  return {
    ...raw,
    OriginalOwnerRosterID: originalOwnerRosterID,
    PreviousOwnerRosterID: previousOwnerRosterID,
    NewOwnerRosterID: newOwnerRosterID,
    OriginalOwner: teamByRosterId.get(originalOwnerRosterID),
    PreviousOwner: teamByRosterId.get(previousOwnerRosterID),
    NewOwner: teamByRosterId.get(newOwnerRosterID),
    Player: playerID ? playerById.get(playerID) : undefined
  };
}

function collectRosterIDs(
  raw: RawTransaction,
  adds: TransactionPlayerRosterMap,
  drops: TransactionPlayerRosterMap,
  draftPicks: TransactionDraftPick[]
): number[] {
  const orderedRosterIDs = [
    ...(raw.RosterIDs ?? []),
    ...Object.values(adds),
    ...Object.values(drops),
    ...draftPicks.flatMap(pick => [pick.PreviousOwnerRosterID, pick.NewOwnerRosterID])
  ];
  const seen = new Set<number>();

  return orderedRosterIDs.reduce<number[]>((result, rosterID) => {
    const normalizedRosterID = normalizeRosterID(rosterID);

    if (normalizedRosterID !== null && !seen.has(normalizedRosterID)) {
      seen.add(normalizedRosterID);
      result.push(normalizedRosterID);
    }

    return result;
  }, []);
}

function normalizeRosterID(value: number | string): number | null {
  const rosterID = Number(value);
  return Number.isFinite(rosterID) ? rosterID : null;
}
