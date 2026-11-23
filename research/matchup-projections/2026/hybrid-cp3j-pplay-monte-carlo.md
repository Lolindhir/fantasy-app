# CP3j — Availability-v3-Teilnahme × Monte-Carlo-Best-Ball (2026 W5–10)

- Datum: 23.11.2026
- Tracking: https://github.com/Lolindhir/fantasy-app/issues/1451
- Forschungsbasis: CP3i, Draft PR #1637, noch ungemergt
- Runner: research/matchup-projections/2026/backtest_product_pplay_best_ball.cjs
- Status: Forschungscheckpoint im V8-Harness auf echten Daten reproduziert, kein produktives Modell.

## Forschungsfrage

Senkt eine vor der Zielwoche aus Availability v3 geschätzte Teilnahmechance die Monte-Carlo-Best-Ball-Überschätzung aus CP3b/CP3d? Liefert individuelle historische Teilnahme über die starke Vorwochenstatus-Baseline hinaus einen messbaren Zusatznutzen?

**Zielgröße ist TWP.PotentialPoints, der nachträglich erreichbare optimale Best Ball**, nicht der tatsächliche Manager-Score und nicht die Siegchance.

## Existing-first-Inputs und Paarprotokoll

- Derselbe archivierte Fantasy-Wochenkader aus data-source/leagues/nfl-reise/seasons/2026/matchups/week-W.json wie CP3b/CP3d (einschließlich IR/Taxi); saisonale Slots aus league.json.
- Wochenpositionen ausschließlich aus dem existierenden kanonischen NFL-Weekly-Roster; 90%-PI1-Projection/Points, Range und finale Actuals aus dem bestehenden Shared-Derived PlayerWeekFantasy V4-C.
- Teilnahme-Modellfeatures ausschließlich aus dem bestehenden Shared-Derived nfl-player-availability-v3 der Wochen bis W−1. Keine Consumer-neue Injury-/Snap-Derivation.
- Gruppen-Training 2016–2022: 128.087 bewertbare Wochen, 55.948 Played, p_global 0,4367968646. Validierung 2023–2024: 36.134, Parameter unverändert k=400, alpha=8, letzte vier bekannte REG-Teilnahmen. Die 2025er CP3i-Holdout-Saison wird in CP3j nicht zum Refit verwendet.
- Die Vorwochen-Gruppe besteht aus W−1-Rosterstatus ACT/INA/RESERVE/OTHER/NONE und W−1-Played T/F/U. Retrospektives Zielwochen-Played wird ausschließlich für Evaluation und Oracle-Diagnostik gelesen. Kein Zielwochen-Report, -Rosterstatus, -Available oder -Ergebnis geht in die Modellfeatures ein.
- Vier Arme: (1) All-Play p=1; (2) CP3i-Roster-/Teilnahmestatus-Baseline mit k=20; (3) CP3i-History mit k=400, alpha=8, window=4; (4) ex-post Oracle nur als Diagnose, niemals als Vorhersage.
- Pro Draw dieselben Kandidaten-Punktziehungen aus PI1-Normalapproximation, dieselben Teilnahme-Uniforms und derselbe globale CP3b-Assignment-Solver einschließlich FLEX und virtuellen Leerslots. Seed 20261123, 1.200 Draws je Team-Woche, 10./90. Perzentil als nominelles 80%-Intervall.
- Die randomisierten Draws der vier CP3j-Arme sind untereinander gepaart, aber nicht behauptet numerisch identisch mit historischen CP3b-Simulationsläufen anderer Seeds.

## Abdeckung der echten 2026er Daten

| NFL Week | Teams | Projizierbare Kandidaten | Ohne Vorwochenrecord | Zielwochen Played=false |
| --- | ---: | ---: | ---: | ---: |
| 5 | 6 | 185 | 0 | 39 |
| 6 | 6 | 173 | 0 | 34 |
| 7 | 6 | 173 | 0 | 31 |
| 8 | 6 | 173 | 0 | 24 |
| 9 | 6 | 185 | 0 | 35 |
| 10 | 6 | 174 | 1 | 35 |
| Summe | 36 | 1.063 | 1 | 198 |

Alle 1.063 Kandidaten haben ein bekanntes Zielwochen-Played-Label. 1.062 sind aus dem CP3i-Vorwochen-Risikoset modellierbar. Ein W10-Kandidat NFLP-14c210d263a1a64d8019 (Roster clr-dc35c0c936175f68a694e7b05bd6861d) hat keinen W−1-Datensatz; die ganze Team-Woche wird **fail-closed** aus dem fairen Paarvergleich ausgeschlossen, ohne p=0/1 zu erfinden.

**35/36 Team-Wochen bleiben**, darunter 192 nicht eingesetzte Spielerfälle. Auf allen 35 reproduziert die Optimierung der finalen PWF-Actuals die TWP-PotentialPoints innerhalb von 0,05 Punkten (35/35). Kein Pflichtslot darf unbemerkt fehlen.

## Ergebnis auf denselben 35 Team-Wochen

MAE / Bias / RMSE in Fantasy-Punkten, Bias = Prognose minus tatsächlicher Best Ball.

| Modellarm | MAE (niedriger besser) | Bias | RMSE | nominelle 80%-Coverage |
| --- | ---: | ---: | ---: | ---: |
| All-Play | 30,70 | +22,99 | 38,47 | 20/35 = 57,1 % |
| Vorwochenstatus, k=20 | 23,11 | -3,38 | 32,52 | 27/35 = 77,1 % |
| Status + Historie, k=400 / alpha=8 / 4 | **22,83** | **+1,85** | **31,81** | **27/35 = 77,1 %** |
| Oracle, ex post | 25,09 | +10,82 | 32,90 | 24/35 = 68,6 % |

