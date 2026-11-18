# CP4 – Isolierte Rookie-/Minimum-/Dead-Cap-Sensitivitäten und Settlement-Gate

> **Stand:** 14.11.2026 · **Forschungs-Issue:** [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status:** begrenzter, reproduzierbarer Mechanik-Test; **kein Regelbeschluss**. Baut auf [CP2b](2026-11-06-salary-cap-cp2b-historical-compliance.md) und [CP3](2026-11-14-salary-cap-cp3-market-retention.md) auf. Die ursprünglichen Vergleichsrechnungen werden nicht rückwirkend umgeschrieben.
>
> **Normative Grundlage:** [geschützte sechsteilige Liga-Philosophie](../../../league-context/league-philosophy.md), Version 1.0 vom 14.11.2026; von Robert als Designmaßstab bestätigt, Zustimmung Marcels nur zu Zielen 1–5 dokumentiert, **noch keine ligaweite Ratifizierung**. Ziel 6 (einfacher, verlässlicher Vollzug) ist eigenständig und gleichwertig zu berücksichtigen.

## 1. Entscheidungsorientierte Ergebnisse

**Warum CP4 gerechtfertigt ist:** CP2/CP3 belegen die wirkliche Juni-Cap-Bereinigung, fehlenden ganzjährigen Vollzug, knappe simultane Käuferliquidität und den Verlust teilweise hochklassiger Nichtstarter. Noch offen ist, ob die bereits **als Konzept** geklärten Rookie-Contracts, das gleitende Minimum und der einjährige Dead-Cap-Zyklus **zusätzliche**, wirtschaftlich sinnvolle Anreize schaffen. Diese Mechaniken werden **nicht als stiller Bestandteil** der A/B/C-Reihe behandelt.

1. **Gleitendes Veteranen-Minimum (isoliert):** Bei dem eingefrorenen November-Preisstand steigt das Salary von **292 der 483** Spieler ab `Player.Year=4` (955 Spieler insgesamt). Die marktweite Summe ihrer Salaries steigt in der Proxy-Rechnung um **455,30 Mio. $**; **kein** betroffener Spieler gehört aber zu den damaligen ligaweiten Top 120 oder den ursprünglichen Top 20 eines Teams. Daher **0 $ Veränderung** an aktuellem Cap und an allen sechs Top-20-Kaderbelastungen. Die Regel differenziert günstige Spieler, erzeugt hier jedoch **keinen gemessenen Elite-Cap-Druck**.
2. **Rookie-Contracts (isolierter 60-Spieler-Kohortentest):** Die exakt zugeordneten **30 Picks 2025 in Year 2 und 30 Picks 2026 in Year 1** verändern die hypothetische 05.11.-Top-20-Belastung der sechs Teams und das **endogene** Liga-Cap. Bei einem offen als **Proxy** deklarierten gemeinsamen Dollar-Anker von 434.255.984 $ entsteht ein Cap von **431.964.895 $** statt **427.653.631 $** (+4.311.264 $); weiterhin **5/6** Teams über Cap. Das ist **keine vollständige Marktumstellung**: 2024er Rookie-Contracts, undrafted und nicht durch unsere beiden Rookie-Drafts abgebildete Young Players sowie echte historische Vorjahresanker sind noch **nicht** rekonstituiert.
3. **Dead Cap an Flos tatsächlichen Juni-Cuts:** Die ununterbrochene Eigentümerhistorie der acht Spieler ist anhand archivierter 2024/2025-Abschlussroster und Transaktionslogs bis 09.06. rekonstruierbar: sechs Tenure 2 (**15 %**), Darnold und Purdy Tenure 1 (**30 %**). Bei ihren historischen Juni-Salaries ergäben sich **37.551.933 $** hypothetisches Dead Cap.
4. **Die Abrechnungsdefinition ist für die Wirkung entscheidend:** Mit additiv stets zählendem Dead Cap stiege Flos Top-20-plus-Dead-Cap-Belastung am 29.06. auf **465.281.512 $** (**31.025.528 $ über Cap**); mit Dead-Cap-Slots **innerhalb** der 20 teuersten Einträge wäre es **439.197.718 $** (**4.941.734 $ über Cap**). **Beides sind offene Testsemantiken, keine beschlossene Regel.**
5. **Settlement-Reihenfolge ist ein eigenes hartes Gate:** Die reale Cap-Deadline der Saison 2026 steht auf **30.06.2026, 23:59:59 UTC**. Wenn Dead Cap beim **einzigen** verbindlichen Prüftermin *vor* der Compliance-Prüfung zurückgesetzt wird, entsteht aus den Juni-Cuts am Prüftermin **kein Dead-Cap-Druck**. Ein Reset *nach* einer vorher definierten Prüfung oder mehrere Prüftermine hätten dagegen andere Wirkungen. **Diese Reihenfolge darf CP5/CP6 nicht übergehen.**
6. **Cut kann Käuferliquidität erhöhen statt Trades zu fördern:** Werden die aktiven Salaries der acht hypothetisch am 09.06. gecutteten Spieler im *noch laufenden* Salary-Zyklus um ihre Retained-Salary-Anteile reduziert, steigen am 29.06. direkte Käuferpaare von **13/40 auf 16/40**, und die gemeinsame 0-Käufercut-Clearing-Obergrenze von **4/8 auf 5/8**. Für Purdy entsteht **ein** direkter Käufer statt keiner. Diese theoretische vorübergehende Vergünstigung kann den Anreiz zum Warten auf einen Cut auf Käuferseite erhöhen. **Sie ist nicht auf den erst nach der Deadline stattfindenden FA-Draft übertragbar.**

**Gesamtinterpretation:** Die Ergänzungen können unterschiedliche Ziele bedienen, sind aber kein nachgewiesener Ersatz für eine **verlässliche** Cap-Kontrolle. Eine höhere rechnerische Last ist nicht gleich mehr echte Trades, geringere Dominanz oder mehrjährige Aufholbarkeit. Positional Criticality und Marcels Franchise-Claim werden in CP4 **nicht** aktiviert.

## 2. Eingefrorene Quellen und saubere Modellgrenzen

| Komponente | Reproduzierbare Quelle / Regel |
|---|---|
| Heutiges Salary und Cap | `public/docs/Salary_Explanation.md`; `public/data/League.json` und `Players.json` aus Commit `799be2a25203f18face8185303f32b31be3d40a7` (05.11.2026, finale Scoring-Week 8), Players-Blob `6459aef56b661eb9f3f83ac6c2516577d328cf93` |
| Historische Juni-Kader | 07.06. `5b4ed63172deae79759e7150f8511bd2ea3edb4e`; 09.06. `7ece134fec39741aba8e82bda554f8f13e8bead4`; 29.06. `85e22feb064fdaf2257d6c3149c8d1655ada0908`, jeweils `public/data/League.json` |
| Historisches Juni-Salary | `public/data/Players.json` **vom selben 29.06.-Commit**; Git-Blob `21001d6c0819dbbcb3deff084d63fe377714541c`. Kontrolliert: Flo 07.→09.06.-Top-20-Differenz **119.838.611 $** wie CP2b; veröffentlichtes Cap **434.255.984 $** |
| Drafts/Zuordnung | `public/data/Drafts.json`, `public/data/past_seasons/Drafts/Drafts_2025.json`, `data-source/leagues/nfl-reise/seasons/{2025,2026}/drafts.json` und `data-source/nfl/draft/{2025,2026}.json`, alle unter `799be2a2…`; exakt 60/60 Spieler per Sleeper-/CanonicalPlayerID verbunden |
| Tenure | `data-source/leagues/nfl-reise/seasons/{2024,2025}/rosters.json` und archivierte abgeschlossene `public/data/past_seasons/Transactions/Transactions_{2024,2025}.json` sowie `public/data/Transactions.json` vom 05.11.-Commit; keine nur aus Namensgleichheit angenommene Zugehörigkeit |
| Konzeptdetails | `fantasy-management/league-economy/salary/salary-dead-cap-concept.md`: 65/35-Rookie-Preis, Y1/Y2/Y3 100/125/150 %, Vorjahres-Cap-Floors, Tenure 50/30/15/5 %, vollständige Salary-Reduktion beim Cut, max-Floor, Reset spätestens beim nächsten Salary Check |
| Modelle / Cap | **Top 120 marktweit, 0,9-Faktor, geteilt durch 6**, ganzzahlig kaufmännisch runden; Teams: die **20 höchsten** individuellen Salaries aus eindeutigem `Teams[].Roster`; Taxi/Reserve gehören bereits zur Roster-ID-Menge |

**Wichtige zeitliche Grenze:** November 2026 ist unter den **tatsächlich** geltenden Regeln entstanden (keine verpflichtende In-Season-Compliance). CP4 legt hypothetische Preise **auf dieselben beobachteten Kader**, verändert aber nicht rückwirkend die Entscheidungen, Drafts oder Transaktionen der Manager. June-Dead-Cap-Stresstest und November-Kohorten-Markt sind getrennte Preis- und Datumsszenarien; sie werden **nicht** in ein fiktives chronologisches Gesamtjahr zusammengeklebt.

## 3. CP4a – Gleitendes Minimum ab Year 4

Konzept, nicht aktiv:

```text
P = publiziertes normales Performance Salary (kein Projected)
M = round_half_up(Anker-Cap × Minimum-Prozentsatz(Player.Year))
NewSalary = max(P, round_half_up(M + 0,50 × P))
```

Die getesteten Minimum-Anteile betragen 0,40 % für Year 4, 0,45 % für Years 5–7 und 0,50 % ab Year 8. Rookie Years 1–3 bleiben ausdrücklich von der gleitenden Veteranenformel ausgenommen. Der Testanker **434.255.984 $** ist der beobachtete Juni-2026-Cap-Wert; das tatsächlich maßgebliche **Vorjahres-Cap des entsprechenden Salary-Zyklus** ist für diese hypothetische Neuregelung nicht vollständig historisch festgelegt.

| Ergebnis für 05.11.-Population | Wert |
|---|---:|
| Spieler im veröffentlichten `Players.json` | 955 |
| Darunter Veteranen `Player.Year>=4` | 483 |
| Veteranen mit verändertem Salary | **292** |
| Summe individueller Salary-Erhöhungen (alle betroffenen Spieler) | **455.300.913 $** |
| Betroffene unter den damaligen marktweiten Top 120 | **0** |
| Betroffene unter den ursprünglichen Top 20 eines der sechs Teams | **0** |
| Änderung endogenes Cap | **0 $** |
| Änderung Top-20-Belegung pro Team | **0 $** |

**Interpretation:** Das gleitende Minimum ist nicht generell wirkungslos: Es verändert individuelle Preise, kann für End-Roster mit weniger als 20 hochpreisigen Spielern und bei Floor-/Retained-Salary-Fällen relevant werden und macht Low-End-Preise differenzierter. **Es erzeugt in diesem eingefrorenen Sechs-Team-Novemberzustand allein jedoch keinen zusätzlichen Star-/Kern-Cap-Druck.** Eine auf seine Einbindung gerichtete Implementierung wäre für den Zweck „bestehende Dominanz brechen“ derzeit schwach begründet. Das ältere **voll additive** Minimum aus dem 05.10.-Bericht bleibt ausdrücklich **überholt** und ist hier kein Testmodell.

## 4. CP4b – Rookie Contracts Year 1–3 als begrenztes Markt-Overlay

### 4.1 Vertragsformel, Reichweite, nicht beobachtete Dollar-Anker

Für zwei Draft-Signale gilt:

```text
DraftPct(r,N) = 0,30 % + 3,20 % × [1 − (r − 1)/(N − 1)]^3,5
Undrafted in einem Signal: 0,25 %
Year1Pct = 65 % × FantasyDraftPct + 35 % × NflDraftPct
Year1Dollar = round_half_up(Year1Pct × Cap des Vorjahres)
Year2Dollar = max(round_half_up(1,25 × Year1Dollar), Year2Minimum)
Year3Dollar = max(round_half_up(1,50 × Year1Dollar), Year3Minimum)
Year4: 3 abgeschlossene NFL-Saisons + normales Performance Salary
```

Der Versuch verwendet 2025 `N_Fantasy=30`, `N_NFL=86`; 2026 `N_Fantasy=30`, `N_NFL=80`, NFL-Pool ausschließlich QB/RB/WR/TE. Alle 60 Picks wurden identifiziert und sind auch im 05.11.-Player-Markt enthalten. Für 2026 gilt im Test **Year 1**, für 2025 **Year 2**, **nicht** fälschlich Rookie Year 1 für beide.

Für **2025 Year 2** wäre das tatsächlich maßgebliche **2024er Cap als ursprünglicher Y1-Dollaranker** nötig, für **2026 Year 1** das **2025er Cap**. Diese Werte sind in der geprüften historischen Quelle als durchgängige *neue-Regel-Cap-Kette* nicht belegt. **Daher werden sie hier nicht erfunden.** Stattdessen wird nur als einheitliche Sensitivitätsachse **434.255.984 $** eingesetzt; zusätzlich ±10 % getestet. Das sind hypothetische Dollarwerte, keine beobachteten gezahlten Verträge und **kein** abgeschlossener Retroaktiv-Backtest. Ein vollständiges Contract-/Cap-Refresh müsste zuerst die historischen Anker, die 2024er Gründungskohorte und die restlichen nicht gedrafteten jungen Spieler einbeziehen.

### 4.2 Ergebnis – gleiches eingefrorenes November-Roster

Nur die Salärs der **60 Fantasy-Rookie-Draftspieler 2025/2026** werden im marktweiten November-Preisvektor ersetzt; alle anderen Spieler bleiben bei ihrem damaligen Salary. Das Cap wird **je Variante erneut** aus den höchsten 120 marktweiten Salaries berechnet, statt den alten Dollarwert zu fixieren.

| Variante | Hypothetisches Cap | Δ gegenüber A | Teams über Cap |
|---|---:|---:|---:|
| **A**: publiziertes November-Salary | **427.653.631 $** | – | **5/6** |
| **M**: nur gleitendes Veteranen-Minimum | **427.653.631 $** | 0 $ | **5/6** |
| **R60**: nur 2025/26-Rookie-Verträge | **431.964.895 $** | **+4.311.264 $** | **5/6** |
| **R60+M**: beide isoliert kombiniert | **431.964.895 $** | **+4.311.264 $** | **5/6** |

| Team | Tatsächliche Top-20-Belegung (Mio. $) | R60-Belegung (Mio. $) | Differenz |
|---|---:|---:|---:|
| Mighty Giants | 440,46 | 451,21 | **+10,75** |
| Packers | 460,08 | 461,40 | +1,31 |
| Flo / Just Bill | 510,87 | 514,47 | +3,60 |
| Jan / Mammoth Marauders | 484,31 | 492,21 | +7,91 |
| Dennis | 348,17 | 366,51 | +18,34 |
| TimpaBay | 460,50 | 472,96 | +12,46 |

**54/60** individuelle Kohorten-Salaries steigen relativ zur publizierten November-Baseline, **6/60** sinken. Das ist erwartbar für die im aktiven Modell vielfach sehr günstigen 2026er Rookies, aber **keine Aussage**, dass ein langfristiger Rookie-Vertrag generell teurer oder billiger als eine künftig unabhängig gerechnete Marktbewertung wird.

Konkrete **nur illustrative, mit dem Testanker berechnete** Verträge:
- Ashton Jeanty, 2025 Rookie 1.01: Y1 **14.810.064 $**, Y2 **18.512.580 $**, Y3 **22.215.096 $**; publiziertes November-2026-Salary **11.745.089 $**. Vertrag **teurer** als publiziertes Y2-Performance-Salary.
- Bhayshul Tuten, 2025 Rookie 3.02: Y1 **3.360.569 $**, Y2 **4.200.711 $**, Y3 **5.040.854 $**; publiziertes November-Salary **1.608.022 $**. Sein 2026er Breakout-PPG aus CP3 ist nicht dasselbe wie bereits realisierter Year-2-Cap-Surplus.
- Jaxson Dart, 2025 Rookie 4.03: Y2 **5.925.648 $** gegenüber publiziertem **13.816.272 $**; günstiger um **7.890.624 $**. **Solche Unterschiede bestehen in beide Richtungen.**
- Carnell Tate, 2026 Rookie 1.01: Y1 **14.781.467 $** statt bislang **0 $**; Year-1-Draftsignal wird bewusst schon im Rookiejahr wirtschaftlich berücksichtigt.

**Modellgrenze der Contract-Portabilität:** Unter der Overlay-Variante folgt der Y1-3-Contract dem **gedrafteten Spieler**, auch wenn er inzwischen getradet oder gecuttet/aufgenommen wurde. Das ist eine **Testannahme**, keine ausdrücklich entschiedene Rücksetz- oder Vertrags-Portabilitätsregel nach Cut. Am Freeze halten **47/60** Spieler irgendein Team, **10/60** davon nicht das ursprüngliche Draft-Team, **13/60** sind ungebunden. Würden nur die beim ursprünglichen Draft-Team gehaltenen Rookies ihren Vertrag behalten, entstünde unter demselben Anker ein anderer Cap-Proxy von **431.520.270 $** (+3.866.639 $); dies ist **keine Empfehlung**, Verträge bei einem Trade zu vernichten. Die Portabilität ist in CP5/CP6 explizit zu behandeln.

### 4.3 Anker-Unsicherheit ±10 % (keine historische Preisbehauptung)

| Einheitlicher Modellanker | R60-Cap | Δ gegenüber publiziertem November-Cap | Minimum allein: Δ Cap |
|---|---:|---:|---:|
| **390.830.386 $** (−10 %) | 429.923.602 $ | +2.269.971 $ | 0 $ |
| **434.255.984 $** (Proxy) | 431.964.895 $ | +4.311.264 $ | 0 $ |
| **477.681.582 $** (+10 %) | 434.233.085 $ | +6.579.454 $ | 0 $ |

Diese Bandbreite prüft nur die **Sensitivität gegenüber einem einheitlichen fiktiven Anker**, **nicht** den tatsächlichen historischen 2024-/2025-Cap-Pfad. Der Vorzeichenbefund bleibt bestehen: Das unvollständige R60-Overlay ist im jeweiligen Modell etwas capsteigernd; die isolierte Veteranen-Minimum-Variante verändert die Top-120-/Top-20-Kosten nicht.

## 5. CP4c – Dead Cap am historischen Juni-2026-Ereignis

### 5.1 Historisch gestützte Teamzugehörigkeit

Abgleich über Sleeper PlayerID, 2024er und 2025er Saisonabschlussroster, erfolgreiche Transaktionen und Juni-2026-Flo-Roster. Sechs der acht Kandidaten sind **durchgehend seit 2024** bei Flo nachgewiesen, ohne archivierten Abgang in den geprüften Folgeprotokollen; Darnold wurde im Oktober 2025, Purdy Ende Oktober 2025 von Flo aufgenommen. Daraus folgt für **League Season 2026** als hypothetische Vertrags-Tenure:

| Am 09.06.2026 von Flo gecuttert | Juni-Salary $ | Tenure | Dead-Cap-Satz | Hypothetisch einbehalten $ |
|---|---:|---:|---:|---:|
| Alvin Kamara | 24.366.017 | 2 | 15 % | 3.654.903 |
| George Kittle | 23.012.459 | 2 | 15 % | 3.451.869 |
| Sam Darnold | 24.155.999 | 1 | 30 % | 7.246.800 |
| Terry McLaurin | 18.972.800 | 2 | 15 % | 2.845.920 |
| Travis Etienne | 22.831.903 | 2 | 15 % | 3.424.785 |
| Javonte Williams | 16.950.753 | 2 | 15 % | 2.542.613 |
| Romeo Doubs | 12.877.813 | 2 | 15 % | 1.931.672 |
| Brock Purdy | 41.511.235 | 1 | 30 % | 12.453.371 |
| **Gesamt** | **184.678.979** | | | **37.551.933** |

Die Preise sind **damals archivierte Salaries**, keine Oktober-/November-Backcasts. Der verwendete Cut-Prozentsatz ist dagegen ein **noch nicht geltendes Konzept**; diese Rechnung sagt nicht, Flo habe tatsächlich Dead Cap bezahlen müssen. Keine der acht rechnerischen Salary-Reduktionen berührt in diesem Beispiel den Veteranen-Minimum-Floor; der Retained-Salary-Identitätscheck gelingt exakt nach Dollar-Rundung.

### 5.2 Zwei explizit *nicht* beschlossene Top-N-Abrechnungssemantiken

Fakten: Flos Top-20-Belastung im 07.06.-Kader **547.568.190 $**, im 09.06.-Kader **427.729.579 $**; exakte Entlastung **119.838.611 $**. Im Juni galt Cap **434.255.984 $**, d. h. nach den Cuts **6.526.405 $** rechnerischer Puffer ohne Dead Cap.

| Isolierter Snapshot-/Abrechnungsversuch am 29.06. | Cap-relevante Belastung | Abstand zum Cap |
|---|---:|---:|
| Historisch **ohne** Dead Cap | 427.729.579 $ | **−6.526.405 $** |
| **S1:** Top20(gehaltene Spieler) **+ alle** acht Dead-Cap-Anteile | **465.281.512 $** | **+31.025.528 $** |
| **S2:** Top20(gehaltene Spielersalaries **und** acht Dead-Cap-Einträge als virtuelle Slots) | **439.197.718 $** | **+4.941.734 $** |

S1 führt die Dead-Cap-Zahlungen **vollständig** gegen das Cap. S2 lässt jede einzelne Dead-Cap-Verpflichtung um einen der 20 begrenzten Salary-Slots konkurrieren, wodurch kleinere Verpflichtungen aus dem betrachteten Top-20-Korb fallen können. **Keine** Semantik ist in den aktuellen konzeptionellen Quellen als produktive verbindliche Top-20-Abrechnung ratifiziert. Vor allem S2 kann die wirtschaftliche Wirkung von Dead Cap massiv abschwächen; deshalb nicht stillschweigend eine davon als „eigentlich gemeint“ festlegen.

Diese Tabelle **ist keine legale Cut-only-Reoptimierung**: Flo könnte unter einer tatsächlich vorab bekannten Dead-Cap-Regel andere Cuts, Trades oder Timing-Entscheidungen getroffen haben. Das hypothetische Festhalten an den acht historischen Cuts ist lediglich die reproduzierbare Gegenprobe.

### 5.3 Reihenfolge am 30.06. – das zentrale Settlement-Gate

Dokumentierter Liga-Zeitpunkt: `CapDeadline = 2026-06-30T23:59:59Z`. Das Konzept lautet: Dead Cap gilt **bis zum nächsten** regulären Salary Check und **wird dann resettet**. Die punktgenaue Reihenfolge von **Prüfung, Reset, Neupreisung und neuen Transaktionen** ist jedoch für die neue Durchsetzungsregel **nicht** entschieden.

| Abrechnungsfenster | Konsequenz am einzigen Pflichttermin |
|---|---|
| **Prüfen vor Reset:** Die zusätzlichen S1-/S2-Dead-Cap-Kosten können vor dem Ende des alten Salary-Zyklus Cap-Compliance verhindern; es müsste eine vorher rechtzeitig erreichbare legale Lösung existieren |
| **Reset vor Prüfen:** Die acht Alt-Cut-Verpflichtungen fallen am Prüftermin heraus; isoliert bei identisch gehaltenen Juni-Preisen gilt wieder die historische 427,73-Mio.-Top20-Belegung; alte Dead Caps würden an diesem Termin **nicht** kontrollwirksam |
| **Vorherige Zusatz-Prüftermine oder permanente Kontrolle:** Dead Cap kann zwischen 09.06. und 30.06. wirksam sein, selbst wenn am 30.06. resettet wird; dies erhöht den Vollzugsaufwand und bleibt **unbeschlossene** Policy |

Nach dem regulären Salary Check wird das neue Cap aus einem **neuen** Preisvektor berechnet; die dritte Tabellenzeile ist daher **kein** historisch beobachteter 2026-Post-Deadline-Wert. **Ohne explizite atomare Reihenfolge ist die oft behauptete Wirkung „Dead Cap macht frühe Juni-Cuts teurer“ nicht gesichert.**

### 5.4 Bilaterale Trade-vs-Cut-Asymmetrie im laufenden Zyklus

Wird der Dead-Cap-Anteil des jeweils cuttenden Managers zu 100 % vom aktiven Salary des Spielers abgezogen, wird derselbe Spieler **vor dem Reset** für die neue Erwerberseite günstiger. Beispiel Purdy: ursprüngliche Salary **41.511.235 $**; hypothetischer Cut bei 30 % → Dead Cap Flo **12.453.371 $**, aktives Salary für anderen Käufer **29.057.864 $**. Dabei bleibt ohne Floor der ligaweite Retained-Salary-Betrag erhalten.

Bei exakt denselben **fünf** Juni-2026-Käuferrosters und bei festgehaltenem Monats-Cap gilt:

| Käuferprobe am 29.06. mit acht Kandidaten | Ursprüngliches Salary (Trade ohne Retention) | Nach hypothetischem Cut, aktives Salary reduziert |
|---|---:|---:|
| Käufer-Spieler-Paare ohne eigenen Käufercut legal | **13/40** | **16/40** |
| Maximale Zahl gleichzeitig aufnehmbarer Spieler, **ohne** Käufercuts | **4/8** | **5/8** |
| Direkte Käufer für Brock Purdy | **0/5** | **1/5** |

**Kein Match der realen 2026er Transaktionen unter B/C:** Diese vergünstigten Preise setzen einen tatsächlichen Cut **vor** dem regulären Reset voraus; die sieben realen FA-Draft-Auswahlen erfolgten **nach** der Deadline. In einem permanenten Cap hätte sich die Verfügbarkeit der Kandidaten ebenso anders entwickeln können.

**Anreizkonflikt:** Ein Verkäufer hat unter Dead Cap einen Grund, vor dem Cut zu traden, um kein Retained Salary zu tragen. Ein Käufer kann zugleich ein Interesse an der billigeren **Cut-/FA-Alternative** haben, gerade wenn er den unveränderten vollen Trade-Salarypreis nicht finanzieren kann. Für die Verkäuferseite ist ein fehlender Käufer nicht durch einen theoretisch vorhandenen Pick zu ersetzen. Die Veränderung dieser Verhandlungsmacht ist **plausibel**, aber ohne Angebots-/Ablehnungsdaten und legalen Counterfactual **nicht kausal beobachtet**. Es ist **keine** neue Salary-Retention-Trade-Option beschlossen.

### 5.5 Repeated Cuts, Floor und Rückerwerb

Das Konzept erlaubt wiederholte Cuts, jeder Cut erzeugt einen neuen Dead-Cap-Anteil auf Basis des *dann* aktiven Salaries. Bei 20 Mio. Ausgangssalary und zweimaligem 50-%-Cut ergeben sich ohne eingreifenden Floor:

```text
Team A Cut 1: 10 Mio. Dead Cap, aktives Salary 10 Mio.
Team B Cut 2:  5 Mio. Dead Cap, aktives Salary  5 Mio.
Gesamte ligaweite Verpflichtung: 10 + 5 + 5 = 20 Mio.
```

Nimmt Team A den Spieler zwischen zwei Cuts erneut auf, kann es **mehrere** eigene Dead-Cap-Anteile tragen. Bei additiv vollständig gezählten Verpflichtungen bleibt die Summe seiner eigenen aktiven und retained Anteile ohne Floor konserviert; bei einer Top-20-**Slot**-Semantik kann sich die **effektiv gezählte** Belastung trotzdem verändern, weil aus einem großen Eintrag mehrere kleinere werden. Sobald der Veteranen-Floor greift, darf die Summe der nominalen Verpflichtungen bewusst oberhalb der ursprünglichen Salary liegen. Diese logischen Invarianten sind **keine operative Anti-Washing-Regel** und werden hier nicht zu einer neuen zusätzlichen Strafe umgedeutet.

**Zusätzliche offene Policy-Gates:** Wann startet bei einer Wiederaufnahme eines ursprünglich gedrafteten Rookie die Vertragstenure? Bleibt ein Year-2/3-Contract unverändert portabel? Werden Dead-Cap-Anteile immer zusätzlich angerechnet oder zählen sie nur innerhalb Top N? Können offene Cuts/Trades zum selben Tick wie Deadline/Reset zugelassen werden? Welche Grace-/Taxi-/IR-Semantik gilt? Diese Punkte sind **nicht durch CP4 beschlossen**.

## 6. Vergleich gegen die sechs geschützten Designziele

| Nordstern-Ziel | Beobachtbare CP4-Wirkung | Abgrenzung |
|---|---|---|
| **1 Langfristige Aufholbarkeit** | Noch keine mehrjährige Titel-/Chancenwirkung gemessen | 2024 kein vergleichbarer Rookie-Draft, 2025/26 ohne kompletten Y3/Y4-Outlook |
| **2 Management belohnen** | Rookie-Verträge bepreisen Draftentscheidung und erzeugen je Spieler unterschiedliche Folgejahreskosten; Dead Cap kann frühes Trade-/Cut-Timing bedeutsam machen | Es dürfen sich nicht automatisch falsche Anreize durch ein Settlement-Loch ergeben |
| **3 Keine gratis perpetuierte Dominanz** | Feste Y1–3-Bindung mit Y4-Neupreisung begrenzt *im Konzept* alte Rookie-Vorteile; zusätzlicher Dead-Cap-Druck ist stichtagsabhängig | Weder tatsächliche mehrjährige Aufholbarkeit noch tatsächliche Trennung starker Star-Duos ist damit bewiesen |
| **4 Wirtschaftliche Konsequenzen** | R60 verändert konkrete Top20-Kosten; isoliertes Minimum verändert sie in diesem Snapshot nicht; DeadCap-S1/S2 massiv verschieden | Ein ausgerechneter Mehrbetrag ist nicht automatisch ein Trade oder erzwungener Starterverlust |
| **5 Strategische Freiheit** | Trade-vs-Cut, Prospects, Bench und Veteranen werden potenziell gegeneinander handelbar | Käufer können auf preisreduzierende Cuts warten, wodurch ein Trade gerade **schwieriger** werden kann |
| **6 Operativer Vollzug** | Cap-Prüfung, Salary-Zyklus, Dead-Cap-Reset, Vertrags-Portabilität und Sequenzierung sind kritische Prozessknoten | Ohne verlässlichen günstig kontrollierbaren Zeitpunkt keine valide Empfehlung eines komplexen Vertragsmodells |

**Zentrale wirtschaftliche Folgerung:** Die Mechaniken sind *nicht* redundant. Rookie-Verträge schaffen Kosten und eventuell zeitlich begrenzte Surplus-Chancen; das gleitende Minimum schützt vor verschwindend kleinen Preisen und beeinflusst Floor-/Cut-Mechanik; Dead Cap kann wirtschaftliche Timing- und Liquiditätskosten erzeugen, wirkt aber nur mit passender Abrechnung und Durchsetzung. **Nicht** auf Basis der größten Over-Cap-Zahl automatisch eine neue Regel empfehlen.

## 7. Reproduktionsvertrag und QA

Die quantitativen Prüfergebnisse stehen zusätzlich maschinenlesbar in [CP4 Kennzahlen](2026-11-14-salary-cap-cp4-metrics.json). Zur unabhängigen Wiederholung:

1. Eingefrorene `Players.json` (05.11.) mit IDs, `Salary`, `Player.Year` laden; alle `Team.Roster`-IDs deduplizieren. Ausgangs-Assertion: aus den 120 höchsten `Salary`-Werten `round_half_up(0,9 × Summe / 6) = 427.653.631` exakt.
2. Veteranen-Minimum: Nur `Player.Year>=4`; `M = round_half_up(434255984 × yearPct)`, `New = max(P,round_half_up(M+0,5×P))`. Dann alle marktweiten Top120 und Team-Top20 erneut bestimmen. Assertions: 483 untersucht, 292 erhöht, Top120- und Team-Top20-Delta null.
3. R60: 2025er `2025_Rookie` und 2026er `2026_Rookie` aus **verschiedenen** Draftdateien laden; aus `data-source` den richtigen **Rookie**-Draft anhand der PlayerID matchen, nicht versehentlich den ebenfalls 30-Pick-starken 2026er Free-Agent-Draft verwenden. NFL-Draft-Pool QB/RB/WR/TE: 86 bzw. 80; Rang aus NFL Overall Pick, dann 65/35-Kurve, ganzzahliges Y1-Salary, 2025 Y2 125 % des **gerundeten** Y1-Dollarwerts. 60/60 gematcht, 0 fehlende ID.
4. R60/M/R60+M **nur** im geänderten Preisvektor bewerten und das Cap aus **dessen** Top120 endogen neu bestimmen; keine Mischung von A-Markt-Cap und R60-Kosten. Assertions: R60-Cap 431.964.895, M-Cap 427.653.631, fünf Teams über Cap im unveränderten beobachteten Roster.
5. 07.06.- minus 09.06.-Flo-Roster ergibt acht IDs; deren Juni-Salarypreise vom 29.06. und den historischen 2024/25-Abschlussroster-/Transaktionsevents entnehmen. Sechs Tenure2, zwei Tenure1; `round_half_up(Salary × Rate)`, ohne Floor-Eingriff. Assertions: Salariessumme 184.678.979, Deadcap 37.551.933, historische Top20-Entlastung 119.838.611.
6. `Top20(gehalten) + Summe(DeadCap)` vs. `Top20(gehaltene Salaries ∪ DeadCap-Slots)` als bewusst unterschiedliche **Testsemantik**. Assertions: **465.281.512** vs. **439.197.718**, beide gegen 434.255.984.
7. Käufermarkt: nach Cut verbleibendes aktives Salary = ursprüngliches Juni-Salary minus DeadCap, Cap am 29.06. für den isolierten **alten** Zyklus festgehalten. Acht Einzelkandidaten × fünf Käufer sowie alle 256 Teilmengen je Käufer, disjunkte Bitmasken-DP. Assertions: direkte Paare 13→16, gemeinsame Clearing-Obergrenze ohne Käufercut 4→5, Purdy direkte Käufer 0→1. Ein späterer Salary-Reset vernichtet diese temporäre Cut-Vergünstigung.
8. Daten- und Entscheidungsevidenz strikt markieren. **Kein** historisches tatsächliches Tradeangebot, kein dauerhaft eingefrorener Cap über mehrere Salary-Zyklen, kein vollständiges Y1–Y4-Vertragsmodell aller NFL-Young-Players, kein hypothetisches in-season-Managerverhalten wird als Tatsache ausgegeben.

Für jedes Beispiel mit historischen Spielersalaries gilt die **jeweilige** datierte Quelle; 05.11.-Salary, Juni-Salary, Oktober-Criticality-Simulation, aktive und nicht aktive Vertragslogik werden nicht vermischt.

## 8. Abschlussgrenze / präziser Handoff an CP5

**CP4 ist als abgegrenzter Mechanik-/Settlement-Stresstest abgeschlossen, nicht als vollständige mehrjährige Vertrags- oder Franchise-Economy-Simulation.** Offen bleiben insbesondere: echte Vorjahres-Cap-Anker und vollständige Jahrgangspopulation; Contract-Portabilität nach Transfer/Cut; Dead-Cap-TopN-Abrechnung; Prüfzeitpunkt relativ zum Reset; atomare Trade-/Roster-Settlement-Reihenfolge; Eigentümerverhalten; echte Mehrjahres-Chancenverteilung. Diese Fragen sind **Design-/Daten-Gates**, keine durch die Rechnung rückwirkend beschlossenen Policyentscheidungen.

**CP5 als nächster Arbeitsschritt:** Innerhalb desselben Issue #1344 das tatsächliche System A, ein schlichtes jährliches/mehrere feste Termine verwendendes Modell, B (permanenter Cap-Vollzug), C (zusätzliche Criticality) und – nur, soweit der Nutzen die zusätzliche Komplexität rechtfertigt – die **bereits** geklärten Rookie-/Minimum-/Dead-Cap-Konzeptbausteine anhand derselben sechs Nordstern-Ziele und messbaren operativen Umsetzungskosten vergleichen. Marcels vorgeschlagener Franchise-Claim bleibt **getrennt** und unbeschlossen. **Keine Veränderung** an `public/data`, `data-source`, `data-derived`, Modellen, Generatoren, App, Salary-Regeln, Drafts, GitHub Actions oder kanonischen Fachentscheidungen.