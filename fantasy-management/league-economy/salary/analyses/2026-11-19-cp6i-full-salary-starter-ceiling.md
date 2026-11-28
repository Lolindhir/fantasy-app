# CP6i – Vollständige Salary-Anrechnung, 40er-Kader und die Starterindex-Grenze

> **Stand 19.11.2026 · Explorative Einjahresforschung zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344). Kein neuer Liga-Beschluss, keine Änderung aktiver Salaries, Kader oder Workflows.** Der [geschützte Nordstern](../../../league-context/league-philosophy.md) bleibt unverändert. [Maschinenlesbare Ergebnistabelle](2026-11-19-cp6i-full-salary-starter-ceiling-metrics.json) und [lesender Rechenprototyp](../simulation/cp6i_starter_ceiling.mjs).

## 1. Forschungsfrage und Kandidat

Der Hauptkandidat für die Salary-Reform 2027 ist **maximal 40 reguläre Spieler, ohne Pflicht zur Vollbelegung**, und **vollständige Anrechnung aller gehaltenen Salaries**. Das gemeinsame Cap beträgt **Top-120-Marktgehaltssumme / 6**, **ohne** den bisherigen Faktor 0,90. Criticality (Centered-25, k=1,5), drei Rookie-Vertragsjahre und das gleitende Minimum bilden die Preis-Hypothese. IR-/Taxi-Geltung, konkrete In-Season-Checkpoints, C-add-Dead-Cap, Cap-Vorgriff und Tilgung sind **separat offen** und in diesem isolierten Test **nicht aktiviert**.

**Zentraler Prüfstein:** Wie hoch darf der Starterindex eines Teams im etablierten System werden, und wie viel davon lässt sich **passiv** versus mit **laufend gutem Management** über fünf Salary-Zyklen halten? Eine konzentrierte Aufstellung ist erlaubt; dauerhaft kostenlose, unangreifbare Dominanz wäre die wirtschaftlich relevante Fehlfunktion. Ein starrer Index-Cap ist **nicht** das Ziel.

Die ca. 202–205 Starterindexpunkte aus CP6h stammten aus einer bewusst ausgleichenden Verteilung auf sechs 30er-Teams und stellen **keine Obergrenze** des neuen 40er-Systems dar.

## 2. Datenstände, zwei strikt getrennte Preiswelten

- **Sportlicher Vergleichsscore:** 2026er Spieler aus dem aktuellen Repository; im selben 13er-Slotformat 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX (RB/WR/TE), 1 K. Der Score kombiniert laufende 2026er Punkte pro Spiel und Vorjahres-AvgPotentialGame analog CP6h (für gespielte Partien: gewichtet mit tatsächlicher GamesPlayed-Zahl und 2,5 Vorjahresspielen; ohne Vorjahreswert 0,92 bei mindestens vier Partien). **Kein Wochen-Forecast und kein zukünftiges Injury-Modell.**
- **Preiswelt A – veröffentlicht 2026:** kompletter Markt aus public/data/Players.json, Top120-Summe **2.851.024.206 $**, Kandidaten-Cap **475.170.701 $**. Das heute aktive Cap beträgt dagegen **427.653.631 $** bei Faktor 0,90; die 475,17 Mio. sind **nur der hypothetische Faktor-1,00-Vergleich**.
- **Preiswelt B – Oktober-2026-Criticality-Proxy:** Preisvektor 05.10.2026 aus der dortigen CSV, **Spalte salary_I_ohne_base_minimum**, für Rookies unverändert; Veteranen als max(P, M + 0,50 P) mit Mindestgehalt nach NFL-Erfahrung und historischem Vorjahres-Cap **428.784.607 $**. **Nicht** die frühere additive CSV-Hauptszenario-Spalte C verwenden. Top120-Summe nach dieser Korrektur **2.939.173.253 $**, Kandidaten-Cap **489.862.208,83 $** (gerundet 489.862.209 $). Das ist ein **datierter historischer Vertragspreis-Proxy**, kein 2027er Preis oder reproduziertes League-Equilibrium.
- **Gepaarte Spielermenge:** Von 613 grundsätzlich NFL-aktiven/produzierenden 2026er Spielern sind 611 auch im historischen Preisvektor; George Holani und Tyler Conklin fehlen dort. Für das bewusst gepaarte **Ein-Team-Starterproblem** bleiben nach Index > 0,15 **560 Spieler**. Alle tabellierten Qualitätswerte basieren auf demselben gepaarten 2026er Score, aber unterschiedlichen **datierten** Preisen. Als Quellen wurden die Blob-SHAs League **923e42dd8551d1bc3f4b812758dd856a34c82394**, Players **113ffa77ce0f607ac73a80204b363bd7af54aab9** und CSV **96ef8deac5930ffc3dc84dbf12cbbf4719c58489** geprüft; League beim Abruf: 2026, Week 11, FinalScoredWeek 10.

