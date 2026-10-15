# RB-Produktionsprofile × Defense-Matchups – explorativer Pilot

**Analysedatum:** 2026-10-14  
**Hypothese:** HYP-RB-PROFILE-001 (`proposed`)  
**Work Package:** [#978](https://github.com/Lolindhir/fantasy-app/issues/978)  
**Kontext:** [Player-/Matchup-Projections #697](https://github.com/Lolindhir/fantasy-app/issues/697), [Weekly Lineup/Waiver #206](https://github.com/Lolindhir/fantasy-app/issues/206)  
**Status:** Explorativ; **keine validierte Prognoseregel**, keine produktive Anpassung.

## Frage und wichtigste Ergebnisse

1. **Defense-Fakten sind bereits teilweise ableitbar:** Die kanonischen NFL-Player-Week-Stats liefern u. a. `Position`, `Team`, `OpponentTeam`, `carries`, `rushing_yards`, `rushing_tds`, `targets`, `receptions`, `receiving_yards` und `receiving_tds`. Ein Group-by `OpponentTeam` + `game_id` über die RB-Zeilen ergibt pro gegnerischer NFL-Defense die zugelassene Rushing-/Receiving-Produktion **aller RBs des gegnerischen Teams**. Es ist **kein eigenständig persistiertes Defense-gegen-RB-Readmodel** nötig, um einen Pilot durchzuführen.
2. **D/ST-Scoring ist etwas anderes:** In der aktiven Fantasy-League `source-data/leagues/nfl-reise/seasons/2026/league.json` sind zwar Defense-Scoring-Keys vorhanden, doch `RosterPositions` enthält keinen D/ST-Starterplatz. D/ST-Scoring beantwortet die Matchup-Frage RB-Receiving-Allowed nicht direkt.
3. **Chase Brown 2026 W1–5:** 30,6 positive Rushing- vs. 36,4 positive Receiving-Punkte im einfachen PPR-Split; Receiving-Anteil 54,3 %. In W4 gegen JAX steckten jedoch allein 18,1 Receiving-Punkte aus 11 Catches / 71 Receiving Yards. **Ohne W4 liegt der Receiving-Anteil nur bei 38,2 %**. Der Produktionsmix allein ist daher noch kein stabiler Spielerrollen-Indikator.
4. **2026 Defense vs. RB:** BAL ließ W1–5 durchschnittlich **5,58 RB-Receiving-PPR-Punkte pro Team-Spiel** zu (NFL-Schnitt in diesem Material: **8,33**), Rang 4 der 32 Teams bei aufsteigenden erlaubten RB-Receiving-Punkten; RB-Rushing-Punkte BAL 13,18 vs. Liga 13,44. **Explorativ**, da die 2026er Weekly-Player-Stats-Partitionen W1–5 im Repository `Finalized=false` tragen. Browns Bengals haben W6 Bye, W7 wäre BAL der Gegner; W6-Ergebnisse und Rollenänderungen müssen vorher berücksichtigt werden.
5. **2025 Walk-forward Pilot:** Bei 510 evaluierten RB-Spieler-Spielen (Weeks 3–10, 2025 W1–10 finalisiert) war die einfache PPG-Baseline **MAE 5,201** und eine unkalibrierte, nach Gegner-Rushing/Receiving geteilte Defense-Korrektur **MAE 5,199**. Der Unterschied von **-0,002 Punkten** ist **praktisch null**. Für Receiving-lastige RBs verschlechterte sich MAE von 4,826 auf 4,828. **Kein empirischer Grund, jetzt einen automatischen Matchup-Multiplikator einzuführen.**

## 2026 – Spielerproduktionsprofile (W1–5)

Punkte aus `rush yards × 0,1 + rush TD × 6` bzw. `receptions × 1 + rec yards × 0,1 + rec TD × 6`, jeweils ggf. inkl. 2-Point Conversions; der individuelle PPR-Gesamtscore kann durch Fumbles und weitere Komponenten abweichen. Alle Werte aus aktuell nicht finalisierten Wochenpartitionen.

| RB | Spiele mit Carry/Target | Rush-Punkte | Rec-Punkte | Rec-Anteil |
| --- | ---: | ---: | ---: | ---: |
| Ashton Jeanty | 5 | 29,1 | 55,5 | 65,6 % |
| Chase Brown | 5 | 30,6 | 36,4 | 54,3 % |
| Jaylen Warren | 5 | 47,0 | 48,0 | 50,5 % |
| Kyren Williams | 5 | 58,3 | 53,0 | 47,6 % |
| Jahmyr Gibbs | 5 | 92,4 | 63,3 | 40,7 % |
| Christian McCaffrey | 5 | 58,6 | 32,7 | 35,8 % |
| Bijan Robinson | 5 | 82,0 | 39,2 | 32,3 % |
| Jonathan Taylor | 5 | 75,8 | 23,6 | 23,7 % |
| Derrick Henry | 5 | 89,6 | 20,2 | 18,4 % |

Chase Brown einzeln:

| Week | Gegner | Carries | Targets | Receptions | Rush-Pkt. | Rec-Pkt. | Gesamte PPR-Pkt. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | TB | 16 | 6 | 5 | 11,6 | 7,2 | 18,8 |
| 2 | HOU | 20 | 5 | 3 | 8,0 | 3,2 | 11,2 |
| 3 | PIT | 13 | 2 | 2 | 6,1 | 2,8 | 8,9 |
| 4 | JAX | 9 | 11 | 11 | 1,0 | 18,1 | 19,1 |
| 5 | MIA | 13 | 4 | 3 | 3,9 | 5,1 | 7,0 (inkl. -2 Fumble Lost) |

**Interpretation:** Eine einzelne ungewöhnliche W4 bestimmt fast die Hälfte von Browns Receiving-Punkten. Empfohlen sind mindestens Targets/Spiel, Rollentrend, Verteilung/Unsicherheit und ein robuster Ausreißercheck, bevor ein dauerhaftes „receiving-dominant“-Label vergeben wird.

## 2026 – Defense-Split gegen RBs (W1–5)

| NFL-Defense | RB-Rushing-Punkte erlaubt pro Spiel | RB-Receiving-Punkte erlaubt pro Spiel |
| --- | ---: | ---: |
| BAL | 13,18 | 5,58 |
| JAX | 6,60 | 9,72 |
| MIA | 13,72 | 12,80 |
| NFL-Durchschnitt | 13,44 | 8,33 |

**Wichtiger Ex-ante-Check:** Vor Browns W5 gegen MIA (nur MIA W1–4 bekannt) lag MIA bereits bei 12,47 erlaubten Receiving-Punkten an RBs pro Spiel, deutlich **über** dem Liga-Schnitt von 8,31. Ein statischer Defense-Faktor hätte daher eher ein günstiges Receiving-Matchup signalisiert. Brown erzielte trotzdem nur 7,0 Gesamt-PPR-Punkte (inkl. -2 Fumble). Er bekam 4 Targets statt 11 in W4. Das ist ein Gegenbeispiel gegen eine zu starke Gegnergewichtung.

**Limit:** Allowances messen sowohl gegnerische RB-Rollen / Game Scripts / Opponent-Quality als auch die Defense-Leistung. Liga-Ränge ohne Opportunity-Normalisierung sind **deskriptiv**, keine isolierten Defense-Effizienz-Ratings.

## 2025 – einfacher Walk-forward Pilot

**Daten:** `source-data/nfl/player-stats/2025/01.json` bis `10.json` (alle `Finalized=true`). Nur RBs mit mindestens einer Carry oder einem Target im jeweiligen Game; 2025 W1–10: **739 RB-Spiel-Beobachtungen mit mindestens einem Carry/Target**, 298 Defense-Team-Spiele. Davon erfüllen **510** Player-Games die Prognose-Inklusionsbedingungen.

**Ex-ante-Regeln, bewusst illustrativ:**
- Für Week W zunächst Spieler-Durchschnitt aus **allen vorangegangenen** Spielen mit Carry/Target; Spieler braucht mindestens zwei Vorgängerspiele.
- Defense-Allowed-Rushing-/Receiving-PPR/G aus **allen vorangegangenen** NFL-Team-Spielen, Defense braucht mindestens zwei Vorgängerspiele.
- Baseline = durchschnittliche individuelle PPR/G der laufenden Saison; modellintern auf Rush/Rec/Residual-Komponenten aufgeteilt.
- Opponent-Korrektur getrennt für Rush/Rec: Defense-/Liga-Ratio, zurückgezogen zu Faktor 1,0 mit vier fiktiven Durchschnittsspielen (Shrinkage `k=4`), anschließend auf `0,70–1,30` begrenzt.
- Keine Features aus W oder späteren Wochen zur Prognose von W. Parameter sind **nicht** optimiert und stellen keine validierte Modellkonfiguration dar.
- Outcome: `Stats.fantasy_points_ppr` aus nflverse, **nicht** der finale kanonische NFL-facts-plus-league-scorer aus #697. Für seltene League-Scoring-Edge-Cases keine Paritätsbehauptung.

| Kohorte | N | MAE Baseline | MAE mit Defense | Δ (Defense − Baseline) |
| --- | ---: | ---: | ---: | ---: |
| Gesamt | 510 | 5,201 | 5,199 | -0,002 |
| Receiving-Anteil ≥ 50 % | 164 | 4,826 | 4,828 | +0,002 |
| Receiving-Anteil 20–50 % | 240 | 5,938 | 5,894 | -0,044 |
| Receiving-Anteil < 20 % | 106 | 4,113 | 4,200 | +0,087 |

MAE nach Wochen: W3 4,921→4,877 (61), W4 5,562→5,584 (68), W5 4,856→5,077 (58), W6 5,123→5,142 (63), W7 4,756→4,740 (69), W8 6,312→6,160 (63), W9 5,092→5,020 (61), W10 4,978→4,993 (67).

**Fazit:** Der simple Split-Faktor liefert insgesamt **keinen praktisch relevanten Mehrwert**. Einige Einzelbeispiele sind besser (z. B. McCaffrey vs. LA in W10), andere deutlich schlechter (derselbe Spieler vs. LA in W5). Ohne mehrjährige, out-of-sample validierte Evaluation weder Gewichtung noch automatische Start/Sit-Konsequenz ableiten.

## Nächste prüfbare Hypothesen

- **HYP-RB-PROFILE-001A – Stabilität / Rolle:** Carries, Targets, Routes, Snap Share, Receiving-Punkte-Schwankung und rollenspezifische Trends bringen zusätzliche Ex-ante-Erklärung gegenüber einem bloßen season-to-date Punktanteil.
- **HYP-RB-PROFILE-001B – Gegner-Effizienz:** Gegen RB-Receiving zugelassene Targets/Receptions/Yards **pro Target oder RB-Route**, statt nur PPR/G, liefern bessere Vorhersagekraft, nachdem Volumen/Games und Sample Size kontrolliert wurden.
- **HYP-RB-PROFILE-001C – Modellnutzen:** Ein kombiniertes Profil-/Defense-Modell schlägt die produktive V4-C/V4-C-PI1-Projektion aus #697 in einem kompletten Walk-forward-Multi-Season-Test statistisch und praktisch nachvollziehbar.

Alle drei bleiben `proposed` / unvalidiert. Nicht in `Grading` der App einspeisen: Das existierende Legacy-Feld `Grading` ist laut Fantasy-Management-Rules **kein** Player-Quality- oder Fantasy-Ranking-Maß.

## Quellen / Reproduktion

- [2026 Canonical weekly player stats](https://github.com/Lolindhir/fantasy-app/tree/main/source-data/nfl/player-stats/2026), Wochen 01–05.
- [2025 Canonical weekly player stats](https://github.com/Lolindhir/fantasy-app/tree/main/source-data/nfl/player-stats/2025), Wochen 01–10.
- [2026 NFL Schedule](https://github.com/Lolindhir/fantasy-app/blob/main/source-data/nfl/schedules/2026.json).
- [2026 League Scoring / Roster Positions](https://github.com/Lolindhir/fantasy-app/blob/main/source-data/leagues/nfl-reise/seasons/2026/league.json).
- [NFL source facts contract](https://github.com/Lolindhir/fantasy-app/blob/main/.ai-context/manual/nfl-source-data.yaml).
- [Workflow / Hypothesis Validation](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/_ai/WORKFLOWS.md).

Diese Datei ist eine **datierte Research-Baseline**, kein dauerhafter aktueller Spielerwert und keine Prognose-Methodenfreigabe. Spätere Reviews und Rechecks werden getrennt datiert, statt dieses Ex-ante-Ergebnis still zu überschreiben.
