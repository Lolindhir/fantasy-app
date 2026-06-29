import type { League } from '../../core/models/fantasy.models';
import type { AwardLegendItem } from './league-standings-view.util';

export function buildDetailedAwardLegend(league: League): AwardLegendItem[] {
  const legendByAwardName = new Map<string, AwardLegendItem>();

  for (const standing of league.Standings ?? []) {
    for (const award of standing.Awards ?? []) {
      const key = award.Name;
      const typeText = award.Type?.DisplayText || award.Type?.Name;
      const existing = legendByAwardName.get(key);

      if (existing) {
        existing.occurrences += 1;
        existing.tooltip = buildTooltip(existing.displayText, existing.occurrences, typeText);
        continue;
      }

      legendByAwardName.set(key, {
        key,
        icon: award.Icon || unicodeToEmoji(award.IconUnicode),
        name: award.Name,
        displayText: award.Name,
        tooltip: buildTooltip(award.Name, 1, typeText),
        order: award.Type?.Order ?? 999,
        occurrences: 1
      });
    }
  }

  return [...legendByAwardName.values()]
    .sort((a, b) => a.order - b.order || a.displayText.localeCompare(b.displayText));
}

function buildTooltip(displayText: string, occurrences: number, typeText?: string): string {
  return [displayText, typeText, `Awarded ${occurrences}x`]
    .filter(Boolean)
    .join(' • ');
}

function unicodeToEmoji(unicode: string): string {
  return unicode
    .split(' ')
    .map(code => String.fromCodePoint(parseInt(code, 16)))
    .join('');
}
