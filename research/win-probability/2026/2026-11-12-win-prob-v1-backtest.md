# win-prob-v1 – Backtest der Pregame-Siegchance (Issue #1443)

Status: `supported` für die Aussage „Chance ist besser als der Münzwurf und bis 80 % gut kalibriert“; keine Produktfreigabe eines Kalibrierungsfaktors (Robert, 2026-11-12: Chance roh aus dem Projektionsmodell, kein Faktor).

## Forschungsfrage
Wie gut sagt die rohe Chance P(A) = Φ((μA − μB) / √(σA² + σB²)) aus team-range-v1 (Modell `win-prob-v1`) den Matchup-Ausgang voraus?

## Methode
- Werkzeug: `python3 tools/historical_win_prob_backtest.py --seasons 2024 2025 2026` (Commit dieses Berichts).
- Eingabe: persistierte PlayerWeekFantasy-Partitionen (`data-derived/player-week-fantasy`), alle Starter der Woche zählen mit ihrer Projektion (nichts ist „final“), Ergebnis aus den league-gewerteten Matchup-Summen. Gleiche Funktionen wie die Auslieferung (`weekly_recaps.pregame_win_probabilities`).
- Gewertet werden Matchups mit bekannter Chance und ohne Gleichstand; Matchups mit fehlender Projektion eines Starters („unbekannt“) bleiben ungewertet. Brier-Basis 0,25 (Chance immer 50 %).
- Unterschied zur Messung vom 11.11. (Walk-forward, 94 Matchups 2024/2025): dort wurde das PWF-Modell je Woche neu aufgebaut, hier werden die gespeicherten Partitionen benutzt (inklusive 2026).

## Ergebnis (Datenstand 2026-11-12)
| Saison | gewertet | Favorit gewinnt | Brier | Upset-Rate (Sieger < 35 %) | unbekannt |
|---|---|---|---|---|---|
| 2024 | 40 | 62,5 % | 0,219 | 10,0 % | 3 |
| 2025 | 36 | 61,1 % | 0,236 | 13,9 % | 4 |
| 2026 (bis Woche 9) | 27 | 66,7 % | 0,196 | 7,4 % | 0 |
| gesamt | 103 | 63,1 % | 0,219 | 10,7 % | 7 |

Kalibrierung gesamt (mittlere Chance → Trefferquote des Favoriten): 50–60 %: 54,6 → 48,7 % (n=37); 60–70 %: 63,5 → 62,1 % (n=29); 70–80 %: 74,1 → 72,0 % (n=25); ab 80 %: 84,5 → 91,7 % (n=12).

## Unsicherheit und Einordnung
- Kleine Stichprobe (n=103, Bänder 12 bis 37): Abweichungen einzelner Bänder liegen innerhalb des Zufalls; das Band 50–60 % ist erwartungsgemäß nahe Münzwurf.
- Die gespeicherten Partitionen können spätere Modellkorrekturen enthalten; das Ergebnis ist deshalb kein strenger Walk-forward-Beweis (siehe Messung vom 11.11.).
- Ein Kalibrierungsfaktor wurde bewusst nicht eingeführt. Wird das Projektionsmodell besser (neue `team-range`-Version), verbessert sich die Chance automatisch; dieser Bericht ist dann neu zu messen (neue datierte Datei).
