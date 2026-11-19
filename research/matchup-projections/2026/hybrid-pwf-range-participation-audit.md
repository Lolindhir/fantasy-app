# CP3c – Diagnose der PlayerWeekFantasy-Ranges und der Teilnahme

**Datum:** 19.11.2026 · **Issue:** [#1451](https://github.com/Lolindhir/fantasy-app/issues/1451) · **Status:** Research-only. Vorgänger: CP3a und CP3b im gleichen Ordner.

## Forschungsfrage

CP3b simulierte einen theoretischen ex-post Best Ball mit unabhängigen Normalziehungen aus den PWF-90-%-Intervallen. Der simulierte Selection-Uplift (+21,2 %) lag weit über dem beobachteten (+11,4 %). CP3c prüft **zuerst die marginale Kalibrierung der Spielerintervalle** und die Relevanz tatsächlicher Spielteilnahme, bevor eine neue gemeinsame Verteilung entwickelt wird.

Das PWF-Modell V4-C-PI1 liefert explizit **conditional-on-participation**-Rangeschätzungen, ohne Availability-Adjustment. Das 90-%-Intervall ist keine Aussage darüber, ob ein Spieler überhaupt eingesetzt wird.

## Echte Quelldaten und reproduzierbare Methode

- 18 finale PWF-Partitionen: data-derived/player-week-fantasy/nfl-reise/{2024,2025,2026}/{05..10}.json
- 18 Snap-Partitionen: data-source/nfl/snap-counts/{season}/{week:02}.json
- Kanonische Identität: CanonicalPlayerID, Saison und Woche; nur PWF-Records mit Projection.Status=available, Actual.State=final und gültigen Levels 50/80/90.
- Positiver relevanter Snap-Nachweis: OffenseSnaps größer null für QB/RB/WR/TE/FB; SpecialTeamsSnaps größer null für K. Aggregation aller Spieler-Snap-Records; Position aus der Snap-Quelle. Analog zur Einsatzregel in tools/historical_projection_backtest.py.
- **Fehlender positiver Snap-Nachweis ist nicht gleich gesichertem DNP oder OUT:** Er kann auch Bye, unvollständige Snap-Evidenz oder andere Quellen-/Positionsfälle bedeuten. Dieser Audit prüft nicht zusätzlich für jede Zeile den kanonischen Player-Stats-Record.
- Gemessen: inklusive Interval-Hits; mittlerer Fehler Forecast minus Actual, MAE, Unter-/Überschreitungen, 90-%-Intervallbreite, Position und RangeQuality. Historische PWF-Revisionen sind nicht als echter Dienstag-As-of-Snapshot belegt.

Reproduktionsskript: [audit_pwf_range_coverage.cjs](audit_pwf_range_coverage.cjs).

**Ausführen im Repository:**

    node research/matchup-projections/2026/audit_pwf_range_coverage.cjs --self-test
    node research/matchup-projections/2026/audit_pwf_range_coverage.cjs --seasons=2024,2025,2026 --weeks=5-10

Deterministisches read-only JSON auf stdout, keine Datei-/Produkt-/Workflow-Mutation.

## Ergebnisse – tatsächlich mit positiven relevanten Snaps

| Saison | Gespielte Fälle | 50-%-Coverage | 80-%-Coverage | 90-%-Coverage | Bias Pkt. | MAE Pkt. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 W5–10 | 2.255 | 45,68 % | 77,69 % | 89,89 % | +0,292 | 4,397 |
| 2025 W5–10 | 2.172 | 50,18 % | 78,78 % | 89,96 % | +0,198 | 4,333 |
| 2026 W5–10 | 2.223 | 46,15 % | 78,27 % | 89,92 % | +0,369 | 4,377 |
| **Gepoolt** | **6.650** | **47,31 %** | **78,24 %** | **89,92 %** | **+0,287** | **4,369** |

Insgesamt **5.980 von 6.650** Fällen innerhalb des 90-%-Intervalls. Marginal liegen die 90-%-Grenzen bei beobachtetem Spieleinsatz damit nahe dem Nominalwert. Die 50-/80-%-Intervalle sind etwas zu eng. Das mittlere Punkt-Bias ist klein und leicht optimistisch.

| Population | Fälle | 90-%-Abdeckung |
| --- | ---: | ---: |
| Positiver relevanter Snap-Nachweis | 6.650 | **89,92 %** |
| Alle projizierten Fälle mit finalem Ist | 10.869 | **84,79 %** |
| Ohne positiven relevanten Snap-Nachweis | 4.219 | unter 80 % |

Das niedrigere All-Player-Ergebnis darf **nicht** als Beleg gegen die conditional-on-participation-Ranges verstanden werden. Viele Spieler ohne Einsatz punkten tatsächlich null, obwohl ein bedingtes PWF-Intervall erst bei positivem Spieleinsatz gelten soll. Das ist eine zentrale Grenze der unbedingten CP3b-Simulation.

## Auffällige Untergruppe: begrenzte Historie

| RangeQuality | Saison | Fälle | 90-%-Abdeckung |
| --- | --- | ---: | ---: |
| player-volatility | 2024 | 2.133 | 89,69 % |
| player-volatility | 2025 | 2.032 | 90,26 % |
| player-volatility | 2026 | 2.059 | 90,68 % |
| limited-history-fallback | 2024 | 122 | 93,44 % |
| limited-history-fallback | 2025 | 140 | 85,71 % |
| limited-history-fallback | 2026 | 164 | **80,49 %** |

Gepoolt **player-volatility: 5.614/6.224 = 90,20 %**, **limited-history-fallback: 366/426 = 85,92 %**. Der Fallback ist ein echter Kandidat für einen separaten Audit, aber 426 korrelierte Spieler-Wochen sind kein belastbarer Beleg für eine sofortige Live-Rekalibrierung.

Die 2026er Positionskontrolle zeigt QB 90,73 % (205), RB 89,00 % (418), WR 91,13 % (800), TE 89,18 % (564), K 90,29 % (175), FB 83,61 % (61). Der JSON-Report des Skripts ergänzt Prognose-Buckets unter 4 / 4–8 / 8–12 / 12–20 / über 20 Punkten.

## Bedeutung für CP3b

1. **Keine pauschale Skalierung oder Verengung der 90-%-PI1-Spielerintervalle:** Die marginale bedingte Abdeckung ist nahe 90 %. Auch eine gute marginale Abdeckung sagt jedoch nichts darüber, ob Normalverteilungs-Sigma und positive Tail-Ausreißer richtig sind.
2. **Participation muss in die ex-ante-Spielerverteilung:** Unabhängige Ziehungen für alle PWF-verfügbaren Kandidaten behandeln auch Spieler ohne realen Einsatz wie sichere Teilnehmer. Der numerische Beitrag dieses Mechanismus zum +21,2-%-Monte-Carlo-Uplift wurde **hier nicht isoliert**; noch keine Kausalaussage.
3. **Joint Distribution bleibt ungeprüft:** QB–Receiver-Korrelation, Spiel-/Teamfaktoren, negative Konkurrenzkorrelationen, asymmetrische Residuen und Manageraufstellungen können den Selektionseffekt verändern.
4. **Pool-/Zeitbruch:** CP3b optimiert spätere vollständige Wochenkader inkl. IR/Taxi, CP2 den aktiven Live-Pool, TWP ex-post das All-Roster-Potenzial. Frühe historische Dienstag-Kader und vollständige PWF-As-of-Revisionsstände fehlen.

## Forschungsentscheidung und nächster Checkpoint

**CP3c ist eine Diagnose, keine Änderung der produktiven Kalibrierung.** Weder PWF V4-C-PI1 noch HybridExpected, WinProbability oder die App-Anzeigen werden umgestellt. Keine additive +11,6-%- oder +21,2-%-Formel.

**CP3d-Empfehlung:** Den CP3b-Best-Ball-Solver unter **identischem Kader und identischer Formation** in zwei Ausprägungen vergleichen: alle projizierbaren Kandidaten versus nur Kandidaten mit ex post bezeugtem Spieleinsatz (Oracle-Availability ausschließlich zur Diagnose; kein Lookahead im Modell). Fehlende Pflichtslots gesondert ausweisen. Erst anschließend reale Spieler-Residualverteilungen gegenüber der Normalannahme und empirische NFL-Spiel-Korrelationen testen. Danach, getrennt, tatsächliche Managerpunkte/Coach-Entscheidungen gegen CP3a-Empirical-Uplift und Projected-Efficiency-Baselines validieren.

**Validierung und CI-Impact:** Source-/Derived-Dateien nur gelesen, 18 historische PWF-/Snap-Wochen aus GitHub. Skript syntaktisch geparst; Self-Test und Auswertung gegen die echten 18 Partitionspaare ausgeführt (per vorab geladenem Inhalt und simuliertem readFileSync). Kein neues produktives Testmodul, keine Tests im Inventar oder an Fast/Deep/Workflow-Routing verändert; kein produktiver Deep-Run notwendig. Historische Auswertungen sind kein vollständiger Dienstag-Walk-forward; wiederholte Spieler-Wochen sind nicht unabhängig. Revert nur der beiden neuen Research-Artefakte möglich.
