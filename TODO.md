# TODO

Menschenlesbare Todo-Liste für die Anwendung und die gemeinsame technische Plattform von `Lolindhir/fantasy-app`.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- Diese Datei sammelt offene App-, Frontend-, Generated-Data-, Infrastruktur- und allgemeine technische Plattform-Aufgaben.
- Fantasy-Management- und Fantasy-Operations-Todos werden getrennt in `fantasy-management/TODO.md` gepflegt.
- Todos werden auf Deutsch gepflegt; erledigte Einträge können entfernt oder unten archiviert werden.

## Offen

### Data Generation / Infrastruktur

- [ ] Repo-weite Publication-Strategie für schreibende Workflows vereinheitlichen.
  - Kontext: Die Inventarisierung vom 20.08.2026 umfasst 20 GitHub-Actions-Workflows. Die sechs Fantasy-Management-Source-Writer nutzen bereits `tools/publish_generated_commit.py` mit `rebase-and-retry`; der Fantasy-Operations-Materializer und der erfolgreiche NFL-Source-Sync verwenden bereits `rebuild-and-retry`. Mehrere App- und Maintenance-Writer pushen dagegen weiterhin einmalig direkt nach `main`.
  - Ziel: Jeden Branch-Writer explizit einer Publication-Klasse zuordnen: self-contained Snapshot = `rebase-and-retry`; repo-/input-abhängiges Derived Output = `rebuild-and-retry`; echter Inhaltskonflikt = fail-closed; niemals Force-Push zur automatischen Konfliktauflösung.
  - Architektur: Gemeinsame Git-Publish-Mechanik unter `tools/` halten und darüber bei Bedarf einen dependency-aware Writer-Runner ergänzen, statt Retry-Schleifen in einzelnen Workflow-YAMLs zu duplizieren.
  - Leitplanke: Fantasy-Management bleibt der bereits abgesicherte Referenzfall. App-Writer nur nach eigener Prüfung ihrer Input-/Output-Abhängigkeiten migrieren; keine pauschale Übernahme des Rebase-Modells.

- [ ] App-Data-Writer dependency-aware gegen `main`-Push-Races absichern.
  - Betroffen: `.github/workflows/update-league.yml`, `update-players.yml`, `update-games.yml`, `update-drafts.yml`, `update-standings.yml`, `update-transactions.yml` und `update-teams.yml`.
  - Priorität 1: `update-league.yml` wegen des 10-Minuten-Takts und der breiten Abhängigkeiten zuerst behandeln.
  - Priorität 2: Players und Games gemeinsam mit dem Tank01-Requestbudget betrachten. Ein verlorener Git-Push darf nicht automatisch unnötige externe Refetches erzeugen; bei irrelevanten `main`-Änderungen soll ein vorhandener validierter Stand möglichst weiterverwendet werden, bei relevanten Input-Änderungen dagegen neu gerechnet werden.
  - Priorität 3: Drafts und Transactions gemeinsam härten, weil beide Generatorpfade gegenseitige Draft-Pick-Anreicherungen und den Past-Seasons-Index berühren.
  - Priorität 4: Standings und Teams anschließend auf denselben Publication-Vertrag bringen.
  - Technische Besonderheit: Gemeinsame Outputs wie `public/data/Timestamps.json` und `public/data/backup/**` erzeugen zusätzliche Same-Path-Races; deshalb ist ein reiner Git-Rebase für App-Writer nicht generell ausreichend.
  - Validierung: Race-Tests müssen sowohl irrelevante parallele `main`-Commits als auch relevante Input-Änderungen und echte Same-Path-Konflikte abdecken.

- [ ] App-Generator-Abhängigkeiten und Orchestrierung nach Etablierung der Source-Data-Schicht neu ordnen.
  - Zeitpunkt / Abhängigkeit: Noch nicht umsetzen. Zuerst die aktuell entstehende persistente `source-data`-/NFL-Sync-Schicht etablieren und klären, welche Sleeper-, Tank01- und nflverse-Daten dort künftig provider-nah beziehungsweise normalisiert vorliegen. Danach die App-Generatorarchitektur gegen diesen tatsächlichen Source-Vertrag neu bewerten.
  - Ausgangslage: Die heutigen Generatoren besitzen mehrere historisch gewachsene gegenseitige Abhängigkeiten. Insbesondere liest `RequestPlayers.ps1` `Games.json` und `League.json`; `RequestLeague.ps1` aktualisiert selbst Transactions und Drafts und liest Players, Standings und Schedule; Drafts verwendet wiederum League, Standings und Transactions. Ein Teil dieser scheinbaren Runtime-Zyklen entstand, weil bestimmte Informationen beim initialen Saison-/Ligawechsel zunächst nur über den League-/Sleeper-Pfad verfügbar waren.
  - Grundsatz: Zwischen **Bootstrap-Abhängigkeiten** und **Normalbetriebs-Abhängigkeiten** unterscheiden. Eine Abhängigkeit, die ausschließlich zur erstmaligen Initialisierung einer neuen Liga/Saison erforderlich ist, soll nicht allein deshalb als permanenter zyklischer Runtime-Datenfluss bestehen bleiben.
  - Manueller Bootstrap: Der Saison-/Ligawechsel beginnt bewusst manuell:
    1. neue Liga in Sleeper anlegen;
    2. neue `LeagueID`, `LeagueYear` und weitere erforderliche liga-/saisonspezifische Angaben manuell in `Metadata.json` pflegen;
    3. danach einen expliziten manuellen Bootstrap starten;
    4. benötigte Sleeper-/Provider-Grunddaten beschaffen und validieren;
    5. erst nach erfolgreicher Initialisierung in den normalen inkrementellen Betrieb wechseln.
  - Bootstrap darf nicht automatisch allein durch eine `Metadata.json`-Änderung ausgelöst werden. Der Start soll bewusst manuell erfolgen, weil das Anlegen einer neuen Sleeper-Liga und das Setzen ihrer Metadaten ebenfalls ein manueller administrativer Vorgang ist.
  - Bootstrap-Fail-Closed: Ein neuer Saisonstand soll nicht teilweise veröffentlicht werden, wenn kritische Grunddaten fehlen oder widersprüchlich sind. Neue League-ID/Season, Team-/Roster-Zuordnung, grundlegende Sleeper-Settings und andere für die Initialisierung notwendige Invarianten vor der produktiven Veröffentlichung prüfen.
  - Wichtig: Ein erfolgreich abgeschlossener Bootstrap bedeutet ausdrücklich **nicht**, dass sämtliche saisonalen NFL-Daten bereits verfügbar sein müssen. Beispielsweise können `Schedule.json` und `Games.json` beim Liga-/Saison-Neustart im Winter legitim leer sein, weil der neue NFL-Spielplan noch nicht veröffentlicht wurde.
  - Source-Availability modellieren: Im späteren Datenvertrag mindestens unterscheiden zwischen:
    - Quelle/Dataset für den aktuellen Saisonzeitpunkt noch **nicht verfügbar / noch nicht erwartet**;
    - Quelle ist grundsätzlich aktiv, Abruf aber **fehlgeschlagen**;
    - Quelle ist aktiv und liefert **unerwartet leere oder unvollständige Daten**;
    - Quelle ist erfolgreich verfügbar.
  - Mehrere saisonale Cutoff-/Readiness-Punkte berücksichtigen: League/Sleeper-Liga angelegt, Draft-Kontext verfügbar, NFL Schedule veröffentlicht, Preseason/Regular Season begonnen, erste Spiele final usw. Nicht alle Generatorinvarianten müssen bereits direkt nach dem initialen Bootstrap gelten.
  - Aktuell bestätigte Normalbetriebs-Abhängigkeiten als Ausgangspunkt für das spätere Audit:
    - `Games/Schedule → Players`, weil `Players.json` spielbezogene Stats, Fantasy Points, Snaps usw. aus `Games.json` materialisiert;
    - `Players → League`, weil League aktuell Players unter anderem für Salary-/Relevant-Player-Kontext liest;
    - `Schedule → League`;
    - `Standings + Transactions → Drafts`;
    - `Drafts → League`;
    - Transactions fachlich als zweistufigen Fluss betrachten: `Transactions Base → Drafts → Transactions Pick-Enrichment`;
    - prüfen, ob heutige `League → Players`- und `League → Drafts`-Kanten nach Einführung gemeinsamer Source-/Season-Contexts vollständig entfallen können.
  - Zielbild Normalbetrieb: Nach Auflösung bootstrapbedingter Rückwärtskanten einen gerichteten Daten-DAG herstellen. Provider-/Source-Daten sollen möglichst vorgelagert verfügbar sein; App-Read-Models sollen nicht gegenseitig als Ersatz für fehlende Source-Daten dienen.
  - Perspektivischer Source-Layer: Prüfen, ob Sleeper-/Tank01-Grunddaten und gemeinsam benötigter Season-/League-Context künftig aus `source-data/providers/**` beziehungsweise einer providerunabhängigen normalisierten Schicht kommen. Keine solche Struktur vorwegnehmen, bevor der laufende NFL-Sync-Strang seinen stabilen Vertrag definiert hat.
  - Orchestrierungspräferenz: Fachlich zusammengehörige abhängige Generatoren nach Möglichkeit **innerhalb eines gemeinsamen GitHub-Actions-Runs und eines gemeinsamen Checkouts** ausführen, statt einzelne Datenabhängigkeiten über Workflow-zu-Workflow-Dispatches abzubilden.
  - Begründung: Ein gemeinsamer Run stellt sicher, dass Downstream-Generatoren exakt die frisch erzeugten Upstream-Dateien desselben Working Trees sehen, reduziert Zwischen-Commits und Push-Races und macht einen fachlichen Refresh als einen zusammenhängenden Run beobachtbar.
  - Workflow-zu-Workflow-Trigger nicht als Standard verwenden. Ein historischer Versuch aus 2025, Players aus dem Teams-Workflow per Workflow-Dispatch auszulösen, kombinierte fehlerhafte Exitcode-/Output-Weitergabe mit einem separaten Workflow/Checkout und war entsprechend unzuverlässig. Reusable Workflows können später technische Wiederverwendung ermöglichen, sollen aber nicht automatisch die Daten-DAG-Kanten darstellen.
  - Vorläufig denkbare Normalbetriebs-Pipelines nach Auflösung der Zyklen:
    - Post-Game: `Games/Schedule → Players → League`;
    - Player-Metadata-Refresh: `Players → League`;
    - Between-Week: `Standings → Transactions Base → Drafts → Transactions Enrichment → League`; `Teams` fachlich unabhängig, kann aber bei einem gemeinsamen Weekly-Refresh im selben Run aktualisiert werden.
  - Noch nicht festlegen: genaue Workflow-Grenzen, Anzahl der orchestrierenden Workflows, konkrete Trigger-/Concurrency-Mechanik und zukünftige Verantwortlichkeit von Sleeper/Tank01 zwischen App-Generatoren und `source-data`. Diese Entscheidungen erst nach Abschluss des aktuellen NFL-Sync-/Source-Data-Ausbaus treffen.
  - Publication separat berücksichtigen: Die Orchestrierung muss mit dem bereits offenen Vorhaben zur dependency-aware Publication und zu `main`-Push-Races zusammengedacht werden. Ein gemeinsamer Generation-Run reduziert konkurrierende Writer, ersetzt aber nicht den geplanten `rebuild-and-retry`-/Publication-Vertrag.
  - Doku nach Klärung: Sobald die Source-Data-Architektur stabil und das Zielbild beschlossen ist, den finalen Dependency-DAG, Bootstrap-/Normalbetriebsvertrag und Source-Availability-Semantik aus dem TODO in `.ai-context/manual/data-sources.yaml` und eine dauerhafte ADR unter `.ai-context/manual/decisions.yaml` überführen.
  - Leitregel für die spätere Architektur: **„Bootstrap dependency ≠ runtime dependency.“** Eine nur zur Initialisierung notwendige Providerbeschaffung darf keine dauerhafte zyklische Generatorabhängigkeit erzwingen.

