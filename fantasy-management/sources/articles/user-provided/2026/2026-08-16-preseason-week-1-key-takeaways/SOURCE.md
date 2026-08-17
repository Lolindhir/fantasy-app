# Source Metadata — Preseason Week 1 Key Takeaways

- **Package ID:** `user-provided-2026-08-16-preseason-week-1-key-takeaways`
- **Source kind:** `article`
- **Origin:** `user-provided`
- **Title:** `Key takeaways and fantasy football analysis from Week 1 of NFL preseason`
- **Publisher:** unknown
- **Author:** unknown
- **Publication date:** unknown
- **Original URL:** unknown
- **Input method:** `user_provided_chat`
- **First captured for repository:** 2026-08-16
- **Capture timezone:** `Europe/London`
- **Source mode:** `living_article`
- **Latest snapshot:** `snapshots/2026-08-17T01-10+01-00-full/`

## Capture-Historie

### 1. Erst-/Legacy-Capture — 2026-08-16

Die Root-Dateien `raw.txt`, `article.md` und `extraction.json` dokumentieren den ersten Persistierungsvorgang.

Beim damaligen Write war der exakte ursprüngliche Chat-Paste nach Kontextkompaktierung nicht mehr wortgetreu verfügbar. Deshalb wurde bewusst **kein rekonstruiertes Raw als Original ausgegeben**:

- Root-`raw.txt`: `unavailable_exact_after_context_compaction`;
- Root-`article.md`: sichtbar gekennzeichneter rekonstruierter Source Digest;
- Root-`extraction.json`: strukturierte historische Claims aus der damals sicher erhaltenen Analyse.

Diese Dateien bleiben als historischer erster Snapshot bestehen und werden nicht nachträglich so umgeschrieben, als wäre der Originaltext damals vorhanden gewesen.

### 2. Vollständiger fortgeschriebener Capture — 2026-08-17 01:10 Europe/London

Der Nutzer stellte den Artikel erneut vollständig bereit. Die neue Fassung enthält den bereits bekannten Donnerstag-/Freitag-Block und zusätzlich den Samstag-Block.

Gespeichert unter:

`snapshots/2026-08-17T01-10+01-00-full/`

- `raw.txt`: vollständiger, direkt vom Nutzer bereitgestellter Artikeltext;
- `article.md`: lesefreundliche vollständige Fassung ohne Fantasy-Interpretation im Quelltext;
- `extraction.json`: Claim-basierter Delta-Snapshot mit stabilen Claim-IDs und `new`/`repeated`-Status.

## Living-Article-Identität

Diese Fassung wird als **Fortschreibung desselben Artikels** behandelt, nicht als zweite unabhängige Quelle. Grundlage dafür sind identischer Titel, wiederholte ältere Abschnitte und die erkennbare Erweiterung um den Samstag-Block.

Folge:

- wiederholte Donnerstag-/Freitag-Claims erhöhen weder Source Count noch Confidence wie eine zweite unabhängige Bestätigung;
- neue Samstag-Claims sind neue Evidenz **innerhalb derselben Source Identity**;
- spätere materielle Änderungen werden als `changed` oder `retracted` in einem weiteren Snapshot erhalten, nicht durch Überschreiben älterer Captures.

## Materialität

Das Paket überschreitet die Persistenzschwelle klar.

Aus dem ersten Capture entstanden bereits:

1. dauerhaftes `player-role-watch` für **Keaton Mitchell**;
2. dauerhaftes `player-role-watch` für **Braelon Allen**;
3. zusätzliche Bestätigung für **Caleb Douglas**;
4. zusätzliche Opportunity-Evidenz für **De'Zhaun Stribling**;
5. die kanonische **Preseason-Usage-Signal-Klassifizierung**.

Der vollständige Snapshot vom 17.08. ergänzt materiell:

1. **Cam Skattebo**: bestätigte Rückkehr zu echter Preseason-Spielbelastung nach schwerer Bein-/Knöchelverletzung;
2. **Jonathon Brooks**: bestätigte Rückkehr zu Game Action sowie kurzfristiger, ausdrücklich `injury_opened` Opportunity-Pfad durch Chuba Hubbards Hamstring-Verletzung;
3. **Brashard Smith**: relevantes KC-RB2-Sequencing-Signal für einen späteren Recheck, aber noch kein dauerhaftes Watch-Target;
4. wiederverwendbare **Living-Article-Regeln** für versionierte Snapshots und Claim-Deltas.

## Bekannte dauerhafte Ableitungen

- `fantasy-management/automation/target-sets/player-role-watch.json`
  - `keaton-mitchell-2026`
  - `braelon-allen-2026`
- `fantasy-management/automation/state/entity-observation.json`
  - `managed-roster-player-12481` / `injury-status` — Cam Skattebo
  - `jonathon-brooks-2026` / `injury-status`
  - `jonathon-brooks-2026` / `role-opportunity`
- `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`
  - Abschnitt `Preseason-Usage-Signal-Klassifizierung`
- `fantasy-management/_ai/ARTICLE_SOURCE_MODEL.md`
  - Abschnitt `Living Articles und fortgeschriebene Quellen`
- bereits vorhandenes Watch-Target:
  - `caleb-douglas-2026`

## Quellenstatus

Dieses Paket ist historische Source-Evidenz. Rollen, Verletzungen, Ownership, Marktwerte, ADP und NFL-Teamkontext müssen bei späterer Verwendung erneut gegen aktuelle Repo-Daten und frische externe Quellen geprüft werden.
