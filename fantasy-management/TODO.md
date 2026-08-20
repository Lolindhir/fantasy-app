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
  - Verbindliche Trennung: Positionsspezifische Module liefern Signale und Vergleichslogik; Daily Monitoring erkennt materielle Änderungen; endgültige Start/Sit-, Add/Drop-, Waiver- und Roster-Entscheidungen gehören in einen übergeordneten Entscheidungsworkflow.
  - Referenz: `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`.

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
  - Aktualisieren: aktuelle League-/Roster-/Transaction-Daten sowie vorhandene FantasyPros-, FantasyCalc-, Fantasy-Football-Calculator-, FFToday-Projections-, CBS-Sports-Projections- und Sleeper-Trending-Snapshots.
  - Bestehende Fetcher weiterverwenden und nur orchestral zusammenführen; keine doppelte Abruflogik in ChatGPT-Prompts oder Analysejobs.
  - Erledigt: Die externen Morgenquellen bleiben fehlerisolierte Einzel-Fetcher; jeder erfolgreiche relevante Source-/Success-Heartbeat-Commit kann unmittelbar materialisieren. Der 06:45-Europe/Berlin-Lauf ist nur zusätzlicher Catch-up und keine Voraussetzung für den 07:00-Monitoringlauf.
  - Output weiterhin offen: nachvollziehbarer Quellenstand mit erfolgreichem oder kontrolliert fehlgeschlagenem Refresh je Datenquelle.

- [ ] Automatisiertes Einlesen ausgewählter Fantasy-Artikel als spätere Source-Pipeline prüfen.
  - Geeignete Publisher, Feeds oder wiederkehrende Artikelserien identifizieren, bei denen neue oder aktualisierte Beiträge zuverlässig erkannt und eingelesen werden können.
  - Vorhandenes Living-Article-Modell wiederverwenden: Source Identity, immutable Snapshots, stabile Claim-IDs sowie `new`/`repeated`/`changed`/`retracted`-Deltas.
  - Automatische Verarbeitung darf Quellenmaterial und strukturierte Claims vorbereiten, aber weder einen Artikel als unabhängige Mehrfachbestätigung doppelt zählen noch daraus autonom Roster-, Draft-, Trade-, Add-/Drop- oder andere Fantasy-Entscheidungen kanonisieren.
  - Copyright-, Zugriff-, robots-/Terms-, Provenienz- und Raw-Capture-Grenzen pro Quelle vor einer Automatisierung prüfen; vollständigen Webseitentext nicht pauschal archivieren.
  - Ziel: relevante externe Artikel künftig ohne manuellen Chat-Paste als aktuelle Research-/Monitoring-Evidenz verfügbar machen, mit denselben Materialitäts- und Human-Approval-Leitplanken wie bei nutzerbereitgestellten Artikeln.
  - Referenz: `fantasy-management/_ai/ARTICLE_SOURCE_MODEL.md`.

