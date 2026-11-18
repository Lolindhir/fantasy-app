# CP5d – Annual Cap Debt, Cut-Retention und Kreditrahmen: historische Gegenprobe

> **Forschung:** 15.11.2026 · **Issue:** [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status:** mechanischer Gegenfaktik-Test, **kein Ligaentscheid, keine aktive Regel**. Die sechs geschützten [Nordstern-Ziele](../../../league-context/league-philosophy.md) bleiben unverändert.  
> **Basis:** [CP4](2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md), [CP5a](2026-11-14-salary-cap-cp5a-system-windows.md), [CP5b](2026-11-14-salary-cap-cp5b-legal-start-settlement.md), [CP5c](2026-11-14-salary-cap-cp5c-windows-deadcap-carryover.md), [Salary-/Dead-Cap-Konzept](../salary-dead-cap-concept.md). [Reproduzierbare Einzelmetriken](2026-11-15-salary-cap-cp5d-metrics.json).

## 1. Kurzbefund

- **B (nur Debt)** verändert am historischen **29.06.2026** nichts: alle **6/6** Kader lagen bereits unter dem damaligen Salary Cap von **434.255.984 $**, ohne frühere Debt.
- **C mit 50/30/15/5-%-Cut-Retention**, angewandt auf **14 echte abgeschlossene Cut-Events** (Packers vier, Just Bill acht, Mammoth zwei) vom 07.06. nachmittags bis 30.06., schafft nominal **54.996.380 $** Cut-Retention. Bei **additiver** Abrechnung wären aus diesen historischen Kadern insgesamt **35.094.437 $** Jahres-Schuld entstanden: Packers **4.068.909 $**, Just Bill **31.025.528 $**. Bei **virtuellen Top-20-Dead-Cap-Slots** wären es nur **4.941.734 $** für Just Bill.
- **25 % / 50 % Kreditrahmen**: Unter keinem der **sieben** beobachteten 2025/26-Snapshots mit hypothetischer isolierter Abrechnung und **D_prior = 0** hätte eine solche Obergrenze gegriffen. **10 %** hätten im September-2026-Preisstand TimpaBay und im November-2026-As-of Just Bill und Mammoth begrenzt. Die Kreditregel allein ist daher bei 25/50 % bislang **kein empirisch starker Schutz**.
- Ein hoher Roll-Over-Cap garantiert **keine Tilgung**. Unter künstlich konstantem Juni-2026-Top20/Cap würde Just Bill seine einmalige additive Debt von **31,03 Mio. $** erst nach **fünf weiteren** Jahreschecks (2031) tilgen; mit *rein hypothetischem* Dezember-2025-Schuld-Seed erst nach **zehn weiteren** (2036).
- **Ungeklärt:** Ob Cuts von Nicht-Top-20-Spielern überhaupt eine additive Verpflichtung auslösen sollen. Bei Mammoth wurde **Devin Neal** aus Salary-Rang **29** gecuttet, hätte aber mit Tenure-1-30-%-Satz **547.215 $** additive Kosten ausgelöst, obwohl der Cut zuvor **0 $** Top-20-Spielergehalt freigab.
- Keine Aussage über reale Managerreaktionen, Angebotspreise, Championship-Wahrscheinlichkeiten oder gemessene Commissioner-Minuten; **CP5/CP6 bleiben offen**.

## 2. Drei voneinander getrennte Modellvarianten

Gleiche Spielerbewertungen, Roster und 20-Slot-Regel; nur die neuen Bilanzregeln werden gewechselt:

```text
P_t      = Summe der 20 teuersten gehaltenen Spieler-Salaries
R_t      = bis zum jährlichen Check noch geltender Cut-Retention-Anteil
D_t      = bereits beim VORHERIGEN Jahresabschluss fixierte Cap-Schuld
Cap_t    = veröffentlichter Cap zur jeweils dokumentierten Preiswelt

A        = heutiger jährlicher Check, keine Schuld; D = 0
B        = max(0, P_t + D_t - Cap_t)
C-add    = max(0, P_t + SUM(R_t) + D_t - Cap_t)
C-virt   = max(0, Top20(alle Kader-Salary-Slots UND R_t-Slots) + D_t - Cap_t)
```

In **C** bleiben die individuelle 50/30/15/5-%-Staffel, der Retained-Salary-Split beim Cut und der einmalige Reset des bisherigen, **noch nicht aktiven** [Konzeptes](../salary-dead-cap-concept.md) erhalten – nur **der bei einer jährlichen Prüfung entstandene Gesamtüberhang** wird als **neue eigenständige Schuld** übernommen. **Prüfung vor Dead-Cap-Reset**, dann **Schuld fixieren**, danach alte Retained-Salary-Anteile resetten und neu bepreisen, ist eine **explizite unbeschlossene Test-Reihenfolge**. Ein FA-Draft **nach** dem Check wirkt nicht retroaktiv auf diese Schuld. Dieser Zeitpunkt ist als wirtschaftlicher Anreiz bewusst beibehalten; keine Verschiebung des Drafts/Checktermins in diesem Test.

`D_next > floor(alpha × Cap_t)` muss **unzulässig** heißen, bis ein Manager den vollständigen wirtschaftlichen Check durch freiwillige korrekte Aktionen erfüllt. Die Differenz **nicht** abschneiden, nicht als abgeschriebene Schuld behandeln, nicht automatisch fremde Spieler cutten. Es gibt weiterhin keine produktive Liga-Regel für die Durchsetzung von Insolvenz/Limit-Verstößen. Weil `P_t` auf Top 20 begrenzt ist, darf `R_t` **nicht** nebenbei wie ein vollständiger 33er-Kader-Contract behandelt werden.

## 3. Juni 2026: alle sechs Teams, dieselben historischen Cut-Ereignisse

**Quellen:** [07.06.-Roster](https://github.com/Lolindhir/fantasy-app/tree/5b4ed63172deae79759e7150f8511bd2ea3edb4e), [29.06.-Roster](https://github.com/Lolindhir/fantasy-app/tree/85e22feb064fdaf2257d6c3149c8d1655ada0908), zeitgenössischer `Players.json`-Git-Blob `21001d6c0819dbbcb3deff084d63fe377714541c`, vollständiger `Transactions.json`-Blob `0aa85766a962a9d499fe5610a269771dd3b02ce1` vom 05.11.2026. Nur abgeschlossene Cut-only-`free_agent`-Transaktionen mit leerem `Adds` und nichtleerem `Drops` **ab 07.06. 12:00 UTC** und vor der **30.06. 23:59:59 UTC** Deadline. Ein früher Cooper-Kupp-Cut am 07.06. 09:14 UTC ist im 07.06.-Startroster bereits verarbeitet und wird nicht doppelt gezählt. Die Team1/6-Spielerbewegungen in Juni sind Trades, keine Cuts.

Die 2026er Team-Tenure der acht Flo-Cuts entspricht exakt **CP4**. Die vier Packers-Cuts und zwei Mammoth-Cuts wurden gegen archivierte 2024/2025 Saisonabschlussroster und 2025er Transaktionen überprüft: Brissett/Devin Neal kamen am **26.11.2025**, übrige Vier-Spieler-Gruppe seit 2024 beim selben Team. **14/14** Spieler mit historischem Salary und individuell begründetem 30- oder 15-%-Rate. Es gelten hier keine sonstigen neuen Salary-/Rookie-Overlays.

**Alle Werte Mio. $, Debt mit Ausgangsschuld 0.** Der am 29.06. archivierte Kader ist historisch real; die monetäre Cut-Anwendung hypothetisch.

| Team | Cuts | Top20-Payroll | Retained Salary | Schuld C-add | Schuld C-virt |
|---|---:|---:|---:|---:|---:|
| Mighty Giants | 0 | 428,34 | 0,00 | 0,00 | 0,00 |
| Ruhr Valley Packers | 4 | 428,07 | 10,26 | 4,07 | 0,00 |
| Just Bill | 8 | 427,73 | 37,55 | 31,03 | 4,94 |
| Mammoth Marauders | 2 | 417,41 | 7,19 | 0,00 | 0,00 |
| Team DennisLACards | 0 | 410,70 | 0,00 | 0,00 | 0,00 |
| Team TimpaBay | 0 | 430,41 | 0,00 | 0,00 | 0,00 |
| **Gesamt** | **14** | **2.542,66** | **55,00** | **35,09** | **4,94** |

**Grund für die große Abweichung:** Packers behalten nach Top20 nur **6.187.215 $** freie Kapazität; die 10.256.124 $ nominalen Cut-Anteile würden additiv eine Schuld von 4.068.909 $ auslösen, als virtuelle Positionen erhöhen sie dagegen die Top20-Belegung nur um **98.449 $**. Bei Flo liegt die nominelle Retention bei 37.551.933 $, additive Schuld 31.025.528 $, virtuelle Schuld 4.941.734 $. Mammoth trägt nominell 7.188.323 $ Cut-Anteile, bleibt additiv unter dem Cap und erhält **bei virtueller Rechnung überhaupt keine zusätzliche Top20-Belegung**.

**Ausdrücklich keine Fortsetzung als echte NFL-Lohnhaftung:** Retained Salary reduziert im bestehenden Konzept das aktive Salary des *ungebundenen* Spielers bis zum regulären Reset. Die **noch nicht übernommenen** Juni-Spieler erscheinen daher mit ihrem alten Teambetrag beim ursprünglichen Manager, nicht gleichzeitig mit einem zweiten vollen aktiven Salary im neuen Team. Die nach der Deadline im FA-Draft erfolgende Aufnahme darf den schon fixierten Debt-Check nicht rückgängig machen. Unter einer anderen Retained-Salary-Laufzeit oder 100-%-Haftung entstehen andere Resultate; die vollständige 100-%-Haftung als **nur algebraischer Stressextremfall** steht gesondert in JSON.

## 4. Empfindlichkeit des Schuldendeckels auf historischen Preis-/Kader-Ständen

Die folgenden **sieben** Snapshots sind unabhängige historische as-of Kader-/Cap-Preismärkte, **keine sieben Jahresdeadlines**. 2025 gilt noch `SalaryDollars`/Top120÷6, 2026 `Salary`/0,9×Top120÷6. Bei allen Snapshots wurde **D_prior=0** gesetzt und **noch kein** neues Dead Cap addiert. September/November 2026 sind unter dem geltenden Regelwerk **kein** Verstoß.

| Archivdatum | Cap | Positiver Überhang | Größter Teamüberhang | Teams über 10 % / 25 % / 50 % |
|---|---:|---:|---:|---:|
| 2025-11-05 | 581,66 | 75,12 | 39,48 | 0 / 0 / 0 |
| 2025-12-05 | 581,66 | 63,71 | 32,58 | 0 / 0 / 0 |
| 2025-12-21 | 581,66 | 51,35 | 32,58 | 0 / 0 / 0 |
| 2026-06-29 | 434,26 | 0,00 | 0,00 | 0 / 0 / 0 |
| 2026-08-25 | 434,26 | 0,00 | 0,00 | 0 / 0 / 0 |
| 2026-09-09 | 434,26 | 122,57 | 45,91 | 1 / 0 / 0 |
| 2026-11-05 | 427,65 | 217,96 | 83,22 | 2 / 0 / 0 |

Beispiele: September 2026 ist TimpaBay mit **45.910.392 $** um **2.484.794 $** über der 10-%-Kreditgrenze; November 2026 (Cap 427.653.631 $) sind Just Bill mit **83.218.306 $** und Mammoth mit **56.654.702 $** über 10 %, zusammen **54.342.282 $** über dem zulässigen Kredit. **25/50 % binden nirgends**. Damit würden beide häufig diskutierten Werte nur das theoretische obere Budget erhöhen, bis alte Schuld hinzukommt.

Der November-Kader zum **September-Salary-Freeze** ist als zusätzliche Kontrolle im JSON dokumentiert. Er ist keine Fortsetzung derselben As-of-Preiswelt wie der originale November-Befund.

## 5. Mehrjahr-Übertrag – algebraische Szenarien, keine historischen Managerentscheidungen

Als **klar gekennzeichneten Nicht-Deadline-Proxy** setzen wir alternativ die *positiven Überhänge* des **21.12.2025** als fiktives `D_2026` ein: Packers **16.674.498 $**, Just Bill **32.575.757 $**, Mammoth **2.099.301 $**. Die damalige 2025er Historie enthält keine bindende Debt-Regel oder rekonstruierte offizielle Schulden-Deadline; daher ist dies **keine tatsächliche Schuld**. Anschließend wird der **reale 29.06.2026-Roster und seine damalige Preiswelt** verwendet.

| Team | Dez-2025-Proxy | Folge-Schuld B | Folge-Schuld C-add | Folge-Schuld C-virt |
|---|---:|---:|---:|---:|
| Mighty Giants | 0,00 | 0,00 | 0,00 | 0,00 |
| Ruhr Valley Packers | 16,67 | 10,49 | 20,74 | 10,59 |
| Just Bill | 32,58 | 26,05 | 63,60 | 37,52 |
| Mammoth Marauders | 2,10 | 0,00 | 0,00 | 0,00 |
| Team DennisLACards | 0,00 | 0,00 | 0,00 | 0,00 |
| Team TimpaBay | 0,00 | 0,00 | 0,00 | 0,00 |
| **Gesamt** | **51,35** | **36,54** | **84,34** | **48,10** |

Ein noch härterer **rein synthetischer** Test friert *alle* zukünftigen Salarypreise, das 2026er Juni-Liga-Cap, Teamzugehörigkeiten und Juni-Endkader ein. Neue individuelle Dead Caps entstehen nicht. So bleibt bei Flo ein jährlicher Cap-Puffer von exakt **6.526.405 $** zur Tilgung. Die isolierte C-add-Schuld von **31.025.528 $** fällt erst nach **fünf** weiteren Checks (2031) auf null. Mit dem bewusst unhistorischen Dezember-2025-Proxy-Seed wären es **63.601.285 $** und **zehn** weitere Checks (2036). Packers 4,07 Mio. $ würden bei unverändertem 6,19-Mio.-Puffer **2027** getilgt. **Keine** Zahl in 2027–2036 ist ein tatsächlich geplanter/archivierter Kader oder ein projiziertes Salary.

Beweis für die Schwäche eines reinen Kreditrahmens: Wenn `P_t=Cap_t` ist, dann `D_next=D_prior` **ohne Ablaufdatum**. Ein Limit von 25 % wird dadurch nie verletzt, obwohl der Kredit dauerhaft einen Vorteil finanziert. Es bedarf einer **separaten** Schuldentilgungsregel oder klarer Jahrgangslaufzeit, falls gerade dies verhindert werden soll.

## 6. Prüfung entlang des geschützten Ligaziels

| Ziel | A heute | B Schuldvortrag | C-add | C-virt |
|---|---|---|---|---|
| Langfristige Aufholbarkeit | Kein in-season Cap-Zwang, aber legale Juni-Kader | Nächste Saisons zahlen das Übergewicht; Realwirkung nicht gemessen | Kosten von Juni-Cuts halten, kann Reload/Rebuild erschweren | Viele Cut-Anteile drücken kaum auf die Bilanz |
| Gutes Management | Gute Trades/Drafts wirken | Finanzdisziplin wird erneut wichtiger | Langfristige Retention kostengünstiger, kurzfristige Fehleinkäufe teuer | Geringere Cut-Kosten |
| Gratisvorteile nicht dauerhaft | Vor FA-Draft deutlicher Cap-Cut möglich | Überhang am Jahrescheck wird teuer | Unverkaufte Cuts verursachen auch beim Deadline-Abschluss Kosten | Kleine Dead Caps fallen unter Top20 |
| Wirtschaftliche Konsequenz | Mit 14 Cuts 0/6 über Cap | Juni mit Nullseed ebenfalls 0 | 35,09 Mio. $ neues Debt ohne Seed | 4,94 Mio. $ neues Debt ohne Seed |
| Strategiefreiheit | Hoher kurzer Spielraum | Win-now auf Kredit, später weniger Flexibilität | Mehr Trade-Anreiz **möglich**, aber schwacher Käufermarkt | Leichterer Reload, weniger Sanktion |
| Verlässlicher Vollzug | Ein jährlicher Check | Ein Schuldensaldo pro Team, aber offene Schuldenlaufzeit | Zusätzlich 14 Cut-Ledger-Einträge, definierte Reset-Reihenfolge | Gleiches Ledger und variable Top20-Slots |

Verglichen mit F2/F3 und permanentem Event-Cap aus CP5a-c ist der jährliche Schuldvortrag **administrativ einfach auf dem Papier**, verhindert aber keine kurzfristige Ansammlung innerhalb der Saison; er zieht ihre Kosten nur auf künftige Prüfungen. Höhere Schulden könnten neue Trades fördern oder gerade schwächeren Teams Liquidität nehmen. Die realen Bid-/Managerreaktionen, Championship-Wahrscheinlichkeiten und Commissioner-Minuten sind weiterhin **nicht belegt**. Deshalb ist noch kein Designpaket Sieger.

## 7. Entscheidungsgates und QA

**Nur drei Entscheidungen weiter testen statt weitere Variablen aufzublähen:** (1) Gibt es **pro Schuldjahrgang** eine echte Tilgungsfrist statt bloß 25/50-%-Gesamtlimit? (2) Zählt Cut-Dead-Cap additiv oder als virtueller Slot, und sollen Nicht-Top20-Cuts wie Devin Neal überhaupt eine zusätzliche Strafe erzeugen? (3) Wie wird eine Überschreitung des Kreditrahmens zum bereits vor dem FA-Draft liegenden Stichtag tatsächlich und fair ausgeräumt, ohne automatisch ungewollte Kaderbewegungen vorzunehmen?

**Beibehalten für diesen Vergleich:** die 20 relevanten **gehaltenen** Spieler, jährliche Performance-Salary-Neubewertung, FA-Draft **nach** der Cap Deadline, keine In-Season-Vertragswahl und keine Restrukturierung. Keine neue hochkomplexe Veteranenvertragsschicht hineinziehen.

**Vollzugsvorbehalt:** Das bisherige konzeptionell geklärte Dead Cap von 50/30/15/5 % gilt **nur bis zum nächsten regulären Salary Check**; die C-Schuld ist eine *andere*, jährlich kumulierte Größe. Ein einmal beim Check fixierter Schuldposten bleibt bei späterer FA-Übernahme bestehen; derselbe Cut-Betrag darf aber nicht **nochmals** als aktiver Dead-Cap-Posten verbucht werden. Kein automatisches Debt-Schuldenglätten oder Auto-Cut eingeführt.

**Prüfprotokoll:** 20 unabhängige programmatische QA-Invarianten, einschließlich Flo-CP4-Reproduktion, Team-Cut-Zählung, 14 einzigartigen PlayerIDs, Cap-Top20, sieben Snapshot-Abgleichen, 10/25/50-%-Grenzen und der Frozen-Future-Arithmetik. Vollständige Spieler-Cut-Event-IDs, gesperrte Input-Refs, Modelle, Rechenannahmen, Formeln, sieben Snapshots und Zukunftsschuldszenarien in JSON. Ausschließlich datierte Research-Dateien und README-Link; keine technischen/aktiven Liga-/Nordstern-Regeln geändert.

**Status:** CP5d als berechenbarer Gegenfaktik-Checkpoint, **CP5-Rest (realer Langfrist-/Markteffekt und Operator-Aufwand) und CP6 bleiben offen**. Eine technische Einführung erfordert einen separaten klar definierten, ausdrücklich autorisierten Scope.
