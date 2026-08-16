# Article Source Model

## Zweck

Diese Datei definiert den kanonischen Umgang mit einzelnen Artikeln, News-Analysen, Preseason-/Camp-Übersichten und vergleichbaren textbasierten externen Quellen, die der Nutzer direkt in den Chat einfügt oder ausdrücklich zur Auswertung übergibt.

Artikel sind **Quellenmaterial**. Sie sind weder aktuelle Liga-Wahrheit noch automatisch Fantasy-Knowledge oder eine Handlungsempfehlung.

Das Grundmodell lautet:

```text
Source Snapshot = was die Quelle zu einem bestimmten Zeitpunkt gesagt hat.
Extraction = welche strukturierten Claims/Signale daraus entnommen wurden.
Knowledge/Monitoring/Analysis = was davon nach Abgleich mit Liga, Rollen, Markt und weiteren Quellen relevant bleibt.
Decision = was Robert tatsächlich tun sollte.
```

## Speicherort

Persistierte Artikelpakete liegen unter:

```text
fantasy-management/sources/articles/<publisher-or-origin>/<year>/<date>-<slug>/
```

Wenn Publisher oder Originalquelle unbekannt sind, verwende `user-provided` als Origin-Verzeichnis. Eine unbekannte Quelle darf nicht erfunden oder nachträglich ohne belastbare Identifikation einem Publisher zugeschrieben werden.

## Standardpaket

Ein vollständiges Artikelpaket besteht aus:

```text
SOURCE.md
raw.txt
article.md
extraction.json
```

### `SOURCE.md`

Enthält Provenienz und Capture-Status, mindestens soweit bekannt:

- Package-ID;
- Quelltyp `article`;
- Titel;
- Publisher;
- Autor;
- Veröffentlichungsdatum;
- Original-URL;
- Input-Methode (`user_provided_chat`, `user_uploaded_file`, `url_researched`, ...);
- Capture-Zeitpunkt;
- Raw-Capture-Status;
- Materialitätsbegründung;
- bekannte dauerhafte Ableitungen aus der Quelle.

Unbekannte Felder bleiben ausdrücklich `unknown`; sie werden nicht geraten.

### `raw.txt`

`raw.txt` ist ein **Fidelity-Artefakt**, kein Analyseartefakt.

Wenn der Nutzer den Artikeltext direkt bereitstellt, speichere exakt diesen bereitgestellten Text, ohne sprachliche Korrektur, Umordnung, Kürzung oder Ergänzung. Zeilenumbrüche dürfen nur dann technisch normalisiert werden, wenn der Wortlaut unverändert bleibt.

Wenn der exakte Nutzer-Input nicht mehr zuverlässig verfügbar ist:

- rekonstruiere ihn **nicht** aus Erinnerungen, Zusammenfassungen oder Web-Suchen;
- schreibe keinen rekonstruierten Text als `raw.txt` aus;
- halte stattdessen den Raw-Capture-Status im Paket explizit als unvollständig fest;
- eine spätere erneute Bereitstellung darf das fehlende Raw-Artefakt vervollständigen.

Für URL-only-Quellen gilt: Archiviere nicht automatisch den vollständigen urheberrechtlich geschützten Webseitentext. Speichere Provenienz, zulässige kurze Belege und strukturierte Extraktion. Ein vollständiges `raw.txt` ist nur vorgesehen, wenn der Inhalt vom Nutzer direkt bereitgestellt wurde oder anderweitig rechtmäßig als vollständiger Source Snapshot vorliegt.

### `article.md`

`article.md` ist die lesefreundliche Fassung.

Wenn ein vollständiges Raw vorliegt:

- Inhalt und Aussagen müssen erhalten bleiben;
- erlaubt sind Überschriften, Absätze, Listen, Tabellen, typografische Bereinigung und ein Metadatenkopf;
- keine stillen Faktenkorrekturen;
- keine Fantasy-Interpretation in den Quelltext mischen.

Wenn kein vollständiges Raw vorliegt, darf `article.md` nur als **Rekonstruktion oder strukturierter Source Digest** erstellt werden. Das muss oben sichtbar gekennzeichnet sein. Eine Rekonstruktion ist niemals Ersatz oder Beweis für den ursprünglichen Wortlaut.

### `extraction.json`

Enthält strukturierte, wiederverwendbare Claims und Signale aus dem Artikel. Die Extraktion soll Quelle und Interpretation trennen.

Typische Felder:

- Entität/Spieler;
- NFL-Team/Position, soweit sicher;
- `source_claim`;
- Signaltyp;
- Preseason-/Usage-Klassifizierung, falls relevant;
- Opportunity-Provenance (`earned`, `injury_opened`, `vacated`, `ambiguous`, ...);
- historische Mighty-Giants-Relevanz;
- damalige Folgeaktion oder Nicht-Aktion;
- Verifikationsstatus, falls gegen andere Quellen geprüft.

Dynamische Werte in `extraction.json` sind historische Source-Evidenz und dürfen später nicht als aktuelle Wahrheit gelesen werden.

## Source- und Interpretationsgrenze

Ein Artikel darf gleichzeitig richtige Beobachtungen und zu aggressive Fantasy-Schlüsse enthalten.

Beispiel:

```text
Source Claim: Seth McGowan bekam die ersten Carries in einem Preseason-Kontext.
Source Conclusion: McGowan ist der klare Jonathan-Taylor-Handcuff.
Our Interpretation: Usage-Signal relevant, Schlussfolgerung wegen DJ-Giddens-Abwesenheit noch nicht ausreichend belegt.
```