- [ ] Ranking- und Signal-Refreshes kurz vor dem geplanten Monitoring-Lauf orchestrieren.
  - Zielreihenfolge: aktuelle veröffentlichte App-Daten als read-only Inputs → externe Rankings → Sleeper Trending und weitere Signale → Derived Player-/Ownership-Datasets → Monitoring.
  - Ranking- und Signal-Läufe sollen mit ausreichendem Sicherheitsabstand vor dem Monitoring enden, damit der Monitoring-Lauf auf den neuesten erfolgreichen Datenständen aufsetzt.
  - Quellen bleiben fehlerisoliert; ein Ausfall darf keine teilweise Quelle veröffentlichen und soll den letzten guten Stand erhalten.
  - Das implementierte Freshness-Gate entscheidet vor Monitoring, ob ein fehlender oder veralteter überwachter Fantasy-Operations-Eingang den Lauf einschränkt oder nur kennzeichnet.
  - Aktive FM-Morgenstaffelung für den 07:00-Europe/Berlin-Monitoring-Lauf: FantasyPros 05:20 → FantasyCalc 05:32 → FFC ADP 05:44 → FFToday 05:56 → CBS Sports 06:08 → Sleeper Trending 06:20 → optionaler Operations-Catch-up 06:45.
  - App-Refreshes bleiben davon unabhängig: Players läuft weiterhin nach seinem App-Schedule einschließlich 05:05, League weiterhin alle zehn Minuten; beide sind read-only Inputs und keine FM-Freshness-Heartbeat-Quellen.
  - Jeder erfolgreiche relevante Source-/Success-Heartbeat-Commit darf unabhängig von der Uhrzeit unmittelbar den Operations-Materializer anstoßen; die frühere 05:00-06:45-Batching-Ausnahme ist entfernt.
  - Gate und eigentlicher Materialize-Job bleiben getrennt. Push-getriggerte Materialisierungen dürfen ältere Push-Materialisierungen superseden; der 06:45-Schedule-Catch-up darf einen bereits laufenden Source-Push-Materializer nicht abbrechen.
  - Der 07:00-Consumer bewertet ausschließlich den tatsächlich veröffentlichten kanonischen Operations-State und `source-freshness.json`; aus „nach 06:45“ wird keine Readiness abgeleitet.
  - Die Management-Zeitfenster werden DST-sicher auf Europe/Berlin ausgerichtet; bestehende zusätzliche App-Refreshes bleiben davon unabhängig bestehen.
  - Noch offen: reale Laufzeiten und Queue-Verhalten über mehrere Morgenzyklen beobachten und nur bei Bedarf weitere Scheduling-Abstände kalibrieren.

- [ ] Konkurrierende Generated-Data-Pushes auf `main` robust behandeln.
  - Problem: `APP • Data • League` kann alle zehn Minuten schreiben, während unabhängige APP- und FM-Quellen ebenfalls von eigenen Checkouts nach `main` pushen; zeitliche Staffelung reduziert, beseitigt aber keine Push-Races.
  - Ziel: Für alle schreibenden Generated-Data-Workflows einen gemeinsamen, idempotenten Retry-/Rebase-/Rebuild- oder Serialisierungsmechanismus definieren, sodass kein erfolgreicher Quelllauf an einem inzwischen veralteten Branch-Head scheitert und keine fremden Änderungen überschrieben werden.
  - Referenz: `FM • Materialize • Operations Inputs` behandelt Push-Races bereits mit Fetch/Reset/Rebuild und bis zu drei Versuchen; prüfen, welche Teile davon in eine gemeinsame Write-Strategie übernommen werden sollen.
  - Leitplanke: Cross-Workflow-Concurrency darf unabhängige Quellen nicht unnötig blockieren und muss No-op-Läufe sowie den jeweils letzten guten Source-State erhalten.

- [ ] Kompaktes Managed-Roster-Dataset materialisieren.
  - Dynamisch die deduplizierte Union aus `Roster`, `Reserve` und `Taxi` des `managed_team` auflösen.
  - Pro Spieler das zentrale Player-Signal-Dataset mit Salary, Projected Salary, aktuellem Rosterbereich und ligaformatbezogenen Strukturinformationen verbinden.
  - Output soll fehlende oder unvollständige Signale ausdrücklich markieren und keine Empfehlung vorwegnehmen.

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

- [ ] Konkrete GitHub-Actions-Orchestrierung für die Datenpipelines weiterentwickeln und Änderungen separat freigeben.
  - Für weitere Pipelines nach stabilen Skripten, Contracts und Branch-Tests festlegen, welche täglich, wöchentlich, ereignisgesteuert oder manuell laufen.
  - Die Morning-Source-/Materialization-Orchestrierung ist freigegeben und produktiv umgesetzt; weitere GitHub-Actions-Änderungen bleiben an die ausdrückliche Freigabe des jeweiligen Umfangs gebunden.
  - No-op-Läufe sollen keine unnötigen Daten- oder Commit-Änderungen erzeugen; echte Dataset-Änderungen müssen nachvollziehbar und atomar veröffentlicht werden.

### Monitoring

