# TODO

Menschenlesbare Projekt-Todo-Liste für `Lolindhir/fantasy-app`.

Diese Datei ist bewusst von `.ai-context` getrennt.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- `TODO.md` sammelt offene Umsetzungs-, Aufräum- und Dokumentationsaufgaben.
- Todos werden hier auf Deutsch gepflegt, damit sie einfach per Hand angepasst werden können.
- Erledigte Einträge können entfernt oder unten im Archiv abgelegt werden.

## Offen

### Data Generation / Infrastruktur

- [ ] Laufzeit-Konfiguration aus `ConfigUtils.psm1` in Umgebungsvariablen bzw. Workflow-Konfiguration auslagern.
  - Kontext: `ConfigUtils.psm1` enthält aktuell technische Pfade und Request-Konfiguration sowie laufzeitabhängige Werte.
  - Ziel: Laufzeitabhängige Werte nicht direkt im Repository pflegen; `Get-Config` soll sie bevorzugt aus der Laufzeitumgebung lesen und nur noch technische Defaults enthalten.

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

- [ ] Player-Snapshot zum Saisonende für historische Moves erzeugen.
  - Kontext: Die Moves-Historie kann historische Transactions laden, löst Spieler aktuell aber weiterhin gegen das jeweils aktuelle `Players.json` auf.
  - Problem: Ausgeschiedene oder später aus dem aktuellen Playerbestand entfernte Spieler können dadurch in historischen Moves nur als `Player <ID>` erscheinen.
  - Ziel: Am Saisonende einen stabilen, saisonbezogenen Player-Snapshot mit mindestens Player-ID, Name, Position, NFL-Team und Bildreferenz erzeugen und über `PastSeasonsIndex.json` auffindbar machen.
  - Leitplanke: Der Snapshot muss generatorseitig entstehen; Angular darf ihn nur laden und zur historischen Anzeige verwenden.

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

### Fantasy Operations / Architektur und Planung

- [ ] Begriffe und Laufzeitebenen für Fantasy Operations verbindlich dokumentieren.
  - Daten- und GitHub-Workflows aktualisieren Quellen, normalisieren Daten und materialisieren deterministische Analysegrundlagen; sie treffen keine Fantasy-Empfehlungen.
  - Monitoring vergleicht vorbereitete Zustände mit dem letzten guten Material-State und erzeugt nur bei materiellen Änderungen oder relevanten Fehlern Ereignisse.
  - Automatisierte Analysen und Entscheidungsprozesse interpretieren aktuelle Daten vorausschauend für Roster-, Trade-, Draft-, Cap-, Free-Agent- oder Lineup-Entscheidungen.
  - Reviews und Auswertungen interpretieren abgeschlossene Zeiträume, Spiele, Drafts, Transaktionen oder Entscheidungen rückblickend.
  - GitHub Actions dienen nur als Orchestrierung; dauerhafte Logik, Verträge und Schwellen gehören in versionierte Skripte und Konfigurationen.

- [ ] Zielarchitektur und Ausbaureihenfolge der Fantasy Operations festlegen.
  - Für jeden Baustein definieren: Zweck, Trigger, Eingabedatensätze, Output-Vertrag, Freshness, Idempotenz, Write Scope, Fehlerverhalten und Benachrichtigung.
  - Reihenfolge: vorhandene Datenflüsse inventarisieren → gemeinsame Derived Contracts festlegen → Skripte lokal und auf Branches testen → Baselines erzeugen → kontrollierte Schreibtests → konkrete GitHub-Actions-Änderungen separat freigeben und aktivieren.
  - Leitplanke: Monitoring und Analysen sollen vorhandene vorbereitete Datensätze wiederverwenden, statt dieselben Rohquellen bei jedem Lauf erneut vollständig abzurufen.
  - Live-Recherche bleibt für fehlende Daten, qualitative Rollenprüfung, Verletzungsdetails und andere nicht zuverlässig materialisierbare Signale möglich.

### Fantasy Operations / Datenaufbereitung und GitHub-Workflows

