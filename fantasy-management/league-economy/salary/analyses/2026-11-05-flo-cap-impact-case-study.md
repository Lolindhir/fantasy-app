---
type: league_economy_case_study
subject: Flo / Just Bill (TeamID 3)
season: 2026
created: 2026-11-05
status: empirical_baseline
scope: historical_offseason_cap_cuts_and_fa_draft
design_decision: none
linked_issue: 1336
---

# Fallstudie: Flo / Just Bill – Salary-Cap-Bereinigung und Free-Agent-Draft 2026

> **Status:** datierte empirische Fallstudie und Ausgangspunkt für weitere Ligaökonomie-Diskussionen. **Keine neue Salary-, Cap- oder Dead-Cap-Regel; keine Entscheidung für Reload, Rebuild oder Hybrid.**
>
> **Perspektive:** historische Transaktionen der 2026er Offseason; Besitzer- und Ergebnisstand: 05.11.2026 nach abgeschlossener Week 8. Salary-Vergleichsrechnung anhand eines **einheitlichen, nachträglichen** Salary-Datenstands vom 05.10.2026.

## 1. Warum dieser Fall relevant ist

Flo ist der Manager von Just Bill (TeamID 3) und gewann die bisherigen Meisterschaften 2024 und 2025. In der Offseason 2026 musste er trotz eines starken Kerns besonders viel Cap-Belastung abbauen. Acht namhafte Spieler verließen ihn am 09.06.2026; sieben dieser acht wurden am 31.08.2026 von anderen Managern im Free-Agent-Draft ausgewählt.

Der Fall macht mehrere Ziele und mögliche Spannungen des Salary-Systems beobachtbar:

- **Umverteilung:** Die Cap-Deadline setzte zuvor gehaltene, für andere Teams interessante Spieler frei.
- **Replacement:** Flo konnte später mit günstigen Picks einen Teil der Produktion ersetzen.
- **Asset-Opportunitätskosten:** Entlassene Spieler brachten ihm keinen direkten Tradegegenwert, obwohl andere Manager anschließend Draftkapital für sie aufwendeten.
- **Dauerhaftigkeit:** Es ist getrennt zu diskutieren, wie stark sich der Cap-Druck über Draft, Saison und spätere Transfers fortsetzen soll.
- **League-fit:** Eine sechs-Teams-Liga mit zwei festen QB-, zwei TE- und vier FLEX-Plätzen unterscheidet sich von einer realen NFL-Vertragsökonomie.

Das ist ein **Einzelfall**. Aus seinem sportlichen Ergebnis allein folgt weder, dass der aktuelle Cap zu schwach noch dass er genau richtig sei.

## 2. Quellen und Rechenmethode

### 2.1 Historische Basis