- [ ] Produktive Free-Agent-Movement-Discovery anhand realer Läufe weiter kalibrieren.
  - Kalibrierung vom 18.08.2026: Die bis dahin breite `tier_change`-Materialität wurde nach Quelle zerlegt. FantasyCalc-`maybeTier` war unbeabsichtigt wie der FantasyPros-ECR-Tier behandelt worden und erzeugte den Großteil der harten Tier-Signale.
  - Umgesetzt: `tier_change` ist nur noch für die explizit autoritative Tier-Quelle `fantasypros-dynasty-superflex-ppr` hart materiell; FantasyCalc-Tier bleibt Provider-Kontext. FantasyCalc erhält stattdessen eigene quantitative Schwellen: `|Δ Perzentil| >= 10` medium / `>= 15` high sowie kombinierte Raw-Value-Schwellen `>= 250 UND >= 20 %` medium / `>= 500 UND >= 30 %` high.
  - Umgesetzt: 1/3/7/14/30-Tage-Fenster werden am Evaluationstag verankert und verwenden je Quelle den letzten erfolgreichen Snapshot am oder vor dem Cutoff. Erfolgreicher Refresh/Freshness und letzter Inhaltsänderungs-Snapshot bleiben getrennte Konzepte.
  - Branch-/CI-Nachmessung gegen 1.175 tatsächliche Fantasy Free Agents: 289 aktuelle Discoveries statt der zuvor tierverzerrten breiteren Population; K 18, QB 48, RB 67, TE 56, WR 100; 60 high und 229 medium. `dynasty_market` liegt bei 204 Discoveries, `redraft_adp` bei 5 und `season_projection` bei 7.
  - FantasyCalc liefert 19 eigenständige quantitative Discoveries; 11 davon haben kein anderes numerisches hartes Signal, 13 liegen nahe oder oberhalb der aktuellen ligaeigenen Roster-/Replacement-Grenze und 5 erreichen ein High-Band. Alle 225 verbliebenen `tier_change`-Threshold-Records stammen ausschließlich von FantasyPros.
  - Mehrfenster bleiben ausdrücklich erhalten: Bei 179 numerisch materiellen Discoveries lag das früheste sichtbare Fenster nur 4-mal bei 1d, 6-mal bei 3d, 29-mal bei 7d, 100-mal bei 14d und 40-mal bei 30d. Slow Riser/Faller würden durch einen Vortagesvergleich massiv untererfasst.
  - Noch offen: dieselbe Kalibrierung erneut durchführen, sobald Redraft-ADP- und Season-Projection-Historien belastbare 14-/30-Tage-Abdeckung besitzen; zusätzlich Event-Volumen und Replacement-Relevanz über mehrere echte Refresh-Tage beobachten, bevor weitere Schwellen angepasst werden.
  - Kanonischer Materialitätsvertrag: `fantasy-management/_ai/FREE_AGENT_MOVEMENT_MATERIALITY.md`.
  - Ziel: Daily Monitoring erhält eine kleine, entscheidungsrelevante Research-Menge, ohne echte Under-the-Radar-Bewegungen in der kleinen Liga zu verlieren.

- [ ] Daily Monitoring Workflow positionsübergreifend vollständig konsolidieren und operationalisieren.
  - Zweck: ausschließlich materielle Veränderungen erkennen, Research priorisieren und die betroffene spätere Entscheidungsklasse benennen; keine finalen Start/Sit-, Add/Drop-, Waiver- oder Trade-Entscheidungen im Monitoring selbst.
  - Populationen: vollständiger Managed Roster; relevante Fantasy Free Agents; gegnerische Fantasy-Roster; ligaweite Ownership-/Transactions; NFL-Team-/Backfield-/Positionsgruppen-Kontext, wenn eine gemeinsame Ursache mehrere Spieler betrifft.
  - Signale je nach Position: Injury/Availability, Rolle/Opportunity, Usage, Markt, ADP, Projections, NFL-Team/Transactions, Fantasy-Ownership, externe Activity sowie positionsspezifische Signale.
  - Materialität: keine Zahlenrauschen- oder No-op-Meldungen; neue Baselines bleiben still; qualitative Live-Recherche nur bei fehlenden Daten, konkreten Änderungstriggern oder entscheidungsrelevanter Uncertainty.
  - Zielarchitektur: Free-Agent-Discovery, Movement-State und Event-Priorisierung laufen für QB/RB/WR/TE/K gemeinsam. Die bereits implementierte Kicker-Beobachtung liefert weiterhin nutzbare positionsspezifische Signale, ist aber keine dauerhafte separate Discovery- oder Event-Pipeline.
  - Erledigt: `free-agent-movement-signals.json` ist die breite aktuelle Zustands-/Detailansicht; `free-agent-movement-events.json` dedupliziert sie gegen den vorherigen guten Movement-State und liefert nur `new`, `changed`, `structural_change` oder `resolved`; der geplante Monitoring-Prompt liest die Event-Schicht primär und den Movement-State nur für Details.
  - Erledigt: `source-freshness.json` ist der vorgeschaltete Readiness-Contract; `block`, `proceed_degraded` und `no_event_conclusion_allowed` begrenzen die Interpretation unabhängig von Uhrzeit oder erwartetem Materializer-Zeitpunkt.
  - Der geplante Task bleibt in seinem zuletzt vorgefundenen deaktivierten Zustand; die technische Prompt-Migration auf die neue Event-/State-Trennung ist erfolgt.
  - Noch offen: Gegner-/Liga-Ownership-Monitoring; NFL-Team-/Positionsgruppen-Events; einheitliche Event-Bündelung mit Managed-Roster-Events; gezielte Folgeanalyse nach Monitoring-Event.
  - Referenz: `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`.