- [ ] Bestehende Fetcher, Skripte, GitHub Actions und erzeugte Datensätze vollständig inventarisieren.
  - Erfassen: Quelle, Aktualisierungstakt, ausführendes Skript, GitHub-Workflow, Output-Pfade, Snapshot-Historie, Freshness-Regeln, Join-Schlüssel und bekannte Qualitätsgrenzen.
  - Ziel: Sichtbar machen, welche Grundlagen bereits regelmäßig erzeugt werden und welche Arbeit Monitoring oder Analysen derzeit noch selbst wiederholen.

- [ ] Gemeinsame Materialisierungs- und Dateiverträge für Fantasy Operations definieren.
  - Festlegen: Zielbereich im Repository, Schema-Versionierung, Provenance, `generated_at`, Quellenstände, Input-Fingerprints, Deltas, Qualitätsstatus und atomare Veröffentlichung.
  - Leitplanke: Materialisierte Dateien sind reproduzierbare Arbeitsdaten und keine dauerhafte Spieler- oder Empfehlungswahrheit.
  - Ziel: Monitoring, Reviews und Analysen greifen auf dieselben stabilen Contracts zu, statt eigene inkompatible Zwischenformate zu erzeugen.

- [ ] Regelmäßigen Source-Refresh als technische Datenpipeline konsolidieren.
  - Aktualisieren: aktuelle League-/Roster-/Transaction-Daten sowie vorhandene FantasyPros-, FantasyCalc- und Fantasy-Football-Calculator-Snapshots.
  - Bestehende Fetcher weiterverwenden und nur orchestral zusammenführen; keine doppelte Abruflogik in ChatGPT-Prompts oder Analysejobs.
  - Output: nachvollziehbarer Quellenstand mit erfolgreichem oder kontrolliert fehlgeschlagenem Refresh je Datenquelle.

- [ ] Zentrales materialisiertes Player-Signal-Dataset aufbauen.
  - Zusammenführen: stabile Spieler-ID, Position und NFL-Team, League Ownership, Verletzungsstatus, Rollen-/Usage-Signale, Dynasty-Ranking, Marktwert, Redraft-ADP und jeweilige Quellenstände.
  - Berechnen: listenlängenbereinigte Perzentile, Deltas zum vorherigen Snapshot, Tiers, Sample-Qualität, Quellenabweichungen, Freshness und fehlende Joins.
  - Keine Hold-, Shop-, Cut- oder Start/Sit-Empfehlungen in dieser Schicht erzeugen.
  - Ziel: zentrale wiederverwendbare Grundlage für Roster-Monitoring, Free-Agent-Board, Gegneranalyse und Reviews.

- [ ] Kompaktes Managed-Roster-Dataset materialisieren.
  - Dynamisch die deduplizierte Union aus `Roster`, `Reserve` und `Taxi` des `managed_team` auflösen.
  - Pro Spieler das zentrale Player-Signal-Dataset mit Salary, Projected Salary, aktuellem Rosterbereich und ligaformatbezogenen Strukturinformationen verbinden.
  - Output soll fehlende oder unvollständige Signale ausdrücklich markieren und keine Empfehlung vorwegnehmen.

- [ ] Vollständiges Free-Agent-Dataset materialisieren.
  - Ownership ausschließlich aus allen `Roster`-, `Reserve`- und `Taxi`-Listen in `League.json` ableiten.
  - Für alle unowned relevanten Spieler Rankings, Marktwert, ADP, Verletzung, Rolle, Usage, Salary und Veränderungen vorbereiten.
  - Ziel: Das spätere Free-Agent-Board klassifiziert einen bereits vollständigen Kandidatenbestand und muss die Population nicht bei jedem Lauf neu zusammensuchen.

- [ ] Liga- und Gegner-Roster-Dataset materialisieren.
  - Für jedes Fantasy-Team Rosterstruktur, Positionsverteilung, Alter, Salary/Cap, Draftkapital, Marktwertsignale, Verletzungen und aktuelle Rosterbereiche vorbereiten.
  - Deterministische Strukturkennzahlen wie Überbesetzung, dünne Positionen oder Konzentrationsrisiken dürfen berechnet werden; Trade-Empfehlungen bleiben der Analyseschicht vorbehalten.