- [ ] Maintenance- und Diagnose-Writer race-safe machen.
  - Betroffen: `.github/workflows/update-past-seasons-index.yml` und `.github/workflows/clean-backups.yml`; beide veröffentlichen aktuell über einen einmaligen direkten Push nach `main`.
  - Past-Seasons-Index: Bei fortgeschrittenem `main` neu gegen den aktuellen historischen Ressourcenbestand berechnen, weil der Index aus Repository-Inhalten abgeleitet wird.
  - Backup Cleanup: Die Retention-Entscheidung immer gegen den aktuellen Backup-Bestand neu treffen; keinen bereits auf einem alten Checkout berechneten Lösch-Commit lediglich rebasen.
  - NFL Source Sync: Der erfolgreiche Sync-Pfad besitzt bereits `rebuild-and-retry`; zusätzlich den direkten Push des `source-data/_sync/last-failure.json`-Diagnosepfads race-safe machen.

- [ ] Repo-weiten Regressionstest für Branch-Writer und Publish-Verträge ergänzen.
  - Ziel: Verhindern, dass neue oder geänderte schreibende Workflows wieder einen nackten einmaligen `git push ... HEAD:main` einführen.
  - Prüfung: Alle Workflows mit `contents: write` beziehungsweise erkennbarer Commit-/Push-Logik inventarisieren und sicherstellen, dass sie einen dokumentierten `rebase-and-retry`-, `rebuild-and-retry`- oder bewusst begründeten alternativen Publication-Pfad verwenden.
  - Ausnahme: Reine CI-, Build- und Pages-Deploy-Workflows ohne Repository-Branch-Write benötigen keinen Generated-Data-Publisher.
  - Schutz: Der Test darf keine konkrete Fachlogik erzwingen, sondern nur verhindern, dass der Race-Schutz still wieder entfernt wird.

- [ ] Schreibrechte der App-Datenworkflows auf das notwendige Minimum reduzieren.
  - Kontext: Mehrere App-Data-Workflows besitzen zusätzlich zu `contents: write` auch `pages: write` und `id-token: write`, obwohl das eigentliche Pages-Deployment separat in `deploy.yml` erfolgt.
  - Ziel: Nach der Publication-Härtung je Workflow prüfen, ob ausschließlich `contents: write` erforderlich ist, und überflüssige Pages-/OIDC-Rechte entfernen.
  - Leitplanke: Permission-Bereinigung getrennt von fachlichen Generatoränderungen validieren und keine benötigten Deploy-Rechte aus `deploy.yml` entfernen.

- [ ] GitHub Actions auf aktuelle Node-24-kompatible Action-Versionen aktualisieren.
  - Kontext: GitHub Actions warnt aktuell unter anderem bei `actions/checkout@v4` und `actions/setup-python@v5`, dass deren Node-20-Runtime-Ziel deprecated ist und vom Runner bereits auf Node 24 erzwungen wird.
  - Ziel: Repository-weit verwendete Actions inventarisieren und auf Major-/Release-Versionen aktualisieren, die Node 24 offiziell unterstützen, bevor die erzwungene Kompatibilität zu einem harten Fehler wird.
  - Validierung: Release Notes und Breaking Changes je Action prüfen; CI-, Deploy- und schreibende Datenworkflows nach der Umstellung separat validieren.
  - Leitplanke: Runtime-/Action-Upgrades nicht mit fachlichen Workflow-Änderungen vermischen und keine bestehenden Secrets, Trigger, Zeitpläne oder Write-Semantiken still verändern.

- [ ] GitHub-Actions-Run-Naming und eindeutige Trigger-Referenzen später erneut auditieren.
  - Kontext: Dynamische `run-name`-Ausdrücke verwenden aktuell teilweise `github.event.head_commit.message`. Bei Commits mit mehrzeiligem Body kann dadurch der komplette Committext im Run-Namen landen; kompakte automatisch erzeugte `data(...)`-Commits ergeben dagegen bereits gut lesbare Namen.
  - Ziel: Repo-weit prüfen, wie event-getriggerte Runs einen kompakten, menschenlesbaren und zugleich eindeutigen Bezug zum konkreten Auslöser behalten, ohne lange Commit-Bodies in den Titel zu übernehmen.
  - Uniqueness: `github.run_number` beziehungsweise `github.run_id` sowie Commit-/PR-Referenzen als mögliche eindeutige Komponente bewerten. Bei Pushes möglichst den Commit-Subject statt der vollständigen Message verwenden, sobald GitHub Actions dafür eine direkt nutzbare native Möglichkeit bereitstellt.
  - Beobachtung: Bei späteren Workflow-Audits die verfügbaren GitHub-Actions-Eventfelder und Expression-Funktionen erneut prüfen; insbesondere auf native Short-SHA-, Subject-, Substring- oder vergleichbare Möglichkeiten achten.
  - Leitplanke: Keine zusätzliche Dispatcher-, Reusable-Workflow- oder sonstige Orchestrierungsarchitektur allein für schönere Run-Namen einführen. Run-Naming bleibt Observability und darf den Datenfluss nicht verkomplizieren.

- [ ] Laufzeit-Konfiguration aus `ConfigUtils.psm1` in Umgebungsvariablen bzw. Workflow-Konfiguration auslagern.
  - Kontext: `ConfigUtils.psm1` enthält aktuell technische Pfade und Request-Konfiguration sowie laufzeitabhängige Werte.
  - Ziel: Laufzeitabhängige Werte nicht direkt im Repository pflegen; `Get-Config` soll sie bevorzugt aus der Laufzeitumgebung lesen und nur noch technische Defaults enthalten.

