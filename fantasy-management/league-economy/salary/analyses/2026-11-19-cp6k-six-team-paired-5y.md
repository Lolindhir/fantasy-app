# CP6k – Sechs-Team-Markt und gepaarte Fünfjahrespfade bei Full-Salary-Cap

> **19.11.2026 · Forschungscheckpoint zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · unratifizierter Designkandidat, keine aktive Ligaregel.** Fortsetzung von [CP6i](2026-11-19-cp6i-starter-ceiling-40er-full-salary.md) und [CP6j](2026-11-19-cp6j-full-cost-depth-sensitivities.md). Der vollständige ausführbare Prototyp ist [`cp6k_six_team_paired_5y.mjs`](../simulation/cp6k_six_team_paired_5y.mjs).
>
> **Kein bewiesenes Maximum:** Die hier genannten Zahlen sind 18 intern ausgeführte **synthetische**, fünfjährige, an jedem jährlichen Settlement legale Managerpfade und ein gepaarter Vergleich zweier Heuristiken. Weder das globale einjährige Maximum noch `max_legal min(I_1,…,I_5)`, ein empirisch kalibrierter 2027–2031-NFL-Verlauf oder eine stationäre Ligawirtschaft sind mathematisch oder extern validiert.

## 1. Konkrete Forschungsfrage und Hauptkandidat

Wie entwickelt sich ein bereits starkes Team, wenn sechs Manager im **gleichen, endogen bepreisten Spielerpool** konkurrieren, jeder gehaltene Spieler vollständig auf das Team-Cap angerechnet wird und der Manager den Elitekern (a) passiv verwaltet oder (b) mit laufenden Rookie-/FA-Entscheidungen erneuert? Welche Rolle spielt die Menge günstig verfügbarer neuer Spieler?

Der führende Hypothesenkandidat ist weiterhin **maximal 40 reguläre Plätze frei belegbar**, volle Salary-Anrechnung für **alle** tatsächlich gehaltenen Spieler, `Top120-Salary-Summe ÷ 6` mit Cap-Faktor `1,00`, Criticality als Performance-Modifier mit `k=1,5`, dreijährige Rookie-Dollarverträge, gleitendes 50-%-Minimum nach NFL-Erfahrung. Das ist **nicht** der heutige Top20-/0,90-Cap und **keine** verabschiedete neue Ligaregel. Die in diesem Prototyp benutzte Untergrenze **20 tatsächlich besetzter Plätze** ist eine **testweise Versorgungsvorgabe**, keine generelle künftige Ligapflicht oder ein Beweis für sinnvolle Minimaldepth.

## 2. Kontrollierte Daten- und Preiswelt

