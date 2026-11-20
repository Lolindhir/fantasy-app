# CP6m – Jährliches Überziehen oder dauerhaft bindendes Salary Cap: Welche Managemententscheidungen werden interessanter?

> **20.11.2026 · Issue [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Forschung unter dem unveränderten [geschützten Sechs-Ziele-Nordstern](../../../league-context/league-philosophy.md), kein Ligabeschluss.** Nutzerfrage: Ist das bewusste unterjährige Überziehen (All-in und nachfolgender Cap-Abbau) gut oder schlecht für die Liga-Ziele, oder führt ein **ganzjährig** bindendes Cap zu interessanteren Entscheidungen? Unter „konstant“ verstehen wir hier **dauernd geltende Compliance**, **nicht** einen über Jahre eingefrorenen Dollar-Cap. Das Cap darf beim regulären Jahres-Repricing nach denselben Regeln für alle neu bestimmt werden.

## 1. Status- und Modelltrennung

- **Aktive 2026er Cap-Regel:** Pflichtprüfung zur jährlichen Cap Deadline. Spätere Under-/Over-Cap-Stände sind nicht automatisch Regelverstöße.
- **Konzeptionell geklärt, nicht aktiv:** Ein Cut kann anteilig **Dead Cap im laufenden Salary-Zyklus** erzeugen, nach 50/30/15/5 % Team-Tenure; alles setzt **am nächsten regulären Salary Check** zurück. Kein mehrfaches jährliches Dead-Cap-Reset nur wegen zusätzlicher Cap-Prüfpunkte.
- **CP6l** rechnete hingegen mit **einer neu erfundenen, ausdrücklichen H2/H3-Cap-Schuld**. Das ist eine *separate, unratifizierte Alternative*, weder notwendig noch Teil des üblichen jährlich wieder legal zu machenden All-ins. Deshalb in **CP6m-Baseline keine** H2/H3-Kreditvintages und keine „Tilgung“ in Folgejahren.
- **Vergleich A/F2/F3/B:** A = heute jährlicher bindender Check; F2 = zusätzlich nach Free-Agent-Draft; F3 = zusätzlich einmal Midseason; B = Cap auch für jeden wirtschaftlich relevanten vollständigen Trade-/Waiver-/FA-/Drop-/Draft-Bundle verbindlich. Zusätzliche Prüfungen **ändern** weder individuelle Salaries noch das Startdatum des Salary-Zyklus.
- **Verschiedene historische und Zukunfts-Preiswelten getrennt:** CP5a/b 2026 reales historisches **Top20-×0,9-Modell**; CP6m neue **Full-Salary-×1,0-Kandidatwelt**, 20 gehaltene Spieler als **nur im Forschungsstart erzwungenes Minimum** und höchstens 40 reguläre Slots. Das tatsächliche `League.json` ist nicht stillschweigend auf 40 umgestellt: aktuell 30 normale Plätze (13 Start + 17 Bank), sechs Teams, vier Playoffplätze, Reserve 5, Taxi 2, `trade_deadline=99`.

## 2. Belegte Historie CP5a/b und Follow-up CP5c: Nicht nur Preisänderungen

Quellen: [CP5a](2026-11-14-salary-cap-cp5a-system-windows.md), [CP5b](2026-11-14-salary-cap-cp5b-legal-start-settlement.md), [CP5c](2026-11-14-salary-cap-cp5c-windows-deadcap-carryover.md). Historische Snapshots 2026 jeweils mit zeitgleichen League-/Player-Dateien und Original-Top20-Cap, keine Neuverwendung des Oktober-Criticality- oder Full-Cap-Preises.

| Datum | Über Cap / sechs Teams | Summe positiver Überhänge |
|---|---:|---:|
| 29.06.2026 | 0/6 | 0 $ |
| 09.09.2026 | 4/6 | 122.567.015 $ |
| 05.11.2026 | 5/6 | 217.960.296 $ |
| 05.11.-Kader mit **eingefrorenen 09.09.-Preisen** | 5/6 | 176.958.042 $ |

- Nach dem legalen 25.08.-Start und dem 09.09.-FA-Draft sind bei **vollständig unverändertem Salary-Vektor** 4/6 Teams über Cap. Das dokumentiert eine **tatsächliche unterjährige Ballung**, keine nachträgliche Regelverletzung.
- September–November: **54/54** historische Event-Bundles reproduziert (43 Waiver, 8 FA, 3 Trades); **10** erhöhen die relevante Top20-Belastung eines danach über Cap liegenden Teams (7 Waiver, 3 Trades). Dies sind Zusatzlast-Signale, *keine* Aussage, dass genau zehn unter B ungültig wären.
- Für einen **hypothetischen legalisierten** September-Start reichen unter CP5b-Top20-Preisen rechnerisch mindestens **sieben Nichtstarter-Cuts**, um die vier Überhänge zu schließen; unter zusätzlichem Schutz der zehn teuersten Kernspieler müssten es **21** sein. Keine Retained C-add-Cut-Kosten, keine Einwilligung der Manager. Solche „Bench Cuts“ können wertvolle QB-/RB-/WR-Optionen vernichten.
- Danach von denselben **54 historischen Anfragen** mechanisch: **F2** lässt 50 fortsetzen, vier werden wegen geänderter Ownership inkompatibel; im November verbleiben drei über-Cap-Teams. **B strikt** setzt 43 fort, hat acht inkompatible und **drei unmittelbar wegen Cap** abgelehnte Events (zwei Waiver, ein Trade). **B mit erlaubten hypothetischen Gegen-Cuts** setzt 50 fort; vier Bundles brauchen einen zusätzlichen Cut, darunter Spieler mit hohem sportlichem/Asset-Wert. Kontrafaktische Anschlusswege sind **keine** echte beobachtete Liga unter B.
- **F3** mit einem weiteren 05.11.-Check würde nach diesem einen historischen F2-Pfad rechnerisch drei zusätzliche Nichtstarter-Cuts erzwingen. CP5c zeigt bei abweichenden Checkterminen andere Pfade und keine bewiesenen Titel-/Managerentscheidungen.

**Interpretation:** Das rein jährliche Cap begrenzt nicht den In-Season-Zuwachs einer Mannschaft. Zusätzliche Kontrollpunkte oder B erzeugen echte Cap-Opportunitätskosten. Ob dadurch bessere Verteilung, mehr sinnvolle Trades oder lediglich stärkerer Cut-/Waiver-Frust entsteht, ist hier **nicht** gemessen.

## 3. Neu durchgerechnete CP6m-Full-Salary-Tradefrontier

**Reproduzierbarer Script:** [`cp6m_cap_window_swap_frontier.mjs`](../simulation/cp6m_cap_window_swap_frontier.mjs); **vollständige [Audit-Metriken](2026-11-20-cp6m-cap-window-swap-metrics.json)**.

- Eingabe: derselbe archivierte **05.10.2026**-CSV-Salary-/3Y-Leistungspool (1.268 Datensätze, Quelle-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`) wie CP6k; eingefrorene Initial-Roster-/Salary-Funktionen aus CP6k-Script-Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`.
- Drei Seeds (11/29/47) erzeugen jeweils sechs **disjunkte, full-salary-legale** synthetische 20er-Kader; **keine tatsächlichen 2026er Team-Besitzrechte**. Jedes Team erfüllt 13 Starter-/Positionsminima. Initialer Cap jeweils **489.862.209 $**; Team 0 liegt bei 208,508/208,667/208,190 3Y-Index und hat nur **11,292/9,354/10,343 Mio. $** freien Cap.
- Für jede der fünf anderen Teams: alle **1:1**-Spielertausche und **2:2**-Bundles mit Team 0, solange beide erhaltenen Kader Positionsminima und mindestens 20 Plätze erfüllen. Für denselben hypothetischen Bundle zeigen wir den Starterindexgewinn von Team 0 und die Abnahme bei Team S sowie volle neue Kosten **für beide**.
- A **erlaubt** einen unterjährigen Cap-Überhang, B setzt **CapLegal nach dem gesamten Bundle auf beiden Seiten** voraus. Eine *Folgejahr*-Deadline-Sanierung von A wird **noch nicht** gerechnet. Keine echten Picks, Gegenleistungsgerechtigkeit, Trade-Annahmen, späteren Salary-Neubewertungen, Dead-Cap-Bundles oder Injury/Bye-Effekte. Es werden insbesondere nicht acht direkt legale Starverkäufe *behauptet*: jeder Kandidat setzt einen freiwilligen Verkäufer voraus.

### 3.1 Alle drei Seeds: 1:1 und 2:2

| Kandidatenklasse | A: Positives Starterindex-Delta für Team 0, unterjährig Cap-Überhang zulässig | B: Derselbe Tausch mit sofort beidseitig legalem Cap |
|---|---:|---:|
| 1:1 – positiver Gewinn (>0,1 Punkte) | **322** | **46** |
| 1:1 – Gewinn ≥2 Punkte | **179** | **0** |
| 2:2 – positiver Gewinn (>0,1 Punkte) | **17.296** | **1.167** |
| 2:2 – Gewinn ≥2 Punkte | **10.038** | **1** |

Diese Zahlen sind **Kandidatenzahlen**, nicht unabhängige Trades: derselbe Elite-Spieler kann in vielen Varianten auftauchen, drei Seeds teilen denselben Datensatz, und 1:1- bzw. 2:2-Kombinationen schließen sich wirtschaftlich teilweise aus. Kein neuer 2027er Spielernachwuchs in diesem Einjahres-Fenster.

**Beispiel Seed 11, Team 0:**

- Star-upgrade im einseitigen 1:1-Envelope **+8,157 Starterindex**, aber sein Tausch erhöht Team-0-Salary um **76,319 Mio. $**, neues Team-0-Budget **554,889 Mio. $**; A erlaubt dies zunächst (bis zum Folgejahres-Check), B liegt **65,027 Mio. $ über Cap**. Der Verkäufer verliert **8,157 Starterindex**, also ohne Extra-Assets kein Grund zuzustimmen.
- B-legaler 1:1-Tausch erreicht in derselben beschränkten Suchklasse höchstens **+1,334 Starterindex**, ebenfalls **−1,334** für den Verkäufer, bei fast aufgebrauchtem eigenen Cap.
- Erlaubt man **2:2-Bundles**, steigt der höchste B-legale Einjahresgewinn auf **+2,138 Punkte** und benötigt das Aufgeben zweier eigener Spieler. Ein hypothetischer 2:2-Überhang könnte dagegen **+13,788** Punkte für Team 0 ergeben und **107,836 Mio. $ Cap-Überhang** erzeugen; Verkäufer verliert gleich viele Punkte. Dass der über-Cap-Käufer die spätere Juni-Sanierung stemmen könnte, ist **nicht** geprüft.
- **0** der Teams-0-positiven 1:1- und 2:2-Kandidaten steigern zugleich den unmittelbaren Starterindex des Verkäufers. Das ist bei diesem sportlich stark sortierten Ausgangspool ein Zeichen für die **fehlende Asset-/Pick-Bewertung**, nicht für das Unvermögen zu traden. Rebuild-Verkäufer können einseitige Punkteabgaben gegen Zukunftspicks ausdrücklich wollen.

Das B-Szenario ist **eher ein Druck auf gezielte Star-/Cap-Pakete als ein nachgewiesenes Verbot von Verstärkungen**. Es ist aber nur ein maximal 2:2 begrenzter statischer Trade-Markt; mit Picks, Free-Agent-Zugängen, Mehrparteien-/Salary-Dump-Deals oder frühen Kaderänderungen können andere B-legale Möglichkeiten entstehen.

### 3.2 Warum die beiden Tests sich ergänzen, nicht aufaddieren

CP5a/b = **echte** Teams, reale 2026er Top20-Gehälter und tatsächlich archivierte Vorgänge; CP6m = **synthetische sechs Besitzstände** aus CP6k, neues 40er-Full-Cap-Kandidatsystem und ex-ante-feasible Hypothesen (ohne Käuferzusagen). **Keine** Kombination von 122,57 Mio. $ historischem Top20-Überhang und +8,157 CP6m-Full-Cap-Indexzuwachs zur quantitativen Titelformel.

## 4. Geschützte sechs Nordstern-Ziele: Welche Entscheidungen gewinnen/verlieren?

| Ziel | A jährliches Überziehen | F2/F3 zusätzliche fixe Prüfungen | B dauerhaft bindendes Cap | Stand |
|---|---|---|---|---|
| **1 Aufholbarkeit** | Cap-Vorteile können bis zur nächsten Deadline in jeder Saison erneut entstehen | Zeitweise harte Gegenkräfte; kein vollständiger Event-Schutz | Stärke/Payroll-Aufrüstung muss im selben Bundle finanziert werden; Verfolger können aber Käuferliquidität verlieren | **Titel-/Catch-up-Kausalwirkung offen** |
| **2 Gutes Management belohnen** | Temporäres All-in, Mut zum Timing, Abwarten bis Playoffs; bezahlter Folge-Cut kann wertvolle Assets kosten | Planung um Checkfenster, rechtzeitiges Verkaufen, Reserven | Jeder Upgrade muss durch Cap-effiziente Gegenmaßnahmen gedeckt sein: günstige Youth, Cut-/Trade-/Bench-Priorisierung; auch frühes Cap-Sparen wird wertvoll | **B erzeugt besonders explizite Budget-Tradeoffs, Wert solcher Entscheidungen noch ungemessen** |
| **3 Keine zementierten Gratisvorteile** | Überhang darf bis zur nächsten Deadline existieren, dann Reset; bei späteren Aufnahmen neue Überhänge möglich | Weniger unkontrollierte Intervalle | Kein neues Payroll-Übermaß nach legalem Start, aber Rookie-Surplus und gute Trades bleiben legitim | **B stärker gegen unmittelbare kostenlose Kumulierung** |
| **4 Wirtschaftliche Konsequenzen** | Marktpreis spürbar erst an jährlicher Cap Deadline; Annual-All-in erlaubt temporären Zug | Zwingende Mehrfach-Settlements | Jede Trade-/Waiver-/FA-Aktion benötigt komplette sofortige Gegenfinanzierung | **B stärker in-season** |
| **5 Strategische Freiheit** | All-in und späte Tradefenster besonders flexibel; Rebuild-Seller können Käufer finden, die über Cap gehen | Berechenbare Fenster und laufende Knappheit dazwischen | 1:1 und 2:2-Stars nur bei sofortigem Cap, dadurch potenziell schwacher Käufermarkt; Rebuild-Picks und Salary-Surplus müssen real handelbar bleiben | **A besser für kurzfristige All-in-Freiheit, B kann Gegenparteiliquidität mindern** |
| **6 Operative Durchsetzung** | Etablierter jährlicher Check | Zwei/drei klar definierte Prüfungen mit Soft/Hard-Zeitpunkten | Jedes vollständige wirtschaftliche Paket auf beiden Seiten in Sleeper/app auditieren und bei Konflikt sperren oder nachverhandeln | **B derzeit nicht als zuverlässig automatisch vollziehbar belegt** |

**Stand 20.11.2026 externe Bestätigung:** Die [offiziellen Sleeper Public API Docs](https://docs.sleeper.com/) charakterisieren diese Schnittstelle als **read-only**. Sleeper beschreibt [Waiver-/FA-Locks](https://support.sleeper.com/en/articles/4037431-why-can-t-i-drop-players), [Commissioner-Trade-Review](https://support.sleeper.com/en/articles/4033467-how-do-i-force-a-trade-through) und [Trade-Pick-Assets](https://support.sleeper.com/en/articles/3188802-how-to-trade), aber hier wurde **keine** native atomare, regelabhängige 6-Team-Salary-Cap-Vorabprüfung nachgewiesen. Dies beweist nicht, dass ein privater nicht öffentlich dokumentierter Prozess unmöglich ist. Reale Operator-Minuten und Fehler-/Appeal-Quote weiterhin offen.

## 5. Obligatorische fünf Finanzierungsachsen

Alle Angaben unten für jeweils **denselben** CP6m-2026-10-05-Preis-/Cap-/Kaderzustand, getrennt von CP5a/b:

1. **Seller Relief:** Beim 1:1/2:2 werden beim Verkäufer die vollständigen **ausgehenden gehaltenen Salaries** vom Bestand abgezogen und die vollständigen **eingehenden** addiert. Beispiele im JSON `sellerAfterCost_m`. **Kein Cut**, daher keine individuellen Retained-Cadd-Kosten ausgelöst; kein Einverständnis/Preis des Sellers.
2. **Buyer Burden:** Team 0 übernimmt die **vollen** Salaries der eintreffenden Spieler abzüglich der abgegebenen. 1:1-Seed11-Maximalgewinn `+76,319 Mio.` und 2:2 `+119,127 Mio.` Mehrbelastung; bei B End-Cap beider Teams prüfen. Zusätzliche Pick-/Salary-Komponenten, 3+-Spieler-/Multi-Trade-Bundles **nicht beobachtet**.
3. **Roster-/Position-Slots:** Beide Partner bleiben im Versuchssetup bei exakt 20 besetzten Slots, 13 gültigen Startern, korrekten Positionsminima. **Keine** neue Taxi-/IR-/Reserve-Belegung, keine simultanen Free-Agent-/Drop-Folgen; echte Liga hat andere Slots als dieses synthetische CP6k-Research-Minimum.
4. **Gesamtliga-Schuld:** **Kein Kredit/Debt-Vintage** in CP6m. Bei A können im isolierten Bundle temporäre Payroll-Überhänge entstehen, sie sind **keine** für Folgejahre gebuchten Geldschulden; bei B bleibt Team-0-/Seller-Usage sofort im Cap. Keine weiteren Buyerseiten oder Transaktionsketten, deshalb **keine** vollständige dynamische Liga-Schuld-/Marktoptimierung.
5. **Nächste Deadline:** A **muss** im nächsten jährlichen Cap-Check legalisiert werden, CP6m führt diese konkrete Sanierung **noch nicht durch**. B erfordert **jetzt** beide Teams legal, daher keine neue über-Cap-Last desselben Bundles, aber der künftige Jahresreprice kann auch bei B neue Bereinigung auslösen. **H2/H3-Tilgung nicht anwendbar**, da es keine mehrjährige Schuld gibt. Keine neue Schuld zur Rückzahlung notwendig oder vorgesehen.

## 6. Entscheidungsrelevante Zwischenbewertung

**Mehr interessante ökonomische Entscheidungen?** Dafür spricht **B**, sofern wir darunter *explizite Kosten-/Opportunity-Entscheidungen bei jedem Upgrade* verstehen. Das ist quantitativ durch die unmittelbare starke Begrenzung einfacher Star-Upgrades unterstützt.

**Mehr tatsächlich ausführbare gute Managemententscheidungen?** **Noch offen.** B kann dieselben star- und pickbasierten Trades schon an fehlenden Käufermitteln hindern, die für Rebuild dringend wichtig sind. Das gilt besonders in einer Sechs-Team-Liga mit 4/6 Playoff-Teams, hoher Replacement-Qualität und ohne normale Trade-Deadline. Auch A hat echte Folgeopfer, **wenn** die nächste jährliche Cap-Deadline sauber durchgesetzt wird. Diese Kosten dürfen nicht ignoriert oder als mehrjähriger Kredit missverstanden werden.

**Operative Empfehlung als Forschungspriorisierung:** Keinen falschen Sieger zwischen A, F2/F3 und B ernennen. Im nächsten **CP6n** denselben legalen sechsfachen Ausgangsmarkt mit atomaren tatsächlichen Spieler-/Pick-/Cut-/Free-Agent-Paketen, gegenseitiger Akzeptanzheuristik und vollem C-add-/jährlichem Salary-Reset-Settlement konfrontieren. Drei gepaarte Führungsstrategien `all-in / reload / rebuild` und drei Enforcement-Welten `A / F2 oder F3 / B`; wenn B unter korrekter full-salary/Price-World keine Verbesserung von nachhaltiger Aufholbarkeit/regelkonformer Titelchance gegenüber F2 zeigt, aber erheblich mehr Operatorkosten/Trade-Friktionen bewirkt, ist der Mehraufwand **nicht** gerechtfertigt. Umgekehrt B weiter priorisieren, falls es A/F2-Gratisvorteile deutlich eindämmt, ohne freiwilligen Markt zu ersticken.

**Bedingungen für vergleichbare Simulation:** Gleicher Cap-/Salary-Vektor und vollständige Team-Starts; alle sechs Manager reagieren auf geänderte Besitzer; Unterscheidung von A-über-Cap-„darf heute spielen“ und „nächstes Jahr cap-legal“; Cut-Retention bis regulärem Check; definierter Check-vor-Reset; wirtschaftlich valide Bundles beider Partner; dokumentierte Folgen für Hard-Failure ohne Auto-Cuts, gleiche Rookie-/Draftorder-/Legacy-Anreize. Kein Coach erhält Ex-post-Zukunftswissen. **H5 bleibt eine Nebenmetrik**, da All-in und Rebuild bewusst sehr unterschiedliche Titel-/Entwicklungskurven wählen.

**Fazit:** **Das dauerhafte Cap stärkt vermutlich Ziel 3/4 und die Budget-Entscheidungsqualität aus Ziel 2, bringt aber erhebliche Ziel-5-/6-Risiken; weder die gesamte Liga-Dominanz noch langfristige Titelchancen wurden hier kausal bewiesen.** Der bereits bestehende F2-Mittelweg ist deshalb nicht überholt, sondern ein sinnvoller eigenständiger Forschungsgegner.

Aktive Produktionsregeln, Sleeper-Settings, Salary-Daten und geschützter Nordstern unverändert; PR bleibt Draft, Issue #1344 offen.