Die Teilnahme-Berücksichtigung gegenüber All-Play senkt den History-MAE um **7,86 Punkte (25,6 %)** und den starken positiven Bias deutlich. Der **Zusatznutzen der individuellen Historie gegenüber der einfachen Vorwochenstatus-Baseline beträgt aber nur 0,28 Punkte MAE (~1,2 %)** und ist derzeit nicht als verlässlich belegt.

Die Oracle-Variante darf in MAE schlechter sein: Oracle-Teilnahme kann die verbleibende Normal-, Korrelations- und Extremwert-Selektion nicht korrekt kalibrieren. Das ist kein Beleg, dass Zukunftswissen schlechter wäre, sondern dass der getestete Score-Generator weiterhin verzerrt ist.

### MAE nach Woche

| Week | n | All-Play | Status | Status+Historie |
| --- | ---: | ---: | ---: | ---: |
| 5 | 6 | 14,57 | 17,44 | 16,85 |
| 6 | 6 | 38,34 | 17,27 | 20,69 |
| 7 | 6 | 25,71 | 20,22 | 16,87 |
| 8 | 6 | 42,98 | 33,23 | 34,22 |
| 9 | 6 | 32,54 | 21,81 | 21,31 |
| 10 | 5 | 29,91 | 29,79 | 27,90 |

Als **nur deskriptive** Stabilitätsprobe wurden alle 6^6 Resamples aus sechs Wochen-Clustern (gewichtet nach enthaltenen Team-Wochen) geprüft. Die mittleren 95% der resampelten MAE-Vorteile liegen für All-Play minus CP3i zwischen 2,54 und 12,81 Punkten, für Status minus CP3i zwischen -1,54 und +1,93. **Keine formalen Konfidenzintervalle:** Es gibt nur sechs NFL-Wochen, wiederkehrende Manager und Spieler, gemeinsame NFL-Spiele und Monte-Carlo-Rauschen. Besonders die zweite Differenz ist unstabil.

## Validierung und exakte Reproduktion

Zum Ausführen auf vollständigem Repository-Checkout des gestapelten CP3j-Branches:

    node research/matchup-projections/2026/backtest_product_pplay_best_ball.cjs --self-test
    node research/matchup-projections/2026/backtest_product_pplay_best_ball.cjs --draws=1200 --seed=20261123

Tatsächlich durchgeführt am 23.11.2026:

1. Den **eingecheckten Quelltext** direkt in einem isolierten V8-Node-Shim mit Node-API-Mocks kompiliert und seinen synthetischen Self-Test erfolgreich ausgeführt. Getestet: strict Lag, Zielwochen-Feature-Isolation, Missing-Prior, Rostergruppen, Slots und deterministische Bernoulli-Quelle.
2. Auf den 9 echten Availability-v3-Saisonprodukten 2016–2024 die reale exportierte fitFrozenModel-Funktion ausgeführt: Training 128.087, Validierung 36.134, 13 Statusgruppen, Auswahl 400/8/4 (Validation Brier 0,090910).
3. Dieselbe eingecheckte runWeek-Funktion auf tatsächlichen 2026-W5–7- und W8–10-GitHub-JSONs ausgeführt, jeweils 1.200 Ziehungen für jedes der sechs Teams. Die per-Week/paired-Metriken ergeben die obige Summe.

**Nicht durchgeführt:** Ein eigenständiger Node-CLI-End-to-end-Lauf mit allen Produkten im vollständigen lokalen Git-Checkout und unabhängiger zweiter Replay; CI allein belegt diesen Full-History-Runner nicht. Das darf nicht als erfolgreich gekennzeichnet werden.

## Forschungslimits, Architektur und Folgeschritt

- Retrospektive Week-Archive enthalten den **später dokumentierten** Fantasy-Gesamtkader, keine belegten Dienstag-/Kickoff-Snapshots. Die W−1-Availability-Records und PWF-Revisionen sind heutige rückblickende Produkte, keine attestierten damaligen Revisionen. Zeitliches Lag schützt gegen explizite Zielwochenfeatures, beweist **kein** echten Point-in-Time-Replay.
- CP3j nutzt weiterhin die CP3b-Normalapproximation für asymmetrische PI1-Ranges, unabhängige Kandidaten, keinen NFL-Team-/Spiel-Zusammenhang, kein Workload-Given-Play. Historischer IR-/Taxi-Pool ist kein gesichert aktivierbarer Live-Pool. Der eine W10-Fehlfall bleibt sichtbar.
- Der Checkpoint enthält **keine** reale Manager-Starterpunkt-, Lineup-/Lock-, Coach-Effizienz-, Matchup-Brier- oder WinProb-Auswertung. Eine bessere Vorhersage des Best Ball bedeutet nicht automatisch eine bessere Siegchance.
- Nächster sinnvoller Research-Schritt: Seed-/Verteilungssensitivität und Paired-Backtest auf mehr unabhängigen 2024/25-Fantasy-Wochen, soweit Availability-v3-Vorwochenabdeckung und echte Zielkader belegbar sind; dann provenance-geführte As-of-/Lock-/Manager-Score-Auswertung. Vorher **keine produktive Aktivierung**.

Risikoeinstufung: Research-only, ohne Source-, Shared-Derived-, App-, Team-Efficiency-, Writer-, Scheduler-, CI- oder data-meta-Änderungen. Bereits existierende Module CP3i/CP3b/CP3d wiederverwendet; der CP3j-Branch hängt ungemergt auf CP3i. Rollback: Forschungs-Commits revertieren bzw. Branch entfernen.
