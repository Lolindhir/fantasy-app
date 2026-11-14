import { publicPhilosophyMarkdown } from './handbook-content.util';

describe('public philosophy excerpt', () => {
  const source = `# Liga-Nordstern – unsere Dynasty-Philosophie

> **Version:** 1.0
> **Status:** internal
> **Abstimmung:** internal

## Unser Nordstern

Gutes Management belohnen.

## Unsere sechs grundlegenden Ziele

### 1. Langfristige Chancengleichheit
### 2. Gutes Management muss belohnt werden
### 3. Keine dauerhaft zementierten Wettbewerbsvorteile
### 4. Sportlicher Erfolg muss wirtschaftliche Konsequenzen haben
### 5. Strategische Freiheit und unterschiedliche Wege zum Erfolg
### 6. Operative Umsetzbarkeit und zuverlässige Durchsetzung

## Auslegung: Einseitige Trades und unterschiedliche Managerkenntnisse

Keine Garantie identischer Ergebnisse.

## Verwendung als Bewertungsgrundlage

Reviewer metadata.

## Schutz, Geltung und Änderungsverfahren

Internal governance.

### Versionshistorie
`;

  it('keeps the six goals and interpretation but hides internal metadata', () => {
    const publicText = publicPhilosophyMarkdown(source);
    expect(publicText).toContain('## Unser Nordstern');
    expect(publicText).toContain('### 1. Langfristige Chancengleichheit');
    expect(publicText).toContain('### 6. Operative Umsetzbarkeit');
    expect(publicText).toContain('## Auslegung: Einseitige Trades');
    for (const privateText of ['**Version:**', '**Status:**', '**Abstimmung:**',
      '## Verwendung als Bewertungsgrundlage', '## Schutz, Geltung', 'Versionshistorie']) {
      expect(publicText).not.toContain(privateText);
    }
  });

  it('fails closed on an unexpected canonical structure', () => {
    expect(publicPhilosophyMarkdown('# Changed\n> **Version:** private'))
      .toBe('# Liga-Philosophie\n\nDie Erklärung ist derzeit nicht verfügbar.');
  });
});