- [ ] Monitoring für die Kader aller gegnerischen Fantasy-Teams aufbauen.
  - Bevorzugt auf dem materialisierten Liga- und Gegner-Roster-Dataset aufbauen.
  - Beobachten: zentrale Verletzungen, Rollenaufstiege und -verluste, Markt- und ADP-Bewegungen sowie Veränderungen der Rosterstruktur.
  - Ziel: Keine allgemeine News-Flut, sondern nur für Liga-, Konkurrenz- und Trade-Entscheidungen relevante Veränderungen.

- [ ] Monitoring für alle relevanten Fantasy Free Agents aufbauen.
  - Kandidaten und Ownership aus dem vollständigen materialisierten Free-Agent-Dataset für QB, RB, WR, TE und K übernehmen.
  - `free-agent-movement-events.json` ist die primäre tägliche Trigger-/Priorisierungsschicht; `free-agent-movement-signals.json` bleibt die vollständige deterministische Zustands- und Detailansicht für die betroffenen Spieler.
  - Beobachten: neue Chancen durch Verletzungen oder Transaktionen, Usage-Sprünge, Rollenwechsel, Markt-, Ranking-, ADP- und Projection-Bewegungen sowie auffällige Add-/Drop-Trends.
  - Ziel: Neue oder deutlich aufgewertete Kandidaten automatisch zur Prüfung beziehungsweise zum Free-Agent-Board zuführen, ohne fortbestehende historische Movement-Zustände täglich erneut zu melden.
  - Leitplanke: Kicker werden in Discovery und Events nicht gesondert behandelt. Positionsspezifische Mathematik und Quellen bleiben möglich, laufen aber innerhalb derselben Population-, Delta-, Materialitäts- und Priorisierungsarchitektur.

- [ ] Monitoring auf NFL-Team-, Backfield- und Positionsgruppenebene ergänzen.
  - Kontext: Eine Verletzung, Verpflichtung, Entlassung oder Depth-Chart-Verschiebung kann mehrere Spieler gleichzeitig verändern.
  - Ziel: Gemeinsame Ursachen einmal erkennen und anschließend nur die betroffenen vorbereiteten Spieler- und Roster-Datensätze gezielt neu bewerten.

- [ ] Ligaweite Transaktions- und Ownership-Veränderungen überwachen.
  - Beobachten: Adds, Drops, Trades, Taxi-/Reserve-Bewegungen und Veränderungen des Draftkapitals.
  - Ziel: Betroffene Materialisierungen aktualisieren und Auswirkungen auf Free-Agent-Verfügbarkeit, Positionsknappheit, Gegnerprofile und potenzielle Trade-Partner ableiten lassen.
  - Positionsübergreifende Grenze: Availability-Änderungen werden für alle Positionen einschließlich K durch dieselbe Ownership-Schicht gemeldet; positionsspezifische Analyseprofile erfinden dafür keine parallele Liga-Transaction-Logik.

### Automatisierte Analysen und Entscheidungsprozesse

