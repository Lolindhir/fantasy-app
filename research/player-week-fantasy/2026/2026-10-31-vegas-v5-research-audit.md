# PlayerWeekFantasy – Vegas/Defense: V5-Forschungs-Audit

**Stand:** 31.10.2026. **Urteil:** `inconclusive`; Vegas-V5 **nicht produktiv ausrollen**.  
**Ursprung:** [Issue #978](https://github.com/Lolindhir/fantasy-app/issues/978). **Modell-/Produktvertrag:** [PlayerWeekFantasy](../../../.ai-context/manual/player-week-fantasy.yaml) / [#697](https://github.com/Lolindhir/fantasy-app/issues/697).  
**Historische Primärbelege:** [alle Checkpoints 3–9 aus #978, unverändert archiviert](2026-10-31-vegas-v5-checkpoints.md).  
**Vorstudien:** [RB-Production/Defense-Pilot](2026-10-14-rb-production-defense-matchup-pilot.md), [RB-Usage/Opportunity/Defense-Pilot](2026-10-14-rb-usage-opportunity-defense-pilot.md).

## Gegenstand und bewusst getrennte Ziele

Die primäre Forschungsfrage ist, **ob zusätzliche Vegas-/Matchup-Features die Punktschätzung pro Spieler (MAE/RMSE/Bias)** verbessern, nicht ob einzelne hypothetische Start/Sit-Entscheidungen zufällig mehr Punkte ergeben. Der Sekundärtest fragt, ob vorhandene **V4-C-PI1-Prediction-Ranges** durch Vegas besser kalibriert werden. Die bereits vorhandenen Intervalle liegen bei 50/80/90 %.

## Daten und Evaluationslogik

- Historische Kalibrierung **2024 W4–17**, finale Evaluation **2025 W4–17**, daneben diagnostische Fantasy-Lineup-Proxies aus **2026 W4–7**.
- NFL-Quelle: `data-source/providers/nflverse/player-stats/raw-{2024,2025}.csv`, IDs via `data-source/nfl/rosters/{2024,2025}.json`. Abgeleitetes Ausgangsmodell / liga-spezifische PPR-Actuals: `data-derived/player-week-fantasy/nfl-reise/{2024,2025}/{04..17}.json`. Vegas-Daten: `data-derived/nfl-games/<season>.json`.
- Gleicher Positions-Kandidatenpool pro Modell: tatsächlich aktive Offensive-Beteiligung (QB Pass Attempts + Carries; RB/WR/TE Carries + Targets), mindestens zwei frühere aktive Player- und drei abgeschlossene Team-Games, available V4-C-Projektion und finaler liga-spezifischer Actual.
- Damit **conditional-on-actual-participation**, keine ex-ante vollständige Injury-/Verfügbarkeits-Population. Historische `nflverse.schedule-odds` **ohne nachgewiesenen ursprünglichen Pregame-Timestamp** – retrospektive Odds-As-of und mögliches Leakage sind ein wesentliches offenes Gate.
- Original-Vegas-B: additive Ridge-Korrektur ohne Intercept, auf **±1 PPR** begrenzt. Drei Features: (1) Implied Team Score minus Mittel der letzten drei tatsächlichen Team Scores, (2) eigener Implied Points Margin, (3) Game Total minus 43. Positionseigene Skalen/Betas aus 2024, Ridge λ32, Featurecap ±5, **kein Refit auf 2025**. Die exakten Parameter, Replay-Checks, Fehlerkorrekturen und Quellen stehen im Checkpoint-Anhang.
- Eine spätere **andere** Ridge-B-Version mit Intercept, Ridge λ512 und Cap ±2 zeigte RB MAE 5,0020; **nicht mit der ursprünglichen B-Reproduktion 5,0301 verwechseln**.

## 1. Kernresultat: Point-Predictions

MAE kleiner besser; Liga-PPR pro Spieler-Spiel, 2025 REG W4–17.

| Position | 2024 Fit N | 2025 N | V4-C | +Vegas-B | ΔMAE relativ | Bootstrap 95 %-Intervall (Δ PPR) |
|---|---:|---:|---:|---:|---:|---|
| RB | 964 | 951 | 5,064883 | 5,030093 | **−0,69 %** | [−0,07045; +0,00316] |
| QB | 451 | 441 | 6,687356 | 6,676145 | −0,17 % | [−0,08729; +0,05889] |
| WR | 1491 | 1484 | 4,873208 | 4,877971 | +0,10 % | [−0,00523; +0,01493] |
| TE | 761 | 785 | 3,952198 | 3,988486 | **+0,92 %** | [+0,01349; +0,05724] |

Die zusätzliche RB-Rollen-/Defense-Ablation verbessert B im MAE nicht: V4-C **5,0649**, B **5,0301**, Rolle+Vegas C **5,0496**, Rolle+Vegas+Defense D **5,0542**. Original B/C/D wurden nach Script-Rekonstruktion unabhängig reproduziert (siehe Checkpoints).

## 2. Exploration extremer Spielumfelder (RB)

Schwellen und Untergruppen **nachträglich exploriert**, teils überlappend, 2025 bereits mehrfach inspiziert: Bootstrap-Intervalle *nicht* als unberührte prospektive Evidenz ansehen.

| RB 2025 | N | MAE V4-C | MAE +B | Relative Änderung |
|---|---:|---:|---:|---:|
| Alle | 951 | 5,0649 | 5,0301 | −0,69 % |
| **Team-Implied ≤18 Punkte** | 129 | 5,0685 | 4,8740 | **−3,84 %** |
| Team-Implied ≥28 | 81 | 5,5726 | 5,6337 | +1,10 % |
| Underdog (7+ Spread) | 153 | 5,0503 | 4,9473 | −2,04 % |
| Favorit (7+ Spread) | 161 | 5,3945 | 5,4564 | +1,15 % |
| Game Total ≥50 | 111 | 5,2396 | 5,1683 | −1,36 % |
| Game Total <40 | 116 | 4,6777 | 4,5613 | −2,49 % |

Das auffälligste Segment **Low-Implied RB** umfasst **56 NFL-Team-Wochen**, verbessert den absoluten Fehler in **13/14 Wochen**, gepaartes Wochenbootstrap 95 % **[−0,2694; −0,1068] PPR**; aber **RMSE 6,8777→6,8912 leicht schlechter**. Das Segment wurde im Material gefunden, nicht in einem unabhängigen Test bestätigt. Eine automatische ≤18-Gating-Regel wäre Overfitting.

## 3. PI1-Ranges: kein nachgewiesener Vegas-Mehrwert

Experiment: Vorhandenes V4-C-PI1-Intervall **nur um B-Korrektur verschieben, gleiche Breite**, kein neues Interval-/Streuungsmodell. Gesamt-RB 2025:

| Kennzahl | PI1 | PI1 + B shift |
|---|---:|---:|
| 50%-Coverage | 50,5 % | 52,1 % |
| 80%-Coverage | 78,5 % | 78,3 % |
| 90%-Coverage | 89,3 % | 89,4 % |
| 80%-Intervallscore | 23,785 | 23,666 |
| 90%-Intervallscore | 28,477 | 28,326 |
| **Low-Implied-RB: 80%-Coverage** | 78,3 % | 81,4 % |
| **Low-Implied-RB: 80%-Intervallscore** | **23,225** | **23,968** |

Intervallscore bestraft Breite **und** Überschreitungen der Grenzen (niedriger besser). Der bloße Vegas-Center-Shift verschlechtert gerade im interessanten Low-Implied-RB-Segment den Score; **keine Evidenz für verbesserte optimale Range-Breite**.

## 4. Start/Sit nur als getrennter diagnostischer Proxy

2025-RB-Same-Fantasy-Team-Week-Pool: 83/84 Team-Wochen auswertbar, +50,2 PPR über 12 geänderte Picks, aber finaler Pool kein nachgewiesener legaler Pre-Lock-Kandidatenpool.

Vier archivierte 2026er Sunday-Pregame-App-Snapshots: 24 Team-Wochen, nur **16 vollständig**, acht partial. Auf den vollständigen Team-Wochen: nur RB **2 Wechsel / +12,1 PPR**, nur QB **1 / +12,2**, nur WR **2 / −1,5**, nur TE **1 / +0,8**, alle Positionen zusammen **3 / +25,1**. Besonders W4 Mammoth Burrow statt Hurts (+12,2), Harvey statt Burden (+7,9), W7 Harvey statt Goedert (+4,2). **Nicht addierbare, nicht prospektiv nachgewiesene Resultate**; historisches Odds-As-of weiterhin ungeklärt. Kein Nachweis, dass ein einzelnes Punktmodell für Start/Sit optimiert werden sollte.

## 5. Quality Gates und Abschluss

- **Raw→canonical RB/FB Feldparität** 2024+2025 REG W01–17: **3.063 matched Rows**, null Abweichungen in den geprüften Feldern; kein Audit aller NFL-Felder.
- Originales `rb_v5_ablation.py` war zunächst nur Chat-Artefakt, später wiedergefunden und B/C/D über GitHub-Quellen rekonstruiert. Die einzelnen End-to-End-Behauptungen und ihre Geltungsgrenzen sind im [Checkpoint-Archiv](2026-10-31-vegas-v5-checkpoints.md) datiert.
- Für echte spätere Validierung: **zeitgestempelte Pregame-Odds**, fixierte Thresholds, neue Holdout-Wochen/Seasons, getrennte Punktfehler- vs Intervall- vs Entscheidungsmetriken. Kein eigenständiger Writer-/Scheduler-Ausbau ausschließlich wegen Vegas.
- **Produktentscheidung:** V4-C und V4-C-PI1 bleiben unangetastet; kein V5 Vegas, kein Extrem-Matchup-Hardcode, keine automatische Start/Sit-Korrektur. Das ist ein dokumentierter **vorläufig negativer Integrationsentscheid**, kein Beweis, dass Vegas grundsätzlich niemals nützlich sein kann.

**Archivprovenienz:** Konsolidierte Darstellung der früheren Audits aus #978; die Migration selbst führt **keinen neuen Modelltest** aus.