**Wichtige Zeitachsenwarnung:** Der 2026er Leistungsindex am 19.11. und der kritikalitätsbasierte Preisproxy vom 05.10. sind ein expliziter *What-if*-Cross-Snapshot. Die Differenz ist **kein kausaler, gegen 2027 validierter Salary-Effekt**. Es werden weder historische Besitzrechte noch die unbewiesene Annahme freier Superstar-Trades unterstellt.

## 3. Rechenmethode und Belastbarkeit

Der kleine lesende Prototyp erzeugt positionslegale Starterkandidaten mittels Score-minus-Lambda-Salary-Sortierung und untersucht lokale **Single-Player-Swaps**. Unter einer vollständigen Salary-Budgetgrenze werden für Besetzungsgrößen von **13, 20, 30, 35 und 40** zusätzliche disjunkte Bankspieler gewählt. Die Reserve wird **nach niedrigstem Salary** ergänzt und umfasst bei mindestens 20 Spielern experimentell **1 QB, 2 RB, 2 WR, 1 TE, 1 K** als definierte Zusatz-Absicherung; weitere Plätze werden möglichst billig gefüllt. Die Bench-Schwellen **0 / 5 / 8** meinen *Mindestwerte unseres geglätteten Indexpunkt-Proxy pro Bankspieler*, keine verifizierte Wochenverfügbarkeit.

Alle Salaries von Starter **und** Bank werden voll addiert; für diesen isolierten Basistest gelten **keine** Top20-Abrechnung, Dead-Cap-Lasten, IR/Taxi, Debt oder historischen Besitzrechte. Diese Belegungsszenarien sind **Sensitivitäten**, keine geplanten Pflichtkadergrößen: Unter dem künftigen Maximum 40 könnte ein Manager auch nur 20 oder 30 Spieler halten.

Die Lösungen sind **konkret finanzierbare Untergrenzen innerhalb der gepaarten Modellwelt**, nicht globale Maxima. Für die 13 Starter liefert die Lagrange-Relaxation zusätzlich eine rechnerische Obergrenze bei unveränderter Modellpopulation. Für 20–40 Spieler liegt **kein zertifizierender globaler MILP-/Constraint-Solver** vor. Insbesondere große Cap-Restwerte im Bank-8-Szenario zeigen mögliche Heuristiklücken an.

## 4. Ergebnisse: konzentrierte Top-13

| Größe | Veröffentlichte 2026er Salaries | Oktober-Criticality-Konzeptproxy |
| --- | ---: | ---: |
| Theoretischer 2026er All-Star-Starterindex (ohne Cap) | **275,504** | **275,504** |
| Kosten dieser All-Star-13 | **481,858 Mio. $** | **594,229 Mio. $** |
| Modell-Cap (Top120 / 6) | **475,171 Mio. $** | **489,862 Mio. $** |
| **Bisher gefundenes cap-legales Starterteam** | **274,670** | **268,199** |
| Starterkosten dieses Teams | **474,170 Mio. $** | **478,810 Mio. $** |
| Mathematische 13er-Relaxations-Obergrenze | **275,257** | **269,135** |
| Ungeschlossene Lücke (Obergrenze minus Fund) | ca. **0,587** | ca. **0,936** |

**Interpretation:** Die neue Preiswelt reduziert innerhalb dieser gepaarten Momentaufnahme das gefundene, allein durch Starter ausgeschöpfte Elite-Potenzial – sie verhindert aber kein sehr starkes Superteam. Ein Manager könnte eine hohe Spitze nur mit begrenztem finanziellen Spielraum für gute Reserven halten.