- [ ] Wöchentliche Usage-Aggregation für die Saison vorbereiten.
  - Snaps, Routes, Targets, Carries, Red-Zone-/Goal-Line-Usage, Fantasy-Punkte und gleitende Vergleichsfenster skriptbasiert materialisieren.
  - Output soll Opportunity und Ergebnis trennen und sowohl Wochenwerte als auch Deltas gegenüber Vorwoche und Mehrwochen-Baseline enthalten.

- [ ] Datenqualitäts- und Freshness-Report für Fantasy Operations erzeugen.
  - Prüfen: fehlende Snapshots, veraltete Quellen, unerwartet kleine Feeds, Schemaänderungen, doppelte oder ungelöste Spieleridentitäten, fehlende Joins und inkonsistente Input-Fingerprints.
  - Fehler sollen nach Quelle und betroffenem Derived Dataset strukturiert vorliegen, damit Monitoring nicht aus unvollständigen Daten falsche Änderungen ableitet.
  - Ziel: Analysen können vorab erkennen, ob ihre vorbereitete Datenbasis vollständig, eingeschränkt oder nicht verwendbar ist.

- [ ] Konkrete GitHub-Actions-Orchestrierung für die Datenpipelines entwerfen und separat freigeben.
  - Erst nach stabilen Skripten, Contracts und lokalen beziehungsweise Branch-Tests festlegen, welche Pipeline täglich, wöchentlich, ereignisgesteuert oder manuell läuft.
  - GitHub-Actions-Dateien nur nach ausdrücklicher Freigabe des jeweiligen Workflow-Änderungsumfangs erstellen, ändern oder aktivieren.
  - No-op-Läufe sollen keine unnötigen Daten- oder Commit-Änderungen erzeugen; echte Dataset-Änderungen müssen nachvollziehbar und atomar veröffentlicht werden.

### Fantasy Operations / Monitoring

- [ ] Monitoring für die Kader aller gegnerischen Fantasy-Teams aufbauen.
  - Bevorzugt auf dem materialisierten Liga- und Gegner-Roster-Dataset aufbauen.
  - Beobachten: zentrale Verletzungen, Rollenaufstiege und -verluste, Markt- und ADP-Bewegungen sowie Veränderungen der Rosterstruktur.
  - Ziel: Keine allgemeine News-Flut, sondern nur für Liga-, Konkurrenz- und Trade-Entscheidungen relevante Veränderungen.

- [ ] Monitoring für alle relevanten Fantasy Free Agents aufbauen.
  - Kandidaten und Ownership aus dem vollständigen materialisierten Free-Agent-Dataset übernehmen.
  - Beobachten: neue Chancen durch Verletzungen oder Transaktionen, Usage-Sprünge, Rollenwechsel, Markt-, Ranking- und ADP-Anstiege sowie auffällige Add-/Drop-Trends.
  - Ziel: Neue oder deutlich aufgewertete Kandidaten automatisch zur Prüfung beziehungsweise zum Free-Agent-Board zuführen.

- [ ] Monitoring auf NFL-Team-, Backfield- und Positionsgruppenebene ergänzen.
  - Kontext: Eine Verletzung, Verpflichtung, Entlassung oder Depth-Chart-Verschiebung kann mehrere Spieler gleichzeitig verändern.
  - Ziel: Gemeinsame Ursachen einmal erkennen und anschließend nur die betroffenen vorbereiteten Spieler- und Roster-Datensätze gezielt neu bewerten.

- [ ] Ligaweite Transaktions- und Ownership-Veränderungen überwachen.
  - Beobachten: Adds, Drops, Trades, Taxi-/Reserve-Bewegungen und Veränderungen des Draftkapitals.
  - Ziel: Betroffene Materialisierungen aktualisieren und Auswirkungen auf Free-Agent-Verfügbarkeit, Positionsknappheit, Gegnerprofile und potenzielle Trade-Partner ableiten lassen.

### Fantasy Operations / Automatisierte Analysen und Entscheidungsprozesse