- [ ] Tank01-Requestbudget und Backup-Key-Fallbacks zentral absichern.
  - Kontext: Tank01/RapidAPI ist pro Account auf 1.000 Requests pro Monat begrenzt; Sleeper-Zugriffe sind dagegen nicht der knappe Teil.
  - Kontext: `RequestPlayers.ps1` und `RequestGames.ps1` verwenden bereits einen Haupt-Key und zwei Backup-Keys als sequentielle Fallbacks; vorhandene Daten werden teilweise wiederverwendet, dennoch erzeugt jeder Players-Lauf einen Tank01-Player-List-Request und jeder Games-Lauf einen vollständigen Schedule-Request.
  - Leitplanke: Neue Generatoren, Saisonabschluss-, Reparatur- und Backfill-Läufe dürfen die Tank01-Frequenz nicht still erhöhen oder vorhandene Backup-Keys als Begründung für zusätzliche Routine-Requests verwenden.
  - Ziel: Alle Tank01-Aufrufe über einen gemeinsamen Helper führen, Request-Anzahl und verbleibendes Monatsbudget je Key ohne Ausgabe der Schlüsselwerte nachvollziehbar machen und vor jedem größeren Lauf eine Request-Kostenschätzung bereitstellen.
  - Fallback: Backup-Keys nur sequenziell bei erschöpftem, gesperrtem oder technisch ausgefallenem aktivem Key nutzen; keine parallele Abfrage, kein Fan-out und keine doppelte Beschaffung derselben Daten über mehrere Keys.
  - Caching: Bereits erzeugte `Players.json`, `Games.json`, `Schedule.json` und Saisonarchive bevorzugen; Tank01 nur für tatsächlich fehlende oder gezielt zu reparierende Daten aufrufen und Antworten endpoint-, saison- und spielbezogen wiederverwenden.
  - Betrieb: Regelmäßige Sleeper-Abrufe dürfen unabhängig bleiben; zusätzliche Tank01-Läufe, historische Backfills oder Force-Reparaturen müssen manuell, budgetiert und bei zu geringem Restbudget fail-closed erfolgen.
  - Sicherheit: API-Key-Werte niemals in Logs, Fehlermeldungen, Artefakten oder generierten Dateien ausgeben.

- [ ] Generatorseitige Provider-Joins auf kanonische Identity-Invarianten auditieren und absichern.
  - Kontext: Der Player-Join Tank01 → Sleeper hat gezeigt, dass mehrere Provider-Datensätze auf dieselbe kanonische ID auflösen können und ein dadurch ungültiger generierter Read Model erst in einem Downstream-Schritt auffallen kann.
  - Ziel: Alle generatorseitigen Joins inventarisieren, bei denen externe oder provider-spezifische IDs auf kanonische IDs beziehungsweise andere eindeutige Schlüssel gemappt werden, und je Join die erwartete Cardinality sowie Missing-/Unique-Invarianten explizit definieren.
  - Schutz: Invarianten am frühesten Publishing-Boundary prüfen; bei Verletzung fail-closed abbrechen und den letzten guten generierten Stand unverändert erhalten.
  - Diagnose: Fehlerausgaben sollen den betroffenen kanonischen Schlüssel sowie relevante Provider-IDs, Namen/Labels und weitere Join-Provenienz aller Konfliktpartner enthalten, ohne Secrets oder Credentials auszugeben.
  - Leitplanke: Keine stillen Dedupes und keine heuristische Gewinnerauswahl ohne dokumentierten fachlichen Vertrag; vorhandene Downstream-Guards als Defense in Depth beibehalten.
  - Priorität: Zuerst Identity-Joins in Player-, Team-, Draft-, Transaction- und Historical-Generation prüfen und dokumentieren, welche Joins bereits abgesichert sind und wo Schutzlücken verbleiben.
  - Validierung: Für abgesicherte Joins gezielte Regressionstests für Duplicate-, Missing-ID- und relevante Cardinality-Fälle ergänzen, soweit die jeweilige Generatorstruktur dies sinnvoll zulässt.

- [ ] `CapDeadlineBufferDays` sauber über `ConfigUtils.psm1` bereitstellen.
  - Kontext: `CapDeadlineBufferDays` liegt als liga-spezifische Regel in `Metadata.json`, wird aber aktuell in `RequestLeague.ps1` direkt aus `Metadata.json` gelesen.
  - Grund: `ConfigUtils.psm1` enthält derzeit noch laufzeitabhängige Werte und konnte deshalb nicht gefahrlos vollständig ersetzt werden.
  - Ziel: Nach Auslagerung der Laufzeitwerte soll `Get-Config` den Wert aus `Metadata.json` laden und als Teil der Generator-Konfiguration bereitstellen.

- [ ] `PastSeasonsIndex.json`-Aktualisierung nur auf relevante Pfad-/Existenzänderungen prüfen.
  - Kontext: Der Index aktualisiert aktuell auch bei geänderten `ContentHash`-Werten historischer Ressourcen, obwohl sich die sichtbaren Pfade nicht ändern.
  - Ziel: Prüfen, ob für die Angular-Navigation ein Vergleich auf relevante Pfade und `Exists` ausreicht, während Hash-/UpdatedAt-Metadaten optional bleiben oder anders behandelt werden.
  - Hinweis: Nur ändern, wenn dadurch keine nützliche Freshness-/Debug-Information verloren geht.

- [ ] Backup-Daten aus `public/data/backup` herausziehen und versioniert im Repo behalten.
  - Kontext: `public` soll nur Dateien enthalten, die die Angular-App zur Laufzeit ausliefert oder lädt.
  - Kontext: Backups werden aktuell über `ConfigUtils.psm1` unter `public/data/backup` erzeugt und vom Cleanup-Workflow `.github/workflows/clean-backups.yml` bereinigt.
  - Ziel: Backups in einen sichtbaren Repo-Root-Ordner wie `data-backup/` verschieben, weiterhin versionieren und für manuelle Nutzung verfügbar halten.
  - Mit anpassen: `ConfigUtils.psm1`, `.github/workflows/clean-backups.yml`, betroffene Update-Workflows mit `git add public/data/** data-backup/**` und ggf. Deploy-Absicherung.

### Data Generation / NFL Source Data

- [ ] Persistente, providerunabhängige NFL-Quelldatenschicht aufbauen.
  - Kontext: Externe NFL-Daten werden derzeit überwiegend direkt während einzelner Generatorläufe von Sleeper und Tank01 bezogen. nflverse stellt zusätzlich umfangreiche strukturierte Datensätze bereit, darunter Player-Identitäten, Draft Picks, Combine, Rosters, Schedules, Player Stats, Snap Counts, Depth Charts und Contracts.
  - Ziel: Externe Beschaffung von der internen Nutzung entkoppeln. Provider-Rohdaten sollen reproduzierbar erhalten bleiben, während Generatoren und Fantasy-Management-Workflows gegen ein stabiles providerunabhängiges NFL-Datenmodell arbeiten.
  - Zielstruktur: Einen Repo-Root-Bereich `source-data/` prüfen und einführen; `source-data/providers/<provider>/` für providernahe Rohdaten und Provenienz sowie `source-data/nfl/` für normalisierte providerunabhängige NFL-Daten verwenden.
  - Abgrenzung: `public/data/**` bleibt generierte App-Ausgabe und darf nicht zum dauerhaften Rohdaten- oder Source-Store werden. `fantasy-management/sources/**` bleibt auf analysebezogene Fantasy-Management-Quellen beschränkt.
  - Provenienz: Je Dataset Provider, Upstream-Quelle, Abrufzeitpunkt, Source-URL bzw. Release-Identität, Format, Content-Hash, Zeilenanzahl, Schema-Version, Lizenz und erforderliche Attribution maschinenlesbar speichern.
  - Schutz: Neue Imports zunächst validieren und fail-closed behandeln; ein fehlerhafter oder unvollständiger Fetch darf einen vorhandenen letzten guten Datenbestand nicht zerstören.

- [ ] NFL-Source-Dataset-Registry und Refresh-/Retention-Regeln definieren.
  - Ziel: Für jedes unterstützte Dataset festlegen, ob es immutable, saisonal finalisierbar, snapshot-basiert oder fortlaufend dynamisch ist.
  - Erste Priorität: Players, Fantasy Player IDs, Draft Picks, Combine, Rosters, Weekly Rosters, Schedules, Player Stats, Snap Counts, Depth Charts und Contracts.
  - Immutable bzw. historisch stabile Daten wie abgeschlossene Drafts und Combine-Ergebnisse dauerhaft saison- bzw. jahrgangsbezogen erhalten und im Normalbetrieb nicht erneut überschreiben.
  - Saisonale Daten wie Stats, Schedules und Weekly Rosters während der laufenden Saison aktualisieren und nach einem validierten Saisonabschluss finalisieren.
  - Snapshot-Daten wie Depth Charts zeitpunktbezogen speichern, sodass historische Änderungen rekonstruierbar bleiben.
  - Große Play-Level-Datensätze wie Play-by-Play, Participation und FTN Charting zunächst nur registrieren und erst bei einem konkreten Consumer dauerhaft importieren.
  - Für jeden Datensatz festlegen, wann ein Force-Refresh bzw. eine historische Korrektur zulässig ist.

