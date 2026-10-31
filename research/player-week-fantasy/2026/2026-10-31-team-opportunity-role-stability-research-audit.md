# PlayerWeekFantasy – Team-Opportunity und Rollenstabilität: historisches Research-Audit

**Archivdatum:** 31.10.2026 · **Originaluntersuchung:** 15.10.2026  
**Ergebnisstatus:** `inconclusive` für einen nachgewiesenen Mehrwert gegenüber V4-C. Die Relevanz von Snap-Rollen und Anomalien ist explorativ sichtbar; die geplante vollständige Modellierung ist **nicht umgesetzt**.  
**Lifecycle-Entscheidung:** #1025 wird auf Nutzerwunsch archiviert und als **not planned / paused** geschlossen, **nicht** als vollständig implementiert. Vor einer Wiederaufnahme ist eine neue ausdrückliche Entscheidung erforderlich.  
**Quellen:** [Original-Issue #1025](https://github.com/Lolindhir/fantasy-app/issues/1025); [PlayerWeekFantasy-Kontrakt](../../../.ai-context/manual/player-week-fantasy.yaml); [Sleeper-/Availability-Audit vom 31.10.2026](2026-10-31-sleeper-projections-availability-shadow-audit.md).

## Zusammenfassung und Datengrundlage

Die ursprüngliche Frage in #1025 **ist breiter als Sleeper**: Kann ein positionsübergreifendes, historisch aus kanonischen NFL-Fakten reproduzierbares Team-Opportunity- und Rollenmodell V4-C verbessern, ohne von einem kontinuierlichen Injury-/Availability-Feed abhängig zu sein?

Auslöser war der 2026er Fall Saquon Barkley: einzelne stark reduzierte Snap-Wochen könnten die bestehende Recent-Usage-Prognose verzerren, obwohl der Spieler bei späterer voller Einsatzfähigkeit wieder eine andere normale Rolle hat. **Aus Snap-Werten allein darf kein Verletzungsgrund oder medizinischer Status abgeleitet werden.**

**Datenquelle:** `data-source/nfl/snap-counts/<season>/<week>.json` mit `CanonicalPlayerID`, `GameID`, `Week`, `Team`, `Position`, `OffenseSnaps` und `OffensePct`. Zum ursprünglichen Audit am 15.10.2026:
- Verzeichnisse `snap-counts` 2013–2026, `player-stats` 1999–2026, `weekly-rosters` 2002–2026 vorhanden. **Existenz bedeutet nicht vollständige Qualitätsprüfung**.
- Alle 18 REG-Snap-Partitionen in **2024** und **2025** lesbar und im damaligen Stand `Finalized=true`: 2024 **25.398** Zeilen (6.468 positive Offense-Snap-Beobachtungen für QB/RB/WR/TE), 2025 **25.395** Zeilen (6.394 entsprechende Beobachtungen).
- 2026 W1–5 damals `Finalized=false`; Barkley nur ein illustrativer Anlass, **kein finaler Trainings-/Holdout-Test**. Für Kicker sind Offense-Snap-Anteile ungeeignet; Special-Teams-/FG-/PAT-Chancen gesondert untersuchen.
- Historische Snap-Records sind die **später beobachtete Wahrheit**, keine zulässigen Features derselben Week zur Pregame-Vorhersage.

## Ursprünglicher Rollen-Snap-Pilot (15.10.2026)

**Pilotpopulation:** QB/RB/WR/TE, nur Spiele mit `OffenseSnaps > 0`; pro `CanonicalPlayerID + Team + Position` innerhalb einer Saison; mindestens drei vorherige tatsächliche Einsätze. Verglichen wurden (A) Mittelwert und (B) Median der letzten drei `OffensePct`. Kein Modelltraining und kein Fantasy-Score-Backtest.

| Saison | Evaluierte Player-Games | Mittelwert-3 MAE (Prozentpunkte) | Median-3 MAE | Starke Drop-Anomalien | Recovery im nächsten Teamspiel | Kein Snap-Eintrag beim selben Team im nächsten Spiel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 | 4.715 | 12,06 | 12,33 | 79 | 17 | 34 |
| 2025 | 4.619 | 12,36 | 12,54 | 75 | 15 | 24 |
| **Zusammen** | **9.334** | **12,21** | **12,43** | **154** | **32** | **58** |

**Drop-Definition:** Voreinsatz-Median der letzten drei Spiele ≥55 %, Zielwoche ≤30 %, Abfall ≥35 Prozentpunkte. „Recovery“: Teilnahme im unmittelbar nächsten Teamspiel mit OffensePct ≥ `max(0,50, vorheriger Median − 0,15)`. Für 58 Fälle wurde beim gleichen Team kein nächster Snap-Beobachtungseintrag gefunden; nicht als dokumentierte Verletzung oder Inaktivität interpretieren.

**Erkenntnisse:**
- **32/154** Drop-Fälle (20,8 %) erfüllten im nächsten Teamspiel die enge Recovery-Definition; bei Fällen mit Snap-Beobachtung beim gleichen Team: **32/96** (33,3 %). Das ist keine Heilungs-/Injury-Wahrscheinlichkeit.
- Unter **3.491** stabilen Vergleichsfällen waren **2.788** im nächsten Teamspiel wieder auf hohem Snap-Niveau; unter **3.308** mit beobachteter nächster Teilnahme ergibt das **84,3 %**. Rollenstabilität hat somit deskriptiven Prognosewert, keine gesicherte Kausalerklärung.
- Ein **pauschaler Median statt Mittelwert** verschlechterte den MAE **in beiden** Jahren (siehe Tabelle). In einer kleinen *ex ante* definierten Anomalie-Teilgruppe verbesserte Median jedoch den Snap-Anteil-MAE: **2024 n=102: 24,88→21,82**, **2025 n=80: 21,66→20,46**, bei deutlich positivem Bias (~12,6/15,4 Prozentpunkte). **Keine produktionsreife Regel**.
- Beispiele für Rebound auf hohe Snaps: James Conner ARI W6/2024 28→84 %, Amon-Ra St. Brown DET W13/2025 6→92 %, Marvin Harrison Jr. ARI W6/2025 23→86 %. Gegenbeispiele: Jalen Tolbert DAL W8/2025 19→10 %, Russell Wilson NYG W4/2025 3 %→keine Snap-Beobachtung beim gleichen Team im nächsten Spiel. Keine Fälle beweisen eine medizinische Ursache.

## Nicht erreichte Gates und spätere Wiederaufnahme

Das ehemalige Issue enthielt einen **umfassenderen Forschungsplan, dessen Akzeptanzkriterien nicht erfüllt wurden**. Das Archiv darf dies nicht als „fertig validiertes Modell“ umetikettieren.

- **Nicht geprüft:** echte Play-/DNP-/Team-Roster-Population inklusive Null-Snap-Spielwochen; differenzierte Kategorisierung von Inactive, Bench, Bye, Teamwechsel, Release, Data-Missingness; positionsübergreifende Player-/Team-Opportunity-Verteilung und sinnvolle Snap-Umverteilung.
- **Nicht geprüft:** expliziter as-of-Feature-/Label-Vertrag und cross-season Priors, Rookies/Teamwechsel/Kicker-Spezifika, reproducible versioniertes Forschungsskript sowie vollständiger Cold-Rebuild mit Ausfall-/Fallbacksimulation.
- **Nicht geprüft:** genuine Walk-forward-Holdouts gegen **V4-C-Fantasy-Punkte** (MAE/RMSE/Bias/P10-P50-P90), kalibrierte Verfügbarkeitswahrscheinlichkeiten, robuste Team-/Saison-Generalisierung. Vorherige Heuristik nur Snap-Share-Fehler bei tatsächlicher Offense-Teilnahme, mit Selection Bias.
- **Nicht umgesetzt:** produktive Trainingsartefakte, Feature-Pipeline, V4-C-Modifikation, Datenbeschaffung oder Scheduler. Kein Modell-/App-Contract freigegeben.
- **Wichtige Designbedingungen für eine mögliche spätere Freigabe:** Historical Replay aus persistierten kanonischen NFL-Fakten, vor Ziel-Kickoff datierte Evidenz (No Leakage), Injury-Feed nur optional, Rebuild/Last-Good bei Ausfällen, Trennung von `P(plays)`, bedingtem Workload und Punkten bei gegebenem Workload, klare Source-/Shared Derived-/App-/Fantasy-Management-Verantwortung gemäß ADR-037 und #697.
- **Separate Folgeforschung:** Sleeper als optionales external Pregame-Signal wurde später exploriert; dessen vollständige 27-/34-/26-Spieler-Piloten mit API-/Rechte-Risiken stehen **ausschließlich** im verlinkten separaten [Sleeper-Audit](2026-10-31-sleeper-projections-availability-shadow-audit.md). Beide Studien bleiben nicht produktiv.

## Historisches Originaldokument aus Issue #1025 (Wortlaut der ursprünglichen Research-Phase)

Der folgende Anhang bewahrt die **vollständige Zielsetzung, Anforderungen, Checklisten, Definitionen und den Originalbefund vom 15.10.2026**. Er ist eine **historische Quelle**, keine aktuelle offene Arbeit. Die im Original offenen Checkboxen sind daher bewusst nicht nachträglich als erledigt markiert. Die späteren Sleeper-Checkpoints sind im eigenständigen Audit konsolidiert; die unveränderte Issue-Historie bleibt auf GitHub nachlesbar.

---

## Ziel / Research-Hypothese (15.10.2026)

Prüfen, ob ein **positionsübergreifendes, historisch vollständig rekonstruierbares und offline trainierbares Team-Opportunity-/Rollenmodell** die aktuelle PlayerWeekFantasy-Baseline **V4-C (#697)** nachweisbar verbessert, **ohne einen durchgehend verfügbaren aktuellen oder historischen Injury-/Availability-Feed vorauszusetzen**.

**Status:** Forschungsfrage, keine bestätigte Modellverbesserung und keine Freigabe für produktive Modell-, Source-, Contract-, Workflow- oder Scheduler-Änderungen.

### Anlass / konkreter Fall

Saquon Barkley (PHI, 2026): laut kanonischen Snap-Counts W1 71 %, W2 16 %, W3 72 %, W4 7 % und W5 keine offensiven Snaps. Die 16 % und 7 % waren im aktuellen Fall nach externer Recherche verletzungsbedingt; **aus Snap-Daten allein darf diese Diagnose aber nicht als historisches Label erfunden werden**. Das derzeitige V4-C-Modell verwendet einen Drei-Spiele-Recent-Usage-Trend und projiziert Barkley für W6 auf 6,90 PPR-Punkte (Snapshot 15.10.2026). Dieser Fall ist eine **Hypothese über mögliche Trend-Verzerrung, kein Nachweis eines Modellfehlers**: bei voller Einsatzfähigkeit könnte seine normale Rolle anders aussehen. Teamweite Snap-/Opportunity-Verschiebungen (Shipley, Bigsby, Pierce) sind aus den kanonischen NFL-Daten nachvollziehbar, aber nicht automatisch an Barkley zu redistribuieren.

## Harte Architektur-/Betriebsanforderungen

1. **Historical replay first:** Training, Features, Labels und Backtest müssen aus vorhandenen **persistierten kanonischen NFL-Fakten** plus explizitem League-Scoringprofil jederzeit von Grund auf wiederherstellbar sein. Kein notwendiger Startpunkt "ab heute sammeln" und keine Pflicht zur lückenlosen Dauerbeobachtung eigener Workflows oder Datenbank.
2. **Point-in-time/No leakage:** Für eine Vorhersage vor Week W/Kickoff ausschließlich Fakten und externe Beobachtungen nutzen, die *damals* schon verfügbar waren. Snap-/Spielausgänge aus W sind für die W-Vorhersage verboten; sie dürfen erst als Label und als Feature ab W+1 dienen. Neu beschaffte rückwirkende Verletzungsmeldungen sind nicht automatisch historische *as-of*-Pregame-Evidenz.
3. **Injury-feed optional:** Verfügbare aktuelle, **verlässlich datierte** Availability-Observations (z. B. aus vorhandenen ESPN/Sleeper-Feldern) können als separat gemessener Zusatzfaktor getestet werden, aber das **Kernmodell muss ohne diese Inputs funktionieren**. Keine implizite Annahme "fehlende Beobachtung = gesund/aktiv/OUT".
4. **Ausfälle und Rebuilds:** Ein verpasster Fetch/Workflow oder DB-Ausfall darf weder Trainingsdaten noch das letzte gültige trainierte Modell vernichten. Deterministische Backfills aus historischen Fakten, versionierte persistierte Modellartefakte, Source-/Training-Manifest, Freshness- und Last-Good-/Fallback-Semantik untersuchen. Ausfall frischer Zusatzsignale => transparent degrade, **keine erfundene Availability**.
5. **Ownership:** Source/Canonical Facts getrennt von Shared Derived Feature-/Modellartefakten, App-Readmodels und Fantasy-Management-Entscheidungen (ADR-037 / #613). Kein Consumer-eigener zweiter Projection-Scorer neben #697.

## Zu erforschende Features / Modellfragen

- **Team Opportunity Pool und Verteilung:** teamweite Offense-Snaps, Rushes/Targets/Passversuche sowie Positionsgruppen-Volumen; individuelle Snap Share, Carries+Targets (RB), Targets (WR/TE), Dropbacks/Attempts (QB), Kicker-Opportunities, soweit verlässlich vorhanden; Positions-/Teamwechsel und Personnel-Größe.
- **Normale Rolle vs. Anomalie:** Eine robuste, samplebewusste Rollenbaseline lernen und abrupten Rückgang bei sonst stabiler Rolle von langfristiger Degradierung oder Scheme-Wechsel *statistisch* unterscheiden; Anomalie als `suspected_role_disruption`/latenten Zustand, **nicht** als behauptete Verletzung. Spiele mit niedriger Usage nicht automatisch aus Training entfernen (Selection Bias).
- **Kohärente Umverteilung:** Änderungen der Team-/Positionsgruppen-Verteilung messen und daraus eine vorsichtige bedingte Neuverteilung abschätzen; keine frei werdenden Snaps 1:1 einem Ersatzspieler zuschlagen. Snap-Share-Summe/Korrelationen, Game Script, Blowouts, Trade/Depth-Chart-Wechsel und Rückkehrer als mögliche Confounder.
- **Verfügbarkeit vs. Produktion trennen:** `P(plays)`, erwartete Rolle **falls Spieler spielt**, und Fantasy-Produktion **bei gegebenem Workload** nicht unbemerkt vermischen. Prüfen, was überhaupt ohne valide Prekickoff-Availability beobachtbar/kalibrierbar ist.
- **Training/ML:** Reproduzierbare historische Trainingsdatensätze; zunächst transparente Heuristik/statistisches Modell als Baseline, danach ggf. regulierte tabellarische ML-/probabilistische oder latente Rollenmodelle. *ML-Eignung ist eine Forschungsfrage, kein Zwang zu neuronalen Netzen/LLMs.* Reproduzierbarkeit, Modellversion, trainierte Parameter, Feature-Provenienz und erklärbare Outputs sind Pflicht.
- **Coverage:** RB, WR, TE, QB und K positionsspezifisch sinnvoll prüfen. Routes/Personnel/medizinische Diagnosen nur, sofern historisch vollständig und point-in-time gültig verfügbar; fehlende Daten nicht still auffüllen.

## Empirischer Testplan

- [ ] Coverage/Qualität der kanonischen `data-source/nfl/snap-counts/<season>/<week>.json`, `player-stats`, `weekly-rosters`, `schedules` und Scoring-Inputs nach Saison/Position auditieren; historische Availability-Quelle aus #613 nur als **optional** separate Feature-Familie prüfen.
- [ ] Player-/Team-Week-`as_of`-Trainings- und Label-Vertrag spezifizieren; ausdrücklich historische Nicht-Teilnahme, Truncation und Rolle ohne retrospektive Injury-Diagnosen behandeln.
- [ ] Anomalie-/Rollenstabilitäts-Pilot für Barkley und Gegenbeispiele (echte Role Losses, Comebacks, Blowouts, Teamwechsel) plus repräsentative Mehrsaison-Kohorte.
- [ ] Offline-Training, versionierte Modellartefakte und vollständigen Cold-Rebuild/Backfill samt simuliertem mehrwöchigem Ausfall konzeptionell bzw. im Research-Prototyp nachweisen.
- [ ] Walk-forward-Backtest (keine Future-Features): **V4-C unverändert** vs. (a) individuelle Anomalie-/Rollenfeatures vs. (b) Team-Opportunity/Umverteilung vs. (c) optionaler, streng zeitgültiger Availability-Layer. Ablations separat.
- [ ] MAE, RMSE, Bias, Kalibrierung/P10-P50-P90, Availability-/DNP-Abdeckung, Extremfälle, Positionsgruppen, Rookies/kleines Sample und Team-/Season-Wechsel auswerten; Ergebnisse mit Unsicherheitsangaben und negativen Befunden dokumentieren.
- [ ] Entscheidungsvorlage erstellen: `supported | partially_supported | rejected | inconclusive` und erst bei belastbarem Mehrwert einen **separat freizugebenden** Integration-Checkpoint in #697 entwerfen.

## Akzeptanzkriterien für diesen Research-Checkpoint

- Forschungsdesign und train/test-/as-of-Leakage-Gates sind reproduzierbar dokumentiert.
- Kernalgorithmus kann historische Features und Training ohne seit heute gesammelte Availability-Snapshots rekonstruieren; Ausfallszenarien und Grenzen werden getestet.
- Verwechslung von `0 snaps`, `injured`, `inactive`, `not selected` oder `missing data` wird vermieden.
- Vergleich mit V4-C auf echten historischen Holdouts; Nutzen oder Nichtnutzen ist explizit belegt.
- Keine neue Datenbeschaffungs-/Scheduler-/Datenbankpflicht oder Produktionsänderung ohne erneute Freigabe.

## Abgrenzung / Beziehungen

- **#697** besitzt die produktive PlayerWeekFantasy-/Matchup-Projektion und deren Integration. Dieses Issue prüft eine neue Feature-/Trainingshypothese; es baut **keine konkurrierende Projektionspipeline**.
- **#613** besitzt Source/Canonical-/historische Injury-Quellen (nflverse Injury 2009–2024 dort als Kandidat, Coverage 2025+ problematisch) und Plattform-Schichtgrenzen. Historische Injury-Backfills können Zusatzvalidierung sein, **nicht verpflichtende Kernvoraussetzung**.
- **#669** besitzt ESPN-Current-Scoring-Availability und Provider-Latenz; nicht mit historischer Verletzungsursache gleichsetzen.
- **#978** erforscht RB-Produktionsprofile/Defense-Matchups. Hier geht es um **teaminterne Rollenstabilität und Opportunity-Neuverteilung über alle Fantasy-Positionen**, unabhängig von Gegner-Defense-Faktoren.
- **#206** nutzt gegebenenfalls belegte Ergebnisse für Weekly Lineup/Start-Sit; die Wahl des Fantasy-Starters gehört nicht in den Shared-Derived-Trainer.

## Aktueller Stand / Handoff

**2026-10-15 — Research-Checkpoint 1 (read-only) abgeschlossen; erste empirische Signale, aber kein belegter Projection-Mehrwert.** Abdeckung und 2-Jahres-Snap-Pilot dokumentiert unten. Kein produktiver Code/Contract/Workflow angefasst, kein Trainingsmodell und kein V4-C-/Fantasy-Points-Backtest durchgeführt. **Nächster Schritt nur nach erneuter Freigabe:** Pilotmethodik als versioniertes Research-Skript reproduzierbar machen, Team-Personnel- und ex-ante Missingness-Features testen, anschließend streng walk-forward auf V4-C Fantasy Points evaluieren. Status bleibt `status:analysis`.


## Research-Checkpoint 1 — historische Snaps / Rollenstabilität (2026-10-15, read-only)

**Autorisierter Umfang:** rein lesende Exploration aus dem GitHub-Repository; keine Änderung an `data-source/`, `data-derived/`, `public/data/`, Generatoren, Source-Fetchern, Modellcode oder Workflows. Ergebnisse zunächst als Issue-Dokumentation; **noch kein versioniertes Auswertungsskript** und daher *noch kein vollständig reproduzierbares Research-Artefakt*. Dieser Checkpoint ist ein explorativer Machbarkeitspilot, keine produktionsreife ML-Validierung.

### Historischer Source-Coverage-Check

- `data-source/nfl/snap-counts`: Saisonverzeichnisse **2013–2026** vorhanden; `player-stats` **1999–2026**, `weekly-rosters` **2002–2026**. Verzeichnispräsenz ist **keine** vollständige Qualitäts-/Lückenprüfung für alle Jahre.
- Der Probe-Lesezugriff auf **alle 18 REG-Snap-Partitionen 2024 und 2025** war erfolgreich; alle abgefragten Week-Partitionen `Finalized=true`. 2024: **25.398** Snap-Records, davon **6.468** positive Offensive-Snap-Beobachtungen QB/RB/WR/TE. 2025: **25.395** Records, **6.394** entsprechend gespielte Beobachtungen.
- 2026 W1–5 `Finalized=false`; Barkley-W1–5 dienen nur als aktuelles Illustrationsbeispiel, **nicht** als Trainings-/Validierungs-Holdout.
- Snap-Records besitzen unter anderem `CanonicalPlayerID`, `GameID`, `Week`, `Team`, `Position`, `OffenseSnaps`, `OffensePct`; Team-Wochen lassen sich aus aktuellen REG-Snap-Records identifizieren. Kicker brauchen eine **gesonderte Feature-Familie** aus Special-Teams- und FG/PAT-Opportunity-Daten, da OffensivePct ungeeignet ist.

### Erste, exakt definierte Pilotheuristiken

Scope: QB/RB/WR/TE, nur **tatsächlich gespielte** Player-Game-Records (`OffenseSnaps > 0`); gruppiert nach `CanonicalPlayerID + Team + Position` **innerhalb jeder Season**, nach Woche sortiert. Für ein Zielspiel in Woche W muss derselbe Player/Team/Pos bereits **mindestens drei frühere Einsätze** in derselben Season haben. Keine Nutzung von W oder späteren Informationen zur Erstellung einer Vorhersage für W. Die Labels der Zukunft werden nur nachträglich zur Evaluation verwendet. Training unter cross-season historischen Priors und echte as-of Verfügbarkeit sind **noch nicht** geprüft.

- **Snap-Predictor A:** arithmetischer Mittelwert aus den OffensePct der letzten 3 tatsächlich gespielten Partien vor W.
- **Snap-Predictor B:** Median dieser 3 Partien.
- **Historische Drop-Anomalie im Spiel W (nach W beobachtet):** Median der vorherigen 3 Einsätze >= 0,55; OffensePct in W <= 0,30; Abfall gegenüber Median >= 0,35.
- **Vergleichsgruppe stable:** Median der vorherigen 3 Einsätze >= 0,55 und OffensePct in W >= 0,55.
- **Recovery-Outcome:** Im nächsten *tatsächlich erfassten Teamspiel derselben Mannschaft* besitzt derselbe Spieler OffensePct >= max(0,50, vorheriger Median - 0,15). **Kein** Spieler-Snap beim selben Team => `missing/no observed participation at team`, **keine** automatische medizinische Ursache, `OUT`-Diagnose oder gesicherte Karriere-/Kaderabwesenheit.
- **Prediktiver Ausreißer-Subgroup:** In den drei Vor-Spielen liegen mindestens 2 OffensePct >= 0,60 und mindestens einer <= 0,30; Vor-Spiel-Median >= 0,60. Diese Gruppe ist bereits vor W identifizierbar.

### Quantitatives Ergebnis

| Saison | Prediktionsfälle | Mean-of-3 Snap MAE | Median-of-3 Snap MAE | Drop-Anomalien | Recovery im nächsten Teamspiel | Keine gleiche-Team-Snapbeobachtung im nächsten Teamspiel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 | 4.715 | 12,06 Prozentpunkte | 12,33 Prozentpunkte | 79 | 17 | 34 |
| 2025 | 4.619 | 12,36 Prozentpunkte | 12,54 Prozentpunkte | 75 | 15 | 24 |
| **Kombiniert** | **9.334** | **12,21 Prozentpunkte** | **12,43 Prozentpunkte** | **154** | **32** | **58** |

- Nur **32 von 154** Drop-Fällen (20,8 %) erholten sich im **direkt nächsten Teamspiel** nach dieser engen Definition. Von den **96** Drop-Fällen mit nächster erfasster Snap-Teilnahme im selben Team waren es **32** (33,3 %). Das ist **keine Injury-Heilungswahrscheinlichkeit**: verletzungsbedingte Absenz, Teamwechsel, Bench, anderes Personnel und Saisoneffekte sind nicht bereinigt; mehrfach gezählte Spielerereignisse sind statistisch korreliert.
- In der stabilen Vergleichsgruppe (3.491 Player-Game-Events) waren **2.788** im nächsten Teamspiel erneut auf hohem Snap-Niveau; unter 3.308 mit nächster Teilnahme: 84,3 %. Der große Unterschied belegt die prognostische Relevanz einer beobachteten Rolle, **nicht** die kausale Erklärung eines Einbruchs.
- Ein naiver allgemeiner Austausch des 3-Game-Mittelwerts durch den Median **verschlechtert** den einfachen Snap-Share-MAE in **beiden** Jahren. In der speziellen ex-ante Ausreißergruppe verbessert sich der MAE dagegen: 2024 `n=102`, **24,88 → 21,82** Prozentpunkte; 2025 `n=80`, **21,66 → 20,46**. Die Subgroup ist klein, und die Median-Prognosen haben dort einen deutlichen positiven Bias (≈12,6/15,4 Prozentpunkte). **Noch keine Rechtfertigung für automatische Gewichtskorrektur.**
- Reale Beispiele für temporäre Rückkehr zu hohen Snaps nach einem Einbruch: James Conner ARI W6/2024 28 % → nächstes Spiel 84 %; Amon-Ra St. Brown DET W13/2025 6 % → nächstes Spiel 92 %; Marvin Harrison Jr. ARI W6/2025 23 % → 86 %. Gegenbeispiele aus reinem Snap-Verlauf: WR Jalen Tolbert DAL W8/2025 19 % → 10 %; QB Russell Wilson NYG W4/2025 3 % → keine Snap-Teilnahme beim selben Team im nächsten Spiel. **Die numerischen Fälle sind keine kausale Diagnose.**
- Für Barkley 2026 W2 und W4 ist die Modellfrage besonders plausibel, aber der **Pilot erfordert drei vorherige Einsätze innerhalb derselben Season und kann deshalb den W2-Einbruch nicht markieren**. Cross-season Priors sind eine wichtige offene Anforderung.

### Grenzen / Designfolgen

1. **Kein V4-C- oder Scoring-Backtest:** Getestet wurde ausschließlich die Prognose des **Offensive Snap Share bei tatsächlicher Teilnahme**, nicht die Erwartung von Fantasy-Punkten, die Injury-/DNP-Wahrscheinlichkeit oder die Qualität der Week-6-Lineup-Empfehlung.
2. **Missingness nicht gleich Verletzung:** Es fehlt eine saubere historische ex-ante Unterscheidung von Bench, Inactive, Teamwechsel, Release, Bye, Injury und fehlendem Datensatz. Gespielte-only Auswertung erzeugt **Survivorship-/Selection Bias**; alternative inklusive aller Team-/Roster-Spielwochen muss separat geprüft werden.
3. **Teaminterner Opportunity Transfer noch nicht getestet:** Ein fehlender RB/WR kann durch andere Spieler, mehr TE-Formationen, Game Script oder Gesamtvolumen ausgeglichen werden. Team-/Positionsgruppen-Features und zeitlich korrekte Roster-Membership sind als *eigene* Forschungskomponente nötig.
4. **Leakage-Schutz:** Vor-W-Features werden korrekt nur aus früheren Einsätzen erstellt; die heutigen finalisierten historischen Records sind aber nicht automatisch belegte **damals veröffentlichte** Provider-Snapshots, und spätere Stat-Korrekturen könnten vorliegen. Validitäts- und Publication-Zeitpunkt müssen für streng as-of externe Daten gesondert definiert werden.
5. **Mehrjährige Evaluation zwingend:** 2024 und 2025 wurden bisher nur als zwei separate Explorationsjahre mit denselben, **nicht trainierten** Heuristiken betrachtet – **kein** gelerntes Modell / kein echter Train/Holdout-Schnitt. Kein ML-Modell, keine Fits und keine Produktionsänderung vorgenommen.
6. **Resilienzprinzip bleibt:** Voller Cold-Rebuild aus persistierten historischen Source-Facts statt kontinuierlicher Current-Availability-Snapshots; optionale Injury-Features nur mit vollständiger ex-ante Coverage/Provenienz. Ein Last-Good-Modell darf nicht als frisch ausgewiesen werden.

### Empfehlung nach Checkpoint 1

**Forschungsfrage bleibt offen / `inconclusive` bezüglich Fantasy-Projection-Mehrwert.** Daten genügen für einen sinnvollen weitergehenden Pilot, aber eine pauschale Korrektur vermeintlich verletzungsbedingt niedriger Snaps ist durch die erste Auswertung **nicht** unterstützt. Nächster eng begrenzter Forschungsschritt: im Repo versionierte reproduzierbare Analyse und echte Play-/DNP-/Team-Availability-Kohorten, danach Team-Opportunity-Features; kein vorzeitiger Modell-Cutover. #697 bleibt unverändert.
