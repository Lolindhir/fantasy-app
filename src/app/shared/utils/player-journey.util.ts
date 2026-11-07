import type { RawDraft } from '../../core/models/draft.models';
import type { FantasyTeam } from '../../core/models/league.models';
import type { Transaction } from '../../core/models/transaction.models';

export type PlayerJourneyEventKind = 'drafted' | 'traded' | 'added' | 'dropped';

export interface PlayerJourneyEvent {
  kind: PlayerJourneyEventKind;
  /** Sort key: EffectiveAt (ADR-066) for moves, draft start (or the season start) for drafts. */
  at: number;
  /** True when the date is only the season start because the draft date is not published. */
  dateApproximate: boolean;
  season: string;
  /** Drafted: "1.03" style pick plus draft name; moves: provider acquisition path. */
  detail: string;
  /** Team the player joined (drafted, added, traded to) or left (dropped). */
  team: FantasyTeam | null;
  rosterID: number | null;
  /** Traded only: team the player came from. */
  fromTeam: FantasyTeam | null;
  fromRosterID: number | null;
  transactionID: string | null;
}

export interface PlayerJourney {
  /** Newest first. */
  events: PlayerJourneyEvent[];
  /** Fantasy teams the player was on, most recent first. Rosters without a resolvable team are skipped. */
  teams: FantasyTeam[];
}

const ACQUISITION_LABELS: Record<string, string> = {
  waiver: 'Waiver claim',
  free_agent: 'Free agent',
  commissioner: 'Commissioner'
};

export function acquisitionLabel(type: string): string {
  return ACQUISITION_LABELS[type] ?? type.replace(/_/g, ' ');
}

function rosterIdOf(value: number | string | undefined): number | null {
  if (value === undefined || value === null) return null;
  const id = Number(value);
  return Number.isFinite(id) ? id : null;
}

/**
 * Chains the existing draft and transaction records of one player into a timeline. It does not
 * evaluate anything (no trade grades); it only orders what happened. Waiver claims carry no bid.
 * Only completed transactions are expected (the mapped read model never contains pending ones).
 */
export function buildPlayerJourney(
  playerID: string,
  transactions: readonly Transaction[],
  drafts: readonly RawDraft[],
  teams: readonly FantasyTeam[]
): PlayerJourney {
  const id = String(playerID);
  const teamByRoster = new Map(teams.map(team => [team.TeamID, team]));
  const teamOf = (rosterID: number | null): FantasyTeam | null =>
    rosterID === null ? null : teamByRoster.get(rosterID) ?? null;
  const events: PlayerJourneyEvent[] = [];
  const seenDraftPicks = new Set<string>();

  for (const draft of drafts ?? []) {
    for (const pick of draft.Picks ?? []) {
      if (pick.PlayerID === null || pick.PlayerID === undefined || String(pick.PlayerID) !== id) continue;
      if (seenDraftPicks.has(pick.PickKey)) continue;
      seenDraftPicks.add(pick.PickKey);
      const start = Number(draft.SleeperStartTime);
      const exact = Number.isFinite(start) && start > 0;
      const rosterID = rosterIdOf(pick.CurrentOwnerRosterID);
      const pickLabel = pick.DisplayPick ? `Pick ${pick.DisplayPick}` : `Round ${pick.Round}`;
      events.push({
        kind: 'drafted',
        at: exact ? start : Date.UTC(Number(draft.Season), 0, 1),
        dateApproximate: !exact,
        season: String(draft.Season),
        detail: `${pickLabel} · ${draft.DisplayDraftKey || draft.DraftKey}`,
        team: teamOf(rosterID),
        rosterID,
        fromTeam: null,
        fromRosterID: null,
        transactionID: null
      });
    }
  }

  for (const transaction of transactions ?? []) {
    const toParticipant = transaction.Participants.find(p => p.AddedPlayers.some(a => a.PlayerID === id));
    const fromParticipant = transaction.Participants.find(p => p.DroppedPlayers.some(a => a.PlayerID === id));
    const added = !!toParticipant;
    const dropped = !!fromParticipant;
    if (!added && !dropped) continue;
    const toRoster = toParticipant ? rosterIdOf(toParticipant.RosterID) : null;
    const fromRoster = fromParticipant ? rosterIdOf(fromParticipant.RosterID) : null;
    const base = {
      at: transaction.EffectiveAt,
      dateApproximate: false,
      season: String(transaction.Season),
      transactionID: transaction.TransactionID
    };

    if (transaction.Type === 'trade' && added && dropped) {
      events.push({
        ...base,
        kind: 'traded',
        detail: 'Trade',
        team: teamOf(toRoster),
        rosterID: toRoster,
        fromTeam: teamOf(fromRoster),
        fromRosterID: fromRoster
      });
      continue;
    }

    if (added) {
      events.push({
        ...base,
        kind: 'added',
        detail: acquisitionLabel(transaction.Type),
        team: teamOf(toRoster),
        rosterID: toRoster,
        fromTeam: null,
        fromRosterID: null
      });
    }
    if (dropped) {
      events.push({
        ...base,
        kind: 'dropped',
        detail: acquisitionLabel(transaction.Type),
        team: teamOf(fromRoster),
        rosterID: fromRoster,
        fromTeam: null,
        fromRosterID: null
      });
    }
  }

  events.sort((a, b) => b.at - a.at || kindOrder(b.kind) - kindOrder(a.kind));

  // Events are newest first, so first appearance of a team is its most recent stay. A player who
  // was dropped is no longer on that team, but the team is still part of the journey.
  const seenTeams = new Set<number>();
  const journeyTeams: FantasyTeam[] = [];
  for (const event of events) {
    for (const team of [event.team, event.fromTeam]) {
      if (team && !seenTeams.has(team.TeamID)) {
        seenTeams.add(team.TeamID);
        journeyTeams.push(team);
      }
    }
  }

  return { events, teams: journeyTeams };
}

/** Tie-break for equal timestamps in newest-first order: a draft is the earliest, a drop the latest. */
function kindOrder(kind: PlayerJourneyEventKind): number {
  switch (kind) {
    case 'drafted': return 0;
    case 'added': return 1;
    case 'traded': return 2;
    case 'dropped': return 3;
  }
}
