# PlayerWeekFantasy – Sleeper-Projections, Availability und Shadow-Test: Research-Audit

**Archivstand:** 31.10.2026. **Forschungsurteil:** `inconclusive` für eine belastbare Modellverbesserung; das Low-Projection-/Einsatzrollen-Signal ist **explorativ teilweise gestützt**.  
**Nutzerentscheidung 31.10.2026:** Forschungsstrang **vorerst zurückgestellt (parked)**, nicht weiter verfolgen; **keine Produktivintegration**.  
**Work Tracking:** [#1025 – Team-Opportunity-/Rollenforschung](https://github.com/Lolindhir/fantasy-app/issues/1025), [#697 – PlayerWeekFantasy](https://github.com/Lolindhir/fantasy-app/issues/697), [#988 – External Source](https://github.com/Lolindhir/fantasy-app/issues/988), [#190 – Quellenrechte](https://github.com/Lolindhir/fantasy-app/issues/190).  
**Geltungsbereich:** Externe undokumentierte Sleeper-/RotoWire-Wochenprognosen als mögliches **zusätzliches** Pregame-Signal für Teilnahme/Workload und Fantasy-Projektionen. Alle Zahlen sind historische Exploration, kein neues Modell- oder Source-of-Truth-Contract.

## 1. Fragestellung und Schlussfolgerung

Kann die Sleeper-Weekly-Projection zusammen mit historischen NFL-Snap-Counts erkennen, ob unser V4-C-Punktmodell die zu erwartende Einsatzrolle eines Spielers überschätzt, und lässt sich V4-C durch einen leichten externen Availability-/Workload-Filter messbar verbessern?

**Fazit:** Das Archivsample liefert ein interessantes **Signal**, insbesondere bei Spielern mit sehr niedrigen Sleeper-Prognosen. Ein einfacher Shadow-Cap verbessert in **26** auswertbaren Week-1-Spielern den MAE von **5,092 auf 4,713** (−7,44 %, vier veränderte Fälle). **Alle vier veränderten Spieler erzielten tatsächlich null Punkte**. Das ist wegen eines kleinen, bewusst ausgewählten Samples, der nachträglichen Schwellenbetrachtung und fehlender unabhängiger Holdouts **kein belastbarer Beleg** für einen generalisierbaren Vorteil. Eine andere intuitive Gap-Regel verschlechtert das Ergebnis sogar leicht. **Keine Integration empfohlen.**

**„Verfügbar“ muss präzise getrennt werden:**
- `confirmed_inactive` / keine Spielberechtigung: nur mit belastbaren Roster-/Availability-Informationen behaupten.
- `played` / Teilnahme: beobachtete offensive oder Special-Teams-Snaps bzw. andere gesicherte Game-Participation.
- `low_workload`: geringe Rolle trotz Teilnahme; Workload ist nicht gleich Availability.
- `snap_absent_unknown`: kein gefundener Snap-Record; **nicht** automatisch „inactive“ oder „injured“.
- `no_game/bye`, fehlende Projektion und ungeklärte Spieleridentität sind separate Zustände.

V4-C/PI1 ist derzeit **`conditional-on-participation`**; `AvailabilityAdjustmentApplied=false`. Ein Sleeper-Faktor darf diese Semantik nicht still überschreiben.

## 2. Quellen, Snapshot-Stände und Populationen

**Externe historische Sleeper-Evidenz:**
- [Tyler Burns – datierte technische Source Findings](https://github.com/tyler-burns/Fantasy-Football-Draft-Tool/blob/main/docs/data-source-findings.md) mit damaligem erfolgreichen HTTP-200-Check (August 2026). Das ist kein aktueller Service-/Support-Nachweis.
- [Archivierte rohe Week-1-Response (50 selektierte Zeilen)](https://github.com/tyler-burns/Fantasy-Football-Draft-Tool/blob/main/data/sample/projections_week1_raw.json). Provider-Metadaten `company=rotowire`; die Punktprognosen haben `updated_at` um **19.08.2026 07:45:58 UTC**, vor den Spielen im September. 40/50 Zeilen mit numerischem `stats.pts_ppr`, 10 ADP-only.
- Dritter Quellenaudit meldete für die gesamte damalige W1-Response **3.301 Zeilen, nur 575 mit `pts_ppr`**. Week 0 war ADP-only. Diese Zahlen stammen **nicht** aus einem eigenen vollständigen Live-Download.
- W1-Fixture fokussiert fast ausschließlich die Opening Games **NE–SEA** und **SF–LAR**; sie ist ausdrücklich **nicht zufällig/ligavollständig**. W1-V4-C-Projektionen wurden **retrospektiv rekonstruiert**, nicht als historischer Produktions-Pregame-Snapshot eingefroren.

**Eigene kanonische Prüfgrundlagen:**
- `data-source/nfl/snap-counts/2026/01.json` – 1.492 Snap-Zeilen, **`Finalized=false`** zum Prüfstand.
- `public/data/PlayerWeekFantasy.json` – zum Audit-Zeitpunkt verwendete Sleeper-PlayerID → CanonicalPlayerID-Bridge; später kann sich dieser Live-Snapshot ändern.
- `data-derived/player-week-fantasy/nfl-reise/2026/01.json` – rekonstruierte V4-C-Projektionen und `Actual.State=final` bzw. finales League-Scoring.
- `data-source/providers/sleeper/leagues/1354177383984267264/league.json` – 2026 League-Scoring, 6 Teams / 13 Starter.
- `data-source/providers/sleeper/leagues/1354177383984267264/matchups/week-1.json` – Gegenprüfung von 15 finalen Spieler-Actuals im ersten Score-Audit, keine Differenz.
- In der älteren Näherungsberechnung aktives Scoringprofil mit SHA-256 `1495de25c56dd51836665d2643ee066a954c3c8941efb6ce518b83e71f137300`.

**Drei strikt unterschiedliche Kohorten:**
1. **27** Spieler mit V4-C und approximativ auf League-Punkte umgerechneten Sleeper-Offensivstatistiken, finalem Actual (erster Punktevergleich vom 26.10.).
2. **34** eindeutig zugeordnete QB/RB/WR/TE-Spieler mit numerischem Sleeper-`pts_ppr` und Snap-Beobachtungs-Proxy (28.10.; von 35 Kandidaten wurde eine ungeklärte Identität ausgeschlossen).
3. **26** QB/RB/WR/TE-Spieler mit numerischem Sleeper-PPR, eindeutiger Identität, V4-C-`available` und finalem Actual (31.10.; Shadow-Regeln). **Nicht** die identische Stichprobe wie (1) oder (2).

## 3. Erster V4-C-/Sleeper-Punktevergleich (26.10.)

In diesem Test wurden die Sleeper-Statistiken **nur näherungsweise** in das spezifische League-Offensive-Scoring umgerechnet, nicht mit dem vollständig kanonischen Scorer für alle exotischen Scoringfelder. K/DST/FB sind nicht Teil dieses Benchmarks.

| Population | N | V4-C MAE | Sleeper-Approx MAE |
| --- | ---: | ---: | ---: |
| QB/RB/WR/TE gesamt | 27 | 5,111 | **4,324** |
| Tatsächliche Fantasy-Punkte > 0 | 14 | **5,229** | 5,272 |
| Tatsächliche Fantasy-Punkte = 0 | 13 | 4,984 | **3,302** |

Gesamtdifferenz V4-C minus Sleeper MAE **+0,787**; exploratives gepaartes Bootstrap (15.000 Resamples) mit 95%-Intervall **[−0,215; +1,838]**. Intervall enthält null und ist unter bewusst selektiertem Sample keine repräsentative Populationsunsicherheit. **Null Ist-Punkte sind kein DNP-Label**; die Teilgruppenbildung anhand des Ergebnisses ist nachträglich und keinesfalls ein Pregame-Feature.

## 4. Abgleich Sleeper-Pregame-Projektion vs. W1-Snaps (28.10.)

Bei den **34** klar zugeordneten QB/RB/WR/TE mit numerischer Sleeper-Prognose:

| Sleeper `pts_ppr` | **Kein** Snap-Record | Snap-Record vorhanden | Gesamt |
| --- | ---: | ---: | ---: |
| ≤ 1 | 9 | 2 | 11 |
| > 1 | 4 | 19 | 23 |
| **Gesamt** | **13** | **21** | **34** |

Als rein explorative Warnregel `pts_ppr ≤ 1` für das *Proxy-Ziel „kein Snap-Record“*: **Precision 9/11 = 81,8 %**, **Recall 9/13 = 69,2 %**, **Spezifität 19/21 = 90,5 %**, **Accuracy 28/34 = 82,4 %**. Wegen der Stichproben-Zusammensetzung sind dies **keine validierten DNP-Modellmetriken**. Alternative Schwellen: bei ≤3 PPR Precision **10/18 = 55,6 %**, bei ≤5 PPR **11/21 = 52,4 %**.

**Konkrete Gegenbeispiele:**
- **Tommy DeVito:** Sleeper 0,76 vs. V4-C 6,74; kein Snap-Record, 0 Ist-Punkte.
- **Eric Saubert:** Sleeper 0,48, **10 offensive + 18 Special-Teams-Snaps**; trotz niedriger Prognose eingesetzt.
- **TreVeyon Henderson:** Sleeper 11,75, **kein Snap-Record** und 0 Ist-Punkte; hohe Projection schützt nicht vor ausbleibender beobachteter Teilnahme.
- **Romeo Doubs:** Sleeper 10,57, **40 Offense-Snaps**, aber 0 Fantasy-Punkte.
- Insgesamt hatten **5 von 18 Nullpunkt-Spielern Offense-Snaps** (Doubs 40, Konata Mumpfield 16, Kyle Williams 12, Elijah Arroyo 11, Saubert 10).

**Nur tatsächliche Week-1-Snaps als Evaluationslabel**, niemals als W1-Pregame-Feature verwenden. Kein Snap-Record ist eine unsichere Negativbeobachtung: Snap-Dataset `Finalized=false`, Game-/Roster-/Identity-Coverage prüfen; ohne verlässliche Inactive-Liste keine medizinischen Verfügbarkeitsgründe behaupten.

## 5. Shadow-Regelvergleich auf denselben 26 Spielern (31.10.)

Jede Regel verändert nur die **simulierte** Punktschätzung, ohne V4-C-Dateien, Scorer oder App zu verändern. Die Schwelle ist keine trainierte und keine produktiv freigegebene Entscheidungsgrenze. `Sleeper` steht für generisches PPR (`stats.pts_ppr`) und wird hier **nicht** auf alle League-Sonderregeln umgerechnet.

| Shadow-Variante | Geänderte Fälle | MAE | RMSE | Bias |
| --- | ---: | ---: | ---: | ---: |
| **V4-C unverändert** | 0 | 5,0920 | 6,4533 | +4,2726 |
| Bei Sleeper ≤ 1 Punkt: V4-C auf maximal `max(0, Sleeper)` begrenzen | 4 | **4,7130** | 6,2955 | +3,8936 |
| Bei Sleeper ≤ 1: V4-C halbieren | 5 | 4,8609 | 6,3327 | +4,0620 |
| Bei V4-C > 2, Sleeper ≤ 3 und Sleeper/V4-C ≤ 0,35: V4-C halbieren | 2 | **5,1082** | 6,4289 | +3,9972 |
| 70 % V4-C + 30 % Sleeper-PPR | 26 | 4,9449 | 6,3185 | +3,9231 |

Die „Cap“-Variante verbessert den **explorativen Sample-MAE um 0,379 Punkte bzw. 7,44 %**. Nur vier Spieler wurden verändert: **Jacardia Wright** (V4-C 2,00 → 0,27), **Jake Bobo** (1,4281 → 0,12), **Eric Saubert** (1,3146 → 0,48) und **Tommy DeVito** (6,74 → 0,76); **alle vier erzielten tatsächlich 0 Punkte**. Die strengere relative Gap-Regel verschlechtert MAE leicht: **Mack Hollins** hatte Sleeper 2,4, V4-C 7,58, 50 Offense-Snaps und 9,1 Ist-Punkte. Solche Fehlalarme können echte Starter-Prognosen verschlechtern.

**Kein Overfitting-Etikett vermeiden:** Vier zufällig günstige Korrekturen in einer nicht repräsentativen Auswahl sind kein Hinweis, dass der gleiche Schwellenwert an anderen Spieltagen funktioniert. Erst unabhängige Wochen und tatsächliche Pregame-Stände könnten dies testen.

## 6. API-Surface, Datenqualität und Betriebsgates

- Offizielle [Sleeper-Dokumentation](https://docs.sleeper.com/) beschreibt Read-only-League-/Roster-/Draft-API, **nicht** den Weekly-Projection-Endpoint `https://api.sleeper.app/projections/nfl/2026/<week>?season_type=regular`.
- Historische Dritt-HTTP-200-Evidenz aus August 2026 und externes August-Pregame-Sample belegen die damalige Antwortstruktur (`player_id`, `week`, `stats.pts_ppr`, `updated_at`, `company=rotowire`). **Keine Zusage für heutigen Endpoint, vollständige Wochen oder stabile Schemafelder.**
- **Eigene Live-Checks 26. und 31.10.2026 gescheitert vor HTTP** an DNS/Netzwerkzugriff der Testumgebung; kein belastbarer aktueller HTTP-Status, keine live überprüften Spielerzahlen. **Nicht** als Sleeper-Outage/403 oder Beweis der Nichtverfügbarkeit ausgeben.
- Viele Response-Zeilen haben kein `pts_ppr`; ADP-Sentinel (z. B. 1000) und `null` nicht als Nullprognose/Inactive interpretieren. Manche projizierten `pass_fd/rush_fd/rec_fd` scheinen mechanisch etwa `yards/10` zu sein (5/5 + 24/24 + 31/31 in der Fixture). Kein vertrauenswürdiger First-Down-Input.
- Pregame-Source-`updated_at` und eigener Beobachtungszeitpunkt/Kickoff sind zu unterscheiden. Historische API-Antworten können nachträglich verändert sein; heutige Rückabfragen sind keine eingefrorenen historischen Pregame-Snapshots.
- [Sleeper Terms of Use](https://support.sleeper.com/en/articles/5486620-general-terms-of-use) (Stand 06.10.2026) und die undokumentierte Route machen automatischen Drittabruf, Retention und Redistribution **genehmigungsbedürftig bzw. ungeklärt**. `company=rotowire` verlangt upstream Attribution-/Sublicensing-Klärung; [RotoWire Terms](https://www.rotowire.com/termsandconditions.php) sind kein automatischer Beweis, welchen Teil Sleeper weiterlizenzieren darf.
- Das GitHub-Repository ist **öffentlich**. **Keine** Provider-Rohdaten und keine dauerhaften automatisierten Full-Week-Snapshots ohne gesicherten Storage-/Publication-/Attribution-Vertrag. `rights.storage/publication=unknown` aus [#190](https://github.com/Lolindhir/fantasy-app/issues/190) / [#988](https://github.com/Lolindhir/fantasy-app/issues/988) bleibt unverändert.

## 7. Archiventscheidung, Wiederaufnahmebedingungen und Ownership

**Entscheidung des Nutzers vom 31.10.2026:** Sleeper-Projection-/Availability-/Ensemble-Untersuchung **pausieren; derzeit nicht weiter verfolgen**. Dieser Bericht ist ein historisches Audit, **kein Auftrag für weitere Analyse, Integration, Datenerhebung oder Workflow-/Scheduler-Aktivierung**. Die produktive V4-C-Punktprognose und PI1-Ranges bleiben unverändert.

**Nur bei späterer expliziter Wiederaufnahme:**
1. Rechte und zulässige Nutzung/Speicherung beim Anbieter klären; keine öffentlichen Vendor-Raw-Projektionen ohne Nachweis.
2. Einmalig einen **erlaubten, aktuellen Live-Probe** an einer funktionsfähigen Netzwerkumgebung durchführen; Antwortschema, Position-/Punkteabdeckung, Aktualität, ID- und Week-/Game-Key-Coverage prüfen.
3. Mehrwöchige, timestampkorrekte und repräsentative **Pregame**-Evidenz beschaffen, nur im zulässigen Rahmen; confirmed inactive vs. low work vs. missing Beobachtungen getrennt labeln, echten Holdout nutzen.
4. **V4-C unverändert** gegen positionsabhängige Sleeper-Warnsignale, Rollenbaselines und soft/hard Gates testen; neben MAE/RMSE insbesondere falsch gewarnte Starter und DNP-Recall messen; keinerlei Schwellen aus den 26 Beispielen übernehmen.
5. Falls ein generalisierbarer Nutzen bestätigt wird, gesonderter freizugebender Integrationscheckpoint in #697. Source-Ownership in ADR-037/ADR-060 und #988; keine konkurrierende Consumer-Prognosepipeline.

**Provenienz/Archivregeln:** Dieser Bericht konsolidiert die Untersuchungen 25.–31.10.2026 aus Chat-Artefakten und datierten [Issue-#1025-Checkpoints](https://github.com/Lolindhir/fantasy-app/issues/1025). Die alten Issue-Evidenzen bleiben als zeitgenössischer Nachweis erhalten. Forschungsdaten wurden in diesem Dokument **nicht erneut beschafft**, und keine Sleeper-Rohantwort wird hier dupliziert. Spätere Änderungen erfordern einen neuen datierten Bericht statt einer rückwirkenden Umschreibung.