Diese Prozesse sollen vorrangig vorbereitete Derived Datasets lesen. Gemeinsame Rohquellen werden nur dann erneut abgerufen, wenn ein benötigtes Signal fehlt, zu alt ist oder eine qualitative Verifikation erforderlich ist.

- [ ] Wöchentliche Roster-Prüfung für das verwaltete Team entwickeln.
  - Eingabe: materialisiertes Managed-Roster-Dataset sowie relevante Entscheidungen und aktuelle League-Phase.
  - Prüfen: Rollen, Verletzungen, Usage, Marktwert, ADP, Alter, Salary/Projected Salary, Cap-Risiko, Roster-Funktion und Ersatzniveau.
  - Output: aktualisierte Kategorien und konkrete Aktionsliste für Hold, Shop, Package, Stash, Cut und Beobachtung.
  - Abgrenzung: strategischer und mittelfristiger als der Weekly Lineup + Waiver Workflow; nicht bloß Start/Sit für die nächste Woche.

- [ ] Wöchentlichen Liga- und Gegner-Roster-Scan entwickeln.
  - Eingabe: materialisiertes Liga- und Gegner-Roster-Dataset.
  - Prüfen: Teamstärken, Schwächen, Positionsüberschüsse, Bedarf, Contender-/Rebuild-Fenster, Cap- und Draftkapital.
  - Output: priorisierte Trade-Partner, angreifbare Roster-Lücken und relevante Konkurrenzveränderungen.

- [ ] Free-Agent-Board regelmäßig vollständig neu aufbauen und klassifizieren.
  - Eingabe: vollständiges materialisiertes Free-Agent-Dataset.
  - Kandidaten nach Position, Rolle, kurzfristiger Nutzbarkeit, Upside, Marktwert, ADP, Salary und Ligaformat bewerten.
  - Output: Tiers, Draft-/Waiver-Priorität, früheste vertretbare Runde und klare Kategorien wie Soforthilfe, Handcuff, Upside-Stash oder Watchlist.
  - Abgrenzung: breiter Markt-/Talentüberblick; nicht identisch mit dem konkreten wöchentlichen Waiver-Move für die nächste Aufstellung.

- [ ] Weekly Lineup + Waiver Workflow entwickeln und später separat operationalisieren.
  - Zweck: für die konkrete NFL-Woche die beste legale Startaufstellung und nur die dafür beziehungsweise für klar positive Roster-Upgrades nötigen Waiver-/Add-/Drop-Moves gemeinsam bestimmen.
  - Inputs: aktueller Managed Roster, tatsächliche Fantasy-Free-Agent-Population, League-Scoring/Roster-Regeln, Schedule/Week, aktuelle Injury-/Availability-Daten, Usage/Opportunity, aktuelle Rankings/Projections und positionsspezifische Analysebausteine.
  - Reihenfolge: Availability/Bye klären → startbare Population bestimmen → Weekly Projection/Opportunity bewerten → beste legale Startaufstellung → Free-Agent-Upgrades prüfen → Drop Opportunity Cost bewerten → Waiver-/Add-/Drop-Empfehlungen → finale Starter/Bench- und Backup-Empfehlung.
  - Output: empfohlene Startaufstellung, zentrale Start/Sit-Entscheidungen, Waiver Adds mit zugehörigen Drops, Alternativen, Injury-/Bye-Risiken, Kicker Hold/Stream, Confidence und zeitkritische nächste Aktion.
  - Kicker-Sonderfall: bestehende Kicker-Streaming-Engine als Untermodul verwenden; Normalfall ein Kicker; stabilen Kicker behalten, wenn kein materieller Weekly-Vorteil existiert; bei klarem Vorteil streamen; Bye/Jobverlust/Injury über explizite Sonderpfade behandeln.
  - Zwei-Kicker-Ausnahme: nur wenn der übergeordnete Workflow feststellt, dass das Behalten eines längerfristig wertvollen Kickers die Opportunity Cost des zusätzlich belegten Bench-Slots übersteigt. Die Kicker-Engine allein darf diese Entscheidung nicht treffen.
  - Drop-Prinzip: Ein positionsspezifischer Upgrade-Score ist nie allein ausreichend; der Wert des Spielers, der für den Move weichen müsste, ist Teil der finalen Entscheidung.
  - Noch festzulegen: Hauptanalysezeitpunkt im Waiver-/Lineup-Fenster, Umgang mit Thursday-/Saturday-/International-Games, Late-Injury-/Late-Swap-Recheck, gewünschte Event-Trigger und Benachrichtigungsformat.
  - Eine automatische Orchestrierung oder Änderung an `.github/workflows/**` erst nach separater ausdrücklicher Freigabe.
  - Referenz: `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md` und für Kicker `fantasy-management/_ai/KICKER_STREAMING_WEEKLY_CONTEXT.md`.

