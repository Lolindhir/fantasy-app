# CP6p – Eingespielte Drei-Jahres-Vertragswirtschaft: Veteranen 100/110/120 gegen 100/125/150 und Rookie-Teil-/Vollgarantien

> **22.11.2026, Forschung zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344), unratifizierter Kandidat.** Anschluss an [CP6n](2026-11-22-cp6n-three-year-contract-market-cap-design.md) und [CP6o](2026-11-22-cp6o-100-50-25-cuts-and-deadcap.md). Der Nutzer will eine **eingespielte** Vertragswelt modellieren, nicht alle Verträge künstlich gleichzeitig im Jahr 2027 abschließen; den resultierenden sportlichen Einbruch nach bewusst gewähltem All-in **nicht als automatischen Fehler** klassifizieren. Testfragen: (1) Veteranen künftig `100/110/120` oder **`100/125/150`**; (2) Rookie-Gehalt bleibt `100/125/150`, Rookie-Restgarantie aber `100/50/25` **oder** `100/100/100`; (3) das **marktwertbasierte** Cap muss sinken können. Wöchentliche Payroll/Spieltagsteilung ausdrücklich **nicht** Bestandteil dieses Checkpoints.

## 1. Beibehaltene und neu verglichene Regeln

| Mechanik | CP6p (keine aktive Ligaregel) |
|---|---|
| Marktpreis/Teamcap | Jährlich neu, Top120 des CP6k-`world.price` geteilt durch 6, **Full Salary aller gehaltenen Spieler**; 2028–31 zusätzliche Markt-Kapazitätsszenarien `0`, `−10`, `−20 %` auf den jeweiligen Jahrestrend, kein nominaler künstlicher Cap-Floor. Beim nächstjährigen Rookie-Year1-Preis wird das **tatsächlich geschockte Vorjahres-Cap** verwendet (anders als bloß unabhängig pro Jahr abgezogener Schock). **Noch kein rein vom Rookie-Kontrakt unabhängiger Marktwert-Index**, siehe Hard Gate unten. |
| Dreijahreslaufzeit | Echte jährliche `startSeason`, `endSeason` und `salaryByYear`; Trade (nicht simulierter Pfad) würde Restvertrag ohne Reset übertragen. |
| Veteranengehalt | `100/110/120` **gegen** `100/125/150` auf den ursprünglichen Year1-Dollarwert; beide nicht kumulativ. |
| Rookie-Gehalt | In **allen** Fällen unveränderte bestehende Entwurfsstaffel `100/125/150` auf das vor dem Draft berechnete Year1-Salary. |
| Veteranengarantien | In beiden Vergleichen `100/50/25` % pro Jahr auf dessen geplantes volles Gehalt. |
| Rookie-Garantien | **Variante P** `100/50/25` % oder **Variante F** `100/100/100` %. F = vollständige Rookie-**Garantie**, nicht Vollgarantie der Veteranen; CP6o-Full-Guarantee-**aller** Spieler ist daher kein gleiches Modell. |
| Cut | Im betreffenden Jahr fällt nur der garantierte Rest dieses Jahrgangs als Dead Cap an, weitere Restjahre werden auf ihr **eigenes Fälligkeitsjahr** gebucht. Unclaimter Cut; keine fiktiven Vertragskäufer. Jahr 1 ist voll garantiert, aktuelle Spieltagsteilungen fehlen. |
| Ablauf/Verlängerung | Nach drei Jahren kann der bisherige Owner **kostenlos nicht verlängern** oder zum **aktuellen** Markt-Salary einen **neuen** Dreijahresvertrag schließen. Ein reiner Nichtverlängerungsakt ist ausdrücklich **kein Cut** und erzeugt **keinen** Dead Cap. Im Simulator sind Verlängerungen zunächst vorläufig und werden erst bei legalem Gesamtbudget verbindlich. |
| Aktivitäts-/Roster-Bedingung | Jährliche Rookie-Drafts, jedes Team fünf neue Spieler pro Jahr; keine Phantom-Free-Agents von anderen Ownern, 13 Starter und Research-Occupancy 20–40; jährliche Full-Salary-Abrechnung 2027–31. |

