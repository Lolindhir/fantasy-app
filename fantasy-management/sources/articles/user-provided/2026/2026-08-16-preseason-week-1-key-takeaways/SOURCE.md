# Source Metadata — Preseason Week 1 Key Takeaways

- **Package ID:** `user-provided-2026-08-16-preseason-week-1-key-takeaways`
- **Source kind:** `article`
- **Origin:** `theScore`
- **Title:** `Fantasy notes, analysis from Week 1 of NFL preseason`
- **Publisher:** `theScore`
- **Authors:** `Eric Patterson`, `Caio Miari`
- **Author-credit note:** the currently indexed full living-article version credits Eric Patterson and Caio Miari; an alternate/current endpoint has also appeared with Eric Patterson alone, so author credit is treated as version-sensitive metadata rather than a claim-independence signal.
- **Publication date:** unknown
- **Original URL:** `https://www.thescore.com/nfl/news/3572139/fantasy-notes-analysis-from-week-1-of-nfl-preseason`
- **Input method:** `user_provided_chat`
- **First captured for repository:** 2026-08-16
- **Capture timezone:** `Europe/London`
- **Source mode:** `living_article`
- **Latest snapshot:** `snapshots/2026-08-17T01-10+01-00-full/`
- **Registry source ID:** `thescore`

## Provenienz-Korrektur — 2026-08-22

Die Quelle konnte nachträglich belastbar als theScore-Artikel mit der oben genannten URL und dem Seitentitel `Fantasy notes, analysis from Week 1 of NFL preseason` identifiziert werden. Die vollständige fortgeschriebene Artikelversion wird aktuell Eric Patterson und Caio Miari zugeschrieben. Eine andere aktuell indexierte Endpoint-Fassung zeigt nur Eric Patterson; deshalb wird die Abweichung transparent dokumentiert und nicht als zweite unabhängige Quelle interpretiert.

Der bestehende Package-Pfad unter `articles/user-provided/...` bleibt als historischer Legacy-Pfad erhalten. Er dokumentiert korrekt, dass der Inhalt ursprünglich per Chat bereitgestellt und die Publisher-Identität beim ersten Persistierungsvorgang noch nicht sicher bekannt war. Raw-Captures und historische `extraction.json`-Metadaten werden nicht nachträglich umgeschrieben, nur um heute bekannte Provenienz so erscheinen zu lassen, als sei sie bereits beim Capture verifiziert gewesen. `SOURCE.md` ist für die nachträglich bestätigte Source Identity maßgeblich.

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

Diese Fassung wird als **Fortschreibung desselben Artikels** behandelt, nicht als zweite unabhängige Quelle. Grundlage dafür sind identischer Titel, dieselbe theScore-Artikel-ID/URL, wiederholte ältere Abschnitte und die erkennbare Erweiterung um den Samstag-Block.

Folge:

- wiederholte Donnerstag-/Freitag-Claims erhöhen weder Source Count noch Confidence wie eine zweite unabhängige Bestätigung;
- neue Samstag-Claims sind neue Evidenz **innerhalb derselben Source Identity**;
- spätere materielle Änderungen werden als `changed` oder `retracted` in einem weiteren Snapshot erhalten, nicht durch Überschreiben älterer Captures;
- wechselnde oder ergänzte Autoren-Credits innerhalb derselben Living-Article-Identität erzeugen keine zusätzliche unabhängige Quelle.

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
- `fantasy-management/_ai/source-registry.json`
  - `thescore`
- bereits vorhandenes Watch-Target:
  - `caleb-douglas-2026`

## Quellenstatus

Dieses Paket ist historische Source-Evidenz. Rollen, Verletzungen, Ownership, Marktwerte, ADP und NFL-Teamkontext müssen bei späterer Verwendung erneut gegen aktuelle Repo-Daten und frische externe Quellen geprüft werden.
