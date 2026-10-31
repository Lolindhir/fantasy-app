# Offseason 2027 – Regelvorschlag: Kicker abschaffen, FLEX stärken

> **Status:** Offener Regelvorschlag für die Liga, **kein beschlossener Regelwechsel**  
> **Stand der Vorlage:** 31.10.2026  
> **Historische Auswertung:** vorläufiger Backtest 2024/2025 und 2026, Wochen 1–7, aus der Diskussion vom 29.10.2026  
> **Work Tracking:** [#1255](https://github.com/Lolindhir/fantasy-app/issues/1255)

## 1. Antrag für die Offseason

**Zur Saison 2027 wird der verpflichtende Kicker-Startplatz pro Team durch einen fünften RB/WR/TE-FLEX-Platz ersetzt.**

| | Heute | Vorgeschlagen für 2027 |
| --- | ---: | ---: |
| Feste QB / RB / WR / TE | 2 / 2 / 2 / 2 | unverändert |
| FLEX (RB/WR/TE) | 4 | 5 |
| Kicker-Starter | 1 | 0 |
| Starter insgesamt pro Team | 13 | 13 |
| Reguläre Bankplätze | 17 | zunächst unverändert |
| Zusätzlich ligaweit startende RB/WR/TE | – | +6 |

Die Umstellung soll **erst nach einem Ligabeschluss und erst zur neuen Saison** gelten. Dabei müssen gehaltene Kicker, bestehende Kicker-Gehälter und mögliche Dead-Cap-Folgen fair geregelt werden; eine kosten-/Dead-Cap-neutrale Umstellung ist **Teil des Vorschlags, noch keine geltende Regel**.

## 2. Begründung: Mehr Managementqualität, weniger schwer planbare Spezialteams-Punkte

**Ziel:** Entscheidungen sollen stärker von Spielerbewertung, Kaderentwicklung, Trade-/Roster-Planung und Start/Sit-Analyse abhängen. Kicker haben einen tatsächlichen Einfluss auf die Punkte, aber im Vergleich zu RB/WR/TE wenig langfristigen Dynasty- und Trade-Wert und einen schwach nachgewiesenen, wiederholbaren wöchentlichen Entscheidungsvorsprung.

### Kicker-Punkte hängen stark von Gelegenheiten ab

Ein NFL-Team, das fünf Touchdowns erzielt, gibt seinem Kicker typischerweise fünf Extrapunktversuche. Vier Drives, die mit Field Goals aus 40–59 Yards enden, können dem Kicker unserer Liga dagegen 16–20 Punkte bringen, obwohl die Offense weniger Touchdowns erzielt. Red-Zone-Effizienz, Spielverlauf, Coach-Entscheidungen und Field-Goal-Gelegenheiten beeinflussen das stark.

In unserem derzeitigen Scoring sind ein erfolgreiches 50–59-Yard-Field-Goal **5 Punkte** und ein misslungenes Field Goal **–1 Punkt** wert. Ein einzelner Versuch kann somit zwischen diesen beiden Resultaten einen Sechs-Punkte-Ausschlag erzeugen.

Das bedeutet **nicht**, dass Kicker komplett unprognostizierbar wären: Vegas-Team-Totals, Matchup, Stadion, Wetter, Offense-Qualität und Job-Sicherheit liefern nutzbare Signale. Entscheidend ist, wie viel Vorteil ein Manager aus diesen Informationen tatsächlich wiederholbar ziehen kann.

### Eigener Backtest: Kicker ändern selten den Sieger

Die im Oktober 2026 vorgenommene historische Rückrechnung entfernte die Punkte der **tatsächlich gestarteten** Kicker aus ansonsten unveränderten Liga-Matchups:

| Saison | Vergleichbare Matchups | Siegerwechsel ohne Kicker |
| --- | ---: | ---: |
| 2024 | 51 | 1 (1,96 %) |
| 2025 | 51 | 1 (1,96 %) |
| 2026, Wochen 1–7 | 20 | 1 (5,00 %) |
| **Gesamt** | **122** | **3 (2,46 %)** |

Aus 2026 wurde ein Matchup ausgeschlossen, weil bei einem Team ein belegter Kicker-Starterplatz fehlte.

Der durchschnittliche **absolute** Unterschied zwischen den gestarteten Kickern je Matchup betrug ungefähr:

- 2024: **5,4 Punkte**
- 2025: **5,6 Punkte**
- 2026 (Wochen 1–7): **5,7 Punkte**

Beispiel **Woche 8, 2025**: Das Matchup endete **169,96 : 161,88**. Der spätere Sieger erhielt 20 Kicker-Punkte, der Gegner 8. Ohne Kicker hätte die Partie **149,96 : 153,88** geendet und der andere Manager gewonnen.

**Interpretation:** Kicker erzeugen merkliche Punkteausschläge, haben aber in dieser Stichprobe selten den Matchup-Sieger geändert. Das allein beweist **weder**, dass die Position überflüssig ist, **noch**, dass diese Ausschläge Zufall statt guter Managerentscheidungen waren.

### Sehr schwacher Zusammenhang zwischen aufeinanderfolgenden Wochen

Die Korrelation der Kicker-Punkte von einer Woche zur folgenden Woche für denselben tatsächlich gestarteten Kicker war:

| Saison | Beobachtungspaare | Pearson-Korrelation |
| --- | ---: | ---: |
| 2024 | 74 | 0,166 |
| 2025 | 80 | 0,087 |
| 2026, Wochen 1–7 | 29 | 0,035 |

In 2025 erklärte die Vorwochenleistung damit rechnerisch weniger als ein Prozent der Unterschiede der nachfolgenden Wochenpunkte (r² ≈ 0,008).

Ein einfacher retrospektiver Streaming-Versuch für 2025, der aus den in beiden Wochen gestarteten Kickern anhand der **Vorwochen-Punkte** auswählte, lag bei **8,00 Punkten pro Woche**, gegenüber **7,94** Punkten der Vergleichskicker (**+0,06**).

**Grenzen:** Das war kein vollständiger echter Streaming-Backtest. Weder damalige Waiver-Verfügbarkeit und Transaktionskosten noch historische Vorab-Projektionen, Vegas-Linien, Wetter oder Job-Sicherheit wurden sauber mitmodelliert. Der Test zeigt nur, dass **Vorwochen-Punkte als einfache Auswahlstrategie wenig geholfen haben**. Er widerlegt keine bessere, kontextbezogene Prognosemethode.

### In einer 6-Team-Dynasty-Liga ist der Kicker strukturell wenig knapp

Sechs Teams stellen jeweils nur einen Kicker. Dem steht ein NFL-Pool von nominell 32 Starterjobs gegenüber. Kicker lassen sich dadurch leichter ersetzen; ein zweiter Kicker besetzt einen Bankplatz, den man auch für einen langfristig entwicklungsfähigen RB/WR/TE nutzen könnte. Für Kicker bestehen normalerweise geringere Entwicklungs-, Trade- und Dynasty-Anreize als für offensive Skill-Positions.

Ein **fünfter FLEX** führt hingegen zu sechs weiteren startenden RB/WR/TE ligaweit. Die Kaderbreite, Bewertung junger Spieler und konkrete Matchup-Entscheidungen könnten dadurch relevanter werden. Ein FLEX macht Spielerpunkte **nicht automatisch weniger zufällig**; der mögliche Vorteil liegt vor allem in der besseren langfristigen Bewertung und Steuerbarkeit der aufgestellten Assets.

## 3. Gegenargumente, die die Liga ernst nehmen sollte

- **NFL-Gefühl und Unterhaltung:** Kicker gehören zum echten Football. Überraschende Field Goals und Game-Winner machen Fantasy spannend. Das ist ein legitimer Wert, den die Liga bewusst höher gewichten kann.
- **Zufall gehört dazu:** Auch WR-Targets, RB-Touchdowns und Verletzungen sind variabel. Ziel kann nur sein, interessante Entscheidungen zu fördern, nicht jede Varianz zu entfernen.
- **Nur 3 von 122 Matchups gedreht:** Der Einfluss auf Sieger war im bisherigen Sample klein. Das ist ein Argument gegen das Überdramatisieren des Problems. Für oder gegen die Position sollte zusätzlich der strategische Gegenwert betrachtet werden.
- **Ein zusätzlicher FLEX kann starke und tiefe Kader begünstigen:** Die Wettkampfbalance und der Grenzwert von Depth-/Prospect-Spielern könnten sich verschieben. Vor Beschluss sollte diese Wirkung simuliert werden.
- **Prognose- und Streamingmöglichkeiten existieren:** Ein korrektes Walk-forward-Modell könnte mehr strategischen Nutzen zeigen als der bislang getestete Vorwochen-Trend.

## 4. Offene Prüfungen vor dem Ligabeschluss

1. **Saison 2026 vollständig auswerten:** Regular Season und Playoffs, mit klaren Kriterien für unvollständige Kicker-Starts.
2. **Echter Walk-forward-Kicker-Backtest:** Nur Informationen verwenden, die **vor** dem jeweiligen Spieltag verfügbar waren; realistische damalige Free Agents, Waiver/Transaktionen, Projektionen und Kontext einbeziehen. Einen stabilen Kicker halten und Streaming fair vergleichen.
3. **Fünften FLEX simulieren:** Nur damals tatsächlich spielbare und verfügbare RB/WR/TE-Kandidaten verwenden, keinen rückblickend perfekten Bench-Spieler einsetzen. Veränderung der Kaderqualität und des Wettbewerbs bewerten.
4. **Umstellung im Salary-System abklären:** Kicker-Gehälter, Dead Cap, mögliche Roster-Rechte und gegebenenfalls Salary-Cap-Anpassungen festlegen; keine unbeabsichtigte Benachteiligung einzelner Manager.
5. **Separater Ligabeschluss:** Gegenargumente und Ergebnisse den anderen Managern vorlegen; erst anschließend Regel- und technische Änderungen beschließen.

## 5. Verhältnis zur Salary- und League-Economy-Arbeit

Dieses Dokument betrifft **Ligaformat und Scoring-Design** und gehört deshalb **nicht** in das persönliche Analyseverzeichnis der Mighty Giants und **nicht** als vierter Salary-Formelteil in `league-economy`.

Es gibt jedoch eine wichtige **Abhängigkeit**: Der zusätzliche FLEX-Slot erhöht die Nachfrage nach RB/WR/TE, während Kicker nicht mehr als Starter benötigt werden. Die vorgeschlagene dynamische *Positional Criticality* muss Änderungen des Ligaformats bei der Kalibrierung berücksichtigen. Bereits aus 4 FLEX + 1 K gewonnene Criticality- und Salary-Benchmarks wären für eine künftige 5-FLEX-Liga neu zu bewerten.

Verwandte, eigenständige Dokumente:

- [Performance Salary / Dynamic Positional Criticality](../league-economy/salary/salary-system-redesign-concept.md)
- [League Economy – Offseason-Synthese](../league-economy/league-economy-redesign-options.md)

**Die hier vorgeschlagene Formatänderung ist kein bereits beschlossener Input für Salary-Simulation oder Produktivsysteme.**

## 6. Empfehlung und aktueller Entscheidungsstand

**Vorläufige Empfehlung:** Kicker ab 2027 durch einen fünften RB/WR/TE-FLEX-Platz ersetzen, weil das in unserer kleinen Dynasty-Liga voraussichtlich mehr strategisch nutzbare Kader- und Start/Sit-Entscheidungen schafft als ein zusätzlicher Kicker-Startplatz.

**Noch nicht entschieden:** Abschaffung, genaue Übergangsregeln, Salary-/Dead-Cap-Folgen und die abschließende Argumentationsbewertung. Bis zu einer gemeinsamen Ligaentscheidung bleiben die geltenden Regeln unverändert.

## 7. Datengrundlage und Reproduzierbarkeit

- **Aktuelle Formateinstellungen und Scoring:** `public/data/League.json` im Repository `Lolindhir/fantasy-app`; die konkrete Struktur muss vor jeder späteren Entscheidung **neu geprüft** werden.
- **Historische Kennzahlen:** Vorläufiger, im Gespräch vom 29.10.2026 berichteter Liga-Backtest zu 2024/2025 und 2026 W1–7. Die Metriken wurden in diesem Dokument **übernommen, nicht unabhängig erneut ausgeführt oder reproduziert**. Die zugrunde liegenden Skripte/Datensnapshots und Commit-SHAs sind für eine reproduzierbare Validierung später zu ergänzen.
- **Methode:** Subtraktion der gestarteten Kicker-Punkte aus historischen Matchup-Ergebnissen, ohne kontrafaktische Roster-/Lineup-Optimierung.
- **Grenzen:** Keine echte Vorab-Prognose-Evaluation, kein kontrafaktischer fünfter FLEX, kein kompletter Stand 2026, keine ausgewerteten Cap-/Trade-Folgen.
- **Externe Studien:** Hinweise aus der ursprünglichen Diskussion wurden hier bewusst **nicht** als unabhängig verifizierte Belege verwendet.

Die Regelargumentation darf bei neuen Erkenntnissen weiterentwickelt werden; historische Kennzahlen müssen dabei datiert, reproduzierbar und getrennt vom Ligabeschluss bleiben.
