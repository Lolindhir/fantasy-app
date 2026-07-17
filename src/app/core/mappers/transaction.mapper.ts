import type { DraftPick, RawDraft } from '../models/draft.models';
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
  players: Player[],
  drafts: RawDraft[] = []
): Transaction[] {
  const draftPickByIdentity = createDraftPickIndex(drafts);

  return (rawTransactions ?? [])
    .map(raw => mapRawTransactionInternal(raw, teams, players, draftPickByIdentity))
    .sort((a, b) => {
      const createdAtDifference = b.CreatedAt - a.CreatedAt;
      return createdAtDifference !== 0
        ? createdAtDifference
        : b.TransactionID.localeCompare(a.TransactionID);
    });
}

export function mapRawTransaction(
  raw: RawTransaction,
  teams: FantasyTeam[],
  players: Player[],
  drafts: RawDraft[] = []
): Transaction {
  return mapRawTransactionInternal(raw, teams, players, createDraftPickIndex(drafts));
}

function mapRawTransactionInternal(
  raw: RawTransaction,
  teams: FantasyTeam[],
  players: Player[],
  draftPickByIdentity: Map<string, DraftPick>
): Transaction {
  const teamByRosterId = new Map(teams.map(team => [team.TeamID, team]));
  const playerById = new Map(players.map(player => [player.ID, player]));
  const adds = raw.Adds ?? {};
  const drops = raw.Drops ?? {};
  const draftPicks = (raw.DraftPicks ?? []).map(pick => mapDraftPick(
    pick,
    teamByRosterId,
    draftPickByIdentity
  ));
  const rosterIDs = collectRosterIDs(raw, adds, drops, draftPicks);

  return {
    ...raw,
    CreatedAtDate: Number.isFinite(raw.CreatedAt) ? new Date(raw.CreatedAt) : null,
    RosterIDs: rosterIDs,
    Participants: rosterIDs.map(rosterID => mapParticipant(
      rosterID,
      teamByRosterId,
      playerById,
      adds,
      drops,
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
  draftPicks: TransactionDraftPick[]
): TransactionParticipant {
  return {
    RosterID: rosterID,
    Team: teamByRosterId.get(rosterID),
    AddedPlayers: mapPlayerAssets(adds, rosterID, playerById),
    DroppedPlayers: mapPlayerAssets(drops, rosterID, playerById),
    AcquiredDraftPicks: draftPicks.filter(pick => pick.NewOwnerRosterID === rosterID),
    SentDraftPicks: draftPicks.filter(pick => pick.PreviousOwnerRosterID === rosterID)
  };
}

function mapPlayerAssets(
  playerRosterMap: TransactionPlayerRosterMap,
  rosterID: number,
  playerById: Map<string, Player>
): TransactionPlayerAsset[] {
  return Object.entries(playerRosterMap)
    .filter(([, targetRosterID]) => normalizeRosterID(targetRosterID) === rosterID)
    .map(([playerID]) => ({
      PlayerID: playerID,
      Player: playerById.get(playerID)
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
  draftPickByIdentity: Map<string, DraftPick>
): TransactionDraftPick {
  const originalOwnerRosterID = normalizeRosterID(raw.OriginalOwnerRosterID) ?? 0;
  const previousOwnerRosterID = normalizeRosterID(raw.PreviousOwnerRosterID) ?? 0;
  const newOwnerRosterID = normalizeRosterID(raw.NewOwnerRosterID) ?? 0;

  return {
    ...raw,
    OriginalOwnerRosterID: originalOwnerRosterID,
    PreviousOwnerRosterID: previousOwnerRosterID,
    NewOwnerRosterID: newOwnerRosterID,
    OriginalOwner: teamByRosterId.get(originalOwnerRosterID),
    PreviousOwner: teamByRosterId.get(previousOwnerRosterID),
    NewOwner: teamByRosterId.get(newOwnerRosterID),
    ResolvedDraftPick: draftPickByIdentity.get(createDraftPickIdentity(
      raw.DraftKey,
      raw.Round,
      originalOwnerRosterID
    ))
  };
}

function createDraftPickIndex(drafts: RawDraft[]): Map<string, DraftPick> {
  const draftPickByIdentity = new Map<string, DraftPick>();

  for (const draft of drafts ?? []) {
    for (const pick of draft.Picks ?? []) {
      draftPickByIdentity.set(createDraftPickIdentity(
        pick.DraftKey,
        pick.Round,
        pick.OriginalOwnerRosterID
      ), pick);
    }
  }

  return draftPickByIdentity;
}

function createDraftPickIdentity(
  draftKey: string,
  round: number,
  originalOwnerRosterID: number
): string {
  return `${draftKey}_R${round}_OO${originalOwnerRosterID}`;
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