- [x] Provideradapter für nflverse mit Raw-Persistierung und Content-Hash-Vergleich entwickeln.
  - Erledigt: Die registrierten nflverse-Datasets werden zentral geladen, vor Veröffentlichung auf Schema und Mindestumfang validiert und unter `source-data/providers/nflverse/` provider-nah persistiert.
  - Content-Hash: Unveränderte Downloads erzeugen keinen neuen Raw-Inhalt; der letzte validierte lokale Stand bleibt als reproduzierbare Fallback-Basis erhalten.
  - Publication: Der produktive Workflow veröffentlicht Raw-Daten zuerst und materialisiert Canonical erst aus dem bereits persistierten Raw-Stand; Fehler zerstören den letzten guten Providerstand nicht.
  - Abgrenzung: nflverse-Feldnamen bleiben in Adapter-/Normalisierungslogik und sickern nicht als neuer App-Vertrag in `public/data/**` durch.

- [x] Kanonische NFL-Player-Identity-Bridge aufbauen.
  - Erledigt: `NFLPlayerID` ist die dauerhafte providerunabhängige Personenidentität unter `source-data/nfl/identities/`; GSIS, Sleeper, Tank01, ESPN, PFR, PFF und weitere Provider-IDs sind Zuordnungen und nicht der Master-Key.
  - App-Vertrag: `public/data/Players.json[].ID` bleibt unverändert die Sleeper-ID für den aktuellen App-/Liga-Kontext.
  - Historie: Provider-Mappings werden saisonbezogen erhalten; spätere ID-Wiederverwendung kann auf eine andere `NFLPlayerID` zeigen, ohne historische Personen umzudeuten.
  - Konflikte: Widersprüchliche oder mehrdeutige Mappings werden explizit quarantänisiert; keine stillen Dedupes, Name-Matches oder heuristischen Gewinner.
  - Validierung: Real-nflverse-Bootstrap, 27 Source-Tests, zweiter semantischer No-op-Pass und Audit mit `duplicateLinkProviderIDCount = 0` sind erfolgreich; Sleeper `133` bleibt als expliziter Zwei-Personen-Konflikt quarantänisiert.

- [x] Kanonische NFL-Draft-Historie und Draftstatus als persistentes Source-Dataset materialisieren.
  - Erledigt: nflverse Draft Picks werden über die zentrale `NFLPlayerID` normalisiert und saisonweise unter `source-data/nfl/draft/` persistiert; der aktuelle Bootstrap umfasst 47 Draft-Saisons von 1980 bis 2026.
  - Semantik: Draftjahr, Runde, Position innerhalb der Runde, Overall Pick, Draft-Team und Player-Identität bleiben explizit; `drafted`, `undrafted`, `not_yet_drafted` und `unknown` werden nicht vermischt.
  - Historie: Abgeschlossene Draftjahrgänge sind kanonische historische Source-Daten und werden nicht als aktuelle App-Draft-Assets interpretiert.
  - Validierung: Draft-Materialisierung ist Bestandteil des Real-Data-Audits und des verpflichtenden zweiten No-op-Passes.

- [ ] NFL Combine als nächstes persistentes kanonisches Source-Dataset materialisieren.
  - Ziel: Jahrgangsbezogene Combine-Messungen mit `NFLPlayerID` und Draft-Verknüpfung in `source-data/nfl/` materialisieren.
  - Historie: Abgeschlossene Jahrgänge dauerhaft erhalten und standardmäßig nur fehlende neue Jahrgänge ergänzen; bewusste historische Korrekturen nur über einen expliziten Force-/Repair-Pfad zulassen.
  - Integration: Erst nach Stabilisierung des Combine-Source-Datasets entscheiden, welche Felder in `Players.json` oder weitere generierte App-Readmodels übernommen werden.
  - Validierung: Coverage gegen den aktuellen Playerbestand prüfen, insbesondere Rookies, ältere Spieler und Spieler ohne eindeutige Combine-Zuordnung.

- [ ] nflverse Player Stats, Schedules, Rosters und Snap Counts gegen die bestehende Tank01-/Sleeper-Datenbasis evaluieren.
  - Ziel: Feld-Coverage, Historientiefe, Aktualität, Identitätsqualität und bekannte Lücken der Quellen systematisch vergleichen.
  - Ergebnis: Pro fachlichem Feld festlegen, welche Quelle primär, sekundär oder nur Fallback ist; keine pauschale Ablösung von Tank01 ohne datenbezogenen Vergleich.
  - Historie: Prüfen, ob nflverse bestehende Lücken in `public/data/past_seasons` verlässlich schließen kann.
  - Synergie: Ergebnis mit den bestehenden TODOs zur historischen Player-/Games-/Schedule-Rekonstruktion und zum Tank01-Requestbudget abstimmen.

- [ ] nflverse Depth Charts als mögliche zusätzliche Depth-Chart-Quelle evaluieren.
  - Ziel: Abdeckung und Aktualität der timestamp-basierten aktuellen Depth Charts gegen Sleeper und weitere geprüfte Depth-Chart-Quellen vergleichen.
  - Datenmodell: Historische Snapshots erhalten, statt nur den jeweils neuesten Stand zu überschreiben.
  - Nutzung: Depth-Chart-Änderungen später als eigenständiges Monitoring-Signal ableiten können.
  - Leitplanke: Depth-Chart-Rankings bleiben Rollen-/Roster-Signale und dürfen nicht ohne zusätzliche Usage-Daten als Fantasy-Opportunity interpretiert werden.

- [ ] Lizenz- und Attribution-Regeln für persistierte externe NFL-Datasets dokumentieren und technisch abbilden.
  - Ziel: Lizenz und erforderliche Attribution pro Dataset im Source-Manifest festhalten, statt pauschal eine einzige nflverse-Lizenz anzunehmen.
  - Besonderheit: Datensätze mit eigenständiger Upstream-Lizenz bzw. Attribution, insbesondere FTN- und Participation-Daten, getrennt kennzeichnen.
  - Schutz: Vor Aufnahme weiterer externer Provider prüfen, ob lokale Persistierung, Weiterverarbeitung und Veröffentlichung im Repository mit den jeweiligen Bedingungen vereinbar sind.

### Data Generation / Drafts

- [ ] Draft-Live-Enrichment für `public/data/Drafts.json` bei nächstem laufenden Sleeper-Draft validieren.
  - Kontext: Die technische Live-Enrichment-Logik für aktuelle Drafts ist implementiert; ein echter laufender Sleeper-Draft wurde damit aber noch nicht praktisch geprüft.
  - Ziel: Bei einem laufenden Sleeper-Draft kontrollieren, ob `Drafts.json` echte Pick-Ergebnisse korrekt setzt.
  - Zu prüfen: `Status = Picked`, `PlayerID`, `PlayerName`, `SleeperPickNo`, `SleeperPickedBy`, stabile `PickKey` und korrekte Frontend-Darstellung.

### Data Generation / League Status

- [ ] Sleeper-Feld für `CutsAllowed` bzw. Move-/Cut-Sperre prüfen.
  - Kontext: `CutsAllowed` wird aktuell wie bisher grundsätzlich auf `true` gesetzt und nur bei `Completed` geschlossen.
  - Ziel: Herausfinden, ob Sleeper ein verlässliches Feld für Cut-/Roster-Move-Sperren liefert und dieses datengetrieben anbinden.
  - Hinweis: `CutsAllowed` darf nicht aus `League.Phase` abgeleitet werden; insbesondere `Cap Check` ist nur ein Prozessstatus, keine eigenständige Cut-Source-of-Truth.

### Data Generation / League History

- [ ] Saisonabschluss-Archivierung vollständig, atomar und wiederholbar automatisieren.
  - Kontext: `Players.json`, `Games.json` und `Schedule.json` wurden bisher nach Saisonende über manuelle Einzelaufrufe bzw. Dateiverschiebungen archiviert; bei einem verspäteten Lauf kann der Saisonendzustand bereits durch Offseason-Änderungen verfälscht sein.
  - Kontext: Drafts und Transactions besitzen bereits eigene historische Generatorpfade, während historische `Standings`- und `Teams`-Dateien im aktuellen `PastSeasonsIndex.json` für die bisherigen Spielzeiten fehlen.
  - Ziel: Vor dem Wechsel von `LeagueYear` einen kontrollierten Saisonabschluss für Players, Games, Schedule, Standings einschließlich Playoffs und Awards, Teams, Transactions und Drafts durchführen.
  - Vollständigkeitsprüfung: Nur finalisieren, wenn die Saison abgeschlossen ist und alle für die Ressource erwarteten Wochen, Spiele, Platzierungen und Identitäten vorhanden beziehungsweise bewusst als nicht verfügbar dokumentiert sind.
  - Wiederholbarkeit: Der Ablauf muss idempotent sein, bestehende finale Saisonstände standardmäßig nicht überschreiben und für bewusste Korrekturen einen expliziten Force-Modus anbieten.
  - Schutz: Der Wechsel auf eine neue Saison beziehungsweise das Leeren aktiver Games-/Schedule-Daten darf erst erfolgen, wenn der vorherige Saisonabschluss erfolgreich archiviert und validiert wurde.
  - Ergebnis: Historische Ressourcen unter `public/data/past_seasons` ablegen, `PastSeasonsIndex.json` aktualisieren und den Archivstatus der Saison maschinenlesbar dokumentieren.