**Die Null-Dollar-Falle:** Unter den heutigen 2026er Salaries lassen sich theoretisch zahlreiche wenig produktive Bankspieler kostenlos ergänzen. Deshalb bleibt unter Preiswelt A selbst ein belegtes 40er-Modell mit fast ausschließlich günstiger Bank beim selben Starterindex von 274,670. **Das beweist gerade nicht**, dass eine starke 40er-Bank finanzierbar wäre oder das spätere Minimum wirkungslos ist.

## 5. Vollständige Kader und Bankqualität (Preiswelt B, kritikalitätsbasierter Proxy)

| Gehaltene Spieler | Mindest-Bankindex | Gefundener 13er-Starterindex | Starter-Salary | Bank-Salary | Rest-Cap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 13 | – | **268,199** | 478,810 Mio. $ | – | 11,053 Mio. $ |
| 20 | 0 | **268,199** | 478,810 Mio. $ | 7,795 Mio. $ | 3,258 Mio. $ |
| 30 | 0 | **266,700** | 456,451 Mio. $ | 18,971 Mio. $ | 14,440 Mio. $ |
| 35 | 0 | **266,700** | 456,451 Mio. $ | 24,937 Mio. $ | 8,474 Mio. $ |
| 40 | 0 | **266,700** | 456,451 Mio. $ | 31,182 Mio. $ | 2,230 Mio. $ |
| 20 | 5 | **268,199** | 478,810 Mio. $ | 9,306 Mio. $ | 1,747 Mio. $ |
| 30 | 5 | **266,700** | 456,451 Mio. $ | 23,442 Mio. $ | 9,970 Mio. $ |
| 35 | 5 | **266,700** | 456,451 Mio. $ | 31,943 Mio. $ | 1,469 Mio. $ |
| 40 | 5 | **265,216** | 435,662 Mio. $ | 41,571 Mio. $ | 12,629 Mio. $ |
| 20 | 8 | **266,941** | 472,896 Mio. $ | 16,222 Mio. $ | 0,744 Mio. $ |
| 30 | 8 | **265,457** | 452,108 Mio. $ | 36,372 Mio. $ | 1,382 Mio. $ |
| 35 | 8 | **265,216** | 435,662 Mio. $ | 52,481 Mio. $ | 1,719 Mio. $ |
| 40 | 8 | **260,739** | 384,580 Mio. $ | 74,284 Mio. $ | 30,998 Mio. $ |

Die 40er-Bank des preisminimalen 0-Schwellen-Falls kommt dabei nur auf ca. **2,64** durchschnittliche Indexpunkte; bei 5-Schwelle ca. **7,51**, bei 8-Schwelle ca. **9,90**. Letztere Szenarien sind **nicht** bewiesene sportliche/finanzielle Effizienzmaxima. Besonders die große verbleibende Cap-Reserve im 40/8-Fall macht deutlich, dass der nächste Constraint-Solver bessere Gesamtkombinationen suchen muss. Die Werte bleiben als *erreichbare* und positionslegale Probe interpretierbar.

Mit demselben Bank-8-Test sinkt in der veröffentlichten 2026er Null-Salary-Preiswelt der gefundene Starterindex für 40 Plätze auf **269,517** (Starter 429,203 Mio., Bank 43,042 Mio., Rest 2,926 Mio.). Damit hängt das scheinbar billige 40er-Roster im Istsystem stark vom **fehlenden allgemeinen Salary-Floor** ab.

**Vorläufige wirtschaftliche Diagnose:** Ein 40er-Limit mit voller Anrechnung kann sehr unterschiedliche Strategien zulassen, wenn niemand alle Plätze füllen muss. Es schafft aber **nicht automatisch** einen attraktiven Free-Agent-Markt oder langfristige Wettbewerbsdurchlässigkeit. Wer maximale Starterqualität konzentriert, zahlt real mit Bankqualität, Verletzungs-/Bye-Risiko oder verfügbaren Slots; ob das gegen **passive Dominanz** ausreicht, ist noch offen.

## 6. Wirtschaftliche Pflichtachsen und sechs Nordstern-Ziele

