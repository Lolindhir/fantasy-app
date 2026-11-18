# CP3a — Hybrid-Expected-Score: Best-Ball-Selektionsaufschlag und Prognosequalität

- **Datum:** 2026-11-18
- **Issue:** [#1451](https://github.com/Lolindhir/fantasy-app/issues/1451)
- **Status:** empirische Analyse; **keine** aktivierte Formel, **kein** neuer Datenvertrag, **keine** Änderung der App-Anzeige
- **Geltung:** Prognose der Team-Punkte vor NFL-Locks. Die echten fortschreitenden Manager-Lineup-/Lock-Snapshots der historischen Dienstage fehlen.

## Ausgangsthese

Der historische `LineupEfficiencyActual`-Wert ist `tatsächliche Starterpunkte / nachträglich optimalen Best Ball des gesamten damaligen Kaders` (TeamWeekPerformance). Die neue Shadow-Formel setzt ihn jedoch auf **vorher projizierten** Best Ball an.

Selbst wenn die einzelnen Spielerprognosen erwartungstreu sind, gilt für einen festen Spielerpool und ein zulässiges Set von Lineups prinzipiell:
`E[max_Lineup tatsächliche Punkte] >= max_Lineup E[tatsächliche Punkte]`.
Die nach dem Spiel gewählten Best-Ball-Spieler profitieren vom **ex post** beobachteten oberen Ende der Ergebnisverteilung. Ein Spieler mit positiven Überraschungspunkten kann im nachträglichen Best Ball auftauchen, obwohl ein anderer Spieler vorab höher projiziert war. Zusätzlich können echte Projektionsfehler, Teilnehmerausfälle, unterschiedliche IR/Taxi-/Roster-Definitionen und historische PWF-Abdeckung die Lücke vergrößern oder verkleinern. Ein empirischer Aufschlag ist deshalb **nicht** gleichzusetzen mit einem reinen mathematischen Volatilitäts- oder Coach-Skill-Faktor.

## Tatsächlich geprüfte Quellen

- `data-derived/season-statistics/nfl-reise/{2024,2025,2026}.json` – die `GameLog`-Felder `Week, Points, ProjectedBestBallPoints, ProjectedStarterPoints, LineupEfficiencyProjected, LineupEfficiencyActual`.
- `data-derived/team-week-performance/nfl-reise/<season>/<week:02>.json` – für **alle** 37 Wochen: 2024 W1–14, 2025 W1–13, 2026 W1–10. `ActualStarterPoints, PotentialPoints` über exakt denselben `CanonicalLeagueRosterID` verknüpft.
- Aus 222 Team-Wochen mit historischen Ergebnissen haben **213** verwertbare Paare aus projiziertem und tatsächlich realisiertem Best Ball (81 / 72 / 60). Bei allen 213 weicht der GameLog-`Points`-Wert nicht mehr als 0,03 Punkte von `TWP.ActualStarterPoints` ab; beobachtete Abweichungen: **0**.
- Die Backtest-Prognosen nutzen pro Team ausschließlich **vor der Zielwoche** abgeschlossene Wochen aus derselben Saison mit validen BB-/PWF-/Effizienzbelegen, mindestens **drei** Trainingswochen. Dadurch entstehen **159** Ziel-Team-Wochen: 63 / 54 / 42 (2024/25/26).
- Kein Test konstruiert historische exakte TNF-Locks oder Dienstag-Roster; die gespeicherten historischen Woche-`GameLog`-Best-Ball-Werte beziehen sich auf die letztlich archivierten Wochenkader. Historische Modellrevisionen/Quellenstände als `as-of` wurden hier nicht unabhängig reauditiert.

### Nachträglicher gegenüber vorher projiziertem Best Ball

| Saison | Gültige Team-Wochen | Verhältnis Summe tatsächlicher Best Ball / Summe projizierter Best Ball |
|---|---:|---:|
| 2024 | 81 | **1,1264** |
| 2025 | 72 | **1,1039** |
| 2026 (W1–10) | 60 | **1,1167** |
| Alle | 213 | **1,1157** |

Die erkennbare Differenz liegt in allen drei Saisons bei gut 10 %, ist aber weder konstant je Team noch unabhängig von der definierten Roster-Eignung.

## Walk-forward-Varianten und Formeln

Für Team und Zielwoche `t`, mit `H={w<t, valide Historie}`, `BBproj(t)`, `EffActual(w)` in Prozent:

1. **CP2-Shadow (raw):** `BBproj(t) × mean_H(EffActual)/100`.
2. **Selection-Uplift (pooled prior-week ratio):** `BBproj(t) × [sum_H(BBactual) / sum_H(BBproj)] × mean_H(EffActual)/100`. Der Aufschlag wird ausschließlich aus vorherigen Wochen geschätzt.
3. **Empirisches Score-Verhältnis:** `BBproj(t) × [sum_H(PointsActual) / sum_H(BBproj)]` (getrennte Alternative, ersetzt keine historische Coach-Kennzahl).
4. **Projected-Efficiency-Benchmark:** `BBproj(t) × mean_H(LineupEfficiencyProjected)/100`. Dies misst Modellübereinstimmung und ist **keine** Definition von guter Managerentscheidung.
5. **Historisch archivierte Starterprojektion:** `ProjectedStarterPoints(t)`. Ein **informativer, aber nicht frühdienstags-fairer** Benchmark, weil die archivierte Aufstellung die spätere Managerentscheidung bereits enthalten kann.
6. **Einfacher Baseline-Schnitt:** `mean_H(PointsActual)`.

| Verfahren | N | MAE Punkte ↓ | Bias (Prognose − Ist) | RMSE Punkte ↓ |
|---|---:|---:|---:|---:|
| **CP2: projizierter Best Ball × tatsächliche Coach-Effizienz** | 159 | 28,43 | **−21,29** | 35,68 |
| **Best Ball × beobachteter Selection-Uplift × Actual-Effizienz** | 159 | **24,18** | **−2,03** | 30,12 |
| Direkter historischer Score-/Projected-BB-Faktor | 159 | 24,19 | −2,15 | 30,17 |
| Best Ball × historische Projected-Effizienz (Vergleich) | 159 | 22,92 | +1,56 | 28,65 |
| Archivierte Starterprojektion (Vergleich, möglicher Lineup-Lookahead) | 159 | 22,94 | +2,61 | 28,38 |
| Vorwochen-Punkteschnitt (einfacher Vergleich) | 159 | 23,04 | +0,01 | 29,09 |

**Auswertung je Saison (MAE / Bias):**

| Saison | N | Raw | Selection-Uplift | Projected-Eff. | archivierte Starter |
|---|---:|---|---|---|---|
| 2024 | 63 | 27,30 / −22,63 | **21,56 / −6,61** | 19,92 / −3,80 | 19,97 / −1,68 |
| 2025 | 54 | 29,33 / −20,60 | **23,89 / +0,04** | 23,02 / +3,24 | 23,82 / +3,15 |
| 2026 | 42 | 28,96 / −20,19 | **28,48 / +2,18** | 27,28 / +7,43 | 26,28 / +8,33 |

**Ergebnis:** Die direkte CP2-Multiplikation erzeugt eine wiederkehrende **erhebliche negative Verschiebung**. Der retrospektiv geschätzte Selection-Uplift verringert ihren Bias und den Fehler deutlich, verbessert aber **nicht** alle Baselines; insbesondere in 2026 ist sein MAE-Vorteil gegenüber raw klein. Die Unterschiede zwischen weitergehenden Korrekturvarianten sind klein im Verhältnis zur Wochenvolatilität. Keine dieser Zahlen belegt, dass sie als frühe Wochen- oder In-Game-Projektion besser ist.

### Flo (2026)

- Actual Starter `215,584` im Schnitt; Projected BB `220,3756`; tatsächlich erreichter retrospektiver Best Ball `252,63`; historische Actual Efficiency `85,4134 %`.
- Aktuelle W11-Shadow-Basis: `BBproj=220,2778`; CP2 `ExpectedPoints=188,1468`.
- 2026-W1–10-*ex-post*-Uplift `252,63/220,3756=1,14636`. **Reine Sensitivitätsrechnung**, noch nicht freigegebener Week-11-Forecast: `188,1468 × 1,14636 = 215,68`.
- Alternativ direkt das historische tatsächliche Score-/Projected-BB-Verhältnis: `220,2778 × 215,584/220,3756 = 215,49`.
- Nicht mit `LineupEfficiencyProjected` als Managerbewertung verwechseln. Insbesondere sind der historische All-Roster-Pool und der aktuelle W11-Active-only-Pool nicht exakt vergleichbar.

## Exploration zu Siegchancen (nicht produktionsreif)

Auf Basis derselben `season-statistics GameLog`-Reihen, je Team mindestens drei vorherige gültige Scores, wurde je historischem Matchup eine Normaldifferenz-Chance aus der jeweiligen Team-Mittelwertprognose und **der historischen Sample-SD tatsächlicher Team-Punkte** gebildet. Realisierte Punkte/Manager-Vergleiche nicht für Zielwochenparameter genutzt; für den Uplift in dieser Zusatzrechnung ist `BBactual` aus `actual Starterpunkte / historischer ActualEfficiency` numerisch approximiert.

| Chancen-Input | Brier Score ↓ (77 Paarungen) |
|---|---:|
| Raw CP2 | **0,2424** |
| Selection-Uplift × Actual-Effizienz | **0,2472** |
| Historical Projected Efficiency | 0,2322 |
| Archivierte Starterprojektion | 0,2320 |
| Reiner früher Punkteschnitt | 0,2439 |

Die Korrektur behebt den **Punkt-Bias**, aber **verbessert in diesem Provisorium die Brier-Güte nicht**. Unterschiede in 77 Spielen sind mit erheblicher Stichprobenunsicherheit belastet. Insbesondere ist eine einfache `score SD` nicht die epistemische/spielzustandsabhängige Varianz der Hybrid-Selektion. **Kein** neues `win-prob-v2` daraus ableiten, keine UI-Chance umschalten. Dies ist nicht das vollständige historische WinProb-v1-Vergleichsprotokoll mit echten Dienstag-Aufstellungen.

## Architektur- und Modellgrenzen / nächster fachlicher Checkpoint

- Historisches `TWP.PotentialPoints` und `LineupEfficiencyActual` bleiben **unverändert**, inklusive erlaubter hypothetischer Taxi-/IR-Auswahl. Diese Kennzahl ist retrospektives Kader-Ausschöpfen inklusive Zufall, nicht „Befolgen der hauseigenen Projektion“.
- CP2 `HybridExpected` bleibt **unverändert** (Shadow, aktiver Kandidatenpool, keine Live-Anzeige); das aktuelle Modell darf wegen sichtbarer Unterprognose **nicht** als zuverlässige Siegchancenbasis promoted werden.
- Der empirische Uplift korrigiert die Kombination unterschiedlicher Nenner, ist jedoch potenziell **roster-, saison-, positions-, varianz- und PWF-versionsempfindlich**; ein pauschaler fixer Faktor 1,12 wäre nicht durch das vorliegende Design gedeckt.
- Nächster CP3b-Vorschlag: getrennt (i) die **erwartete ex-post-optimale Punktzahl** aus vorliegenden PlayerWeekFantasy-Ranges mit Monte Carlo/Assignment-Solver unter korrekter Pool-/Availability-/Korrelationsannahme schätzen und mit dem empirischen Uplift vergleichen, (ii) anschließend die **Varianz des voraussichtlich tatsächlich gestarteten Hybrid-Lineups** plus die Coach-Entscheidungsunsicherheit modellieren, (iii) beide im as-of/Wochen- und Matchup-Walk-forward evaluieren. Ohne diese Tests keine automatisierte Gleichsetzung eines erwarteten Best-Ball-Highs mit der erwarteten realen Manager-Scoreverteilung.
- **Risiko/Safety:** rein empirischer Bericht, keine produktive Source-, Derived-, Generator-, App-, CI- oder Workflow-Mutation. Keine neuen CI-Tests im Research-Only-Checkpoint; bestehende Produktionsrechnungen bleiben identisch. Revert des Reports möglich.