- [ ] Player-Snapshot zum Saisonende für historische Moves erzeugen.
  - Kontext: Die Moves-Historie kann historische Transactions laden, löst Spieler aktuell aber weiterhin gegen das jeweils aktuelle `Players.json` auf.
  - Problem: Ausgeschiedene oder später aus dem aktuellen Playerbestand entfernte Spieler können dadurch in historischen Moves nur als `Player <ID>` erscheinen.
  - Ziel: Im vollständigen Saisonabschluss einen stabilen, saisonbezogenen Player-Snapshot mit mindestens Player-ID, Name, Position, NFL-Team und Bildreferenz erzeugen und über `PastSeasonsIndex.json` auffindbar machen.
  - Leitplanke: Der Snapshot muss generatorseitig entstehen; Angular darf ihn nur laden und zur historischen Anzeige verwenden.
  - Abhängigkeit: Der Moves-Snapshot soll aus dem validierten Saisonarchiv entstehen und nicht durch einen späteren Lauf gegen bereits veränderte aktuelle Spielerquellen rekonstruiert werden.

- [ ] Player-Historie und Vorjahres-Fallback dynamisch statt fest über `SeasonMinus1` bis `SeasonMinus3` modellieren.
  - Kontext: `RequestPlayers.ps1` erwartet aktuell zwingend drei konkrete archivierte Player-Dateien; fehlt eine davon, bricht der gesamte Player-Lauf ab.
  - Kontext: Vor Woche 1 dient die vergangene Saison bereits als vollständige Punktebasis, anschließend werden aktuelle und letztjährige Werte in den ersten Wochen schrittweise gemischt.
  - Ziel: Alle verfügbaren historischen Spielzeiten saisonbezogen als Liste oder Map erhalten, während Salary-, Ranking- und Projektionsformeln weiterhin bewusst eine konfigurierbare Auswahl der jüngsten vollständigen Jahre verwenden können.
  - Fallback: Die jüngste vollständig archivierte Saison als Vorjahresbasis verwenden und fehlende ältere Jahre kontrolliert behandeln, statt den gesamten Lauf unnötig zu beenden oder fehlende Daten still als echte Nullleistung zu interpretieren.
  - Datenqualität: Unterscheiden zwischen fehlendem Saisonarchiv, Spieler noch nicht in der NFL, vorhandenem Spieler ohne Einsatz und nicht mehr auflösbarer Spieleridentität.
  - Migration: Bestehende Felder und Frontend-Verträge nur kontrolliert ablösen oder über einen Übergangs-Fallback weiter bedienen.

- [ ] Historische Player-, Games-, Schedule- und League-Daten vor dem bestehenden Archivzeitraum analysieren und soweit möglich nachpflegen.
  - Kontext: Für 2022 bis 2025 existieren aktuell Player-, Games- und Schedule-Dateien, während Standings und Teams fehlen; Drafts und Transactions reichen ebenfalls nicht für alle Spielzeiten gleich weit zurück.
  - Ziel: Zunächst eine Coverage-Matrix je Saison und Ressource erstellen und anschließend belastbar rekonstruierbare Daten nach `public/data/past_seasons` übernehmen.
  - Quellenprüfung: Für Player-Historie getrennt prüfen, welche Daten über Sleeper, bestehende Tank01-/Games-Daten, historische Boxscores oder andere bereits zulässige Quellen mit stabiler ID-Zuordnung verfügbar sind.
  - Qualitätsstufen: Vollständig rekonstruierbar, nur aggregierte Saisonwerte verfügbar, ohne einzelne Detailfelder wie Snaps verfügbar oder nicht zuverlässig rekonstruierbar.
  - Leitplanke: Fehlende historische Werte nicht erfinden; Herkunft, Abdeckung und bekannte Lücken je Saison dokumentieren.

- [ ] Hall-of-Fame-/Legacy-Auswertungen generatorseitig modellieren.
  - Kontext: Die Standings-Route erzeugt Hall-of-Fame-Highlights, Award-Legende, All-Time-Regular-Season und Season-Archive aktuell bewusst als Frontend-Prototyp in `league-standings-view.util.ts`.
  - Entscheidung: Season-Awards bleiben dauerhaft Teil von `Standings.json`; es soll kein eigenständiges `Awards.json` für diesen Contract entstehen.
  - Ziel: Nach Stabilisierung der UI und Datenform prüfen, welche Legacy-/History-Readmodels generatorseitig aus `Standings.json` abgeleitet und ggf. als eigener Legacy-/History-Contract bereitgestellt werden sollen.
  - Kandidaten: Legacy-Highlights (`Champ of Champs`, `Regular Season King`, `Podium Machine`, `Award Collector`), Award-Legende, Season-History-Readmodel, All-Time-Regular-Season-Readmodel.
  - Hinweis: Angular darf diese Werte vorläufig als Frontend-ViewModel ableiten; langfristige source-of-truth-nahe Historienauswertungen sollten aber generatorseitig entstehen.

- [ ] `WinPercentageDisplay` für All-Time Regular Season generatorseitig erzeugen.
  - Kontext: All-Time-Regular-Season-Daten enthalten aktuell `WinPercentage`, aber kein `WinPercentageDisplay`.
  - Kontext: Die Frontend-Anzeige nutzt vorläufig `WinPercentageDisplay`, falls vorhanden, und formatiert sonst das vorhandene numerische `WinPercentage` als Fallback.
  - Ziel: Der Generator soll für `Placements.AllTime.Regular` dasselbe Display-Feld erzeugen wie bei anderen Regular-Season-Platzierungen, damit Angular kein Display-Fallback mehr benötigt.

### Frontend