### Wirtschaftliche Beispielrechnung

Ein Veteran mit Year1-Ausgangssalary **20 Mio. $**:

- `100/110/120`: jährliches Salary `20 / 22 / 24` Mio. $, dreijährige Summe `66` Mio. $. Cut **vor Year2** ohne Übernahme: `11` Mio. $ Year2-Dead-Cap + `6` Mio. $ Year3-Dead-Cap = **17 Mio. $**.
- `100/125/150`: `20 / 25 / 30` Mio. $, Summe `75` Mio. $. Cut vor Year2: `12,5` Mio. $ + `7,5` Mio. $ = **20 Mio. $**.
- Rookie mit **10 Mio. $** Year1-Salary und stets `100/125/150`: Jahr2 `12,5` Mio., Jahr3 `15` Mio. – bei **P** kostet ein Cut vor Year2 insgesamt `6,25 + 3,75 = 10` Mio. $ Garantien; bei **F** `12,5 + 15 = 27,5` Mio. $. **F** macht den Rookie-Cut in Year2 zur **Null-Cap-Entlastung**, solange es keinen Claim-/Trade-Käufer gibt. Das erklärt, warum weniger gemessene Cuts unter F **kein** eigener Erfolgsbeweis sind.

## 2. Warum CP6p anders konstruiert werden muss als CP6o

**CP6o-Problem (bewusst isolierter Finanz-Test):** Alle 2027er Altspieler wurden als 2027 neu auf drei Jahre signiert. Damit traf der 2028er/-29er Cap-Schock auf synchron verjüngte teure Verträge, und der Algorithmus musste Teams teils um 50+ Starterindex-Punkte binnen eines Jahres auseinandernehmen. Der Nutzer wies zurecht darauf hin, dass eine stets etablierte Drei-Jahres-Vertragswirtschaft **laufend Jahrgänge besitzt, die ohne Cut ablaufen**.

**CP6p-kontrollierte Approximation:**

1. Dieselben 2027er sechs CP6k-Owner je Seed 11/29/47 und dieselbe archivierte Okt-2026-Spielerbasis (1.268 Altspieler). Zuerst werden sechs **vollständig legale** Startkader mit 2027er Rookie Draft wie in CP6o erzeugt. Alle **sechs 2027er Team-Gehaltsvolumina und das 2027er Cap** sind auf den Dollar identisch zu den [CP6n-Kohorten](2026-11-22-cp6n-contract-cohort-inputs.json), keine rückwirkenden eigentumsfreien Spielerzuweisungen.
2. Bereits ältere Rookiejahrgänge erhalten ihr Startjahr aus `Player.Year` (Year2 -> Beginn 2026, Year3 -> 2025), sofern die CP6k-Rookie-Contract-Quelle diese Klassifikation hergibt; Rookie-Neuzugänge 2027 beginnen 2027. **Veteranen** erhalten zufallsfrei **deterministisch** über ihren PlayerID-Hash verteilt Vertragsjahrgänge **2025, 2026 oder 2027**. Die entstehenden Vertragsvintages: Seed 11 **45/45/58**, Seed 29 **45/49/54**, Seed 47 **53/40/55** für Start 2025/26/27.
3. **Grenze der historischen Behauptung:** Im Repository ist **kein tatsächlich unter diesen neuen Regeln 2025/26 unterschriebenes, verbindliches Contract-Ledger** vorhanden. Um alle 2027er Spieler in beiden Veteranenstaffeln bei demselben Start-Cap identisch zu bewerten, wird der hypothetische historische Year1-Signing-Wert aus dem festgestellten 2027er Vertragssalary und dem faktischen Vertragsjahr-Faktor **zurückgerechnet**. **Das sind keine echten 2025er oder 2026er Marktwerte/Entscheidungen.** Die ursprünglichen 2027er Kader wurden nicht 2025–26 vertragssensitiv optimiert; frühere 2025/26-Cut-Dead-Caps werden mangels historischer Ereignisse **nicht erfunden**. CP6p testet somit eine **eingespielte Jahrgangsstruktur**, aber **kein vollständig historisch durchgeführtes 2025–27 Franchise-Gleichgewicht**.
4. Jedes Jahr 2028–31: exogene synthetische NFL-Entwicklung, jährlicher Markt-/Cap-Neupreis, 30 neue Rookie-Draftverpflichtungen, auslaufende Verträge **provisorisch** zum Marktwert erneuern, komplette Team-Over-Cap-/Positionsprüfung, ggf. freiwilliges Nichtverlängern (0 Dead Cap), aktive Cut-Verträge unter 100/50/25-/Rookie-F-Garantie, bezahlte unowned FA-Signings sowie fällige Alt-Dead-Cap-Vintages. Bei maximal 40 Plätzen erzwungene Drop-Aktionen aus Draft werden im Ledger nachgehalten und **nicht** als kostenlose Salary-Freigabe versteckt.
5. Der Manager ist ein **deterministischer Greedy-Agent** für sämtliche sechs Teams: kennt `known`-Drei-Saison-Qualität und Cap, schützt ungefähr Lineup-Stärke/Positionsdeckung, darf keine gegnerischen Spieler ohne Gegenleistung übernehmen; keine echten bilateralen Trades, Rookie-Pick-Tauschgeschäfte, NFL-2027–31-Ergebnisse, Anspruch auf bestimmte Waiver-Claims oder tatsächliche menschliche Präferenzen. Ein gestresster 2028er Rückgang ist hier **kein** nachgewiesener bewusster 2025er All-in-Vertrag – nur ein konsistenter **All-in-/Sanierungsmechanismus**.