- **Archiv:** `fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv`, Git-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`, 1.268 Spieler; Startqualität `performance_3y` als archivierter 3Y-Index; Positionen QB/RB/WR/TE/K. **Es gibt keine realen NFL-Saisons 2027–2031 in dieser Quelle.**
- **Einjährige Initialpreise:** `salary_I_ohne_base_minimum` aus archivierter k1,5-Criticality/Rookie-Preiskombination. Für Veteranen ab Year 4 wird `max(P, M+0,5P)` nach dem historischen **Modell-Anker 434.255.984 $** aufgelegt; Rookie Year1–3 behalten ihre damals archivierten Rookie-Dollarvintages. Der 2026er Anfangs-Cap f=1 ist damit **489,862 Mio. $**, auf derselben Preisbasis wie CP6j-KF. Dieses Overlay ist keine vollständig rekonstruierte echte Vorjahres-Cap-/Rookie-Kette.
- **Initialverteilung:** sechs **disjunkte** synthetische 20er-Kader, je zwei QB/RB/WR/TE, vier RB/WR/TE-FLEX und ein K plus mindestens eine weitere QB/RB/WR/TE/K-Abdeckung, mit Qualitätsuntergrenze 3 für die initialen Bankspieler. Ein überlegener Konzentrationsmanager (Team 0) wählt zuerst; andere fünf Manager anschließend. Das ist **kein realer 2026er Besitz-/Trade-Replay** und kein unabhängiger MILP-Solver. Anfängliche Starterindizes je Seed: 11: **208,508 / 202,559 / 199,994 / 177,278 / 169,409 / 162,089**; 29: **208,667 / 199,380 / 196,868 / 186,319 / 167,785 / 160,562**; 47: **208,190 / 202,138 / 191,327 / 187,871 / 168,852 / 160,630**.
- **Kapazität:** genau 13 gültige Starter, mindestens 20 tatsächlich belegte reguläre Slots, höchstens 40. Die simulierten zusätzlichen besetzten Plätze kosten **voll** Salary. Keine kostenlose IR-/Taxi-/Reserve-Ausnahme und keine Top20-Ausnahme: **jene Sonderregeln werden nicht abgebildet**, sondern als separat entscheidungsbedürftig gekennzeichnet.
- **Neue NFL-Klassen:** pro Jahr exakt 30 hypothetisch ligaweit gedraftete Spieler plus **0 / 30 / 50** hypothetisch undrafted neue NFL-Spieler als drei *gepaarte* Supply-Szenarien. Synthese aus kontrolliertem Positionsmuster, publiziertem Scout-Proxy, unabhängig generierter tatsächlicher Leistung und individuellen Zufallssignalen – keine echten 2027+-Prospects. Rookie-Year1-Salary = 65 % Fantasy-Draft- und 35 % NFL-Draft-Rangsignal am **Vorjahres-Cap**, Year2 = 125 %, Year3 = 150 % des initialen Dollarbetrags, Year4+ normales Leistungs-/Minimum-Repricing. Die ungedrafteten Spieler stehen dem FA-Markt zur Verfügung und werden **nicht** gratis einem Team zugeschlagen.
- **Künftige Performance:** per Spieler/Seed/Jahr deterministisch unabhängige synthetische Produktion, moderate Erfahrungseffekte und altersabhängige NFL-Exit-Wahrscheinlichkeiten. Der zu messende jährliche **Starterindex `I_t`** entsteht aus der Drei-Saison-Glättung über diese simulierten Leistungen, nicht aus der ungesmoothten einzigen Jahresleistung und nicht aus echten Week-Statistiken. **Alle externen Einzelspielerschicksale bleiben in den zwei Managementregimen eines Paares identisch.**
- **Künftiges Salary:** Jahres-Repricing aus 3Y-Leistung und dynamisch aktualisiertem Positionsrang auf der **fest gehaltenen 2023–2025-DMLI-Kurvenform** (Criticality-Referenz 8,4417, Centered-25, `k=1,5`, lineare Extrapolation oberhalb von 20). Es erfolgt **keine jährlich neu gemessene DMLI-Kurvenform** aus 2027er Play-by-Play. Der Rookie-Zugang wird vor dem jährlichen marktweiten Top120/6-Cap-Lock eingerechnet; die Salary-Kette des nächsten Jahres nutzt dieses Vorjahres-Cap.
- **Kontrolltermine:** jährliches Preseason-Salary-/Roster-Settlement nach Rookie-Draft und freien Add/Drop-Reaktionen. Ausgeschiedene NFL-Spieler werden vor Rookie-Picks als notwendige Roster-Moves abgegeben. Während eines in sich abgeschlossenen Settlement-Bundles ist vorläufiges Overcap möglich, aber der **Endzustand** muss für alle sechs Teams cap- und slot-konform sein. Ein ganzjähriger permanenter Cap-Vollzug, Transaktionszeitfenster, IR/Taxi und echte Sleeper-Sanktionsmechanismen sind **nicht** nachgewiesen.
- **Keine de-facto-vollständige Marktökonomie:** Inter-Team-Trades und Gegenpartei-Zustimmung, Rookie-Pick-Trading, Cut-Retained/Dead Cap, Schuldvortrag/Amortisation und wöchentliche Availability/Injury-/Bye-Daten **nicht modelliert**. Nur tatsächlich freie, nicht von einem anderen Team gehaltene Spieler sind als Free Agents erwerbbar.

### Fairer Regimevergleich

**Passiv (Team 0):** Behält den einmal erstellten starken Veteranenkern, soweit legal; vollzieht nötige Cap-/Retirement-Cuts und reguläre fünf Rookie-Picks je Jahr auf Basis des öffentlichen Scout-Proxy, **keine** freiwilligen FA-Optimierungsswaps. Passiv bedeutet daher **nicht** absichtliches Nichtmitspielen oder Verzicht auf den regulären Rookie Draft.

**Aktiv (Team 0):** Dieselbe Startwelt, Rechte und exogene Talent-/Verletzungszufallszahlen; Rookie-Auswahl berücksichtigt öffentliches Scout-/Salary-Verhältnis und Positionbedarf. Je Jahr bis zu acht legale freiwillige FA-One-for-One-Swaps anhand des bekannten 3Y-Indizes, der Bench-, Young- und Cap-Optionen. Kein ex-post Blick auf die künftigen Leistungszahlen und keine Übernahme bereits gehaltener gegnerischer Spieler ohne Trade.

**Manager 1–5:** Unter beiden Regimen dieselbe dokumentierte Strategieklasse und bis zu zwei legale FA-Upgrades je Jahr. Sie reagieren auf die sich durch Team 0 ändernde Verfügbarkeit, statt künstlich einen ausbalancierten Kader zugeteilt zu bekommen. Rookie-Pick-Reihenfolge aus dem sportlichen Vorjahresrang: **5., 6., 4., 3., 2., 1.** (fünf Runden). Pick- und Counterparty-Assets selbst nicht gehandelt.

## 3. Ergebnismatrix – H5 = schlechtester Starterindex über fünf Jahre

Jede Zeile ist ein **gepaartes Experiment**: gleicher Seed, Rookie-Supply, ursprünglicher Sechs-Team-Besitzstand, Salary-/Cap-Zyklus und simulierte NFL-Ereignisse; nur Team-0-Managementverhalten ändert sich. `H5` bezieht sich auf tatsächlich nach dem jeweiligen synthetischen Saisonjahr verfügbaren 3Y-Starterindex und ist eine **erreichte Pfad-Untergrenze**, kein optimierter oder garantierter globaler Index.

| Seed | undrafted Spieler zusätzlich pro Jahr | H5 passiv | H5 aktiv | aktiv − passiv | alle Jahres-Checks legal |
|---:|---:|---:|---:|---:|:---:|
| 11 | 0 | 167,145 | 172,515 | +5,370 | ja |
| 11 | 30 | 167,513 | 175,498 | +7,985 | ja |
| 11 | 50 | 167,513 | 177,382 | +9,869 | ja |
| 29 | 0 | 166,393 | 175,309 | +8,916 | ja |
| 29 | 30 | 166,393 | 178,150 | +11,757 | ja |
| 29 | 50 | 166,393 | 179,932 | +13,539 | ja |
| 47 | 0 | 174,393 | 168,944 | **−5,449** | ja |
| 47 | 30 | 174,393 | 182,119 | +7,726 | ja |
| 47 | 50 | 174,393 | 180,738 | +6,345 | ja |

**Median über drei Seeds (nur diese drei, kein Konfidenzintervall):**

| zusätzliche undrafted Rookies | H5 passiv Median | H5 aktiv Median | Median der *gepaarten* H5-Differenzen |
|---:|---:|---:|---:|
| 0 | 167,145 | 172,515 | **+5,370** |
| 30 | 167,513 | 178,150 | **+7,985** |
| 50 | 167,513 | 179,932 | **+9,869** |

**8/9** gepaarte Szenarien belohnen die gewählte aktive Heuristik; **1/9** liefert ein negativ verbessertes Minimum trotz legaler Aktivität (Seed 47, Supply 0: −5,449). **Keine** Aussage, dass „gutes Management“ im Sinne eines global optimalen Verhaltens manchmal schlechter wäre: Dies ist eine begrenzte menschlich interpretierbare **Heuristik**, kein perfekter Strategiebeweis. Zusatz-Rookie-Supply wirkt stark auf dessen Handlungsraum; die passive Heuristik profitiert kaum vom undrafted FA-Markt, weil sie diesen nicht proaktiv nutzt.

### Beispiel: gleicher Seed 29, 30 zusätzliche Rookies

| Saison | H3Y-Starterindex passiv | aktiv | Aktiver Abstand zum besten Verfolger | Aktiver Anteil am unbeschränkten Jahres-All-Star-Index |
|---:|---:|---:|---:|---:|
| 2027 | 196,317 | 197,449 | +11,083 | 84,73 % |
| 2028 | 190,731 | 187,836 | +7,510 | 81,03 % |
| 2029 | 187,539 | 190,528 | +11,443 | 83,70 % |
| 2030 | 170,800 | 187,133 | +7,723 | 82,18 % |
| 2031 | 166,393 | 178,150 | +1,597 | 79,01 % |

**Plausibler Mechanismus (innerhalb der Modellspezifikation):** jährliches Repricing und Veteranen-Exits vermindern die bezahlbare/spielbare Kernqualität. Neue günstige Rookie-Vintages und legale FA-Swaps erlauben günstigere Erneuerung. Der aktive Manager bleibt bei Seed29/Supply30 alle fünf Jahre knapp/mehrfach vor jedem einzelnen Konkurrenten, aber sein **2031er All-Star-Anteil ist nur 79,01 %**. Im Beispiel Seed47/Supply30 liegt er 2031 trotz höherem H5 sogar **1,178 Punkte hinter** dem besten Verfolger. Ein höheres Team-H5 bedeutet nicht notwendig fünf Titel oder eine anhaltende positive Verfolger-Differenz.

Die `2027`-Werte starten aus der **frozen Oktober-2026-Proxywelt**, die in Jahr 1 mit einer synthetischen neuen Klasse fortgeschrieben wird. Sie dürfen nicht als reale 2027er Gehalts-, Football- oder NFL-Leistungsprognosen bezeichnet werden.

## 4. Reproduktions-/QA-Status

Detaillierte maschinenlesbare Originalausgaben je Seed:

- [Seed 11](2026-11-19-cp6k-seed-11-results.json), Commit `df439f4cd1158312b7d83c8987c35987478fab60`
- [Seed 29](2026-11-19-cp6k-seed-29-results.json), Commit `caf80e10e0463f69e60f9aa06a3a5f24cea26864`
- [Seed 47](2026-11-19-cp6k-seed-47-results.json), Commit `6a26e2df28baaaac195d8566d100ef97b1c0f066`

Alle Ergebnisse enthalten die erkannten Input-/Script-Blobs (`96ef8deac5930ffc3dc84dbf12cbbf4719c58489` / `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`), die jährlichen Team-Indizes, Caps, H5, Abstände und protokollierten Gesamtsystem-Aktionen. **Die Action-Counter beziehen sich auf alle sechs Teams zusammen; sie beweisen keine einzeln zurechenbare Team-0-Manager-Aktivität.**

- **18 von 18** vollständig fünfjährige Simulationspfade intern legal, d. h. **90 von 90** Jahres-Settlements mit **sechs disjunkten** Mannschaften jeweils 20–40 gehaltenen Spielern, 13 gültigen Startern und voller Salary ≤ Cap (540 Team-Jahresprüfungen).
- Alle **45 gepaarten** Jahresvergleiche besitzen jeweils denselben endogenen Team-Cap und denselben unbeschränkten All-Star-Index. Alle Team-0-Ausgangsroster und anfänglichen Sechs-Team-Verteilungen sind innerhalb des jeweiligen Seeds identisch.
- Alle Index-/Cap-/Roster- und gültigen H5-Ausgaben wurden aus den drei persistierten JSON-Dateien erneut gelesen und quergeprüft. **Das im Repo gespeicherte Node-ESM-Skript wurde mit dem Original-CSV in der verbundenen V8-Ausführung und einem Adapter für den CLI-Dateizugriff ausgeführt.** Kein unabhängiger nativer Node-CLI-/CI-/MILP-Solver- oder Peer-Review-Nachweis. Die verbundene Vollmatrix im Einzelaufruf lief ins Timeout; die Ergebnisse wurden deshalb **separat per Seed** ausgeführt und gespeichert; alle drei Blobs besitzen denselben Simulator- und CSV-Hash.
- Insbesondere ist **kein** global maximiertes `H5` oder mathematisch nachgewiesene Konzentrationsobergrenze gefunden. Es wurden keine realen abgeschlossenen 2027–2031er Saisons verarbeitet.

Nach Reproduktion im lokalen Repository:
```bash
node fantasy-management/league-economy/salary/simulation/cp6k_six_team_paired_5y.mjs --seeds 11 --supply 0,30,50 --json
node fantasy-management/league-economy/salary/simulation/cp6k_six_team_paired_5y.mjs --seeds 29 --supply 0,30,50 --json
node fantasy-management/league-economy/salary/simulation/cp6k_six_team_paired_5y.mjs --seeds 47 --supply 0,30,50 --json
```

## 5. Abgleich mit CP6f/CP6g und unveränderte offene Grenzen

- CP6f verwendete **30er-Pflichtkader, nur Top20-Salary-Cap-Anrechnung und faktorabhängige 0,70–0,90-Caps**, plus 30 gedraftete und 50 undrafted Rookies jährlich. CP6g verwendete einen anders aufgebauten 30er-Start und weniger Rookie-Nachschub mit abweichender Optimierung. Aus den zuvor stark divergierenden Expansionstests durfte **kein Faktor als bewiesen** gelten.
- CP6k stellt dagegen **alle gehaltenen Spieler** cap-relevant, Maximalgröße 40/versorgungsorientierte 20er-Untergrenze und **f=1,00** fest. Unter **einer einzigen identischen** Algorithmus-/Preiswelt variiert es zunächst nur die jährliche zusätzliche Rookie-Zahl **0/30/50** und gepaart das Management. Der positive aktive H5-Impuls wächst damit in mehreren Seeds deutlich, aber in Seed47 von 30 auf 50 nicht monoton. Dies belegt eine **starke Modellsensitivität** gegenüber dem Nachwuchspool; **es löst nicht** die ursprüngliche CP6f-/CP6g-Divergenz auf, weil deren Inputs/Cap-/Kadersemantik nicht identisch sind.
- Der Passiv-vs-Aktiv-Vergleich misst **FA-/Rookie-Management auf Basis bekannter Informationen**; keine realen Inter-Team-Trades, Trade-Pakete, Marktverhandlung, Verletzungs-/Bye-/Wochen-Verfügbarkeit, Salary-Retention oder Rebuild-Finanzierung.
- Die jährliche Positionen-*Rangzuordnung* ist dynamisch, die Kritikalitäts-*Kurvenform* ist eingefroren. Echte Positionsknappheit über veränderte NFL-Saisons oder eine neue Ligaformatstruktur wird dadurch **nicht** vollständig modelliert.
- Die heuristisch starke Team-0-Initialisierung (rund 208–209) bleibt unter dem bereits gefundenen 20er-/Bench-Qualität3-CP6j-Wert **211,094**. Die anderen Teams entstehen seriell nach diesem Manager, nicht aus einem endogenen vollständigen Trades-Gleichgewicht. Ein zukünftiger Maximalitätsnachweis muss die initiale Marktstruktur und alle sechs Manager gemeinsam optimieren, statt diesen H5 als systemische Obergrenze zu behandeln.

## 6. Fünf Finanzierungsachsen (explizit, nicht als erfüllte Vertragsprüfung behauptet)

| Forschungsachse | Evidenz aus CP6k |
|---|---|
| 1. Seller-Entlastung | Im Modell notwendige Cuts/FA-One-for-One-Swaps reduzieren die vollen gehaltenen Salaries; **reales Retained/Dead-Cap-Settlement nicht modelliert**, gross/netto mit Retention nicht bestimmbar |
| 2. Buyer-Gesamtkosten | **Kein Inter-Team-Trade**, also weder konkreter Buyer noch Zustimmung/Trade-Bundles. FA-Aufnahme wird mit **vollem** Salary gerechnet; keine real beobachteten Käufer-Transaktionen |
| 3. Roster-/IR-/Taxi-Kapazität | Sechs disjunkte reguläre 20–40er Kader jährlich überprüft, Draft-Kapazität hat explizite Cut-Kosten; **keine echten Sleeper-Taxi/IR-Berechtigungen** und keine wöchentlichen Start-/Activation-Deadlines |
| 4. Ligaweite Debt/Vintages | **Nicht modelliert**, nicht mit dem realen Schuldenstand von 0 $ gleichzusetzen |
| 5. Folgejahres-Tilgung | **Nicht modelliert**; weder Zahlungsdeadline noch H2/H3-Amortisation, Hard-Failure bei echter Zahlungsunfähigkeit oder Refinanzierungsverbot nachgewiesen |

## 7. Sechs Nordstern-Ziele – bisheriger Stand

1. **Langfristige Chancengleichheit:** Synthetische Verfolger bleiben aktiv; der vorerst stärkste Kern kann in mehreren Jahren überholt werden. Keine empirische Turnaround-Rate, keine echte Playoff-/Titelwahrscheinlichkeit.
2. **Gutes Management belohnen:** 8/9 gepaarte H5-Vergleiche belohnen die konkret modellierte aktive Heuristik, aber nicht immer, und nicht als globale optimale Strategie.
3. **Keine zementierte Dominanz:** Der Startvorsprung erodiert teils erheblich; es gibt keine automatisch garantierte fünfjährige Qualitäts- oder Titelvorherrschaft. Nicht bewiesen für optimales Management, freie Trades oder anders kalibrierte NFL-Zukunft.
4. **Wirtschaftliche Konsequenzen:** Alle Salary-Positionen voll anrechnen, der Preis stark gewordener Spieler steigt bei annualisiertem Reprice und der Starter-/Depth-Tradeoff bleibt messbar. Echte DeadCap-/Asset-Kosten fehlen noch.
5. **Strategische Freiheit:** Passiv und aktiv sind unterschiedliche legale Pfade; echter Reload/Rebuild/Win-Now-/Trade-Markttest steht aus.
6. **Operative Durchsetzung:** Jährliches Settlement ist intern reproduzierbar; permanente Sleeper-/App-Durchsetzung, Commissioner-Minuten, Grace/Hard-Failure und tatsächliche Ir-/Taxi-Aktivierung bleiben offen.

**Ratifizierung:** Der geschützte sechs-Ziele-Nordstern ist Forschungsmesslatte und nach wie vor nicht durch alle sechs Manager als Ligastatut bestätigt. Das neue Salary-/40er-Full-Cap-Modell ist ebenso **unratifiziert und nicht produktiv**.

## 8. Nächster fachlicher Hard-Gate (kein stilles "fertig")

1. **Echte obere Grenzen:** exakter MILP-/CP-SAT-Solver für 13+funktionale Bank und die **sechs disjunkten** Manager, mit optimalitätsbescheinigtem Einjahreswert; danach gekoppelte fünfjährige Strategie-Optimierung über begrenzte, legale Marktaktionen statt nur einer Heuristik.
2. **Empirisch kalibrierten 5Y-Pool herstellen:** reale NFL-Retirement-/Undrafted-/Rookie-Performance- und 3Y-Repricing-Übergänge der verfügbaren Saisons, ex ante getrennt von ex post und wöchentlich verfügbare Spieler/BYE/IR. Mehr Seeds (mindestens einige Dutzend), vorab definierte P10/P50/P90, allstar-normalisierte Dominanz und Aufholdauer statt nur n=3.
3. **Trade-/Contract-Ökonomie:** simulierbare, beidseitig akzeptierte Trades und Picks, Buyer-/Seller-Bundles, C-add-Retention, Debt-Vintages, echte amortisierbare Rückzahlung, sichere Cut-/IR-/Taxi-Deadline-Behandlung ohne gratis Nachrüstung.
4. **CP6f/g auf gleichen Inputs re-runnen**, sonst sind Unterschiede von 30+50-Rookie-Zufluss, Short-/Full-Salary, Greedy-Optik und Cap-Faktoren weiter nicht kausal zerlegt.
5. **Unabhängiger Node-/CI-/Reviewer-Check** auf diesem Draft-Zweig; keine Produktivdaten anfassen und nicht als finale Ligaregel mergen.