- [ ] Teams-Übersicht und Team-Detail als Salary-zentrierten Franchise-Hub neu gestalten.
  - Zielbild: `/teams` soll die sechs Teams als kompakte, responsive Material-Cards zeigen; Desktop bevorzugt als 2×3-Grid, Mobile einspaltig. Die Seite bleibt eine Ist-Zustands-/Analyseansicht und enthält keine What-if-Simulation.
  - Team-Card: Teamlogo, Teamname und Owner sowie ein kombiniertes Salary-Health-Signal anzeigen. Grün bedeutet Current und Projected im Cap, Gelb Current im Cap aber Projected über Cap, Rot bereits Current über Cap. Die Card selbst nicht vollflächig einfärben; Status nur als zurückhaltendes Signal/Pill nutzen.
  - Cap-Balken: Current und Projected mit Salary, Cap Space, Prozentwert und kompaktem Progress-Balken direkt auf der Card zeigen.
  - Roster-Struktur: `Roster`, `Taxi` und `IR` jeweils mit aktuellem Wert und vorhandenem Maximalwert anzeigen; fehlt ein fachliches Limit, nur den aktuellen Wert anzeigen. Normales Roster nicht direkt aus `Roster.length` ableiten, weil Sleeper Taxi-/Reserve-Spieler zusätzlich im Roster-Array führt; Taxi und IR vor der normalen Roster-Zählung herausrechnen.
  - Limits: Normales Roster aus `League.RosterSize` bzw. den zugrunde liegenden Roster-Positionen ableiten; Taxi-/IR-Limits aus den bereits mitgelieferten League-Settings (`taxi_slots`, `reserve_slots`) verwenden. `Reserve` im UI als `IR` bezeichnen, solange der Generatorvertrag weiterhin direkt Sleeper `roster.reserve` abbildet.
  - Saisonstatus: Solange kein sinnvolles Current Standing vorliegt, auf die letzte Saison zurückfallen und dort Regular-Season-Record plus finale Playoff-/Overall-Platzierung anzeigen, z. B. `10–3 Regular Season · 4th Overall`. Sobald Current tatsächlich läuft, aktuelle Werte verwenden.
  - Open Picks: Auf der Card nicht `0` für eine bereits vollständig gedraftete Saison zeigen. Stattdessen ab aktueller Saison die früheste Saison mit mindestens einem noch offenen Pick des Teams bestimmen und z. B. `2027 Open Picks: 10` anzeigen; wenn keine offenen Picks existieren, die Zeile ausblenden.
  - Team-Detail: Klick auf die Team-Card öffnet einen großen Team-Detaildialog nach dem etablierten Player-Detail-Muster: heller Material-Dialog, Teamlogo/Name/Owner im Header, Salary-Health-Signal, Close-Button und Tabs `Overview`, `Roster`, `Salary`, `Drafts`, `History`. Desktop ca. 950–1000 px max-width, Mobile nahezu fullscreen.
  - Detail-Overview: Salary Health, fünf Core Assets, Roster Structure mit `Roster/Taxi/IR` und Positionsverteilung sowie einen kompakten Franchise Snapshot kombinieren. Salary nicht global über alle Tabs festpinnen.
  - Core Assets: zunächst fünf wichtigste Spieler aus einer bestehenden, nachvollziehbaren App-Logik ableiten; vorhandene Salary-/Ranking-Logik bevorzugt wiederverwenden, keine neue undokumentierte Team-Stärke erfinden.
  - Roster-Tab: bestehende `PlayerListComponent` wiederverwenden und in getrennten Sections für normales Roster, Taxi und IR rendern. Default-Sortierung Current Salary absteigend; optional Sortierung nach Projected Salary, Ranking, Age und Name. Salary und Projected Salary bleiben direkt sichtbar; Player-Klick öffnet weiterhin den bestehenden Player-Detaildialog.
  - Salary-Tab: `Current <Season> | Projected <Season+1>` als Material-Toggle, Default Current. Der ausgewählte Zustand bekommt einen großen dominanten Cap-Balken; der andere Zustand bleibt als kleinere Vergleichszeile sichtbar. Toggle steuert Salary/Cap, Donut-Verteilung und `Most Expensive`.
  - Salary by Position: Salary-Verteilung als Donut-Chart darstellen und für QB/RB/WR/TE/K die bereits zentral definierten Positionsfarben wiederverwenden; zusätzlich absolute Positionssummen und Prozentwerte anzeigen. Im Projected-Modus auf `SalaryProjected` umschalten.
  - Salary Top 5: `Most Expensive` als Top 5 und abhängig vom Current-/Projected-Toggle berechnen. `Biggest Projected Increases` und `Biggest Projected Decreases` jeweils als stabile Top-5-Listen aus `SalaryProjected - Salary` zeigen; diese beiden Movement-Listen ändern sich beim Toggle nicht.
  - Drafts-Tab: teamzentriert kommende/offene Picks für aktuelle und zukünftige Saisons sowie vergangene Draft-Picks mit tatsächlich ausgewählten Spielern zeigen; bestehende Draft-Contracts und nach Möglichkeit bestehende Draft-Pick-Trigger/Popover-/Display-Logik wiederverwenden statt eine parallele Draft-Semantik aufzubauen.
  - History-Tab: Season Record, finale Platzierung, Championships, Runner-ups, Regular-Season-Titel, Awards und All-Time-Werte kompakt aus den bestehenden Standings-/History-Daten darstellen; keine neue Historien-Source-of-Truth im Frontend einführen.
  - Abgrenzung Simulator: bestehende Exclude-/Cap-Simulation nicht in den neuen Team-Detaildialog übernehmen. What-if-Cuts, Trades und kombinierte Salary-Szenarien perspektivisch im Trade Simulator zu einem Salary-&-Trade-Simulator weiterentwickeln.
  - Wiederverwendung: `PlayerListComponent`, `PlayerDetailDialogComponent` als Interaktions-/Dialogvorbild, `PositionStylePipe`, vorhandene Draft-UI-Helfer/-Trigger und bestehende Material-Komponenten bevorzugt nutzen. Neue UI-Bausteine wie Salary-Health-Signal, Cap-Progress-Bar und Salary-by-Position-Chart bewusst wiederverwendbar statt nur teamlokal entwerfen, wenn dadurch keine unnötige Abstraktion entsteht.
  - Optik: keine neue Dark-/Dashboard-Designsprache einführen. An bestehender heller Angular-Material-Optik, ca. 900–1000 px Content-Breite, weißen/hellgrauen Cards, dünnen Borders, 8–16 px Radien, zurückhaltenden Schatten und punktuellen Akzentfarben orientieren.
  - Mobile: Cards einspaltig; Team-Dialog nahezu fullscreen; Tabs horizontal scrollbar; PlayerList im bestehenden Compact-Modus verwenden; große Tabellen und unnötige horizontale Scrollflächen vermeiden.

- [ ] Alternative Sortierung für kompakte Future-Drafts in Drafts prüfen.
  - Kontext: Future-Drafts werden aktuell nach Pick Strength sortiert: zuerst Anzahl Picks in Runde 1, dann Runde 2, dann Runde 3 usw. bis zur flexiblen Draft-Rundenzahl.
  - Alternative: Optional eine Sortierung nach den Draft-Order-Regeln anbieten, z. B. Free-Agent-Drafts nach All-Time-Standings und Rookie-Drafts nach Saison-/Vorjahresplatzierung, sobald eine verlässliche Reihenfolge verfügbar ist.
  - Ziel: Falls die Pick-Strength-Sortierung nicht intuitiv genug ist, später einen klar beschrifteten Sortiermodus oder Toggle prüfen.

- [ ] `DataService` als schmale App-Datenfassade überprüfen und bei Bedarf weiter stabilisieren.
  - Kontext: `src/app/core/services/data.service.ts` ist aktuell vor allem öffentliche App-Datenfassade und Orchestrator.
  - Kontext: Die alte Location `src/app/services/data-service.ts` wurde entfernt; Consumer importieren `DataService` aus `src/app/core/services/data.service.ts`.
  - Kontext: Die Zielstruktur `src/app/core`, `src/app/shared` und `src/app/features` ist umgesetzt; geroutete Feature-Seiten liegen unter `src/app/features/**`, wiederverwendbare UI-Komponenten unter `src/app/shared/components/**`.
  - Kontext: `src/app/core/models/fantasy.models.ts` ist der zentrale Model-Importpfad. Feature- und Shared-Komponenten importieren ihre reinen Model-/Type-Abhängigkeiten von dort statt direkt aus `data.service.ts`.
  - Kontext: Draft-Modelle liegen in `src/app/core/models/draft.models.ts`, League-/Standing-/FantasyTeam-Modelle in `src/app/core/models/league.models.ts`, Player-/NFLTeam-/Stats-/FreeAgentMarket-Modelle in `src/app/core/models/player.models.ts` und Transaction-Modelle in `src/app/core/models/transaction.models.ts`.
  - Kontext: `src/app/core/services/data-api.service.ts` enthält das HTTP-Laden der generierten JSON-Dateien und Timestamps einschließlich des Moves-Datenpakets.
  - Kontext: `src/app/core/mappers/league.mapper.ts` enthält die reine `RawLeague`-/`RawFantasyTeam`-/DraftPick-zu-`League`/`FantasyTeam`-Transformation inklusive Team-Roster-Zuweisung.
  - Kontext: `src/app/core/mappers/player.mapper.ts` enthält die reine `RawPlayer`-zu-`Player`-Transformation inklusive Stats-, Injury-, SalaryDisplay- und GameHistory-Mapping.
  - Kontext: `src/app/core/mappers/transaction.mapper.ts` enthält die reine `RawTransaction`-zu-`Transaction`-Transformation mit Team-/Player-Auflösung und participant-bezogener Asset-Richtung.
  - Kontext: `src/app/core/services/free-agent-market.service.ts` enthält die FreeAgentMarket-/RuleBasedAutoCut-Logik für Current- und Projected-Salary-Modi.
  - Kontext: `src/app/shared/utils/player-sort.util.ts` enthält die wiederverwendbare Player-Sortierung.
  - Kontext: `src/app/shared/utils/trade-calculator.util.ts` enthält wiederverwendbare Salary- und Trade-Roster-Berechnungen.
  - Kontext: `src/app/shared/utils/league-standings-view.util.ts` enthält wiederverwendbare ViewModel-Logik für Current Standings, Season Results, Previous-Season-Awards und All-Time Standings.
  - Ziel: Prüfen, ob Consumer künftig direkt die Shared Utils nutzen sollen, damit die Kompatibilitäts-Delegates in `DataService` entfallen können.
  - Ziel: Prüfen, ob `DataService` dauerhaft als App-Datenfassade benannt bleibt oder später klarer als `FantasyDataService`/`DataFacade` bezeichnet werden soll.
  - Optional: Import-Aliases wie `@core/*`, `@shared/*` und `@app/*` prüfen.

- [ ] Dynamische Farbbindung der Overview-Draft-Pick-Chips prüfen.
  - Kontext: Die statischen Draft-Pick-Chip-Styles liegen inzwischen in `overview.scss`; im Template bleibt nur die dynamische Hintergrundfarbe per `[style.background-color]="pick.backgroundColor"`.
  - Ziel: Prüfen, ob diese Binding-Lösung bewusst beibehalten wird oder ob die Farbe später über CSS-Klassen bzw. CSS Custom Properties modelliert werden soll.

- [ ] Overview-Cap-/Awards-Blöcke als nächste UI-Slices prüfen.
  - Kontext: Standings, Season Results und All-Time Standings wurden aus der Overview in gemeinsame ViewModels bzw. Shared-Komponenten ausgelagert.
  - Kontext: `overview.scss` enthält weiterhin Cap-Space-, Deadline- und Regular-Season-Awards-Styles direkt in der Overview.
  - Ziel: Bei weiterem Overview-Refactor prüfen, ob Cap Space, Deadline und Awards eigene Komponenten/ViewModels bekommen sollen.