- [ ] Ereignisgesteuerte Neubewertung nach materiellen Monitoring-Events entwickeln.
  - Beispiel: Eine Verletzung oder Rollenänderung aktualisiert zuerst die betroffenen Derived Datasets und stößt danach nur die betroffenen Roster-, Free-Agent-, Trade-, Weekly-Lineup- oder Board-Analysen erneut an.
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

- [ ] In-Season-Lineup- und Start/Sit-Analyse als Teil des Weekly Lineup + Waiver Workflows umsetzen.
  - Während der Saison aktuelle Matchups, Verletzungen, vorbereitete Usage-Trends, erwartete Rolle und Ligaformat einbeziehen.
  - Nicht als parallelen zweiten Lineup-Prozess neben `Weekly Lineup + Waiver` aufbauen.
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

- [x] Morning-Source-Refresh und Operations-Materialisierung unabhängig triggerbar orchestrieren.
  - Ergebnis: Erfolgreiche relevante Ranking-/Projection-/Activity- und Success-Heartbeat-Pushes materialisieren unabhängig von der Uhrzeit unmittelbar; die frühere Batching-Sonderregel von 05:00 bis 06:45 Europe/Berlin ist entfernt.
  - Ergebnis: League-, Players-, Timestamps- sowie Materializer-Code-/Config-/Schema-Änderungen bleiben sofortige Trigger.
  - Ergebnis: Der DST-sichere 06:45-Lauf bleibt als zusätzlicher Catch-up, ist aber keine Readiness-Voraussetzung und darf einen laufenden Source-getriggerten Materializer nicht abbrechen.
  - Ergebnis: Generated-Operations-only-Pushes und irrelevante Pushes werden im Resolver explizit abgewiesen; der Workflow selbst hört weiterhin nicht auf `fantasy-management/generated/operations/**`, wodurch kein rekursiver Materializer-Loop entsteht.
  - Ergebnis: PR-Kontext fordert keine Produktionsmaterialisierung; Source-Workflows mit PR-Validierung schreiben dort weiterhin keine Produktionsheartbeats.
  - Ergebnis: `source-freshness.json` bleibt die zentrale Sicherheitsinstanz für den 07:00-Consumer; aus Uhrzeit oder erwartetem 06:45-Abschluss wird keine Readiness abgeleitet.
  - Ergebnis: Die Triggerentscheidung liegt testbar in `resolve_fantasy_operations_materialization_trigger.py`; Morning-/Outside-Morning-Source-Push, Heartbeat, League/Players/Timestamps, Generated-only, irrelevant, PR, DST-Catch-up und manueller Dispatch sind durch Regressionstests abgedeckt.
  - Ergebnis: Der bestehende dreifache Fetch/Reset/Rebuild-Push-Race-Pfad des Materializers bleibt unverändert und ist nun zusätzlich durch einen Workflow-Regressionstest geschützt.

