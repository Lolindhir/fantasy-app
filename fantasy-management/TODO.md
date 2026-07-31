# Fantasy Management TODO

Menschenlesbare Todo-Liste für den isolierten Fantasy-Management- und Fantasy-Operations-Kontext.

- App-, Frontend-, Generated-Data- und allgemeine technische Plattform-Todos bleiben in der Root-Datei `TODO.md`.
- Diese Datei sammelt offene Management-Aufgaben unabhängig davon, ob sie durch Skripte, GitHub Actions, ChatGPT-Aufgaben oder manuelle Analysen umgesetzt werden.
- Die Einordnung richtet sich nach Zweck und fachlichem Eigentümer, nicht allein nach dem technischen Implementierungsort.
- Dauerhafte Regeln, Quellenverträge und Architekturentscheidungen werden nach ihrer Klärung in die kanonische Dokumentation unter `fantasy-management/_ai` überführt.
- Todos werden auf Deutsch gepflegt; erledigte Einträge können entfernt oder unten archiviert werden.

## Offen

### Architektur und Planung

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

### Datenaufbereitung und GitHub-Workflows

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

### Monitoring

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

### Automatisierte Analysen und Entscheidungsprozesse

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

### Automatisierte Reviews und Auswertungen

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

### Analysevalidierung

- [ ] Salary-Effizienzthesen nach Abschluss der Saison 2026 verifizieren.
  - Baseline: `fantasy-management/analyses/2026/league-meta/salary-efficiency/2026-07-31-three-year-history-baseline.md` und die gleichnamige JSON-Datei.
  - Auslöser: Saison 2026 ist abgeschlossen und die vollständigen Saisonstatistiken wurden im Repository erzeugt.
  - Populationen vergleichen: alle gehaltenen Spieler; mindestens drei vollständige Statistikjahre; mindestens drei Statistikjahre plus `Year >= 5`; mindestens drei Statistikjahre und nicht mehr auf dem ursprünglichen Rookie-/Einstiegsvertrag.
  - Thesen prüfen: `SALARY-H01` bis `SALARY-H04` einschließlich Stabilität der Grenzwerte, Out-of-Sample-Kalibrierung, Fehlklassifikationen, Positionsunterschiede und Robustheit gegenüber Median, getrimmtem Mittelwert und Perzentilbändern.
  - Review ablegen unter `fantasy-management/analyses/2026/league-meta/salary-efficiency/reviews/2027-postseason-validation.md` und `.json`; die Baseline nicht überschreiben.
  - Ergebnisstatus je These: `supported`, `partially_supported`, `rejected` oder `inconclusive`; Evidenzstufe separat auf `one_season_validated` beziehungsweise später `multi_season_validated` setzen.
  - Danach ausdrücklich entscheiden, welche bestätigten Erkenntnisse nach `knowledge/`, welche methodischen Vorgaben nach Nutzerfreigabe in `FANTASY_MANAGEMENT_RULES.md` und welche bewusst gewählte Standardmethode gegebenenfalls nach `decisions/` überführt werden.
  - Leitplanke: Numerische Salary-Cut-offs bleiben datierte Analysewerte und werden nicht als zeitlose Regeln übernommen.

## Erledigt / Archiv

- [x] Vollständiges Roster-Monitoring für das verwaltete Team einrichten.
  - Ergebnis: Der dynamische Selector löst bei jedem Lauf die deduplizierte Union aus `Roster`, `Reserve` und `Taxi` des `managed_team` auf.
  - Ergebnis: Für jeden Spieler werden Verletzung und Verfügbarkeit, Rolle und Opportunity, Dynasty-Marktbewegung sowie Redraft-ADP als getrennte Profile beobachtet.
  - Ergebnis: Neue Spieler erhalten stille Baselines; unveränderte Läufe erzeugen keinen Event, keinen Commit und keine Benachrichtigung; materielle Änderungen können eine sichtbare ChatGPT-/Push-Benachrichtigung auslösen.
  - Leitplanke: Die technische Konfiguration wurde ohne Änderungen an GitHub Actions oder `public/data` umgesetzt.

Erledigte Einträge hier nur ablegen, wenn die Historie für spätere Management-Entscheidungen oder den Ausbau der Fantasy Operations nützlich ist.