- [ ] Deadline-Anzeige im Overview allgemein statt Cap-Deadline-spezifisch modellieren.
  - Kontext: Die Overview-Header-Deadline nutzt aktuell `League.CapDeadline` und den festen Text `until Cap Deadline`.
  - Ziel: Deadline-Datum und Anzeige-Label allgemein modellieren, z. B. als `DeadlineDate`/`DeadlineLabel` oder als Liste von Deadlines, damit später auch andere League-Deadlines angezeigt werden können.
  - Hinweis: Die aktuelle Restzeitanzeige mit Tagen bzw. unter 24 Stunden mit Stunden/Minuten beibehalten.

### Dokumentation / AI-Kontext

- [ ] Fehlenden generierten AI-Kontext klären.
  - Kontext: `.ai-context/ai-context.yaml` verweist in der Lesereihenfolge auf `.ai-context/generated/file-docs.json` und `.ai-context/generated/generated-json-contracts.json`.
  - Kontext: Diese generierten Kontextdateien sind aktuell nicht im Repository abrufbar.
  - Ziel: Entweder die generierten Dateien über den vorgesehenen Generator erzeugen und committen oder die Lesereihenfolge/Guidance so anpassen, dass fehlende Generated-Kontextdateien ausdrücklich optional sind.
  - Hinweis: Dateien unter `.ai-context/generated` dürfen nicht manuell gepflegt werden.

- [ ] Leichten Validierungscheck oder CI-Check ergänzen, der parallele AI-Kontext-Doku unter `docs/ai-context/**` verhindert.
  - Kontext: AI-Kontext-Dokumentation soll ausschließlich unter `.ai-context` liegen.
  - Ziel: Doppelte oder auseinanderlaufende Dokumentation vermeiden.

### Später / Ideen

- [ ] Draft-Kapital-Score und Pick-Werte für Draft-Assets prüfen.
  - Kontext: Drafts zeigen bereits Pick-Besitz und Trade-History; für Dynasty-Planung wäre zusätzlich interessant, wie wertvoll die aktuellen und zukünftigen Picks eines Teams sind.
  - Kontext: Overview Draft Capital und Drafts nutzen vorläufig eine frontendseitige Pick-Strength-Sortierung aus `src/app/shared/utils/draft-capital.util.ts`.
  - Idee: Einzelne Picks mit einem Wert versehen, z. B. abhängig von Runde, konkretem `OverallPick` bei Exact-Drafts und reduzierter Rundenschätzung bei RoundOnly-Future-Drafts.
  - Idee: Eine generierte Statistikdatei für historische Pick-Werte aufbauen, z. B. `public/data/stats/DraftPickValueStats.json`.
  - Idee: Historische Draft-Picks mit den gepickten Spielern und deren Fantasy-Punkten nach Rookie-Year, 2-Year-Window und 3-Year-Window verbinden.
  - Ziel: Daraus pro Team und Draft/Season einen Draft-Capital-Score ableiten, ohne Draft-Ownership als Source-of-Truth ins Frontend zu verlagern.
  - Ziel: Durchschnittliche Punkte pro konkretem Pick, Pick-Bucket, Runde und DraftType berechnen, damit Pick-Werte liga-spezifisch statt nur manuell geschätzt werden.
  - Ziel: Sobald generatorseitig Draft-Capital-Werte vorliegen, Overview Draft Capital und Drafts-Sortierungen auf diese Datenwerte umstellen und die frontendseitige Pick-Strength nur noch als Fallback verwenden.
  - Hinweis: Gewichtung später bewusst diskutieren, weil `1.01`, frühe Runde 1 und spätere Runden sehr unterschiedlich bewertet werden sollten.
  - Hinweis: Kleine Sample Sizes über Fallbacks abfangen, z. B. exakter Pick → Pick-Bucket → Runde → DraftType-Durchschnitt.

- [ ] Rollenbasierte AI-Arbeitsmodi für fokussierte Chats prüfen.
  - Kontext: Aktuell soll ohne expliziten Rollenmodus weiterhin die vollständige Projekt-Guidance gelten, damit keine globalen Regeln versehentlich weggefiltert werden.
  - Idee: Später optionale Arbeitsmodi wie Architektur, Frontend, Data Generation oder AI-Kontext-Maintenance definieren, um relevante Kontextdateien und Checks gezielter zu priorisieren.
  - Leitplanke: Arbeitsmodi dürfen globale Source-of-Truth-, Write-Strategy-, Dokumentations-, TODO- und Post-Commit-Regeln nicht deaktivieren.

- [ ] Aussagekräftigere Summary-Kacheln für Moves prüfen.
  - Kontext: Der Moves-MVP zeigt aktuell einfache Counts für Moves, Trades, hinzugefügte Spieler und gehandelte Picks.
  - Ziel: Summary-Kacheln sollen später stärker auf echte Aktivität, Relevanz und nächste Entscheidungen fokussieren.
  - Potenzielle Kacheln: `Traded Picks`, `Next Draft`, `Most Active Team`, `Round 1 Moves`, `Upcoming`, `Moves`.

- [ ] Moves optisch mit Sleeper-Screenshots und eigener Zielvorstellung weiter verfeinern.
  - Kontext: Die Current-Season-Timeline mit Teams, Acquired-/Sent-Assets und Summary-Kacheln ist als funktionaler MVP umgesetzt.
  - Ziel: Nach weiterem Abgleich mit Sleeper-Trades und der gewünschten eigenen Darstellung UI/UX gezielt verbessern.

- [ ] Trade Simulator später in Moves integrieren.
  - Kontext: `src/app/features/trade/trade-simulator/trade-simulator.ts` bleibt vorerst eine eigene Route unter `/trade`.
  - Ziel: Später prüfen, ob und wie der Trade Simulator als Tool oder Subbereich unter Moves aufgeht.

## Erledigt / Archiv

- [x] `Transactions.json` im Frontend modellieren und als Moves-MVP anbinden.
  - Ergebnis: `transaction.models.ts` trennt den generierten Raw-Vertrag vom aufgelösten Frontend-Modell; `transaction.mapper.ts` ordnet Teams, Spieler und Draft-Picks participant-bezogen als acquired/sent zu.
  - Ergebnis: `DataApiService` lädt das Moves-Datenpaket, `DataService.getTransactions()` reicht ausschließlich gemappte `Transaction[]` durch und berücksichtigt den Transactions-Timestamp.
  - Ergebnis: `/moves` zeigt eine chronologische Current-Season-Timeline mit Summary-Kacheln, Teams sowie Player- und Pick-Assets.
  - Korrektur: Gleichrunde Picks werden über `OriginalOwnerRosterID` unterschieden; sichtbare Pick-Chips enthalten die Team-Abkürzung des Originalbesitzers und Angular-Track-Keys enthalten die vollständige Pick-Bewegung.
  - Hinweis: Pending Transactions bleiben ausgeschlossen, solange keine zuverlässige Pending-Quelle existiert.

- [x] Abgeschlossene Drafts der aktuellen Saison in `Drafts.json` und Current-Ansichten behalten.
  - Kontext: Ein abgeschlossener Draft gehört bis zum Wechsel von `League.Season` weiterhin zur aktiven Saison und wird für Overview, Current Drafts und vollständiges Draft Capital benötigt.
  - Ergebnis: `Drafts.json` enthält alle Drafts aus `LeagueYear` unabhängig vom Status und zusätzlich je Draft-Typ die konfigurierte Anzahl nicht abgeschlossener Drafts. Abgeschlossene aktuelle Picks bleiben in den Team-DraftPicks; `Best Open Pick` filtert weiterhin separat nach Verfügbarkeit.
  - Ergebnis: Nach einem abgeschlossenen aktuellen Draft und vor Terminierung des nächsten offenen Drafts bleibt die Liga in `Draft-Season / Between Drafts`. Current, Future und Past werden über explizite Saisonvergleiche getrennt.
  - Validierung: 2026 Rookie bleibt abgeschlossen in Current, 2026 Free Agent bleibt offen, Rookie reicht offen bis 2029 und Free Agent bis 2028; die Oberfläche und generierten Daten wurden nach dem Lauf geprüft.

- [x] Draft-Startzeit aus Sleeper prüfen und in `Drafts.json` übernehmen.
  - Ergebnis: `Drafts.json` bekommt für aktuelle Sleeper-Drafts `SleeperStartTime` aus `start_time` und `DraftStartTimeUtc` als UTC-ISO-Wert. `League.Phase = "Pre Draft"` nutzt diese generierte Startzeit jetzt datengetrieben.

- [x] Draft-Pick-Trigger-Darstellung weiter vereinheitlichen.
  - Kontext: Current-Pick-Chip und Future-Round-Pill duplizierten Button-, traded-dot- und Popover-Trigger-Logik.
  - Ergebnis: `DraftPickTriggerComponent` kapselt die gemeinsame Trigger-Mechanik und bietet Varianten für `chip` und `round-pill`. `CurrentDraftPickChipComponent` bleibt als Wrapper für bestehende Current/Past-Views erhalten; Future-Round-Pills nutzen den Trigger direkt. Die Overview-Kachel bleibt wegen ihrer eigenständigen Card-Darstellung in `DraftPickCardComponent`.