Speichere diese Ebenen getrennt. Ein persistierter Artikel übernimmt nicht automatisch die Meinung des Autors als kanonische Fantasy-Regel.

## Materialitätsschwelle für Persistenz

Ein Artikel soll als dauerhaftes Source Package vorgeschlagen werden, wenn mindestens einer der folgenden Punkte erfüllt ist:

- er verändert eine Roster-, Draft-, Trade-, Free-Agent- oder Spielerbewertung materiell;
- er eröffnet einen neuen dauerhaften Watch-Kandidaten;
- er bestätigt oder widerlegt eine bestehende wichtige These;
- er enthält schwer später rekonstruierbare Camp-, Preseason-, Usage-, Snap-, Route-, Injury- oder Depth-Chart-Information;
- er führt zu einer dauerhaften Regel-, Quellen- oder Monitoring-Änderung;
- er ist als wiederverwendbarer Evidenz-Snapshot für eine spätere Entscheidung wertvoll.

Reine Unterhaltung, Boxscore-Rauschen ohne Entscheidungswirkung oder ein Artikel ohne neue/relevante Evidenz muss nicht persistiert werden.

## Nutzerbefehle und Write-Semantik

### `Artikel auswerten` oder `nur auswerten`

- Quelle analysieren;
- aktuelle Repo-/Liga- und externe Kontexte bei Bedarf abgleichen;
- relevante Claims und Fantasy-Auswirkungen erklären;
- Persistenzvorschlag nennen, wenn die Materialitätsschwelle erreicht ist;
- **keine dauerhaften Repository-Writes** allein aufgrund dieses Befehls.

### `nur Quelle sichern`

- Source Package persistieren;
- Raw/Provenienz/Lesefassung/Extraktion nach diesem Vertrag anlegen;
- keine neue Knowledge-, Watch-, Board-, Decision- oder Regelableitung kanonisieren, sofern nicht separat freigegeben.

### `auswerten und persistieren` / `Artikel auswerten und persistieren`

Dies ist die ausdrückliche Write-Freigabe für:

1. das Source Package, sofern die Quelle vollständig oder transparent teilvollständig erfasst werden kann;
2. die in derselben Antwort klar ausgewiesenen sinnvollen Source-Ableitungen innerhalb des normalen Write-Scope;
3. notwendige Quellen-/Regelpflege, wenn die Auswertung eine neue allgemein wiederverwendbare Regel identifiziert und der Nutzer diese Persistierung ausdrücklich mitfreigibt.

GitHub-Actions-Änderungen oder andere separat genehmigungspflichtige technische Aktivierungen bleiben davon ausgenommen.

### `Freigabe`

Wenn unmittelbar davor konkrete Source-/Watch-/Baseline-/Rule-Änderungen vorgeschlagen wurden, gilt die Freigabe für genau diesen sichtbar beschriebenen Umfang. Bei einem materialitätswürdigen Artikel gehört das Source Package standardmäßig dazu, wenn es im Vorschlag genannt wurde.

## Künftiger Ablauf bei nutzerbereitgestellten Artikeln

1. Artikel als Quelle lesen, ohne seine Schlussfolgerungen ungeprüft zu übernehmen.
2. Exakten bereitgestellten Rohtext für den möglichen Source Snapshot im aktuellen Arbeitskontext erhalten.
3. Claims, Entitäten und Signaltypen extrahieren.
4. Relevante Claims gegen aktuelle Liga-/Roster-Daten und bei dynamischen Aussagen gegen frische belastbare Quellen prüfen.
5. Source Claim, externe Verifikation und Mighty-Giants-Interpretation trennen.
6. Materialitätsschwelle anwenden.
7. Bei read-only Auftrag nur Persistenzvorschlag ausgeben.
8. Nach Freigabe Source Package und die konkret genehmigten Ableitungen persistieren.
9. Bei fehlendem exaktem Raw niemals eine Rekonstruktion als Original ausgeben.

## Preseason-Artikel

Für Preseason- und Camp-Artikel gilt zusätzlich die kanonische Klassifizierung aus `MONITORING_AND_WEEKLY_DECISIONS.md`.

Besonders relevante Signale sind:

- `first_team_snap_share`;
- `held_out_with_starters`;
- `starter_drive_targets`;
- `backup_hierarchy_change`;
- `injury_opened_opportunity`;
- `box_score_splash`.

Bei `injury_opened_opportunity` muss verdienter Rollenaufstieg von nur vorübergehend freigewordener Opportunity getrennt bleiben.

## Source Registry

Einzelne Artikelpakete benötigen nicht automatisch einen eigenen Eintrag in `source-registry.json`.

Ein Registry-Eintrag wird sinnvoll, wenn:

- derselbe Publisher oder Autor wiederholt genutzt wird;
- eine dauerhafte Gewichtung/Qualitätskalibrierung benötigt wird;
- automatische oder wiederkehrende Verarbeitung geplant wird;
- Quellenidentität für Vergleiche oder Conflict Resolution kanonisch werden soll.

Bis dahin trägt jedes Paket seine Provenienz selbst in `SOURCE.md`.

## Leitprinzip

> Wir persistieren Evidenz so, dass später nachvollziehbar bleibt, **was die Quelle sagte**, **was wir daraus extrahierten** und **welche Entscheidung daraus entstand** — ohne diese drei Ebenen miteinander zu vermischen.