| Forschungsachse | Status dieser Einjahresprobe |
| --- | --- |
| Seller-Entlastung / Cut-Retention | **Nicht modelliert / N/A:** kein tatsächlicher oder hypothetischer Cut-Settlement |
| Buyer-Belastung | **Nicht modelliert / N/A:** keine Buyer, Deals oder akzeptierten Angebote konstruiert |
| Roster-Kapazität | **Hypothetisch 13/20/30/35/40 regulär**; alle disjunkt, mit definierten Backup-Quoten; tatsächliche IR-/Taxi-Eligibility, Besetzung, Aktivierung und gleichzeitige Drops ungeklärt |
| Ligaweite Dead-Cap-/Debt-Last | **Nicht modelliert**; bewusst keine bestehenden oder neu entstehenden Debt-Vintages im isolierten Snapshot |
| Folgejahres-Tilgung | **Nicht modelliert / N/A:** keine Kredite aufgenommen, daher auch keine belastbare Rückzahlungsprognose |

Der geschützte **Sechs-Ziele-Nordstern** wird damit nur teilweise überprüft: Ziel 4 (Kostendruck) und Ziel 5 (Wahlfreiheit zwischen Konzentration und Tiefe) sind als Mechanik sichtbar; Ziele 1/3 (mehrjährige Aufholbarkeit / Vermeidung kostenloser struktureller Dominanz), Ziel 2 (Unterschied zwischen dauerhaft gutem Management und passivem Besitz) sowie Ziel 6 (verlässlicher Vollzug inklusive IR/Taxi und Cap-Zeitpunkten) bleiben im Mehrjahresmodell zu validieren. Keiner der sechs Manager hat deshalb eine neue Regel beschlossen.

## 7. Nächste Forschungsgates

1. **Exakten Gesamtroster-Optimierer** als Gegenprüfung gegen die heuristischen Untergrenzen bauen; vollständige Kaderqualität, Verfügbarkeit und Salary-Anrechnung bei 20/30/35/40 als Wahl des Managers gemeinsam optimieren. Alle 13 Starter, 27 mögliche Bankspieler und Bank-Qualität müssen im gleichen Optimierungsproblem liegen.
2. **Sechs Manager statt nur eines:** das konzentrierte Topteam plus fünf konkurrierende, eigenständig legale Kader gleichzeitig bilden; Abstand zum realisierbaren zweitstärksten Team und verfügbare Free Agents nach dem Draft quantifizieren. Keine erzwungene Symmetrie von CP6h; keine fiktiven Käuferzusagen.
3. **Fünf oder mehr Zyklen:** echte/kalibrierte Rookie-Jahrgänge, Rookie-Year4-Neubewertung, NFL-Active/Retirement, Verletzungen/Bye-Kosten, Criticality-Repricing und dynamisches endogenes Cap. Berichten: Jahresmaximum, passiver Kern-Erhalt, aktive Jahr-für-Jahr-Strategie und **H5 = max über legale Strategien des Minimums der fünf Jahres-Starterindizes**; Verteilungen aus gepaarten Seeds statt einer perfekten Vorhersage.
4. **Erst danach** Zusatzhebel wie Elite-Progression (mit Cap-Endogenität), IR-/Taxi-Einbezug, C-add, erlaubter Vorgriff/Rückzahlung, Checkpoints und reale Durchsetzungskosten isoliert prüfen. Welt Z (eingespieltes System) vor Welt M (Migration), Expansion nur als gesonderter Marktbenchmark.
5. **Fachentscheidung offen:** Die vollständige 40er-Salary-Anrechnung ist ein ernsthafter Kandidat, nicht automatisch die beste Variante. Eine Regelvorlage benötigt mindestens einen reproduzierbaren Mehrjahresvergleich gegen 30/35, Bewertung aller sechs Nordstern-Ziele und Review durch die sechs Manager.

**Methodischer Grenzvermerk:** Alle konkreten Starter- und Bankwerte sind Einjahres-What-if-Ergebnisse mit dem 2026er Index. Keine genuine 2027–2031-Simulation, keine Titelwahrscheinlichkeit, kein echter Sleeper-Transaktionspfad, keine realen Managerreaktionen und keine historische Cap-Verletzung. Der ausführbare Rechenprototyp ist ein Research-Helfer, **kein Produktionsmodell**.