- [x] Draft-ViewModel-Service für die Drafts-Route ergänzen.
  - Kontext: `DraftsPageComponent` sollte ViewModel-Erzeugung nicht direkt über Mapper-Funktionen orchestrieren.
  - Ergebnis: `DraftsViewModelService` kapselt die Drafts-ViewModel-Erzeugung und delegiert an die reinen Mapper.

- [x] Current-Draft-Team- und Listen-Gruppierungen ins zentrale Drafts-ViewModel ziehen.
  - Kontext: Teams- und Listen-Sichten leiteten Gruppierungen und Sortierungen zunächst komponentennah aus `draftVm.rounds` ab.
  - Ergebnis: `DraftViewModel` enthält `orderedPicks` und `currentOwnerPickGroups`; die Komponenten rendern diese Felder direkt.

- [x] Draft-Pick-Overview-Kachel als wiederverwendbare UI-Komponente extrahieren.
  - Kontext: Die Overview-Kachel enthielt Markup, Position-Farben, Popover-Trigger und ein nachträgliches DOM-Rendering des Kontextlabels direkt in der Overview-View.
  - Ergebnis: `DraftPickCardComponent` kapselt die Overview-Pick-Kachel inklusive Popover-Trigger und Kontextlabel; die Overview-View rendert nur noch das Board-Grid.

- [x] Draft-Round-Chip-Farblogik aus Overview und Drafts in eine gemeinsame Frontend-Utility auslagern.
  - Kontext: Overview und Drafts berechneten Draft-Round-Farben lokal und leicht unterschiedlich.
  - Ergebnis: `getDraftRoundColor` und `getDraftStatusClass` liegen in `src/app/shared/utils/draft-ui.util.ts`; Overview und Drafts verwenden dieselbe Rundenskala.

- [x] Gemeinsames Draft-Pick-Popover neutral benennen und verschieben.
  - Kontext: Das frühere `CurrentDraftPickPopoverComponent` wurde von Current/Past Drafts und Future Drafts genutzt, lag aber technisch unter dem Current-Drafts-Pfad.
  - Ergebnis: `DraftPickPopoverComponent` liegt unter `src/app/features/drafts/components/draft-pick-popover/**` und wird von Current/Past/Future-Draft-Triggern verwendet.

- [x] Draft-Card-Header und Metrikzeile zwischen Current/Past und Future vereinheitlichen.
  - Kontext: Current/Past Drafts nutzten `DraftShellComponent`, Future Drafts renderten `mat-card` inklusive Header und Metrikzeile direkt.
  - Ergebnis: Future Drafts rendern jetzt ebenfalls `DraftShellComponent`; Header und Metrikzeile kommen zentral aus der Shell.

- [x] Current-Draft-Pick-Popover und Player-Mini-Card als gemeinsame UI-Komponente prüfen.
  - Kontext: `CurrentDraftPickChipComponent`, `CurrentDraftOverviewViewComponent` und Future-Draft-Round-Pills nutzten ähnliche Popover-Inhalte für Pick, Overall, Player, Owner, Original Owner und Traded Pick.
  - Ergebnis: Der gemeinsame Popover-Content liegt inzwischen in `DraftPickPopoverComponent` und unterstützt vollständige Current/Past-Picks sowie kompakte Future-Picks. Die kompakte Trigger-Mechanik wurde später zusätzlich in `DraftPickTriggerComponent` zentralisiert.

- [x] Unbenutzte Hilfslogik im Drafts-Feature bereinigen.
  - Kontext: `CurrentDraftPickComponent.statusLabel` wurde nicht im Template verwendet.
  - Ergebnis: Der ungenutzte Getter wurde beim Umstellen auf das gemeinsame Draft-Pick-Popover entfernt.

- [x] Past Drafts im Frontend auf Basis von `PastSeasonsIndex.json` ergänzen.
  - Kontext: `PastSeasonsIndex.json` macht verfügbare historische Season-Ressourcen auffindbar.
  - Ergebnis: `/drafts` hat einen dritten Reiter `Past`, lädt verfügbare Draft-Seasons aus `PastSeasonsIndex.json`, bietet eine Season-Auswahl und rendert historische Draft-Cards analog zu Current Drafts mit Overview, Teams und List.
  - Hinweis: Historische Draft-Dateien bleiben getrennt von `Drafts.json` und werden nicht als aktuelle Team-Assets interpretiert.

- [x] Drafts und Moves als getrennte Routen vorbereiten.
  - Kontext: Der gemeinsame Bereich `/league-activity` wurde durch getrennte sichtbare Feature-Routen ersetzt.
  - Ergebnis: Drafts liegen als eigene Route `/drafts` unter `src/app/features/drafts`; Moves nutzt weiterhin `LeagueActivityComponent` als technische Komponente unter `/moves`; `/league-activity` leitet auf `/moves` weiter.
  - Validierung: Tests nach Merge erfolgreich.


- [x] Legacy-Kompatibilitäts-Re-Exports entfernen.
  - Kontext: Nach dem Angular-Struktur-Refactor lagen die gerouteten Feature-Seiten unter `src/app/features/**`; alte Pfade waren temporär als Re-Export-Wrapper erhalten.
  - Ergebnis: Die alten Wrapper-Dateien `src/app/overview/overview.ts`, `src/app/team-list/team-list.ts`, `src/app/players-page/players-page.ts`, `src/app/trade-simulator/trade-simulator.ts`, `src/app/league-activity/league-activity.ts`, `src/app/about/about.ts`, `src/app/player-list/player-list.ts` und `src/app/player-detail-dialog/player-detail-dialog.ts` wurden nach Build-/Testbestätigung und Repo-Suche ohne produktive Referenzen entfernt.

- [x] Alte Komponenten-Specs aus den früheren Root-Locations entfernen.
  - Kontext: Nach dem Angular-Struktur-Refactor lagen noch alte `.spec.ts`-Dateien in früheren Root-Locations und importierten lokale Wrapper, die nicht mehr produktiv genutzt wurden.
  - Ergebnis: Alte Specs für Team List, About, Overview, Players Page, Trade Simulator, Player List und Player Detail Dialog wurden entfernt.

- [x] Angular-Feature-Struktur vorbereiten und geroutete Seiten verschieben.
  - Kontext: Geroutete Angular-Seiten sollten von wiederverwendbaren UI-Komponenten getrennt werden.
  - Ergebnis: Routen zeigen auf `src/app/features/**`; `PlayerList` und `PlayerDetailDialog` liegen unter `src/app/shared/components/**`; alte Compatibility-Re-Export-Wrapper wurden nach erfolgreicher Stabilisierung entfernt.
  - Validierung: Build-Workflow und manueller UI-Durchklick waren erfolgreich.

- [x] League Activity MVP für Drafts & Moves im Frontend anlegen.
  - Kontext: Der bisher deaktivierte Navigationseintrag `Drafts & Moves` sollte aktiviert werden, aber die technische Struktur sollte einen stabileren Namen bekommen.
  - Ergebnis: Route `/league-activity`, `LeagueActivityComponent` und Navigationseintrag wurden angelegt. Der MVP zeigte current/upcoming/live Drafts aus `Drafts.json` als Draft-Cards mit Runden und Pick-Zeilen; Moves blieb Platzhalter bis `Transactions.json` im Frontend modelliert ist.
  - Hinweis: Diese Architektur wurde später durch getrennte `/drafts`- und `/moves`-Routen abgelöst.

- [x] Completed-Draft-Historie separat von `Drafts.json` aufbauen.
  - Kontext: Der ursprüngliche Vertrag hielt abgeschlossene Drafts vollständig aus `Drafts.json` heraus, damit historische Picks nicht als aktuelle Team-Assets erschienen.
  - Ergebnis: `DraftHistoryUtils.psm1` erzeugt historische Draft-Dateien unter `public/data/past_seasons/Drafts/Drafts_<season>.json`; der bestehende wöchentliche/manuelle `RequestDrafts.ps1`-Flow aktualisiert Current-Drafts und Completed-History zusammen.
  - Hinweis: Dieser Vertrag wurde durch ADR-021 für abgeschlossene Drafts der aktuellen `LeagueYear` teilweise abgelöst. Ältere abgeschlossene Saisons bleiben weiterhin ausschließlich historisch; abgeschlossene Drafts der aktuellen Saison bleiben zusätzlich in `Drafts.json`.

- [x] `CHAT_START.md` als Projektquelle und im Repository-Root hinterlegen.
  - Kontext: Die Datei liegt sowohl hier im ChatGPT-Projekt als Quelle als auch im Repository-Root.
  - Ziel: Neue Chats sollen zuerst auf `AGENTS.md` und danach auf die `.ai-context`-Lesereihenfolge verweisen.

Erledigte Einträge hier nur ablegen, wenn die Historie nützlich ist. Ansonsten können erledigte Einträge aus der offenen Liste entfernt werden.
