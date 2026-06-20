import type { Player, TopPlayersSalaryResult } from '../../core/models/player.models';

export function calculateTopPlayersSalary(
  roster: Player[],
  topN: number,
  salarySelector: (player: Player) => number
): TopPlayersSalaryResult {
  if (!roster || roster.length === 0) {
    return { cap: 0, topPlayers: [] };
  }

  const sortedRoster = [...roster]
    .sort((a, b) => salarySelector(b) - salarySelector(a));

  const actualTopN = Math.min(topN, sortedRoster.length);
  const topPlayers = sortedRoster.slice(0, actualTopN);
  const cap = topPlayers.reduce((sum, player) => sum + salarySelector(player), 0);

  return { cap, topPlayers };
}

export function getRosterAfterTrade(
  currentRoster: Player[],
  outgoing: Player[],
  incoming: Player[]
): Player[] {
  let newRoster = [...currentRoster];

  outgoing.forEach(player => {
    newRoster = newRoster.filter(existing => existing.ID !== player.ID);
  });

  incoming.forEach(player => newRoster.push(player));
  return newRoster;
}