| Quelle | Verwendung |
|---|---|
| [League-Snapshot 28.04.2026](https://github.com/Lolindhir/fantasy-app/blob/e2d3fd52f3c6fa579756f4a375650d736b071fe0/public/data/League.json) | Flo vor den April-Cuts, Taxi und Reserve |
| [League-Snapshot 07.06.2026](https://github.com/Lolindhir/fantasy-app/blob/5b4ed63172deae79759e7150f8511bd2ea3edb4e/public/data/League.json) | Kader vor der Juni-Cut-Serie und damaliges Cap |
| [League-Snapshot 09.06.2026 nach Cuts](https://github.com/Lolindhir/fantasy-app/blob/7ece134fec39741aba8e82bda554f8f13e8bead4/public/data/League.json) | Kader nach acht Juni-Cuts |
| [League-Snapshot 29.06.2026](https://github.com/Lolindhir/fantasy-app/blob/85e22feb064fdaf2257d6c3149c8d1655ada0908/public/data/League.json) | Kader kurz vor der Cap-Deadline |
| [League-Snapshot 25.08.2026](https://github.com/Lolindhir/fantasy-app/blob/539aae40da3de444000805cea3170a116fae129d/public/data/League.json) | Kader nach Rookie-Draft und vor FA-Draft |
| [League-Snapshot 09.09.2026](https://github.com/Lolindhir/fantasy-app/blob/b40956172a704ff616008d7835f527b86f128063/public/data/League.json) | Kader nach dem Free-Agent-Draft |
| [Transactions.json](https://github.com/Lolindhir/fantasy-app/blob/main/public/data/Transactions.json) | abgeschlossene Cuts, spätere Waiver und Trades, effektive Transaktionszeiten |
| [Drafts.json](https://github.com/Lolindhir/fantasy-app/blob/main/public/data/Drafts.json) | Picks der 2026er Rookie- und Free-Agent-Drafts, Besitz und Reihenfolge |
| [Salary-Simulation, Spielertabelle vom 05.10.2026](2026-10-05-salary-simulation-players.csv) | Einheitliche Werte der Spalte salary_published für rückblickenden Gehaltsvergleich |
| [PlayerWeekFantasy 2026, Weeks 01–08](https://github.com/Lolindhir/fantasy-app/tree/main/data-derived/player-week-fantasy/nfl-reise/2026) | tatsächlich ausgewiesene Fantasy-Punkte pro Woche |
| [Aktueller League-/Standings-Stand](https://github.com/Lolindhir/fantasy-app/blob/main/public/data/League.json) | Tabelle nach Week 8 sowie Besitzstand Anfang November |

Die Salary-Simulation ist **keine neue beschlossene Formel**. Verwendet wird ausschließlich die Vergleichsspalte des damaligen veröffentlichten Salary-Modells, nicht das simulierte neue Salary.

### 2.2 Vergleichsdefinition

- Für einen Kader-Snapshot werden die 20 **höchsten individuellen Salaries** seiner kontrollierten Spieler aufsummiert; das ist die hier rekonstruierte Top-20-Cap-Belegung.
- Nach jedem Cut wird die Top 20 **neu gebildet**. Nachrückende Spieler reduzieren daher die effektive Entlastung gegenüber der Summe der nominal entlassenen Salaries.
- Historischer Cap zum Juni-Stichtag: **434.255.984 $**. Die für die Rekonstruktion verwendeten individuellen Salaries stammen einheitlich vom **05.10.2026**, nicht aus am 09.06. archivierten Einzel-Salaries.
- Diese nachträgliche Rechenbasis ermöglicht Vergleichbarkeit, **beweist aber nicht den centgenauen damaligen Salary-/Cap-Verbrauch**. Falls ein historischer, unveränderlicher Valuation-Snapshot verfügbar wird, ist die Berechnung dagegen zu validieren.
- Bei den tatsächlichen Fantasy-Punkten werden nur vorhandene finale Actual-Werte addiert; **ein nicht vorhandener Wochen-Record ist kein bewiesener Nullwert**. Die Werte belegen realisierte Produktion, nicht einen optimalen oder tatsächlich gestellten Flo-Lineup-Beitrag.
- „Durch Cap verursacht“ ist bei individuellen Entscheidungen eine **Interpretation**. Transaktionslogs beweisen Cut und Zeitpunkt, nicht Flos vollständiges damaliges Motiv.

## 3. Ablauf der Cuts

### 3.1 April: zwei frühe Entlassungen

Am **29.04.2026** cuttete Flo **Juwan Johnson (TE)** und **Kareem Hunt (RB)**. Im unmittelbar vorherigen Snapshot standen 33 Spieler im Roster; zwei waren auf Taxi und zwei auf Reserve, bei 29 regulären Rosterplätzen. Die Cuts erhöhten damit die Kaderflexibilität.

In der oben definierten Salary-Rückrechnung lag **keiner der beiden Spieler in der cap-relevanten Top 20**. Der Effekt auf die rekonstruierte Top-20-Belegung betrug **0 $**. Daher sind dies **nicht als nachgewiesene erforderliche Cap-Cuts** zu klassifizieren.

### 3.2 Juni: acht Cuts wegen massivem Cap-Druck

Am **09.06.2026** gab Flo diese acht Spieler ab (Transaktionsreihenfolge):

| Reihenfolge | Spieler | Position | Individuelles Salary in der Vergleichsbasis | Rekonstruierte Top-20-Belegung danach |
|---:|---|---|---:|---:|
| Start | **Kader vor Cuts** | – | – | **542,99 Mio. $** |
| 1 | Brock Purdy | QB | 40,73 Mio. $ | 515,13 Mio. $ |
| 2 | Alvin Kamara | RB | 24,18 Mio. $ | 503,48 Mio. $ |
| 3 | Travis Etienne | RB | 22,76 Mio. $ | 492,37 Mio. $ |
| 4 | Sam Darnold | QB | 23,35 Mio. $ | 480,40 Mio. $ |
| 5 | Javonte Williams | RB | 16,65 Mio. $ | 473,29 Mio. $ |
| 6 | George Kittle | TE | 23,01 Mio. $ | 457,57 Mio. $ |
| 7 | Romeo Doubs | WR | 12,88 Mio. $ | 448,80 Mio. $ |
| 8 | Terry McLaurin | WR | 18,91 Mio. $ | **433,90 Mio. $** |

**Rechenbefund:**

- Rekonstruierte Top-20-Belegung vor den acht Cuts: **542.987.565 $**.
- Rekonstruierte Top-20-Belegung danach: **433.901.493 $**.
- Entlastung: **109.086.072 $**.
- Individuelle Salaries aller acht Cuts zusammen: **182.468.823 $**; **nicht** identisch mit der Cap-Ersparnis.
- Cap zum damaligen Stichtag: **434.255.984 $**; rechnerisch erst nach dem achten Cut um **354.491 $** unterschritten.
- Der vorherige Kader enthielt 31 Spieler inklusive zwei Taxi-Spielern, somit 29 aktive Spieler bei 30 regulären Plätzen. Es lag vor dieser Serie **kein unmittelbarer normaler Active-Roster-Überhang** vor.

**Interpretation (hoch plausibel, nicht psychologisch bewiesen):** Die extreme Ausgangslücke und der Abschluss knapp unter der Deadline-Cap-Linie sprechen dafür, dass der maßgebliche Handlungsdruck das **Salary Cap** war, nicht primär die Anzahl aktiver Plätze. Welche acht Alternativen Flo erwog, ist nicht belegt.

### 3.3 Späterer Pre-Draft-Cut

Am **25.08.2026** cuttete Flo zusätzlich **Dont’e Thornton Jr. (WR)**. Er gehört **nicht** zu den zehn April-/Juni-Cuts. Für die Analyse der eigentlichen Cap-Deadline bleibt er separat.

## 4. Wie der Free-Agent-Draft Flos Cuts umverteilte

Der vollständige **2026 Free-Agent-Draft** begann am **31.08.2026**. Von den zehn April-/Juni-Cuts wurden **acht gedraftet, zwei nicht**. Flo draftete **keinen** seiner früheren Cuts zurück.

| Von Flo gecuttet | Datum | FA-Auswahl / neuer Manager | Stand 05.11.2026 |
|---|---|---|---|
| Brock Purdy | 09.06. | **1.03 – Jan** | Jan |
| Javonte Williams | 09.06. | **1.02 – Tim** | Tim |
| Travis Etienne | 09.06. | **1.04 – Dennis** | Dennis |
| Terry McLaurin | 09.06. | **2.01 – Dennis** | Dennis |
| Juwan Johnson | 29.04. | **2.02 – Tim** | Tim |
| George Kittle | 09.06. | **2.03 – Jan** | Jan |
| Romeo Doubs | 09.06. | **2.05 – Tim** | Tim |
| Sam Darnold | 09.06. | **5.05 – Marcel** | nach Marcel-Cut vom 19.10. Free Agent |
| Alvin Kamara | 09.06. | **undrafted** | Free Agent |
| Kareem Hunt | 29.04. | **undrafted** | Free Agent |

**Konzentration der Nachfrage:** Drei der ersten vier Picks (1.02, 1.03, 1.04) waren Flo-Cuts. Auch 2.01 bis 2.03 gingen an Flo-Cuts. Insgesamt waren **sechs der ersten neun FA-Picks** ehemalige Flo-Spieler.

- **Jan** erhielt Purdy und Kittle: Verstärkung an zwei in unserer Liga fest zu besetzenden QB-/TE-Positionen.
- **Tim** erhielt Javonte Williams, Juwan Johnson und Romeo Doubs: drei Spieler und damit den größten zahlenmäßigen Anteil.
- **Dennis** erhielt Etienne und McLaurin: RB-/WR-Produktion.
- **Marcel** nahm Darnold erst 5.05 und cuttete ihn später wieder.
- **Robert** erhielt **keinen** dieser zehn Spieler direkt im FA-Draft.

**Grenze des Marktsignals:** Ein früher FA-Pick belegt Nachfrage bei dem damals verfügbaren Spielerpool; er beweist **nicht**, dass der betreffende Manager zuvor einen gleichwertigen Trade-Pick unter Übernahme des alten Salaries gezahlt hätte.

## 5. Was Flo über seine Drafts zurückbekam

### 5.1 Free-Agent-Draft: fünf andere Spieler

| Flo-Pick | Spieler | Position | Individuelles Salary in der Vergleichsbasis | Stand 05.11. |
|---|---|---|---:|---|
| 1.06 | Parker Washington | WR | 6,39 Mio. $ | Flo |
| 2.06 | Chuba Hubbard | RB | 16,50 Mio. $ | Flo |
| 3.06 | MarShawn Lloyd | RB | 0,08 Mio. $ | Flo |
| 4.06 | Tre Tucker | WR | 6,97 Mio. $ | nach Flo-Cut bei Robert |
| 5.06 | Malik Willis | QB | 4,26 Mio. $ | nach Flo-Cut Free Agent |

Summe ihrer individuellen Salaries: **34.196.176 $**. Dies ist **kein** Netto-Cap-Vergleich mit den acht Juni-Cuts: andere Spielerzahl, Top-20-Nachrücken und zusätzliche Rookie-Draft-Zugänge sind zu beachten.

### 5.2 Rookie-Draft: zusätzliche Verjüngung

| Rookie-Pick | Spieler | Stand 05.11. |
|---|---|---|
| 1.06 | Kenyon Sadiq (TE) | Flo |
| 2.06 | Omar Cooper (WR) | Flo |
| 3.06 | Germie Bernard (WR) | nach Flo-Cut bei Robert |
| 4.06 | Emmett Johnson (RB) | nach Flo-Cut bei Dennis |
| 5.06 | Drew Allar (QB) | Flo |

**Kaderpfad:** Nach den Juni-Cuts 23 kontrollierte Spieler; fünf Rookie-Zugänge führten rechnerisch auf 28; Thornton-Cut im August auf 27; fünf FA-Draft-Picks auf 32. Im Snapshot nach dem FA-Draft befanden sich zwei davon auf Taxi: damit **30 reguläre aktive Spieler bei 30 Plätzen**.

### 5.3 Spätere Verluste von Draft-Assets

- **Tre Tucker:** Flo-Cut 01.10.; Robert-Add 21.10.
- **Germie Bernard:** Flo-Cut 07.10.; Robert-Add 18.10.
- **Emmett Johnson:** Flo-Cut 07.10.; Dennis-Add 02.11.; Flo-Claim am 03.11. **fehlgeschlagen**.
- **Malik Willis:** Flo-Cut 07.10.; zum Betrachtungszeitpunkt Free Agent.

Damit sind **vier der zehn 2026 selbst gedrafteten Spieler** vorläufig nicht mehr in Flos Kader. Diese Folge-Cuts sind **nicht** mit den Juni-Cap-Cuts gleichzusetzen.

## 6. Beobachtete Produktion statt rückprojizierter Erwartungen

Die folgenden Summen stammen aus den finalen wöchentlichen PlayerWeekFantasy-Actual-Werten **innerhalb der Weeks 1–8**. Fehlende Record-Abdeckung wird nicht zu einem sicheren Nullpunkt umgedeutet. Es handelt sich um Spielerproduktion, **nicht** um eine exakte Berechnung ihrer tatsächlich von Flo oder den Gegnern gestarteten Punkte.

| Vergleichsgruppe | Spieler | Beobachtete Punkte W1–W8 |
|---|---|---:|
| RB | Javonte Williams, an Tim verloren | **137,2** |
| RB | Chuba Hubbard, von Flo gedraftet | **133,0** |
| RB | Travis Etienne, an Dennis verloren | 30,9 |
| WR | Parker Washington, von Flo gedraftet | **95,5** |
| WR | Romeo Doubs, an Tim verloren | 58,1 |
| WR | Terry McLaurin, an Dennis verloren | 46,0 |
| QB | Brock Purdy, an Jan verloren | **150,0** |
| QB | Dak Prescott, bei Flo geblieben | 152,9 |
| TE | George Kittle, an Jan verloren | **104,5** |
| TE | Tucker Kraft, bei Flo geblieben | 88,5 |
| TE | Brock Bowers, bei Flo geblieben | 123,7 |
| TE | Kenyon Sadiq, von Flo gedraftet | 45,9 |

**Fakten:** Hubbard erreichte nahezu Javontes beobachtete Produktion (Differenz 4,2 Punkte); Washington lag im beobachteten Zeitraum vor McLaurin und Doubs; Purdy und Kittle blieben dagegen hochwertige Producer.

**Interpretation:** Flo ersetzte auf RB und WR auffällig viel kurzfristige Produktion zu vergleichsweise geringen individuellen Salaries. Purdy ist der deutlichste potenzielle **nicht vollständig kompensierte Dynasty-/Trade-Asset-Verlust**; Kittle ein möglicher Qualitäts-/Coverage-Verlust trotz Bowers und Kraft. Diese Werturteile sind keine dokumentierten ex-ante-Preise und berücksichtigen nicht alle Markt-, Verletzungs- oder Altersfaktoren.

## 7. Teamresultat und nachfolgende Verstärkung getrennt betrachten

Nach **Week 8** stand Just Bill bei **7–1**, auf **Platz 1** und mit **1.656,9 Fantasy-Punkten**. Das ist ein beobachtetes gutes sportliches Ergebnis **nach** der Cap-Bereinigung; es beweist **keinen** kausalen Vorteil des Cap-Systems und sagt nicht, wie derselbe Kader ohne Cuts abgeschnitten hätte.

**Trades vom 03.11.2026, erst nach dieser Bilanz:**

- **Mit Tim:** Flo erhielt Jared Goff und gab Josh Jacobs ab.
- **Mit Dennis:** Flo erhielt Christian McCaffrey sowie Dennis’ 2027er Rookie-Runde-3-Pick; Flo gab Braelon Allen sowie seine 2027er Rookie-Picks aus Runde 1 und Runde 2 ab.

Diese Trades sind **kein** Beleg für den Erfolg der ursprünglichen FA-Picks und **keine** Rückakquisition eines Juni-Cuts. Sie zeigen stattdessen eine spätere, kostspielige neue Win-now-Investition.

## 8. Ligaweiter Maßstab

Aus den 31 abgeschlossenen **reinen** Pre-Deadline-Cuts bis einschließlich 30.06.2026 (ohne Trades, nur Transaktionen mit Drop ohne Add) entfielen auf Flo zehn Cuts.

Auf Basis desselben späteren individuellen Salary-Vergleichsstands:

| Manager | Reine Cuts | Summe individuelles Cut-Salary |
|---|---:|---:|
| Flo | **10** | **201,00 Mio. $** |
| Marcel | 9 | 83,67 Mio. $ |
| Tim | 4 | 64,70 Mio. $ |
| Jan | 4 | 50,97 Mio. $ |
| Dennis | 4 | 17,58 Mio. $ |
| **Liga gesamt** | **31** | **417,92 Mio. $** |

Flo verursachte damit rund **48,1 % des nominal freigesetzten Cut-Salaries**. Die Zahl ist **nicht** sein Anteil an ligaweiten tatsächlichen **Top-20-Cap-Ersparnissen**. Diese müssten für jedes Team mit historischen Kaderständen separat berechnet werden.

## 9. Einordnung: Beobachtung, Interpretation, offene Designfrage

### Was durch Daten gestützt ist

1. Ein erheblicher Top-20-Cap-Überhang lag vor; die acht Juni-Cuts führten in der einheitlichen Rekonstruktion bis knapp unter das Cap.
2. Flo gab acht Spieler mit erheblichem nominalem Salary ab, die andere Teams mit sieben FA-Picks nachfragten; zwei zusätzliche April-Cuts hatten in dieser Rechenbasis keinen Top-20-Cap-Effekt.
3. Flo erwarb andere und insgesamt günstigere FA-Draft-Spieler und erhielt fünf Rookie-Zugänge.
4. Der erhaltene Kern blieb stark genug für ein 7–1 nach Week 8.
5. Im Oktober und November fanden weitere Roster- und Asset-Transfers statt, die separat beurteilt werden müssen.

### Vorläufige Interpretation – **nicht** beschlossen

- Die heutige Cap-Deadline erzeugt nachweisbar einen relevanten jährlichen **Umverteilungs- und Selektionsdruck**, insbesondere bei tiefen Meisterschaftskadern.
- Sie muss deshalb nicht automatisch stärker gemacht werden, nur weil Flo danach weiter erfolgreich ist: Ein Cap kann gerade **teure Tiefe** reduzieren, während Elitequalität bleibt.
- Der Verlust von Asset-Kontrolle ist real; welcher **handelbare** Wert tatsächlich verloren ging, ist ohne historische Tradeangebote und damalige Marktwerte nicht seriös als Summe bezifferbar.
- Ob das Liga-Ziel einen raschen Reload, dauerhafte Vertragsfolgen oder echte mehrjährige Teamzyklen vorsieht, ist weiterhin **offen**.

### Fragen für die anschließende Diskussion – noch keine Vorgaben

1. **Welche Cap-Wirkung erwarten wir konkret?** Teure Reservebank, gelegentliche Starterverluste, Abgabe von echten Difference Makern oder vor allem Tradeaktivität?
2. **Soll die Cap-Deadline allein reichen?** Oder soll der Cap-Druck während der Saison beziehungsweise nach FA- und Rookie-Draft stärker weiterwirken?
3. **Wie viel Verlust von Talentkontrolle ist gewünscht?** Wann soll ein Manager vor dem Cut lieber zu einem niedrigeren Gegenwert traden, statt gratis zu entlassen?
4. **Wie dauerhaft müssen Folgen sein?** Ist ein jährlicher Reset ausreichend, oder wollen wir kontrollierte Konsequenzen über Vertragsdauer/Dead Cap? Dies ist getrennt von bereits festgehaltenen **Konzeptentscheidungen**, aber noch keine produktive Regel.
5. **Welche Erfolgsmetriken sind entscheidend?** Spielerumverteilung, Tradeaktivität, Qualität der Starting Lineups, Competitive Balance, Asset-Liquidität, Zeit bis zum Reload, Cap-Disziplin nach der Deadline?
6. **Welche Anreize passen zur sechs-Teams-Liga?** Soll Flos gelungenes Reload als Erfolg des Systems gelten, selbst wenn andere Teams seine gecutteten Starter aufnehmen konnten?

## 10. Methodische Lücken und möglicher späterer Audit

- Damalige **individuelle Salary-Snapshots** zum 29.04./09.06./30.06. separat sichern, statt nur den 05.10.-Datenstand rückzurechnen.
- Historische **Owner-/FA-Pool-/Tradeangebot-Snapshots** erfassen, um realisierbare Tradeoptionen statt nachträglicher abstrakter Asset-Werte beurteilen zu können.
- Für sportlichen **Value Over Replacement** tatsächliche Lineup-Entscheidungen und valide Positions-Ersatzspieler modellieren; bloße Saisonpunkte einzelner Spieler sind noch kein Counterfactual.
- Finale Weekly-Actual-Coverage für einzelne Spieler prüfen; nicht vorhandene Wochendatensätze nie automatisch als Score 0 behandeln.
- Die 2026er Case Study bei späteren Regel-Backtests unter gleichem Format und kontrollierten Vergleichsbedingungen erneut auswerten.
- Ergebnisse später für weitere Teams/Offseasons wiederholen; **keine allgemeine Regel aus einem einzigen erfolgreichen Team** ableiten.

## 11. Anschluss an die bestehende Research-Struktur

- [Salary-Überblick](../README.md) – Einstieg und Lesereihenfolge.
- [Performance-Salary-Redesign](../salary-system-redesign-concept.md) – offene Formelfragen und Criticality.
- [Rookie Salary / Minimum / Dead Cap](../salary-dead-cap-concept.md) – bislang dokumentierte, nicht automatisch aktive Konzeptentscheidungen.
- [Team-Window-Konzept](../../team-window-strategy-concept.md) – Reload / Rebuild / Hybrid.
- [League-Economy-Synthese](../../league-economy-redesign-options.md) – ligaweite offene Ziele und Optionen.
- [Issue #1336](https://github.com/Lolindhir/fantasy-app/issues/1336) – Nachverfolgung der **Archivierung dieser Fallstudie**, nicht der noch offenen Ligaentscheidung.

**Gültigkeitsgrenze:** Diese Datei friert den **Stand 05.11.2026** als Diskussionsbasis ein. Spätere Änderungen an Rankings, Salary, Rosterbesitz, Produktionsdaten oder Ligaregeln überschreiben den historischen Befund nicht stillschweigend; neue Vergleiche benötigen eigenen Datenstand und Quellenbezug.
