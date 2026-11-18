# CP5c – Zusatzprüftermine und mehrjähriger Dead Cap als **getrennte** Wirkungshebel

> **Forschungsdatum:** 14.11.2026 · **Owner:** [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status:** ausdrücklich hypothetische Designsensitivität; **keine** Regel- oder Vertragsentscheidung.  
> **Normativ:** [Sechs geschützte Nordstern-Ziele](../../../league-context/league-philosophy.md), ligaweite Ratifizierung noch nicht abgeschlossen.  
> **Quellen:** [CP5a](2026-11-14-salary-cap-cp5a-system-windows.md), [CP5b](2026-11-14-salary-cap-cp5b-legal-start-settlement.md), [CP4](2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md), kanonisches [Salary-/Dead-Cap-Konzept](../salary-dead-cap-concept.md), [maschinenlesbare CP5c-Metriken](2026-11-14-salary-cap-cp5c-metrics.json).

## 1. Ausgangslage und Statusdisziplin

CP5b bestätigte eine hypothetische, **unter dem September-2026-Preisstand legale Startaufstellung** durch sieben Starter-erhaltende Cuts. Das ist keine Managerabsicht, und die abgeschnittenen QB-/WR-/RB-Assets sind nicht „wertlose Bank“. Das vollständige historische **A-Replay 54/54** ist verifiziert. Sobald gegenfaktische Cuts stattfinden, sind die nachfolgenden historischen Eventpakete nur noch **Anfragen**; bei fehlendem Ausgangsspieler wird das Paket als nicht fortsetzbar, nicht als bewiesener Trade-Veto, markiert.

**Aktives Ligarecht:** 2026er Istsystem mit jährlichem Cap-Check; weder F2/F3/B noch neue Dead-Cap-Verträge sind beschlossen. **Bereits geklärter *nicht aktiver* Konzeptstand:** Cut-Dead-Cap-Sätze 50/30/15/5 % bei Team-Tenure 0/1/2/3+, vollständige Active-Salary-Reduktion durch Retained Salary im aktuellen Salary-Zyklus, Reset beim nächsten regulären Salary Check, **kein mehrjähriger Carry**, ohne separate Cut-Strafe. Der neue Nutzerimpuls **prüft eine Alternative hierzu, er ändert oder widerruft die geklärte Konzeptentscheidung nicht.**

## 2. CP5-Rest: Wie viel zusätzliche Zeitwirkung hat F3 gegenüber F2?

### Datengrundlage

September-`Players[].Salary` und Cap **434.255.984 $** eingefroren; 09.09.2026 20:33:55 UTC bis 05.11.2026 23:59:59 UTC. Alle **54** im CP5a/CP5b-Beleg referenzierten und abgeschlossenen Vorgänge nach `EffectiveAt`, darunter **43 Waiver / 8 Free Agents / 3 Trades**. Ausgang sind sechs hypothetisch legale 09.09.-Kader. Alle Drops vor Adds; komplette Trades atomar. Historisch inkompatible Pakete werden übersprungen.

**Neue rein mechanische Messgröße:** `Positive Cap-overhang Mio. $ × Tage`. Zwischen zwei Events wird der zuletzt berechnete positive `max(0, Usage − Cap)`-Überhang pro Team mit der Zeitspanne multipliziert und über alle Teams integriert. Dieser Betrag ist **keine echte Cap-Zahlung, keine Titelchance und kein Wohlfahrts-/Fairness-Score**. Die frei gewählten Checkdaten dienen einer Zeitpunktsensitivität; sie sind keine empfohlenen festen 2027er Fristen.

| Pfad vom legalisierten September-Start | Über-Cap-Team-Tage | Mio.-$-Tage an positivem Überhang | Weiterhin über Cap am 05.11. (vor zusätzlichem Jahres-Reset) |
|---|---:|---:|---:|
| **F2**, keine weitere Kontrolle bis zum Beobachtungsende | **66,681** | **661,19** | **3 Teams**, 46,51 Mio. $ |
| **F3: zusätzlicher Check 01.10.** | **31,681** | **352,94** | **2 Teams**, 38,35 Mio. $ |
| **F3: zusätzlicher Check 15.10.** | **43,832** | **461,19** | **2 Teams**, 38,35 Mio. $ |
| **F3: Check erst 05.11. nach den beobachteten Events** | **66,681** | **661,19** | **0 unmittelbar nach dem Check**, keine vorherige Zeitentlastung |
| **B strikt** | **0 nach akzeptierten Paketen per Definition** | **0** | **0**, jedoch abgewiesene/inkompatible Anfragen |

Bei F2 sind **50/54** historische Anfragen fortsetzbar und **vier** wegen geänderter Vorbesitzer nicht fortsetzbar. Der 01.10.-Check löst nur Team 2 mit **8,17 Mio. $** Überhang; der 15.10.-Check betrifft Team 2 und Team 3 mit zusammen **22,70 Mio. $**. Als mechanische Existenzpakete würden die Cuts von **Travis Kelce** (01.10.; auch 15.10.) bzw. zusätzlich **Tyreek Hill** (15.10.) genügen. **Das sind weder Empfehlungen noch plausible Zusagen der Manager.**

**Wichtiger Schutzfilter:** Für Oktober existiert in diesem Versuch kein eigener archivierter, zeitgenauer Starter-Commit. Deshalb bleiben allein die **September-Starter-IDs geschützt**; ein im Oktober tatsächlich startender oder strategisch relevanter Spieler kann in der Cut-Liste auftauchen. Genau dies passiert bei den teuren genannten Spielern. Bei einem 05.11.-Check würde ein Schutz nur der *September*-Starter beispielsweise Mahomes/CMC als hypothetische Cuts ausgeben. CP5b schützte alternativ die am **05.11. tatsächlich eingetragenen Starter** und erhielt als **andere** drei Cut-Beispiele Davante Adams, De’Von Achane und Lamar Jackson. Dieser Unterschied ist **methodische Sensitivität, kein Widerspruch oder Beleg echten Managerverhaltens.**

Der 15.10.-F3-Pfad verändert eine zusätzliche spätere Transaktionsvorbedingung: **49** fortsetzbare und **5** inkompatible Pakete (vs. F2 **50/4**). Dadurch ist die Mio.-$-Tage-Differenz **nicht** als isoliert kausaler Nutzen des Kontrolltermins interpretierbar.

**Vollzugsschwelle:** F2/F3 würden primär zwei/drei vorher angekündigte Prüfereignisse mit jeweils sechs Teams erfordern; B müsste theoretisch alle wirtschaftlich relevanten vollständigen Events (in diesem Fenster 54 Kandidaten) auf Cap-Basis gegen ihren gesamten Postzustand prüfen. Die Zahl ist **weder** eine reale Zahl manueller Commissioner-Aktionen **noch** ein Minutenvergleich. Die dokumentierte Sleeper-API ist read-only; ein automatisches Pre-Commit-Waiver-Cap-Gate wurde nicht nachgewiesen. Ohne den zusätzlichen gesicherten Wettbewerbseffekt und gemessene Betriebszeit ist B nicht zum Sieger zu erklären.

## 3. Der neue Nutzerimpuls: Laufzeit von Dead Cap != Höhe von Dead Cap

**Problemformulierung:** Langjährig gehaltene Spieler sollen leichter entlassen werden dürfen als kurzfristig teuer eingekaufte Assets. Der bisherige Entwurf reduziert die Cut-Prozente mit wachsender ununterbrochener Team-Tenure, die Verpflichtung endet aber stets am nächsten Salary Check. Denkbare Erweiterung: Mit frischem Erwerb bleiben Verpflichtungen auch nach diesem Check bestehen.

**Präzision:** Die Team-Tenure 0/1/2/3+ ist **nicht** die Restvertragslaufzeit. Das einzige bereits im Konzept quantifizierte echte mehrjährige Salary-Schema ist der **dreijährige Rookie Contract** mit Year1-/Year2-/Year3-Dollarfaktoren **100/125/150 %**; ab Year4 werden Veteranen **jährlich neu nach Leistung** bewertet, ohne bisherige individuelle Veteranen-Vertragsenddaten. Ein „Dead Cap bis Vertragsende“ benötigt folglich entweder einen neu eingeführten Veteranen-Contract-Term oder eine ausdrücklich nicht als Vertragsablauf ausgegebene **Tenure-basierte Laufzeit-Proxyregel**.

### 3.1 Vier streng getrennte Varianten

| Code | Fälligkeit / Laufzeit (Tenure 0/1/2/3+) | Was sie wirtschaftlich bedeutet | Kompatibilität mit bestätigtem Konzept |
|---|---|---|---|
| **D0 – bereits geklärter Ein-Zyklus-Entwurf** | **1/1/1/1** Salary-Zyklen | Cut-Anteil nur bis regulärem Reset; im laufenden Zyklus Retained Salary und entsprechend günstigeres aktives Salary | **Ja** (nur Konzept, nicht aktive Regel) |
| **D1 – moderat, pro Zyklus neuer feststehender Betrag** | **3/2/1/1** Zyklen | Zum Cut fixierter nominaler Anteil wird in jedem dieser Zyklen erneut fällig; neue Garantie-/Buyout-Schuld | **Nein**; zusätzliche zukünftige Kosten |
| **D2 – längere Garantie, pro Zyklus neuer feststehender Betrag** | **4/3/2/1** Zyklen | Wie D1, länger; Neuzugang vier Zyklen, langfristiges Team nur laufender Zyklus | **Nein**; stärkere zukünftige Schuld |
| **D3 – **derselbe** Gesamtbetrag nur zeitlich verteilt** | **4/3/2/1** Zyklen, aber Gesamtpool = einmaliger Cut-Anteil | Keine zusätzliche Gesamtverpflichtung, schwächere sofortige Belastung und andere Käufer-Salary-Absenkung | **Nein**; ursprüngliche Retained-Salary-Zuordnung und die Jahresprüfung müssten neu definiert werden |

Bei D1/D2 bedeuten die festen Beträge **kein** jährliches Tracking des nach dem Cut neu errechneten Markt-Salarys. Sie sind zum Cut in Dollar eingefrorene **Garantie-/Buyout-Verpflichtungen**. Sie sollten, falls jemals beschlossen, auch genau so benannt werden – nicht als vermeintlich unveränderte vollständige Retained-Salary-Invariante.

D3 ist **nicht** einfach „D2, aber harmloser“: Würde man den 2026er Cut-Anteil über zukünftige Jahre strecken, stünde im ursprünglichen Cut-Zyklus entsprechend **weniger** als bisher für die Preissenkung des aktiven Salaries und für die bisherigen CP4-Top20-/Additiv-Semantiken zur Verfügung. Ein direkter Vergleich durch bloßes Addieren zum alten Team-Usage wäre falsch.

### 3.2 Acht belegte Cuts als mechanische Dollar-Gegenprobe

Historischer Ausgang: **Flo / Just Bill**, acht tatsächliche Cuts am 09.06.2026, bei zeitgenössischen Juni-Salaries. Aus CP4 als nicht aktive Retained-Salary-Regel hypothetisch rekonstruierte **37.551.933 $** nominal Dead Cap: sechs Spieler mit Tenure **2** (15 %), zwei mit Tenure **1** (30 %). Reproduzierter Cap **434.255.984 $**, nach den Cuts aktive Top20-Belegung **427.729.579 $**.

| Variante | Z0: laufender Salary-Zyklus (Cut) | Z1: folgender Zyklus | Z2: weiterer Zyklus | **Kumulierte Nominalsumme** |
|---|---:|---:|---:|---:|
| D0 – Ein-Zyklus | 37,55 Mio. $ | 0 | 0 | **37,55 Mio. $** |
| D1 – kurze Staffel 3/2/1/1 | 37,55 Mio. $ | 19,70 Mio. $ | 0 | **57,25 Mio. $** |
| D2 – lange Staffel 4/3/2/1 | 37,55 Mio. $ | 37,55 Mio. $ | 19,70 Mio. $ | **94,80 Mio. $** |
| D3 – fixer **Gesamtpool** über 4/3/2/1 | 15,49 Mio. $ | 15,49 Mio. $ | 6,57 Mio. $ | **37,55 Mio. $** |

Die **19,70 Mio. $** in den letzten Varianten stammen ausschließlich aus den damals kurzfristiger erworbenen Spielern **Brock Purdy** (12.453.371 $ Dead Cap) und **Sam Darnold** (7.246.800 $); die sechs Tenure-2-Spieler erzeugen 17.851.762 $ und laufen bei der moderaten Staffel nach Z0 aus.

**D0/CP4 direkte Liquiditätsprobe:** Additive Dead-Cap-Abrechnung beim **29.06.2026** ergäbe **465.281.512 $** (31.025.528 $ über Cap); virtuelle Dead-Cap-Top20-Slots **439.197.718 $** (4.941.734 $ über Cap). Beide Top-N-Semantiken sind weiterhin **unbeschlossen**. Ein Reset **vor** dem einzigen verpflichtenden Check könnte dieselben alten Beträge effektiv nullstellen. D1/D2 bewahren stattdessen nominale zukünftige Belastung – aber die zukünftigen Team-Roster, Cap-Basis und Preise sind **nicht bekannt**. `37,55 Mio. $` entsprechen **8,647 % des historischen 2026er Caps**; dieser Quotient ist **kein** gemessener 2027er Anteil.

### 3.3 Entscheidende Zeitachsen-Falle: Salary-Zyklen sind keine Vertragsjahre

Für diese konkreten Flo-Cuts liegen zwischen **09.06.2026** und der tatsächlichen damaligen Deadline am **30.06.2026, 23:59:59 UTC** nur rund drei Wochen. **Z0** ist daher lediglich der damals noch laufende Rest-Zyklus, **Z1** beginnt nach dem nächsten regulären Reset, **Z2** nach dem darauf folgenden. Eine nominelle „3-Zyklen-Garantie“ ist nicht automatisch eine Garantie über drei volle Jahre; eine Cut-Transaktion direkt vor einem Check wäre sonst wirtschaftlich anders behandelt als unmittelbar danach.

Vor einer echten Regelentscheidung muss daher definiert sein, ob Laufzeit nach **vollen League Seasons**, nach **Salary-Zyklen** oder in **verbleibenden tatsächlichen Vertragsjahren** zählt, wie Restjahre proratiert werden und ob ein Post-FA-/Midseason-Cap-Check **nur kontrolliert** oder auch einen Vertragszyklus beendet (empfohlen in CP5b/CP5c **nur Kontrolle**, ausdrücklich kein neuer Reset).

## 4. Warum jährliche Performance-Neupreisung die Schlüsselfrage ist

Im bestehenden Entwurf gilt **innerhalb** eines Zyklus, solange kein Minimum greift:

`aktives Spieler-Salary + Summe aller alten Dead-Cap-Anteile = Salary beim Salary Check`.

Wird ein Veteran im Folgejahr von zum Beispiel 30 Mio. $ auf 12 Mio. $ neu bewertet, sind drei mechanisch unterschiedliche Ansätze denkbar:

1. **Fixe zukünftige Schuld D1/D2:** Die Verpflichtung des Cut-Teams ist beim Cut in Dollar fixiert. Das neue Team zahlt im neuen Salary-Zyklus grundsätzlich das **voll neu berechnete** Performance Salary; die alte Schuld ist **zusätzliche** Team-Budget-Belastung und erweitert die ligaweite Summe über den unveränderten Player-Salary-Markt hinaus. Das ist eine **neue Garantie-/Cut-Strafe**, keine unbemerkte Fortsetzung der alten Zero-Sum-Invariante.
2. **Anpassung der Schuld an das neue Markt-Salary:** Alte Teams behalten beispielsweise einen Prozentsatz der neuen 12 Mio. $. Der Betrag ist dann **nicht garantiert** und kann trotz bereits abgegebenem Spieler stark sinken oder steigen. Bei mehrfachen Cuts, Salary-Floor, Free Agency und New Owner Tenure entsteht ein mehrjähriges verzweigtes Verrechnungssystem. Ohne definierte Deckelung könnte allein die Summe der Ansprüche das neue Salary übersteigen.
3. **Echter länger bindender Spieler-Contract:** Feststehende oder zu Vertragsbeginn determinierte Zahlungen, garantierte Anteile, Restjahre und Übernahmeregeln bei Trades/Cuts. Für Rookies ist ein dreijähriges **Year1–Year3-Salary-Schema** bekannt; bei Veteranen wäre dies eine **neue Vertragsarchitektur**, die jährliche Performance-Preise teils ersetzt oder überlagert.

**NFL-Abgrenzung:** Laut [NFL Football Operations – Contract Language](https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language) ist Dead Money nicht schlicht der restliche nominelle Base-Salary-Gesamtvertrag, sondern beinhaltet insbesondere bereits gezahlte oder garantierte, noch nicht gegen den Cap verbuchte Vergütung. Eine klassische Restrukturierung wandelt aktuelles Gehalt in auf Vertragsjahre verteilten Bonus um, schafft sofortigen Raum und verschiebt Cap-Kosten in die Zukunft. Für unsere sechs Teams wäre „Restrukturierung“ daher **eine weitere eigenständige Spieler-/Team-Finanzierungsmechanik**, nicht notwendige Eigenschaft von Dead Cap. **Nicht** in diesen Test hineinmischen.

## 5. Zweite Ordnung: Welchen Anreiz würde die Änderung tatsächlich erzeugen?

- **Mehrjähriger Schuldendienst kann echte Win-now-gegen-Zukunft-Entscheidungen erzeugen**, weil ein kurzfristig erworbener Elite-Spieler bei einem schnellen Cut mehrere künftige Budgets belastet. Zugleich lässt ein solches System gut geführte Manager ihre langfristig gehaltenen Assets für nur noch 5 % lösen, was bewusstes Belohnen von Retention ist.
- **Veräußerbarkeit vs. Free-Agent-Weg:** Im bisherigen Modell sinkt beim Cut das aktive Salary des Spielers und macht ihn im gleichen Zyklus für andere kaufbar; die alte Team-Schuld endet am Reset. Bleibt die Schuld über Jahre beim früheren Team, während der neue Besitzer wieder voll nach Performance bezahlt, erhalten wir einen **anderen** Käufer-/Verkäufermarkt. Bei fortgesetzter Salary-Reduktion über mehrere Jahre entstehen hingegen weitere mögliche Discount-/Washing-Arbitragen.
- **Schlechte Teams/Verletzungen:** Ein teurer Neuzugang, der kurz nach Verpflichtung ausfällt, könnte bei D2 mehrere Saisons Cap blockieren – gerade auch für Rebuilds. Ein extremer Lern-/Verhandlungsfehler kann mehrere Saisons strafen, ohne die Ausgeglichenheit messbar zu erhöhen.
- **Rookie-Verträge und 2024-Gründung:** Keine automatische Gleichsetzung von Team-Tenure und NFL-Rookie-Contract-Jahr. Trades, Cuts, Re-Acquisition und mehrfaches Retaining erzeugen unterschiedliche Verpflichtungs-Verläufe. Ein nicht geklärter Veteranenvertrag darf nicht rückwärts aus einer 2026er Salary-Projektion erfunden werden.
- **Cap-Endogenität / Liquidität:** Das Cap entsteht aus den Top120-Spielersalaries, nicht aus separat auf Mannschaften gebuchten alten Garantieschulden. Mehrjähriger Debt kann deshalb zusätzliche Gesamtdruck-Summe und weniger finanzierbare Käufer erzeugen, ohne das Cap zu erhöhen. CP3 hatte unter der damals legalen Juni-Welt bereits nur **4/8** Flo-Cut-Kandidaten gemeinsam ohne zusätzliche Käufer-Cuts finanzierbar gefunden.
- **Zeit-/Vollzugsaufwand:** Mehrjährige individuelle Post-Cut-Verpflichtungen benötigen pro Cut eine einzigartige unveränderliche Obligation-ID, Verursacher-Team, Spieler-ID, Frozen-Dollar-Betrag, Saison/Startzyklus, Restperioden, Zahlungsplan, Status sowie Behandlung von wiederholtem Cut, Retention, Re-Acquisition, Owner-Transfer, Reserve/Taxi und Cap-Refresh. Das ist zusätzlich zu F2/F3/B und ohne Betreiber-Minutenmessung.

## 6. Bewertung entlang der sechs geschützten Ligaziele

| Ziel | D0/1 Zyklus | D1/2/3-Zyklen | D2/4/3/2/1 | D3/verteilter Pool |
|---|---|---|---|---|
| 1 Aufholbarkeit | Zukunft nach Reset frei, gut für Reload | Kann wiederkehrende Erwerber budgetieren, kann schwache Teams selbst verfestigen | Größtes Blockade-/Rebuild-Risiko | Sanfte Zukunftslast, geringerer Sofortdruck |
| 2 Management belohnen | Geduld über niedrigere Prozente belohnt | Verstärkt Konsequenz guter Planung und teurer Fehlkäufe | Hoher Bestrafungsgrad auch bei Verletzung/Glück | Weniger Strafe, aber zeitverschobenes Budgetieren |
| 3 Gratisvorteile begrenzen | Nur zyklischer Druck | Höhere Persistenz von Opportunitätskosten | Höchste, noch **nicht** als nötig belegte Mehrjahres-Persistenz | Gleiches Gesamtvolumen; Wirkung stärker im Timing |
| 4 Wirtschaftliche Kosten | Im Cut-Zyklus real, Reset-Frage kritisch | Künftige Kosten zusätzlich zu aktiven Spielern | CP4-Beispiel nominal 94,80 Mio. $ statt 37,55 Mio. $ | Insgesamt nur 37,55 Mio. $, sofort geringer |
| 5 Strategievielfalt | Hohe Trade-/Reload-Freiheit | Größere Zukunftsdisziplin, aber potenziell weniger Käufer | Droht kurzfristiges Management auf Jahre zu verriegeln | Weniger hart, aber neue Arbitrage-/Timing-Varianten |
| 6 Vollzug | Einzelner Reset, einfachste Buchhaltung | Mehrjähriges Legacy-Ledger | Zusätzliche Laufzeit-/Cap-/Transfer-Fehlerflächen | Schuldpool/-Verteilung und Buyer-Salary schwerer erklärbar |

**Kein Gewinner- oder Punkt-Score:** D1/D2 sind mit D0 nicht dieselbe Finanzverpflichtung, sondern eine **neue** nominale Mehrjahresgarantie; D3 verändert statt Gesamtlast die zeitliche Zuordnung. Keiner der 54 kontrafaktischen Eventpfade weist tatsächliche 2027/2028-Ligaziele oder realistische Commissioner-Minuten nach. Die neue Konstruktion darf weder als „NFL-fähiger“ noch als „fairer“ gelten, nur weil sie länger wirkt.

## 7. Fachliche Entscheidungsschwellen und Handoff

**Belastbarer nächster Maßstab aus CP5c:** Ein verbindlicher zusätzlicher Check ist eine vergleichsweise kleine, abgrenzbare Veränderung des heutigen Vollzugs; eine Mehrjahresgarantie verändert dagegen die gesamte Kosten- und Marktstruktur. Vor einer Empfehlung zuerst **F2/F3-Operator-Pilot mit realen Prozess-/Ausnahmekosten** und klaren Starter-/Trade-/Waiver-Vorbedingungen. Dann **nur bei belegter Restlücke** eine kurze mehrjährige Cut-Schuld in einem separaten Jahrgang/Contract-Szenario prüfen. D0 bleibt zulässiges Ergebnis.

Konkrete noch offene Designfragen (keine Antworten erfunden):

1. Soll nur das **aktuell erworbene Jahr 0** zusätzliche Folgekosten erzeugen oder auch Tenure 1/2? Wie viele **volle Jahre** statt angebrochener Salary-Zyklen? Welche Wirkung bei schwerer Verletzung?
2. Soll der Betrag bei Cut **fix in Dollar** sein (neue Garantie), **proportional neu bewertet** werden (kein garantierter Betrag) oder als **einmaliger Pool** nur verschoben werden?
3. Gilt die alte Retained-Salary-Reduktion im Cut-Zyklus weiter; wie verhält sich die zukünftige Schuld zum aktiven neu bepreisten Salary? **Ein Zyklus != alle zukünftigen Zyklen.**
4. Additive oder virtuelle Top20-Abrechnung des Dead Caps; Prüfung **vor** Reset oder **danach**. Kontrafaktische Gegenprobe: 2026 Flo additiv +31,03 Mio. über Cap, virtuell +4,94 Mio.
5. Welche periodischen Settle-Termine und Endzustände kann Sleeper/Commissioner wirklich zuverlässig und mit welchem messbaren Aufwand enforce'n?
6. Wie vermeidet man unnötige Mehrjahres-Sperren bei echten Rebuilds und Verarmung des bereits dünnen Käufermarktes?

**Ergebnis:** Die Ausweitung über einen Zyklus kann als **begrenzt definierte, ausdrücklich nicht beschlossene Alternative** weiter erforscht werden. Aus den vorhandenen Daten ist **keine fachliche Freigabe** für garantierte 3–4-Jahres-Dead-Caps, Restructuring oder einen vollständigen Veteranen-Contract abzuleiten. CP5 bleibt bezüglich echter Mehrjahres-Chancengleichheit, Verhaltensreaktion und Operationskosten offen; CP6 bleibt als Liga-Abstimmungsvorlage offen. Alle sechs Nordstern-Ziele unverändert, produktive Regeln unangetastet.

## 8. QA-/Reproduktionsvertrag

- Historische Flo-Salary-/Tenure-Items: CP4 vom 09.06.2026, exakt **8**, davon **6×Tenure2 / 2×Tenure1**; `sum(deadcap)=37.551.933`.
- `L_D1(t)=max(1,3−t)`, `L_D2(t)=max(1,4−t)` für `t=0,1,2,3+`; D0 = 1. `D_i = round_half_up(active_salary_at_cut × rate(t))` aus CP4 als Frozen-Dollar-Input wiederverwenden, **nicht** neu aus späteren Salaries berechnen.
- D1/D2: derselbe `D_i` in Z0…Z(L−1), summe über Items. D3: `floor(D_i/L)` in allen Zyklen und die ganzzahligen Restdollar vollständig **im letzten Zyklus** zuweisen. Keine zukünftigen tatsächlichen Salary-/Cap-Zahlen behaupten.
- Assertion-Summen D0 **37.551.933**, D1 **57.252.104**, D2 **94.804.037**, D3 **37.551.933**; D2 Periode Z2 **19.700.171**; D3 Z0 **15.492.602**.
- Replay: Startzeit und Ende laut JSON, alle 54 historischen Events nach `EffectiveAt`; Zeitintegration über positive Team-Top20-Überhänge. Checkpoints 01.10./15.10./05.11. 23:59:59 UTC; jeweils alle Teams gegen denselben September-Preis-Freeze, nicht gegen spätere Novemberpreisdaten. Jede Variantenabweichung und die veränderten Folgeevent-Vorbedingungen dokumentieren.
- Reale Ligasaison- und Managerdaten niemals durch plausible hypothetische Vertrags- oder Salary-Jahre ersetzen.