Diese Prozesse sollen vorrangig vorbereitete Derived Datasets lesen. Gemeinsame Rohquellen werden nur dann erneut abgerufen, wenn ein benötigtes Signal fehlt, zu alt ist oder eine qualitative Verifikation erforderlich ist.

- [ ] Wöchentliche Roster-Prüfung für das verwaltete Team entwickeln.
  - Eingabe: materialisiertes Managed-Roster-Dataset sowie relevante Entscheidungen und aktuelle League-Phase.
  - Prüfen: Rollen, Verletzungen, Usage, Marktwert, ADP, Alter, Salary/Projected Salary, Cap-Risiko, Roster-Funktion und Ersatzniveau.
  - Output: aktualisierte Kategorien und konkrete Aktionsliste für Hold, Shop, Package, Stash, Cut und Beobachtung.

- [ ] Wöchentlichen Liga- und Gegner-Roster-Scan entwickeln.
  - Eingabe: materialisiertes Liga- und Gegner-Roster-Dataset.
  - Prüfen: Teamstärken, Schwächen, Positionsüberschüsse, Bedarf, Contender-/Rebuild-Fenster, Cap- und Draftkapital.
  - Output: priorisierte Trade-Partner, angreifbare Roster-Lücken und relevante Konkurrenzveränderungen.

- [ ] Free-Agent-Board regelmäßig vollständig neu aufbauen und klassifizieren.
  - Eingabe: vollständiges materialisiertes Free-Agent-Dataset.
  - Kandidaten nach Position, Rolle, kurzfristiger Nutzbarkeit, Upside, Marktwert, ADP, Salary und Ligaformat bewerten.
  - Output: Tiers, Draft-/Waiver-Priorität, früheste vertretbare Runde und klare Kategorien wie Soforthilfe, Handcuff, Upside-Stash oder Watchlist.

- [ ] Ereignisgesteuerte Neubewertung nach materiellen Monitoring-Events entwickeln.
  - Beispiel: Eine Verletzung oder Rollenänderung aktualisiert zuerst die betroffenen Derived Datasets und stößt danach nur die betroffenen Roster-, Free-Agent-, Trade- und Board-Analysen erneut an.
  - Ziel: Monitoring nicht nur melden lassen, sondern Folgeanalysen gezielt, datenbasiert und idempotent auslösen.

- [ ] Wiederkehrende Trade-Chancen-Analyse entwickeln.
  - Eingaben: eigene Shop-/Package-Kandidaten, materialisierte Gegnerdaten, Marktwerte, Owner-Profile, Draftkapital und jüngste Transaktionen.
  - Output: realistische Trade-Ideen, sinnvolle Partner, Preisgrenzen und Verhandlungsansatz; keine automatischen Angebote oder Transaktionen.

- [ ] Phasenabhängige Draft-Vorbereitungsanalyse entwickeln.
  - Vor Rookie- und Free-Agent-Drafts Boards, Team Needs, verfügbares Kapital, Tier Breaks, Positionsknappheit und Trade-up/-down-Szenarien aktualisieren.
  - Ziel: kurz vor einem Draft eine aktuelle, ligaangepasste Entscheidungsgrundlage auf vorbereiteten Daten statt eines dauerhaft statischen Boards erzeugen.

- [ ] Cap-, Cut- und Deadline-Analyse entwickeln.
  - Vor relevanten Fristen Salary, Projected Salary, Cap Space, Cut-/Trade-Kandidaten und vorbereitete Ersatzoptionen prüfen.
  - Output: priorisierte Maßnahmen mit Frist, Auswirkung und Alternativen.

- [ ] In-Season-Lineup- und Start/Sit-Analyse prüfen.
  - Nur während der Saison aktuelle Matchups, Verletzungen, vorbereitete Usage-Trends, erwartete Rolle und Ligaformat einbeziehen.
  - Leitplanke: Offseason-Starter aus `League.json` nicht als Qualitäts- oder Rollenwahrheit behandeln.

### Fantasy Operations / Automatisierte Reviews und Auswertungen