**Reproduktion / Audits:**

- [CP6p-Simulator](../simulation/cp6p_mature_vintage_contracts.mjs), eingefrorener CP6k-Markt-/Draft-/Rosterkern aus Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`, archivierter Oktober-Player-CSV Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`.
- [Maschinenlesbare Gegenüberstellung aller 36 Pfade](2026-11-22-cp6p-mature-vintage-summary.json), **vollständige Spieler-Cut-/Extension-/Dead-Cap-Audits** [Seed 11](2026-11-22-cp6p-seed11-mature-contracts.json), [29](2026-11-22-cp6p-seed29-mature-contracts.json), [47](2026-11-22-cp6p-seed47-mature-contracts.json). Für sehr große JSON-Dateien den [GitHub Blob-Zugriff](https://docs.github.com/en/rest/git/blobs) oder GitHub-Website verwenden, da der File-Connector bei großen Dateien nur SHA/leerem Text antworten kann.
- Validation in V8 gegen die **tatsächlich im Branch gespeicherte JS-Funktionsquelle**; alle drei 2027er Bestände gegen CP6n nach Preis/Cap validiert; **36 Pfade × vier volle Folgejahre × 5 finanzielle Kontrollbedingungen = 720 fachliche Assertions**, **0 Abweichungen**. GitHub CI ist ein **separater** QA-Status, kein Nachweis, dass ein vollständiges Handels-Gleichgewicht gelöst wurde.

## 3. Ergebnis: 36 gepaarte fünfjährige Finanz-/Franchise-Wege

| Variante | Gepaarte Pfade | Ende 2031 alle sechs Teams cap- und positionslegal? |
|---|---:|---:|
| Veteranen `100/110/120`, Rookie-Teilgarantie `100/50/25` | 9 | **9/9** |
| Veteranen `100/110/120`, Rookie-Vollgarantie | 9 | **9/9** |
| Veteranen `100/125/150`, Rookie-Teilgarantie `100/50/25` | 9 | **9/9** |
| Veteranen `100/125/150`, Rookie-Vollgarantie | 9 | **9/9** |

Gegenüber **CP6o**, wo **alle** 2027er Verträge neu anfingen, 2028/29 nur eine gezwungene Cut-Sanierung zuließen und **voll garantierte Verträge aller Spieler** zu 0/27 legalisierten Pfaden führten, ist CP6p **keine** identische Garantievariante: **Veteranen sind weiterhin 100/50/25 garantiert**, und es gibt echte jährliche Expirations/Verlängerungen. Keinesfalls die beiden Erfolgs-/Fehlerquoten als kausalen Effekt von nur einer einzelnen Politikachse darstellen.

**Die harte Einschränkung:** `36/36` ist ein **Existenzbeleg für diese 36 greedy konstruierten Lösungen unter deren Annahmen**, keine mathematische Garantie für beliebige Preisentwicklungen oder historische Managerentscheidungen und keine erfundene Prognose-Wahrscheinlichkeit.

### 3.1 Härtester Cap-Stress (ab 2028 jährlich zusätzlicher −20%-Markt-Cap-Schock)

Alle Werte sind **Cuts über vier Folgejahre 2028–31 in EINER sechs-Team-Welt je Seed**, in der Spanne aus den drei synthetischen Besitzverteilungen:

| Veteranenstaffel | Rookie Garantie | Getätigte belastete Cuts | Nicht verlängerte **ausgelaufene** Verträge |
|---|---|---:|---:|
| **100/110/120** | 100/50/25 | **44–65** | **49–54** |
| **100/110/120** | 100 % | **29–32** | **71–75** |
| **100/125/150** | 100/50/25 | **61–86** | **44–49** |
| **100/125/150** | 100 % | **45–49** | **66–81** |

Hier steckt die wesentliche **Rookie-Garantie-Wirkung**: Vollgarantien führen zu **weniger finanziell sinnvollen, effektiven Cuts**, aber zu **mehr kostenlos nicht verlängerten Vertragsendpunkten**. Ein Delta bei Cuts darf man daher nicht als einseitige Verbesserung bewerten. Über 9 alternative Schock-/Seed-Pfade pro Regelkandidat sind die Zahlen:

| Veteranenstaffel | Rookie Garantie | Garantierte Cuts | Nichtverlängerungen | Gesamte Vertrags-Exits* |
|---|---|---:|---:|---:|
| 100/110/120 | Teilgarantie | 435 | 397 | 832 |
| 100/110/120 | Vollgarantie | 243 | 591 | 834 |
| 100/125/150 | Teilgarantie | 576 | 384 | 960 |
| 100/125/150 | Vollgarantie | 386 | 577 | 963 |

\* Die Summe betrifft **neun alternative**, nicht unabhängige fünfjährige Stresspfade (3 Seeds × 3 Cap-Schocks) – **nicht** eine historische Liga mit so vielen realen Trades/Cuts. Auch sportlich und finanziell sind Cut und Nichtverlängerung fundamental verschieden.

**Strukturelle Interpretation:** Mehr Veteranen-Eskalation erhöht die erforderlichen Vertrags-Exits in beiden Rookie-Garantiewelten; die Rookie-Vollgarantie verschiebt vor allem den **Exittyp** von Cut auf Expiry/Decline. Eine vollständige Rookie-Garantie könnte gezielt die bewusste Risikobindung beim Rookie-Pick erhöhen, aber dem Manager bei Rookie-Busts weniger Flexibilität lassen.

### 3.2 Wirkliche sportliche Rückwirkung auf Team 0

Ausgangspunkt für Team 0 im 2027er Referenzmarkt: Starterindex **202,084** (Seed11), **200,973** (Seed29) oder **200,188** (Seed47), jeweils ohne Erfindung echter 2027er NFL-Ergebnisse.

**Markt-Cap-Schock −20 %, nach 2028er Budget-/Roster-Sanierung und in 2031:**

| Veteranen-Contract / Rookie-Garantie | Team 0: Starterindex 2028 in den drei Seeds | Team 0: Starterindex 2031 in den drei Seeds |
|---|---|---|
| 100/110/120 · Rookie P | 181,12 / 186,24 / 180,10 | **180,22 / 175,47 / 175,37** |
| 100/110/120 · Rookie F | 176,67 / 177,88 / 180,17 | **176,71 / 176,75 / 174,93** |
| 100/125/150 · Rookie P | 176,67 / 177,65 / 170,52 | **175,24 / 170,93 / 167,06** |
| 100/125/150 · Rookie F | 168,26 / 178,79 / 174,30 | **165,13 / 173,14 / 167,31** |

- Das ist ein **beobachteter Modellpreis des vormals starken Kaders**; der frühere All-in kann also durchaus in ökonomischen Druck übergehen, **ohne** dass wir einen künstlich kostenlosen Reset bauen. Diese Kosten nicht automatisch als „unfair“ werten.
- Zugleich ist der **2028er Indexverlust** nicht mehr mechanisch der CP6o-Horrorfall von Team0 `~197 → 141` beim synchronen Year2-Salary. Im Seed11-CP6p-Szenario `2027~202 → 2028~181` bei 100/110/120 + Rookie-P, `2028~177` bei 100/125/150; bereits auslaufende Verträge erzeugen echte Exit-Optionen. Diese Studien unterscheiden sich auch in **Laufzeit und 2027-Vertragsbuchhaltung**; daher nicht als empirisch isolierten Kausalschätzer ausgeben.
- **Volle Rookie-Garantien sind sportlich nicht dominant:** Im harten 100/125/150-Veteranenszenario liegt Team0 mit Rookie-Full 2031 Seed11 **10,11 Indexpunkte schlechter** als mit Rookie-Teilgarantie, Seed29 aber **2,21 Punkte besser** und Seed47 **0,26 besser**. Daraus folgt ausdrücklich **kein** allgemeiner sportlicher Sieger.
- Die 2031er Team0-Werte bewegen sich relativ zum jeweils stärksten anderen Team von punktgleich/vorn bis grob zehn Punkte hinten; diese Modellwerte sind **keine echten Titelwahrscheinlichkeiten**, da der Simulator kein Matchup-/Playoff-/Gesundheitsmodell und keine verhandelten Trades enthält.

## 4. Bewertung der beiden Nutzerthesen

### A. „Regel schon immer in place“ – methodisch richtig, empirisch erst teilweise umgesetzt

Die Frage nach laufenden Vertragsschichten ist der **richtige Modellierungsschritt**. Andernfalls würde eine für All-in und Risiko geplante Vertragswirtschaft durch eine künstliche gleichzeitige Neuverpflichtung des ganzen Bestands von vornherein benachteiligt.

Aber ein echtes **Burn-in** muss später mindestens 2024–26 kontraktgesteuerte Draft-/WA-/FA-/Trade-Entscheidungen, Jahr-1/2/3-Salary, eventuelle alte Dead-Cap-Jahrgänge, aktuelle Rechte und begrenzte 30er-Realroster **endogen** simulieren. Im vorhandenen CP6p sind nur die **bestehenden Alterskohorten** synthetisch verschieden, der 2027er Vertragssalary-Anchor wurde rückgerechnet. Diese wichtige Wahrheitsgrenze im Bericht und Issue sichtbar halten.

### B. „All-in → hohe Kosten → Umbau“ – als gewollte Dynamik ernst nehmen

Der Nordstern fordert **nicht**, dass starke Teams jedes Jahr den höchsten Starterindex halten. Er verlangt, dass gutes Management Vorteile erzeugen darf, die später **erneute wirtschaftliche Entscheidungen** erfordern. Unsere CP6p-Stressfälle zeigen solche Budget-/Rookie-/Renewal-/Cut-Trade-offs und keinen zwangsläufigen Totalkollaps.

**Gegenkontrolle:** Ein Abbau ist nur dann „gutes All-in-Design“, wenn 2025–27 ein Manager **bewusst vor Laufzeitabschluss** die Titelchance gegen das spätere Risiko wählen konnte und danach durch Wissen/Assets/Trades wieder aufbauen kann. CP6p hat **keine signierenden Menschen, keine bewusste All-in-Vertragswahl oder Sporttitel modelliert**. Deshalb kann man den gewünschten ökonomischen Effekt positiv bewerten, aber nicht behaupten, der Nordstern sei bereits quantitativ bewiesen. Gleichzeitige Verpflichtungen von Rookies, Vertragserneuerungen, Transfer-/Claim-Markt, Opportunity Cost und Planbarkeit bleiben ausdrücklich zu testen.

## 5. Die fünf verbindlichen Finanzierungsachsen (auditierbar)

1. **Seller Relief:** Kein tatsächlicher Trade-Seller. Jeder im JSON aufgeführte `guaranteed-cut` hat ursprüngliches volles jährliches aktives Salary, im aktuellen Jahr gebuchten garantierten Rest, jahresweise folgende Dead-Cap-Vintages und Netto-Ersparnis **inklusive eventueller FA-Signing-Kosten**. **`expiration-declined`** besitzt nach Ablauf des ursprünglichen dreijährigen Vertrags **0 Dead Cap** und kann vor neu verbindlich unterschriebenem Vertrag kostenlos erfolgen. Forced-Draft-40er-Drops werden nicht aus dem Ledger gelöscht.
2. **Buyer Burden:** Bei modellierten Free Agents aus dem tatsächlich unowned Simulationspool wird ein eigener **voller** dreijähriger Vertrag zum aktuellen Spielerpreis abgeschlossen. Bilaterale Vertrags-Claims/Trades, Käuferbereitschaft, Pick-Gegenleistung, eigentümerübergreifende Salary Retention **nicht beobachtet**. Es wurde **kein** fiktiver wirtschaftlich toleranter anderer Owner erzeugt.
3. **Roster Capacity:** 6 exklusive Owner, 13 Pflichtstarter inklusive vier FLEX, CP6k-Minimum **20 / Max 40** aktive Research-Slots. Die tatsächliche 2026er Sleeper-Liga hat **30 reguläre + 5 Reserve/IR + 2 Taxi**; diese reale 30er-Kapazität, Taxi-Lock und Positionsberechtigung sind **noch nicht** pro kontraktgebundenem 2027er Team modelliert. Damit ist keine Ausführbarkeit am echten Sleeper-Bestand belegt.
4. **League-wide debt/guarantees:** Jede Cut-Garantie wird mit signiertem Vertragsjahrgang und Jahr der **tatsächlichen Fälligkeit** im Ledger dem alten Team zugeordnet. Keine neue Cap-Kredit-/H2-/H3-Vintage, keine automatische Rückzahlung, kein künstliches Weiterreichen beim Cut oder bei einem jährlichen Marktwert-Neupreis. Echte Garantiefall-Vintages in kompletten Seed-Audits. Frühere neue C-add-Tenure-50/30/15/5-Ein-Zyklus-Mechanik bleibt **alternativer unratifizierter Vorschlag**, nicht parallel und doppelt gebucht.
5. **Future settlement:** Für alle sechs Teams wird bis einschließlich 2031 der jeweilige Full-Salary-/Dead-Cap-Budgetzustand unter einem neuen jährlichen, auch sinkenden Cap gerechnet. Pro legalem Pfad vier weitere Rookie-Drafts zu 30 Spielerpflichten = **120 Rookie-Vertragsabschlüsse**, plus Vertragsexpirations/Verlängerungen. Der Simulator schreibt zusätzlich die prognosefrei vertraglich fälligen Gehälter/Dead Caps **über 2031 hinaus** aus, aber 2032–34 neue Markt-Caps, Roster-Aktionen und realisierbare Folge-Titelmöglichkeiten werden **nicht** bewertet. Kein künstlicher Kredit als Insolvenzlösung.

## 6. Nordstern-Vergleich der vier neuen Kombinationswelten

| Geschütztes Ziel | CP6p-Evidenz | Nicht gesicherte Folgerung / Risiko |
|---|---|---|
| **1 Langfristige Aufholbarkeit** | Starke Teams verlieren bei hohen Vertragsstaffeln und niedrigem Markt-Cap bezahlte Kaderqualität, aber können nach Ablauf neu disponieren; alle 36 Pfade in 2027–31 legal | Ohne echte Liga-Win-/Playoff-/Trade-/Draft-Endogenität kein Beweis, dass schwächere Manager wieder echte Championship-Chancen erhalten |
| **2 Gutes Management belohnen** | Alte günstige Verträge behalten Wert, neues Rookie-Capital/Cap und Verlängerungszeitpunkt haben echten wirtschaftlichen Hebel | 2025–26 Kaufentscheidungen rückgerechnet, nicht rational unter vorher bekannten Regeln simuliert |
| **3 Keine zementierten Vorteile** | Vertragsende und Markt-Repricing erzwingen regelmäßiges neu verhandeltes Cap-Budget statt kostenlosem Weiterhalten | Selbst ein drei Jahre günstiger Core kann stark sein; das ist legitim, sofern die neue spätere Entscheidung echt ist |
| **4 Konsequenzen des Erfolgs** | Hohe 2027er Starterindex-Ausgangswelt kann Jahre später fortlaufende Garantiebelastung, Nichtverlängerungen, notwendige Cuts und sportlichen Stärkeabbau auslösen | Mechanischer schwerer Verlust ist allein kein Beweis für gut gewählten oder vorab willentlich akzeptierten All-in |
| **5 Strategische Wege** | Rookie-Full erzeugt gebundene Draft-Risiken, Rookie-P andere FA-/Cut-Optionen; Veteranen 100/125/150 verändert Zeithorizont stark | Kein bilateraler Trade-/Asset-/Claim-Markt, kein freier Vertragspreis und keine freiwilligen All-in-/Rebuild-Managertypen |
| **6 Durchsetzbar** | Jährliches 3Y-`salaryByYear`-/`guaranteeByYear`-Ledger braucht **keine** Spieltagsabrechnung, legale Cut-/Cap-Prüfungen reproduzierbar | 14-Tage-Claims/Grace, automatischer Sleeper-Trade-/Starter-Gate, 30+IR/Taxi-Occupancy, schwierige Dead-Cap-Status-/Einspruchs- und Hard-Failure-Fälle sind noch nicht operativ gelöst |

## 7. Entscheidungsstand und nächster fachlicher Test

**Befund, keine Liga-Regelentscheidung:**

- **Bestätigter brauchbarer Kandidat:** Teilgarantierter Veteranenvertrag (`100/50/25`), marktwertabhängiges, auch sinkendes Cap und vollständig dreijährige Verträge **mit versetzten Laufzeitjahrgängen**. In CP6p sind sowohl 100/110/120 als auch 100/125/150 **rechnerisch sanierungsfähig**, jedoch sehr unterschiedlich streng für Management und sportliche Stärke.
- **100/125/150 % auch bei Veteranen ist nicht „unmöglich“** und darf nicht nur deshalb verworfen werden, weil es häufiger zu einem absichtsvoll harten All-in-/Rebuild-Rückbau führt. Es wird aber schwerer, das Team dauerhaft stark zu halten; in den harten Szenarien hat Team 0 2031 meistens weniger Starterindex als unter 100/110/120.
- **Rookie-Vollgarantie ist offen.** Sie zwingt weniger direkte Cuts und mehr Verlängerungs-/Expiry-Entscheidungen, ohne in diesen 36 Pfaden einen strukturellen Hard-Failure zu erzeugen. Ob Rookie-P oder Rookie-F aus Nordstern- und Liga-Sicht besser ist, lässt sich aus `36/36` und den gemischten Starterindizes **nicht** entscheiden.
- **Top-Priorität** ist jetzt ein wirklich **vor-2027 begonnenes** kontraktsensitives Liga-Burn-in mit getrenntem **market-value (inklusive Rookie-Year2/3 ohne Contract-Lookup)**, echten oder nachvollziehbar simulierten früheren PlayerAcquisition-/Salaries-/DeadCaps, 30+5+2 Slotlogik, simulierter Trade-/Waiver-Claim-Akzeptanz und Gegenwerten der Draft-Picks. Vor einer Implementierung müssen Vertragsjahrgrenze bei midseason adds, Signing Grace, Claim-Offset/-Priorität, Rookie-Taxi-Kosten, Year1-Garantie und Hard-Settlement transparent geregelt und sechsfach ratifiziert werden.

**Keine** produktive Salary-/Sleeper-/Frontend-Regel, Deadline oder ein normatives Nordsternziel wurde geändert. Forschungsstand verbleibt in Issue #1344 und der noch nicht gemergten Draft-PR #1576.