- [x] Positionsübergreifende Free-Agent-Movement-Events materialisieren und produktiv veröffentlichen.
  - Ergebnis: `free-agent-movement-events.json` vergleicht den aktuellen `free-agent-movement-signals.json`-State mit dem vorherigen erfolgreichen Movement-State und emittiert nur `new`, `changed`, `structural_change` oder `resolved`.
  - Ergebnis: Eine erstmalige Baseline bleibt still; reiner Vergleichsfenster-Churn wird normalisiert; strukturelle Day-over-Day-Änderungen werden als Edge-Events behandelt und erzeugen am Folgetag kein künstliches Gegenereignis.
  - Ergebnis: Kicker laufen durch denselben QB/RB/WR/TE/K-Event-Contract; es gibt keine separate Kicker-Discovery- oder Event-Pipeline.
  - Ergebnis: `FM • Materialize • Operations Inputs` sichert den vorherigen Movement-State runner-temporär, baut und validiert die Event-Schicht direkt nach dem Movement-State und veröffentlicht sie atomar mit den übrigen Operations-Inputs.
  - Produktiver Nachweis vom 17.08.2026: 322 vorherige und 322 aktuelle Discoveries, `baseline_mode=comparison`, exakt 0 Events bei unverändertem Material-State; Quality `ok`; 34 fokussierte Operations-Tests erfolgreich.

- [x] Positionsübergreifende Free-Agent-Movement-Discovery materialisieren und produktiv veröffentlichen.
  - Ergebnis: `free-agent-movement-signals.json` scannt die vollständige tatsächliche Fantasy-Free-Agent-Population QB/RB/WR/TE/K; Kicker laufen durch dieselbe Discovery-, Materialitäts- und Priorisierungsarchitektur und verwenden lediglich positionsspezifische Quellen beziehungsweise Schwellen.
  - Ergebnis: historische 1/3/7/14/30-Tage-Vergleiche für ADP, Dynasty-Markt/Ranking/Tier und Season Projections, Cross-Signal-Confirmation/-Divergence, ligaangepasste positionsspezifische Replacement-Relevanz sowie Day-over-Day-Strukturänderungen werden deterministisch vorbereitet.
  - Ergebnis: vorhandene Schwellen aus `redraft-adp-movement`, `market-movement`, `season-projection-movement` und für Kicker `kicker-signal-movement` werden wiederverwendet; Sleeper Activity ist nur Bestätigungs-/Research-Kontext und keine Discovery-Voraussetzung.
  - Ergebnis: `FM • Materialize • Operations Inputs` baut und validiert den Contract nach `free-agent-signals.json`, sichert den vorherigen Free-Agent-State für strukturelle Deltas und veröffentlicht den Movement-Contract atomar mit den übrigen Operations-Inputs.
  - Erster produktiver Lauf: 1.201 tatsächliche Fantasy Free Agents bewertet, 322 Research-Discoveries erzeugt; Schema-/Ownership-/Positionsprüfung erfolgreich.

- [x] Kicker-spezifische Daily-Signale in das bestehende Monitoring integrieren.
  - Ergebnis: neues dynamisches Target Set `kicker-daily-monitoring` für den gehaltenen Kicker plus alle tatsächlichen Fantasy-Free-Agent-Kicker aus `kicker-streaming-inputs.json`.
  - Ergebnis: neues Profil `kicker-signal-movement` überwacht Kicker-Baseline, FFC-Kicker-ADP, FFToday/CBS-Projections, Projection Consensus, Sleeper Activity, Injury, nominal K1, NFL-Team und triggerbasierte aktuelle Job Security.
  - Ergebnis: die bestehende Baseline-Engine wird wiederverwendet; es existiert keine zweite Kicker-Scoring-Formel im Monitoring.
  - Ergebnis: Kicker Daily Monitoring ist in `entity-observation` verdrahtet und bleibt read-only; keine Weekly-Matchup-/Weather-Bewertung, keine automatische Start/Sit- oder Add/Drop-Entscheidung.
  - Leitplanke: finale Kicker-Hold-/Stream-Entscheidung gehört als Untermodul in `Weekly Lineup + Waiver`.

- [x] Kicker-Streaming-Analysebaustein fachlich und technisch vorbereiten.
  - Ergebnis: `kicker-streaming-inputs.json`, Baseline-/Decision-Engine, Weekly Research Plan, Venue-/Weather-/Job-/Injury-Freshness-Gates und held-Bye-Sonderfall sind implementiert.
  - Ergebnis: Provider-FPTS bleiben getrennt; CBS-/FFToday-Scoringunsicherheit wird transparent modelliert; Job Security ist Eligibility-Gate; Sleeper Activity bleibt Research-Tiebreaker.
  - Ergebnis: Es wird bewusst kein eigenständiger produktiver Kicker-Wochenworkflow mehr als Ziel verfolgt. Die Engine ist ein positionsspezifisches Untermodul des geplanten `Weekly Lineup + Waiver` Gesamtworkflows.

