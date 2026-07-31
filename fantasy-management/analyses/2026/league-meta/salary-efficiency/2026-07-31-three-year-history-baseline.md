# Salary-Effizienz 2026: Baseline mit Drei-Jahres-Historie

## Status

- Typ: Liga-Metaanalyse
- Status: aktiv
- Erstellt: 2026-07-31
- Analyse-ID: `salary-efficiency-2026-three-year-baseline`
- Evidenzstufe: `single_snapshot`
- Geplanter Review: nach Abschluss und vollständiger Datenaktualisierung der Saison 2026

## Zweck

Diese Baseline untersucht nicht die Qualität der Salary-Formel selbst, sondern den aktuell beobachtbaren Zusammenhang zwischen Salary und tatsächlich nutzbarer Fantasy-Produktion auf den sechs Liga-Rostern.

Die Untersuchung soll insbesondere klären, ob junge oder statistisch unvollständige Spieler die üblichen Salary-Ertrags-Grenzen künstlich nach unten verschieben. Die Ergebnisse sind prüfbare Thesen und noch keine dauerhaften Fantasy-Management-Regeln.

## Datenstand und Quellen

- Repository: `Lolindhir/fantasy-app`
- Ref: `main`
- Ausgangs-Commit: `f178e650696eec0c412cd79a55195b09015b21c7`
- Liga- und Rosterzustand: `public/data/League.json`
- Spielerdaten: `public/data/Players.json` beziehungsweise die passenden Chunks unter `public/data/chat/players-relevant/`
- Ligaregeln und manuelle Zuordnungen: `public/data/Metadata.json`
- Format: sechs Teams, 2 QB, 2 RB, 2 WR, 2 TE und 4 FLEX

Die kanonischen Repository-Daten gelten gemäß Projektregel als aktuell. Dateialter oder unveränderte Zeitstempel sind allein kein Hinweis auf veraltete Ligadaten.

## Methode

### Vergleichspopulation

Berücksichtigt werden ausschließlich gehaltene Spieler der Positionen QB, RB, WR und TE, bei denen `SeasonMinus1`, `SeasonMinus2` und `SeasonMinus3` jeweils als statistische Saison vorhanden sind. Für die Reproduktion gilt eine Saison als vorhanden, wenn der historische Saisonblock eine reguläre Vergleichsbasis enthält; vollständig leere Saisonblöcke werden ausgeschlossen.

Kicker sowie Spieler mit weniger als drei vorhandenen Statistikjahren werden nicht zur Ableitung der Marktgrenzen verwendet.

Qualifizierte Spieler in dieser Baseline:

| Position | Anzahl |
|---|---:|
| QB | 13 |
| RB | 28 |
| WR | 42 |
| TE | 17 |
| **Gesamt** | **100** |

### Ertragsmetrik

Als availability-adjusted Ertrag der letzten abgeschlossenen Saison wird verwendet:

```text
Ertrag = (FantasyPointsAvgGame + FantasyPointsAvgPotentialGame) / 2
```

Damit werden Produktion bei tatsächlichen Einsätzen und Verfügbarkeit gleich gewichtet.

### Rollen- und Positionsbezug

Salary-Effizienz wird nicht über eine gemeinsame ligaweite Kennzahl wie reine Punkte pro Million bewertet. Die Interpretation erfolgt positions- und rollenbezogen, weil Ersatzniveau und Startpflichten zwischen QB, RB, WR und TE deutlich differieren.

## Vorläufige Marktgrenzen

Die folgenden Bereiche sind eine datierte Kalibrierung für den aktuellen Datenstand. Sie sind keine dauerhaften Regeln.

| Rolle | Vorläufig neutraler Bereich | Kritischer Bereich |
|---|---|---|
| QB1 | 35–45 Mio. für ungefähr 19–21 Punkte | über 45 Mio. bei weniger als 19 Punkten |
| Elite-QB | bis etwa 55 Mio. bei 21+ Punkten | über 55 Mio. ohne klare Eliteproduktion |
| QB2 | 16–38 Mio. für ungefähr 14–19 Punkte | über 40 Mio. bei weniger als 18 Punkten |
| RB1 | 28–38 Mio. für ungefähr 16–22 Punkte | über 30 Mio. bei weniger als 16 Punkten |
| Elite-RB | 40–50 Mio. für 20+ Punkte | über 40 Mio. bei weniger als 20 Punkten |
| RB2/FLEX | 11–22 Mio. für ungefähr 10–14 Punkte | über 22 Mio. bei weniger als 12–13 Punkten |
| WR1 | 25–38 Mio. für ungefähr 16–21 Punkte | über 30 Mio. bei weniger als 16 Punkten |
| Elite-WR | 38–48 Mio. für ungefähr 19–23 Punkte | über 40 Mio. bei weniger als 18 Punkten |
| WR2/FLEX | 10–23 Mio. für ungefähr 11–15 Punkte | über 23–25 Mio. bei weniger als 13 Punkten |
| TE1 | 10–15 Mio. für ungefähr 10–13 Punkte | über 15 Mio. bei weniger als 10 Punkten |
| Elite-TE | bis etwa 28 Mio. bei mindestens 15 Punkten | über 20 Mio. bei nur 10–12 Punkten |
| TE2 | 4–11 Mio. für ungefähr 7–10 Punkte | über 11–12 Mio. bei weniger als 8 Punkten |

## Vorläufige Roster-Erkenntnisse

