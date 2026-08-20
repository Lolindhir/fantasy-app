# Entscheidung: Race-sichere Veröffentlichung generierter Source-Commits

Datum: 2026-08-20  
Status: angenommen

## Kontext

Mehrere schreibende GitHub-Actions-Workflows aktualisieren `main` in engem zeitlichem Abstand. GitHub startet geplante Runs nicht sekundengenau; dadurch können eigentlich versetzt geplante Source-Refreshes parallel laufen. Zusätzlich können andere Daten- oder Materialisierungsworkflows `main` während eines laufenden Refreshes fortschreiben.

Der FFToday-Lauf `FM • Projection • FFToday #37` hat den Fehler konkret sichtbar gemacht: Fetch, Validierung, Snapshot-Erzeugung, Heartbeat und lokaler Commit waren erfolgreich. Der abschließende direkte Push nach `main` wurde jedoch als Non-Fast-Forward abgelehnt, weil `main` zwischen Checkout und Push durch FFC und die anschließende Fantasy-Operations-Materialisierung weitergelaufen war. Der erfolgreiche manuelle FFToday-Lauf am selben Tag bestätigte, dass Source und Parser gesund waren und ausschließlich die Publication-Race-Semantik fehlte.

## Entscheidung

Race-sichere Veröffentlichung wird als wiederverwendbare technische Repository-Funktion unter `tools/publish_generated_commit.py` implementiert.

Für Source-Refreshes, deren bereits validierter Output als genau ein selbstständiger Generated-Data-Commit vorliegt, gilt:

1. Der Writer erzeugt seinen fachlich vollständigen lokalen Commit wie bisher.
2. Vor der Veröffentlichung wird der aktuelle Zielbranch neu gefetcht.
3. Es darf genau ein lokaler, noch nicht veröffentlichter Commit existieren; mehrere lokale Commits werden fail-closed abgelehnt.
4. Ist `main` durch disjunkte Änderungen fortgeschritten, wird dieser eine Commit auf den aktuellen Zielstand rebased.
5. Danach wird ohne Force-Push veröffentlicht.
6. Nur erkannte Branch-/Ref-Races werden mit begrenztem Backoff erneut versucht; Standard sind fünf Versuche.
7. Ein echter Rebase-Konflikt, ein Dirty Worktree, fehlende gemeinsame Historie, Auth-/Permission-Probleme oder andere Git-Fehler bleiben harte Fehler und werden nicht automatisch übergangen.

Der erste Rollout umfasst die sechs schreibenden Fantasy-Management-Source-Workflows für FantasyPros, FantasyCalc, Fantasy Football Calculator, FFToday, CBS Sports und Sleeper Trending.

## Abgrenzung zu Derived Materialization

Ein bereits validierter Source-Snapshot bleibt nach einem disjunkten Commit auf `main` fachlich gültig und kann deshalb rebased werden.

Derived Materializations können dagegen durch einen zwischenzeitlich veröffentlichten Input bereits fachlich veraltet sein. Solche Writer müssen bei einem verlorenen Push gegen den aktuellen `main` **neu berechnen**, nicht lediglich den alten Derived-Commit rebasen. `FM • Materialize • Operations Inputs` behält deshalb seinen bestehenden Reset-/Rebuild-Retry.

Die gemeinsame Plattformregel lautet damit:

- **self-contained source/generated snapshot:** rebase-and-retry;
- **derived output abhängig vom aktuellen Repository-Inputstand:** rebuild-and-retry;
- **echter Inhaltskonflikt:** fail-closed;
- **niemals Force-Push zur automatischen Konfliktauflösung.**

## Cross-Context-Grenze

`tools/publish_generated_commit.py` ist absichtlich repo-weit wiederverwendbar abgelegt. Diese Entscheidung autorisiert jedoch nicht automatisch Änderungen an App-Produzenten wie Players oder League. Gemäß der bestehenden Cross-Context-Grenze werden diese Workflows erst nach eigener Prüfung und expliziter Freigabe auf einen gemeinsamen Publication-Mechanismus umgestellt.

## Folgen

Positiv:

- parallele, disjunkte Source-Refreshes verlieren ihre erfolgreichen Daten nicht mehr nur deshalb, weil `main` während des Runs weiterläuft;
- die Race-Behandlung liegt zentral statt in mehreren YAML-Kopien;
- echte Konflikte und fehlerhafte Repository-Zustände bleiben sichtbar;
- die technische Lösung ist später auch für weitere Writer wiederverwendbar.

Negativ:

- Source-Commits können beim Rebase eine neue Commit-SHA erhalten;
- bei echtem Pfadkonflikt ist weiterhin menschliche bzw. fachliche Auflösung nötig;
- App-Writer sind mit diesem ersten Rollout noch nicht automatisch abgesichert.
