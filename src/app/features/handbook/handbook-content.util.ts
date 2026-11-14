/** Render the public explanation directly from the protected single philosophy source. */
export function publicPhilosophyMarkdown(source: string): string {
  const title = source.match(/^# .+$/m)?.[0];
  const start = source.indexOf('\n## Unser Nordstern\n');
  const end = source.indexOf('\n## Verwendung als Bewertungsgrundlage\n');
  // An unexpected source format must not expose administrative metadata.
  if (!title || start < 0 || end <= start) {
    return '# Liga-Philosophie\n\nDie Erklärung ist derzeit nicht verfügbar.';
  }
  return `${title}\n\n${source.slice(start + 1, end).trim()}\n`;
}
