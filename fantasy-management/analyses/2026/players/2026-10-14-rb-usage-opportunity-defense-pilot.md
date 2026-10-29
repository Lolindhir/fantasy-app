# RB-Usage × Defense Opportunity/Efficiency – historischer Walk-forward-Pilot

**Analysedatum:** 2026-10-14  
**Work Package:** [#978](https://github.com/Lolindhir/fantasy-app/issues/978)  
**Hypothese:** HYP-RB-PROFILE-001A/B/C (`proposed`)  
**Vorgänger:** [RB-Produktionsprofil × Defense-Split Pilot vom 14.10.2026](2026-10-14-rb-production-defense-matchup-pilot.md)  
**Stand der untersuchten Repository-Basis:** [`a0ff68f49381009bdc118f89038042e43cb6f9b0`](https://github.com/Lolindhir/fantasy-app/commit/a0ff68f49381009bdc118f89038042e43cb6f9b0) (Ankunfts-Snapshot; die untersuchten 2024-/2025-Partitionen wurden nach ihren Git-Blobs gelesen).  
**Status:** datierter Research-Checkpoint; keine validierte Produktionsregel, keine Änderung an App, Projection oder Spieler-`Grading`.

## Kurzfazit

- **Ja, Defense-Matchup-Fakten sind bereits aus unseren Daten rekonstruierbar**, ohne D/ST-Fantasy-Scores. Aus kanonischen Player-Stats je Team/Gegner/Spiel können wir gegen RBs zugelassene Carries, Targets, Receptions, Rushing-/Receiving-Yards, PPR und Effizienz ableiten.
- **Das Signal ist deskriptiv aussagekräftig:** 2025 ließen die Broncos gegnerischen RBs **4,24 Targets/Spiel** und **12,1 % RB-Target-Share** der gegnerischen Passversuche zu; die Seahawks **7,24 Targets/Spiel** und **20,5 %**. Dabei waren die Receiving-Yards pro RB-Target ähnlich (**5,01 vs. 4,90**). Viel/wenig Gelegenheit ist nicht dasselbe wie gute/schlechte Effizienz.
- **Der simple wöchentliche Prognoseeinsatz ist bisher nicht erfolgreich:** Bei **2.190 ex ante auswertbaren RB-Spieler-Spielen** über die abgeschlossenen Seasons 2024 und 2025 war die einfache season-to-date PPR/Spiel-Baseline bei **MAE 5,058**, eine naive Recent-Usage-Projektion bei **5,211** und Usage + Defense-Faktoren bei **5,205**. Ein zusätzlicher Defense-RB-Target-Share-Faktor direkt auf die PPG-Baseline ergab **5,071**. Unterschiede sprechen **nicht** für automatische Defense-Multiplikatoren.
- **Konsequenz:** Defense-Profile als explorative, explainable Information weiter erforschen, aber **nicht** still in Player Projections, Start/Sit oder Fantasy-`Grading` einspeisen. Der nächste Kandidat ist ein stabilisiertes **Role-/Usage-Change-Modell** plus defenseseitige Opportunity unter Kontrolle der gegnerischen Offensive, nicht ein isolierter Saisonmultiplikator.

## Fragen und Hypothesen

- **001A:** Ist eine über mehrere Spiele stabile Rolle (Carries/Targets, gegebenenfalls Snaps/Routes, Splits) prognostisch verlässlicher als jüngste beobachtete Usage allein?
- **001B:** Sind gegen eine Defense zugelassene Positions-Opportunities (*RB-Target-Share*) und Effizienz (*Receiving Yards pro RB-Target*, *Rushing Yards pro RB-Carry*) differenziertere Merkmale als PPR-Allowed?
- **001C:** Können diese Daten die **produktive V4-C/V4-C-PI1** aus [#697](https://github.com/Lolindhir/fantasy-app/issues/697) *out of sample* schlagen? **Noch nicht getestet.**
  
Forschungsstatus der allgemeinen Hypothesen: **`proposed` / offen**. Die hier getesteten **einfachen Ausprägungen** erhalten für den vorliegenden Zeitraum **keine positive Validierung**.

## Daten und Reproduktion

- **Quelle:** `source-data/nfl/player-stats/2024/{01..18}.json` und `source-data/nfl/player-stats/2025/{01..18}.json`; alle **36 Partitions `Finalized=true`**. Je Player-Week: `CanonicalPlayerID`, `Position`, `Team`, `OpponentTeam`, `Stats.game_id` und Einzelstatistiken.
- **Ligakontext:** `source-data/leagues/nfl-reise/seasons/2026/league.json -> ScoringSettings`; klassische PPR-Kernbestandteile: Rush Yards × 0,1; Rec Yards × 0,1; Receptions × 1; Rush/Rec TD × 6; 2PC × 2. **Outcome:** vorhandenes `Stats.fantasy_points_ppr` (nflverse), **nicht** endgültig liga-rekonstruierter Player-Score. Passing/Return/Turnover-Edge-Cases bleiben Residuum.
- **Population:** `Position=RB` und im Spiel mindestens ein `carries` oder `targets`. 2024: **1.359** RB-Games; 2025: **1.356** RB-Games. Für den Walk-forward-Test: Spieler hat vor Zielwoche mindestens 2 solche Games, gegnerische Defense mindestens 2 vorherige Team-Games, Liga mindestens 30 vorige Team-Games. 2024 **1.099**, 2025 **1.091** Predictions. Jede Saison beginnt mit leerer In-Season-Historie; keine Vorjahresinformation.
- **Defense-Spielzeile:** Aggregation der RB-Records *des gegnerischen Offense-Teams* nach `OpponentTeam` und `Stats.game_id`, je Spiel mit Team/RB `carries`, `rushing_yards`, `targets`, `receptions`, `receiving_yards`. Als Nenner der gegnerischen Passversuche werden die `Stats.attempts` sämtlicher Players auf der Offense-Seite dieses Team-Games summiert. Dadurch auch Team-Games ohne RB-Beteiligung im Defense-Nenner; 32 × 17 = **544** Team-Games je Saison.
- **Leakage-Regel:** Für Ziel-Week `W` ausschließlich vor `W` beobachtete Spieler-Games und Defense-Team-Games derselben Saison, einschließlich Ligadurchschnitt, verwenden. Kein `W`-Outcome in Feature oder Parameteranpassung. `Bye` wird nicht als Null-Spiel gezählt.
- **Einschränkung:** Kein Injury-/Start-/Rollenwechsel-Gate, keine positionsspezifischen Pass-/Rush-Game-Script-Adjustments, keine Strength-of-Offense-Korrektur, keine Route-/Coverage-Evidenz, keine mehrjährige Parameteroptimierung. Alle Modellparameter bewusst vor dem Vergleich fix gewählt und nicht als optimal anzusehen.

### Exakt getestete Modellvarianten

1. **PPG-Baseline:** arithmetischer Mittelwert `fantasy_points_ppr` über bisherige aktive RB-Games (≥2).
2. **Recent Usage:** letzte maximal 3 aktive Spiele mit chronologisch aufsteigenden linearen Gewichten `1,2,3` (bei 2 Spielen `1,2`). Prognostizierte Carries × über bisherige Saison aggregierte positive Rush-Punkte pro Carry + prognostizierte Targets × positive Receiving-Punkte pro Target + durchschnittliches Residuum des Player-PPR gegenüber den zwei Punktsplits. Dies modelliert jüngstes **Volumen**, nicht geänderte Effizienz.
3. **Defense Target Share direkt auf PPG:** wie 1, aber Season-Receiving-Komponente × `fTarget`.
4. **Recent Usage + Defense Target Share:** wie 2, aber Receiving-Komponente × `fTarget`.
5. **Recent Usage + Defense Efficiency:** wie 2, aber nur Rushing-*Yard-Punkte* × `fRushYPC` und Receiving-*Yard-Punkte* × `fRecYPT` modifizieren; Receptions/TDs/Residuum nicht direkt skalieren.
6. **Recent Usage + beide Defense-Arten:** 4 und 5 kombiniert.

Die gegnerische RB-Target-Share ist `sum(RB targets allowed) / sum(opponent pass attempts)`. Relativer Defense-Faktor gegenüber dem **bis W−1** beobachteten Ligadurchschnitt:

`fTarget = clamp(1 + n/(n+4) × (DefenseRBTargetShare / LeagueRBTargetShare − 1), 0.70, 1.30)`.

`fRushYPC` und `fRecYPT` analog für *zugelassene* Yards/Carry bzw. Yards/Target mit denselben `n/(n+4)` und `[0.70; 1.30]`-Grenzen, aber jeweils nur auf die entsprechende Yard-Komponente. `n` ist die Zahl früherer Defense-Team-Games. Alle diese gewählten Faktoren sind **hypothetisch / unkalibriert**; das Ergebnis belegt nicht ihren optimalen Wert.

### Walk-forward-Fehler (MAE, niedriger besser)

| Modell | 2024 (N=1.099) | 2025 (N=1.091) | 2024+2025 (N=2.190, N-gewichtet) |
| --- | ---: | ---: | ---: |
| Season PPG | **5,034** | **5,081** | **5,058** |
| Recent Usage (Carries/Targets) | 5,090 | 5,332 | 5,211 |
| Season PPG + Defense RB-Target-Share | 5,033 | 5,110 | 5,071 |
| Recent Usage + Defense RB-Target-Share | 5,077 | 5,355 | 5,215 |
| Recent Usage + Defense YPC/YPT | 5,078 | 5,325 | 5,201 |
| Recent Usage + beide Defense-Faktoren | 5,066 | 5,346 | 5,205 |

2025 Receiving-Anteil-Kohorten (Anteil positiver Receiving-Punkte aus historischen Rush-/Rec-Splits):

| Kohorte | N | PPG MAE | Recent Usage MAE | Usage + Target Share MAE |
| --- | ---: | ---: | ---: | ---: |
| Receiving ≥50 % | 349 | 4,485 | 4,563 | 4,629 |
| Receiving 20–50 % | 518 | 5,782 | 6,204 | 6,207 |
| Receiving <20 % | 223 | 4,398 | 4,524 | 4,528 |

**Qualifikation:** Die Kohortenzuordnung basiert auf **vor** der jeweiligen Zielwoche beobachteten Rush-/Rec-Punkten. Eine weitere einzelne Beobachtung mit null/negativer Summe wurde keiner der drei Kohorten zugeordnet (Gesamt-N 1.091; Kohorten-N 1.090). Für 2024 liegt kein signifikanter gesamthafter Vorteil vor: kleine Einzelkohorten und späte Wochen können anders ausfallen. **MAE-Differenzen sind nicht statistisch getestet;** kein Kausalitäts- oder Signifikanzanspruch.

## 2025 Defense-Steckbrief: alle 32 NFL-Teams, nur gegen RBs

**Deskriptive Saisonaggregation, nicht ex ante auf jedes einzelne Spiel anwendbar.** 17 Team-Games je Defense. `RB Target Share` = gegnerische RB-Targets / gegnerische Passversuche; `RB Targets/G` = RB-Targets pro Defense-Spiel; `Rec Yds/Tgt` = zugelassene Receiving-Yards pro RB-Target; `RB Carries/G` und `Rush Yds/Carry` analog. Diese Werte enthalten **Opponent-Mix und Game Script** und sind keine isolierten Defense-Qualitätsmaße.

| Defense | RB Target Share | RB Targets/G | Rec Yds/Tgt | RB Carries/G | Rush Yds/Carry |
| --- | ---: | ---: | ---: | ---: | ---: |
| DEN | 12,1 % | 4,24 | 5,01 | 18,59 | 3,86 |
| TEN | 13,8 % | 4,18 | 6,30 | 21,18 | 4,31 |
| NO | 14,1 % | 4,06 | 5,74 | 25,59 | 4,01 |
| DET | 14,2 % | 4,65 | 5,29 | 20,71 | 4,30 |
| IND | 15,0 % | 5,53 | 4,40 | 21,71 | 4,00 |
| WAS | 15,0 % | 4,76 | 6,84 | 24,71 | 4,67 |
| NYJ | 15,5 % | 4,71 | 7,34 | 25,24 | 4,36 |
| PHI | 15,8 % | 5,06 | 7,37 | 23,06 | 4,17 |
| MIN | 15,9 % | 4,18 | 4,66 | 26,88 | 3,91 |
| KC | 15,9 % | 4,76 | 5,83 | 20,59 | 4,03 |
| TB | 16,0 % | 5,35 | 9,35 | 18,29 | 4,31 |
| PIT | 16,0 % | 5,76 | 5,41 | 22,41 | 4,30 |
| JAX | 16,1 % | 6,00 | 5,43 | 17,53 | 3,86 |
| CHI | 16,1 % | 5,06 | 5,30 | 21,53 | 4,84 |
| ARI | 16,3 % | 5,47 | 6,26 | 23,82 | 4,76 |
| LAC | 16,6 % | 4,94 | 4,86 | 19,71 | 4,30 |
| HOU | 16,7 % | 5,29 | 5,97 | 19,65 | 3,74 |
| NYG | 16,9 % | 5,47 | 5,46 | 21,12 | 5,52 |
| GB | 17,3 % | 5,59 | 4,75 | 24,12 | 4,17 |
| ATL | 17,4 % | 5,41 | 5,54 | 22,12 | 4,51 |
| LV | 17,6 % | 5,41 | 4,89 | 24,24 | 4,03 |
| LA | 17,8 % | 6,18 | 5,91 | 20,88 | 4,24 |
| DAL | 17,8 % | 5,82 | 7,41 | 20,18 | 4,72 |
| MIA | 17,9 % | 5,41 | 6,57 | 22,29 | 4,81 |
| CLE | 18,3 % | 5,24 | 4,99 | 22,71 | 4,24 |
| CAR | 18,3 % | 5,47 | 5,24 | 23,18 | 4,59 |
| BAL | 18,4 % | 6,76 | 6,30 | 19,65 | 4,18 |
| NE | 18,6 % | 5,76 | 5,18 | 19,65 | 3,93 |
| CIN | 18,7 % | 5,88 | 7,11 | 22,88 | 5,21 |
| BUF | 19,2 % | 5,24 | 4,75 | 21,53 | 4,98 |
| SF | 19,3 % | 6,65 | 5,37 | 20,71 | 4,49 |
| SEA | 20,5 % | 7,24 | 4,90 | 20,59 | 3,54 |

### Gegenbeispiele und mögliche Archetypen

- **DEN vs. SEA:** DEN sehr niedrige *RB-Opportunity* (4,24 Targets/G; 12,1 % Target Share); SEA hohe *RB-Opportunity* (7,24; 20,5 %). Beide erlaubten jedoch etwa fünf Receiving-Yards pro RB-Target – **das Opportunity-/Efficiency-Profil ist unterschiedlich**, nicht einfach „gute vs. schlechte Passing Defense“.
- **TB:** 5,35 RB-Targets/G bei **9,35 Receiving-Yards pro RB-Target**. Deskriptiv eher auffällige zugelassene *Receiving-Effizienz* als besonders hohes RB-Target-Volumen.
- **HOU vs. NYG:** RB-Rushing-Allowed **3,74 vs. 5,52 Yards/Carry**. Ein pauschales RB-Fantasy-Points-Allowed-Rating vermengt diesen Unterschied mit Volumen und Receiving.
- **BAL:** 2025 relativ viel RB-Passing-Opportunity zugelassen (**6,76 Targets/G; 18,4 % Target Share**), während ein vorläufiger W1–5-Snapshot 2026 aus der **separaten** Vorgängeranalyse relativ wenige RB-Receiving-PPR-Points zeigt. Die unterschiedlichen Seasons, Zeitfenster, Metriken und unfinalisierte 2026-Daten **dürfen nicht als direkte gegensätzliche Defensetrends verkauft werden**.

**Interpretationsgrenze:** Niemand kann aus diesen Aggregaten allein beweisen, dass die Defense bestimmte Plays *verursacht* oder *verhindert*. Gegnerspielstile, Spielstand und offensive Qualität beeinflussen die Werte.

## Weiterentwicklung: erklärbares Defense-Scouting für 32 Teams

**Fachliche Zielidee, keine Implementierungsfreigabe:** Teambezogene Defense-Profile nach gegnerischer Offense-Position und Fantasy-Rolle, mit ausdrücklicher Zeit-/Sample-/Evidenzkennzeichnung.

| Facette | Beispiel RB | Spätere Übertragung / zusätzlicher Datenbedarf |
| --- | --- | --- |
| Opportunity allowed | RB Targets/G, RB Target Share, Carries/G | WR-/TE-Target Shares, QB-Passversuche; jeweils positionsbezogen |
| Efficiency allowed | RB Receiving Yds/Target; Rush Yds/Carry | WR/TE Yds/Target, QB Yds/Attempt, Sack Rate |
| Fantasy-scoring fit | PPR-komponentengetrennte Punkte | Liga-Scoring, TDs, Turnovers getrennt, Varianz |
| Usage/role of player | Carries, Targets, 3rd Down, 2-minute, Red Zone | Snaps ggf. aus `source-data/nfl/snap-counts/**`; Routes/Coverage **nicht** aus aktuell geprüften Stats belegt |
| Context controls | Opponent-Mix, Pass-/Rush-Volumen, Game Script, Injury | weitere verifizierte NFL Facts/Externe Daten nur nach Quellenprüfung |
| Confidence | Sample Size, `Finalized`, Shrinkage, zeitlicher Verlauf | Kein „starkes“ Matchup-Label ohne ausreichende Evidenz |

Die 32 Defense-Steckbriefe können zunächst **abgeleitete, datierte Forschungs-Outputs** sein. Später wäre bei fachlicher Freigabe eine deterministische `Defense vs Role`-Materialisierung aus Source Facts denkbar. Sie darf nicht als handgepflegter aktueller Spielerfakt oder als konkurrierende Source of Truth entstehen.

## Empfohlener nächster Versuch

1. **Stabilität der Rolle:** statt „letzte drei Spiele strikt stärker gewichten“ zuerst Trends auf echte Role Changes (Injury/Coach/Personnel/Routes/Snaps) prüfen; im Normalfall regressiv zur längeren Baseline.
2. **Opponent-normalisiertes Allowed:** gegnerische RB-Target-Rate und Efficiency gegen das vergleichen, was deren Offenses gegen andere Defenses normalerweise produzieren (leave-one-opponent-out / walk-forward, ohne zukünftige Games).
3. **V4-C-Vergleich und mehrjährige Validation:** dieselbe zulässige Player-Game-Population und exakt liga-spezifische Points, mindestens 2024/25, gegen produktive #697-Baseline testen. Auf Hold-out/zeitliche Trennung achten.
4. **Nur bei nachgewiesenem Mehrwert** eine begrenzte Matchup-Justierung vorschlagen; andernfalls Defense-Profil als reine interpretierbare *Research-/Scouting-Evidenz* für Grenzentscheidungen anbieten.

**Status:** `HYP-RB-PROFILE-001A/B/C = proposed`. Die getesteten simplen Recent-Usage- und Defense-Heuristiken zeigen in der Gesamtheit **keinen sinnvollen Prognosevorteil**. Keine Anpassung von `Grading`, Weekly-Rules, Datencontract oder Pipeline.
