# CP3b — Simulierter Ex-post-Best-Ball aus PlayerWeekFantasy-Ranges

- **Datum:** 2026-11-19
- **Work Package:** [Issue #1451](https://github.com/Lolindhir/fantasy-app/issues/1451)
- **Status:** Research-Checkpoint; weder produktive Hybrid-Expected-Score-Formel noch WinProbability oder UI verändert.
- **Vorgänger:** [CP3a Selection-Uplift Walk-forward](hybrid-selection-uplift-walk-forward.md).

## Forschungsfrage und statistische Unterscheidung

Das im TeamWeekPerformance rückblickend bestimmte Best Ball maximiert nach der jeweiligen Spielwoche die **tatsächlich realisierten** Spielerscores. Das bisherige projizierte Wochen-Best-Ball maximiert vorab die **PWF-Erwartungswerte**. Wegen der nachträglichen Auswahl günstiger Überraschungen gilt für identischen Kandidatenpool und zulässige Lineups prinzipiell E[max(L)] >= max(E[L]). Entscheidend ist aber die Größe der Differenz unter den **wirklichen** Spielergebnisverteilungen, nicht unter einer willkürlichen Simulationsannahme.

CP3b untersucht zunächst ausschließlich diese Auswahlkomponente. Eine gute Prognose des nachträglichen Optimalwerts ist **nicht** automatisch eine gute Prognose des von einem Manager tatsächlich gewählten, teilweise gelockten Lineups. Deshalb werden erwartete Punkte und Siegchancen nicht umgestellt.

## Datenbasis und Reproduktionsweg

- `data-derived/player-week-fantasy/nfl-reise/<season>/<week>.json`: projizierte PWF-Points und PredictionRange der veröffentlichten PI1-90-%-Schätzung.
- `data-source/leagues/nfl-reise/seasons/<season>/matchups/week-<week>.json`: archivierter gesamter Fantasy-Wochen-Kader je CanonicalLeagueRosterID. Der historische Auswertungs-Pool enthält – analog zum TWP-Potential – auch IR/Taxi; er ist ausdrücklich **nicht** der aktive CP2-Live-Kandidatenpool.
- `data-source/nfl/weekly-rosters/<season>/<week>.json`: saison- und wochenspezifische Positionen.
- `data-source/leagues/nfl-reise/seasons/<season>/league.json`: saisonabhängige RosterPositions und FLEX-Berechtigungen.
- `data-derived/team-week-performance/nfl-reise/<season>/<week>.json`: tatsächlich retrospektiv erreichter Best-Ball als `PotentialPoints`; `OptimalLineup` für Abdeckungs-Checks.
- Read-only-Reproduktionsskript: `research/matchup-projections/2026/simulate_best_ball_ranges.cjs` (kein produktiver Consumer, kein Publisher und keine neue GitHub Action).

Aufruf innerhalb des Repositories (Node.js):

```bash
node research/matchup-projections/2026/simulate_best_ball_ranges.cjs --self-test
node research/matchup-projections/2026/simulate_best_ball_ranges.cjs --seasons=2024,2025,2026 --weeks=5-10 --draws=1200 --draws-2024=800 --block=3 --seed=20261119
```

Für jeden projizierbaren Spieler: µ = Projection.Points und σ = (PredictionRange.Upper90 − PredictionRange.Lower90)/(2 × 1,64485362695). Unabhängige standardnormalverteilte Punkteziehungen werden je Durchlauf global positionsgerecht mit einem Hungarian-Assignment optimiert, wobei Nullpunkte-Leerplätze erlaubt sind. Die Optimierung ist vom Prinzip der bestehenden `weekly_lineup_optimizer.maximize_lineup` entlehnt; dieser Research-Helper ist nicht selbst die kanonische Python-Implementation. Fehlende gültige Projektionen werden **nicht** als sicher null behauptet. Wenn sich Pflichtslots nicht besetzen lassen, wird die Team-Woche als incomplete ausgewiesen.

### Historisch korrekte Slotregeln

| Saison | QB | RB | WR | TE | FLEX | WRRB_FLEX | REC_FLEX | K | Summe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024 | 1 | 2 | 2 | 2 | 2 | 1 | 1 | 1 | 12 |
| 2025/2026 | 2 | 2 | 2 | 2 | 4 | 0 | 0 | 1 | 13 |

Eine erste interaktive Rechnung hatte irrtümlich für 2024 die 2025er Slotstruktur angenommen. Ihre Werte wurden **verworfen**, die 2024er Durchläufe danach mit globalem Assignment und den historischen Slottypen neu gerechnet.

## Week-11-2026 Live-Sensitivität (kein Aktivierungsvorschlag)

3.000 unabhängige Normal-Samples aus den aktuellen PI1-Intervallen im vor-Lock aktiven CP2-Kandidatenpool, anschließend jeweils globale Best-Ball-Wahl (bei dieser Saison entspricht die Positionsstruktur zwei QB und vier FLEX).

| Manager | Simulierter Best-Ball-Aufschlag zum projizierten Wochen-Best-Ball |
|---|---:|
| Mighty Giants | +17,1 % |
| Marcel | +18,6 % |
| Flo | +18,4 % |
| Jan | +22,9 % |
| Dennis | +29,1 % |
| Tim | Incomplete: zweiter QB-Pflichtslot unbesetzt |

Dies sind modellabhängige theoretische **Ex-post-Best-Ball**-Werte, nicht die Erwartung realer Starterentscheidungen oder von Injury-Risiko bereinigte Scores.

## Historischer Gegencheck – alle sechs Teams, Wochen 5 bis 10

Diese explorative Auswertung umfasst 108 archivierte Team-Wochen (2024/25/26 × 6 Wochen × 6 Teams). 2024 jeweils 800 Samples, 2025 und 2026 jeweils 1.200 Samples pro Team-Woche. Sie vergleicht **den theoretischen Ex-post-Best-Ball** mit TWP.PotentialPoints, noch nicht tatsächliche Starterpunkte mit einer Manager-Expected-Score-Prognose.

| Saison | Team-Wochen | Sim. Uplift* | Beobachteter Uplift* | Sim. Bias (Pkt.) |
|---|---:|---:|---:|---:|
| 2024 | 36 | +21,3 % | +10,8 % | +19,0 |
| 2025 | 36 | +21,9 % | +13,5 % | +17,7 |
| 2026 | 36 | +20,6 % | +10,0 % | +21,7 |
| **Gesamt** | **108** | **+21,2 %** | **+11,4 %** | **+19,4** |

* Mittelwert der individuellen Team-Wochen-Verhältnisse zum aus den jeweiligen PWF-Mittelwerten optimalen Best Ball, nicht gepoolter Quotient von Saison-Gesamtsummen. Rundungen und Approximation der simulierten Verteilung berücksichtigen.

| Qualitätsmaß (108 Team-Wochen) | Raw projizierter Best Ball | Unkalibrierter Monte-Carlo-Best-Ball |
|---|---:|---:|
| MAE, niedriger besser | 29,25 Pkt. | 28,33 Pkt. |
| Bias (Forecast − TWP Actual) | −22,06 Pkt. | +19,43 Pkt. |
| Nominelle Abdeckung des 80-%-Intervalls | nicht geprüft | nur 56,5 % |

**Befund:** Die unkalibrierte Simulation erzeugt einen deutlich höheren Aufschlag als historisch beobachtet. Sie verbessert den MAE im gepoolten Forschungssample nur marginal und verlagert die negative systematische Abweichung in eine positive. Der 80-%-Coverage-Wert weist auf eine nicht belastbare Verteilungsprognose hin. Die Schätzer sind explorativ: keine statistische Überlegenheits- oder Stabilitätsaussage angesichts der korrelierten Team-Wochen und der Testfall-Auswahl.

## Warum der Unterschied nicht einfach mit einer festen Skala behoben werden sollte

1. **Distribution:** PWF-PI1 liefert Intervallgrenzen, aber keine garantierte symmetrische Normalverteilung. Die Umrechnung aus zwei Grenzen ignoriert Schiefe, diskrete Touchdowns und tails. Zusätzlich erlaubt die Gaussian-Fiktion negative Fantasy-Scores und kann einzelne extrem positive Ausreißer überzeichnen.
2. **Dependence:** Spieler eines Teams/eines NFL-Spiels sind korreliert, teilweise negativ (z. B. alternative Receiver) oder positiv (QB + Receiver). Unabhängige Ausreißer auf 30 Fantasy-Spielern erzeugen künstlich viele austauschbare Highs.
3. **Teilnahme:** Conditional-on-participation PWF gilt nicht als sicher availability-adjusted; OUT, QUESTIONABLE und unklare Ersatzrollen müssen probabilistisch betrachtet werden, wenn eine reale Spieltagsverteilung modelliert wird.
4. **Kaderbasis:** Historischer gesamter Wochenkader einschließlich IR/Taxi versus Live-Active-only; retrospektive TWP-Auswahl ist keine real einsatzfähige IR/Taxi-Aufstellung.
5. **As-of-Historie:** Archivier­te finale Wochenkader können nach Dienstag verändert worden sein; echte Dienstag-Starts, Waiver-/Move-Constraints und tatsächliche Zwischen-Locks liegen nicht lückenlos vor. Auch historische PWF-Revisionsstände wurden nicht vollständig eingefroren.
6. **Zielvariable:** Selbst ein perfekt kalibriertes erwartetes Ex-post-Optimum sagt die tatsächliche Managerentscheidung nicht ohne eigenes Coach-/Lineup-Modell vorher. Die historischen tatsächlichen Effizienzen werden deshalb nicht einfach auf diese Simulation multipliziert.

## Entscheidung und nächste Grenzen

- **Nicht aktivieren:** Kein pauschaler +11,6-%-Uplift und kein unkalibrierter +21-%-Monte-Carlo-Aufschlag in `HybridExpected`; weder `win-prob-v1` noch UI-Werte ändern.
- **Nächste Forschung:** Prüfen, ob bereits verfügbare empirische residuelle Verteilungen/Positions-Buckets und gemeinsame NFL-Spiel-Faktoren die Selektionsverteilung plausibler machen, getrennt von einem expliziten Spielteilnahme-/Availability-Mechanismus. Diese Varianten müssen mit identischen historischen Wochen und echten As-of-Splits (so weit nachweisbar) evaluiert werden.
- **Manager-Punkte:** Später gelockte Starterpunkte/Projektionen und verbleibende flexible Slots als **andere** Zufallsvariable modellieren; historische Actual Efficiency bleibt retrospektive Managerkennzahl, nicht automatische zukünftige Verteilungsregel.
- **Siegchance:** Erst nach Punkte- und Intervallkalibrierung Brier, Calibration, LogLoss und historische Matchup-Baselines gegen bestehende v1 evaluieren. Kein v2 ohne gesonderte Modell-/Contract-Abnahme.

**Risiko/Publikation:** Research-only im Repository; keine Source-/Derived-/public/data-/Workflow-/App-Mutation. Entfernbar durch Revert des Research-Commits. Der Live-CP2-Shadow bleibt unverändert.