- [ ] Wöchentliches Spieltagsreview für das verwaltete Team entwickeln.
  - Auf vorbereiteten Wochen-, Lineup- und Usage-Daten aufbauen.
  - Auswerten: Ergebnis, tatsächliche gegen optimale Aufstellung, liegengelassene Punkte, Start/Sit-Entscheidungen, Spielerentwicklung, Verletzungen und unmittelbare Folgemaßnahmen.
  - Ziel: Ergebnisglück von Prozessqualität trennen und konkrete Verbesserungen für die Folgewoche ableiten.

- [ ] Wöchentliches ligaweites Spieltagsreview entwickeln.
  - Auswerten: alle Matchups, höchste und niedrigste Scores, Effizienz, Formtrends, Power Shifts, Standings- und Playoff-Auswirkungen.
  - Ziel: Veränderungen der echten Konkurrenzlage und neue Trade- oder Roster-Chancen erkennen.

- [ ] Wöchentliche Player-Usage-Auswertung entwickeln.
  - Die materialisierte Usage-Aggregation interpretieren und Snaps, Routes, Targets, Carries, High-Value-Usage und Fantasy-Punkte gegenüberstellen.
  - Ziel: nachhaltige Rollenveränderungen von punktgetriebenem Zufall sowie Buy-Low-/Sell-High-Signale unterscheiden.

- [ ] Wöchentliches Review der Ligaaktivität entwickeln.
  - Vorbereitete Adds, Drops, Trades, Pick-Bewegungen und Ownership-Veränderungen zusammenfassen und bewerten.
  - Ziel: Marktverhalten der Liga, veränderte Teamstrategien und verpasste beziehungsweise neue Chancen sichtbar machen.

- [ ] Monatliches beziehungsweise phasenbezogenes Strategiereview entwickeln.
  - Prüfen: Contender-Fenster, Rosterqualität, Altersstruktur, Positionsrisiken, Cap, Draftkapital, Marktwertentwicklung und Liquidität.
  - Output: aktualisierte Saisonstrategie und priorisierte nächste Entscheidungen.

- [ ] Draft-Review nach jedem Rookie- und Free-Agent-Draft entwickeln.
  - Auswerten: eigener Prozess, Board-Abweichungen, Value, Positionsfit, Trades, verpasste Optionen und neue Rosterstruktur.
  - Später zusätzlich mittel- und langfristige Ergebnisbewertung der Picks vorsehen.

- [ ] Saisonabschlussreview entwickeln.
  - Auswerten: Teamleistung, Entscheidungen, Trades, Drafts, Free-Agent-Aktionen, Lineup-Prozess, Cap-Management und wichtigste Fehlannahmen.
  - Ziel: wiederverwendbare Erkenntnisse und konkrete Regel-, Quellen- oder Datenpipeline-Verbesserungen für die nächste Saison ableiten.

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

- [x] Vollständiges Roster-Monitoring für das verwaltete Team einrichten.
  - Ergebnis: Der dynamische Selector löst bei jedem Lauf die deduplizierte Union aus `Roster`, `Reserve` und `Taxi` des `managed_team` auf.
  - Ergebnis: Für jeden Spieler werden Verletzung und Verfügbarkeit, Rolle und Opportunity, Dynasty-Marktbewegung sowie Redraft-ADP als getrennte Profile beobachtet.
  - Ergebnis: Neue Spieler erhalten stille Baselines; unveränderte Läufe erzeugen keinen Event, keinen Commit und keine Benachrichtigung; materielle Änderungen können eine sichtbare ChatGPT-/Push-Benachrichtigung auslösen.
  - Leitplanke: Die technische Konfiguration wurde ohne Änderungen an GitHub Actions oder `public/data` umgesetzt.

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

- [x] `Players_Relevant.json`- und Chat-Export-Pfade nach `ConfigUtils.psm1` verlagern.
  - Kontext: `RequestLeague.ps1` baute den relevanten Spielerpfad und den Chat-Chunk-Zielordner ursprünglich lokal über `$config.DataDir`.
  - Ergebnis: `Get-Config` stellt `PlayersRelevantFile` und `PlayersRelevantChatDir` bereit; `RequestLeague.ps1` nutzt diese Config-Werte für `Players_Relevant.json` und den Chat-Export unter `public/data/chat/players-relevant`.

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