- [x] Zentrales materialisiertes Player-Signal-Dataset aufbauen und produktiv veröffentlichen.
  - Ergebnis: Ligaweite QB/RB/WR/TE/K-Population mit stabiler Spieler-ID, NFL-Team, League Ownership, Injury-/Depth-Chart-Signalen, Dynasty-Ranking, Marktwert, Redraft-ADP, FFToday-/CBS-Projections, Sleeper-Add-/Drop-Aktivität und Quellenständen.
  - Ergebnis: Listenlängenbereinigte Perzentile, Projection-Provider-Abweichung und Freshness werden deterministisch berechnet; Provider-Fantasy-Punkte bleiben getrennt und Top-N-Abwesenheit wird nicht als Nullaktivität behandelt.
  - Ergebnis: `FM • Materialize • Operations Inputs` baut `player-signals.json` nach der aktuellen External-Signal-Materialisierung und veröffentlicht alle geänderten Operations-Inputs über denselben Retry-/Rebuild-Pfad.
  - Leitplanke: Der Datensatz erzeugt keine Hold-, Shop-, Cut-, Add-, Start- oder Sit-Empfehlungen; historische Deltas/Tiers und bestätigte Alias-/Join-Verbesserungen bleiben bei Bedarf spätere Erweiterungen.

- [x] Vollständiges Fantasy-Free-Agent-Dataset materialisieren und produktiv veröffentlichen.
  - Ergebnis: `free-agent-signals.json` wird deterministisch aus dem zentralen Player-Signal-Dataset erzeugt und enthält ausschließlich `ownership.status == fantasy_free_agent`.
  - Ergebnis: Rankings, Marktwert, ADP, Projections, Activity, Injury, Rolle und Freshness bleiben pro Spieler vollständig erhalten; `Players.json -> IsFreeAgent` wird nicht als Fantasy-Verfügbarkeit verwendet.
  - Ergebnis: `FM • Materialize • Operations Inputs` baut und validiert den Free-Agent-Contract direkt nach `player-signals.json` und veröffentlicht ihn über denselben Retry-/Rebuild-Pfad.

- [x] Kicker-Streaming-Kandidatencontract materialisieren und produktiv veröffentlichen.
  - Ergebnis: `kicker-streaming-inputs.json` kombiniert den aktuell gehaltenen Mighty-Giants-Kicker mit allen tatsächlichen Fantasy-Free-Agent-Kickern.
  - Ergebnis: CBS-/FFToday-Projections, FFC-Kicker-ADP, Sleeper Activity, Injury und nominale Rolle stehen für die Analyseschicht in einem Contract bereit; Provider-FPTS bleiben getrennt.
  - Ergebnis: CBS 50+ und FFToday ohne Distanz-Buckets werden als transparente Liga-Scoring-Ranges statt als erfundene exakte Punkte behandelt.
  - Ergebnis: Der Contract wird nach `free-agent-signals.json` gebaut, validiert und produktiv veröffentlicht.

- [x] Vollständiges Roster-Monitoring für das verwaltete Team einrichten.
  - Ergebnis: Der dynamische Selector löst bei jedem Lauf die deduplizierte Union aus `Roster`, `Reserve` und `Taxi` des `managed_team` auf.
  - Ergebnis: Für jeden Spieler werden Verletzung und Verfügbarkeit, Rolle und Opportunity, Dynasty-Marktbewegung sowie Redraft-ADP als getrennte Profile beobachtet.
  - Ergebnis: Neue Spieler erhalten stille Baselines; unveränderte Läufe erzeugen keinen Event, keinen Commit und keine Benachrichtigung; materielle Änderungen können eine sichtbare ChatGPT-/Push-Benachrichtigung auslösen.
  - Leitplanke: Die technische Konfiguration wurde ohne Änderungen an GitHub Actions oder `public/data` umgesetzt.

Erledigte Einträge hier nur ablegen, wenn die Historie für spätere Management-Entscheidungen oder den Ausbau der Fantasy Operations nützlich ist.