- Der vollständige etablierte Kern von Team DennisLACards war in dieser Momentaufnahme am günstigsten pro availability-adjusted Punkt.
- Die Ruhr Valley Packers erreichten den höchsten etablierten Output, benötigten dafür aber das höchste Salary.
- Mighty Giants und Just Bill konnten unter dem strengen Filter keine vollständige 12-Spieler-Vergleichsformation bilden, weil relevante Startrollen durch jüngere Spieler besetzt werden.
- Bei Mighty Giants lag der sichtbarste Salary-Hebel im etablierten RB-Raum, während der qualifizierte WR- und TE-Kern überdurchschnittlich stark war.
- Die QB-Marktgrenze stieg gegenüber einer ungefilterten Betrachtung deutlich an, weil günstige junge Starter nicht mehr als Referenz dienten.

Diese Aussagen beschreiben ausschließlich die Baseline-Population. Ausgeschlossene junge Spieler können real wertvolle Roster-Assets sein; sie werden nur nicht als Beleg für einen marktüblichen etablierten Vertrag verwendet.

## Prüfhypothesen

### SALARY-H01

**These:** Spieler ohne drei vollständige Statistikjahre verzerren positionsbezogene Salary-Mediane nach unten, weil ihr Salary häufig durch fehlende Historie oder Vertragszugehörigkeit reduziert ist.

- Status: `proposed`
- Erwartung: Die gefilterten Median-Salaries liegen in den relevanten Starterklassen systematisch oberhalb der ungefilterten Mediane.

### SALARY-H02

**These:** Der Filter „drei vollständige Statistikjahre“ erzeugt stabilere Salary-Ertrags-Grenzen als die ungefilterte Gesamtpopulation.

- Status: `proposed`
- Erwartung: Grenzwerte verändern sich bei der Postseason-Replikation weniger stark durch einzelne neue Spieler oder kleine Stichprobenänderungen.

### SALARY-H03

**These:** Der Drei-Jahres-Filter allein entfernt den Young-Player-Discount nicht vollständig; ein zusätzlicher Filter auf vertraglich etablierte Spieler liefert eine bessere Veteranen-Marktlinie.

- Status: `proposed`
- Erwartung: Die Population „drei Jahre plus nicht mehr ursprünglicher Rookie-/Einstiegsvertrag“ besitzt weniger extreme günstige Ausreißer und bessere Out-of-Sample-Kalibrierung.

### SALARY-H04

**These:** Salary-Cut-offs müssen positions- und produktionsklassenbezogen abgeleitet werden; eine gemeinsame Kennzahl wie Punkte pro Million klassifiziert insbesondere Stars und Ersatzspieler systematisch falsch.

- Status: `proposed`
- Erwartung: Rollenbezogene Grenzwerte erklären Roster- und Startwert besser als eine gemeinsame lineare Effizienzrangliste.

## Postseason-Verifikation

Nach Abschluss der Saison 2026 werden mindestens vier Populationen neu berechnet:

| Variante | Population |
|---|---|
| A | alle gehaltenen QB, RB, WR und TE |
| B | mindestens drei vollständige Statistikjahre |
| C | mindestens drei Statistikjahre und mindestens `Year 5` |
| D | mindestens drei Statistikjahre und nicht mehr auf dem ursprünglichen Rookie-/Einstiegsvertrag |

Für jede Variante werden geprüft:

1. Stabilität der Positions- und Rollenmediane.
2. Prognosefähigkeit der Baseline-Grenzen für die Produktion der Saison 2026.
3. Häufigkeit und Ursache von Fehlklassifikationen.
4. Sensitivität gegenüber Median, getrimmtem Mittelwert und Perzentilbändern.
5. Aussagekraft für Rosterproduktion und Cap-Nutzung.
6. Unterschiede zwischen QB, RB, WR und TE.

Jede These erhält danach einen der Statuswerte:

- `supported`
- `partially_supported`
- `rejected`
- `inconclusive`

Die Evidenzstufe wird zusätzlich auf `one_season_validated` oder später `multi_season_validated` gesetzt.

Der geplante Review wird als neue Datei unter folgendem Pfad gespeichert; die Baseline bleibt unverändert:

```text
fantasy-management/analyses/2026/league-meta/salary-efficiency/reviews/2027-postseason-validation.md
fantasy-management/analyses/2026/league-meta/salary-efficiency/reviews/2027-postseason-validation.json
```

## Überführung in Knowledge oder Regeln

- Numerische Cut-offs bleiben datierte Analyseergebnisse und werden nicht als zeitlose Regel übernommen.
- Bestätigte empirische Erkenntnisse können nach einem gesonderten Interpretationsschritt unter `fantasy-management/knowledge/fantasy/` abgelegt werden.
- Eine dauerhafte methodische Vorgabe für künftige Agentenanalysen wird erst nach der Verifikation und ausdrücklicher Nutzerentscheidung in `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md` übernommen.
- Eine bewusst gewählte Standardmethode kann zusätzlich als Entscheidung unter `fantasy-management/decisions/` dokumentiert werden.

## Gültigkeitshinweis

Diese Datei dokumentiert eine Momentaufnahme und offene Hypothesen. Sie ist weder aktuelle Spielerbewertung noch permanente Salary-Wahrheit. Dynamische Roster-, Produktions- und Salary-Werte müssen bei späterer Verwendung aus den dann aktuellen Repository-Daten neu abgeleitet werden.
