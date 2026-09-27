# Salary- und Dead-Cap-Konzept

> **Status:** Diskussionsentwurf – noch keine beschlossene Ligaregel
>
> Dieses Dokument hält den aktuellen Stand der Diskussion fest und soll als gemeinsames Konzeptpapier für die Liga dienen. Es ist bewusst menschenlesbar formuliert und wird bei materiellen Änderungen der Idee fortgeschrieben.

## Ziel

Das Salary-System und ein mögliches Dead-Cap-System sollen sich wie ein zusammenhängendes Vertragsmodell anfühlen.

Die Grundidee:

- ein Spieler besitzt innerhalb eines Salary-Zyklus ein festes aktuelles Salary;
- bei einem Cut verschwindet dieses Salary nicht vollständig;
- ein Teil des Salaries bleibt als Dead Cap beim abgebenden Team;
- der verbleibende Teil wird zum Salary, das ein neues Team für den Spieler übernehmen würde;
- beim nächsten regulären Salary Check beginnt ein neuer Salary-Zyklus.

Dead Cap ist damit nicht nur eine abstrakte Cut-Strafe, sondern kann als **weiterbezahlter Anteil eines bestehenden Spielervertrags** verstanden werden.

---

## 1. Gemeinsamer Drei-Jahres-Horizont

Sowohl das Salary-Modell als auch die vorgeschlagene Dead-Cap-Logik orientieren sich an einem Drei-Jahres-Horizont.

### Veteranen-Salary

Das Salary eines etablierten Spielers berechnet sich aus den Ergebnissen seiner letzten drei abgeschlossenen Saisons.

### Rookie Year 1: Draft-basiertes Salary als geklärte Konzeptentscheidung

Bei einem Rookie existiert noch keine abgeschlossene NFL-Leistungshistorie. Sein Year-1-Salary wird deshalb vollständig aus zwei Draft-Signalen abgeleitet:

- seiner Draft Position im Rookie Draft unserer Fantasy-Liga;
- seiner realen NFL Draft Position, bereinigt auf den für Fantasy relevanten QB/RB/WR/TE-Pool.

Der Fantasy-Draft ist das primäre ligainterne Marktsignal. Der NFL Draft bleibt ein starkes externes Korrektiv.

Die Gewichtung lautet:

```text
Year1Pct
= 65 % × FantasyDraftPct
+ 35 % × NflDraftPct
```

Das resultierende Year-1-Salary wird aus dem maßgeblichen Vorjahres-Salary-Cap berechnet:

```text
Year1Salary
= Vorjahres-Salary-Cap × Year1Pct
```

Anschließend wird nach der allgemeinen Salary-Rundungsregel auf volle Dollar kaufmännisch gerundet.

#### Kurve je Draft-Signal

Für einen regulär gedrafteten Spieler wird jedes der beiden Draft-Signale mit derselben fallenden Kurve bewertet:

```text
DraftPct(r, N)
= 0,30 %
+ (3,50 % - 0,30 %)
  × (1 - (r - 1) / (N - 1))^3,5
```

Dabei gilt:

- `r` = Rang des Spielers im jeweiligen Draft-Pool;
- `N` = konkrete Größe dieses Draft-Pools;
- Rang 1 ergibt **3,50 %**;
- der letzte reguläre Rang ergibt **0,30 %**;
- der Exponent **3,5** sorgt dafür, dass frühes Draft Capital deutlich stärker differenziert wird als spätes Draft Capital.

Ist ein Spieler in einem der beiden Signale **undrafted**, erhält genau diese Komponente **0,25 %**.

Damit kann ein Spieler beispielsweise in der Fantasy-Liga undrafted sein, aber über hohes reales NFL Draft Capital weiterhin ein relevantes Year-1-Salary erhalten. Die 65/35-Gewichtung dämpft diesen Effekt bewusst, verhindert ihn aber nicht künstlich.

#### Dynamische Fantasy-Draft-Poolgröße

`N_Fantasy` entspricht der konkreten Größe des jeweiligen Rookie Drafts.

Für 2026 gilt:

```text
N_Fantasy = 30
```

Die Regel ist nicht dauerhaft auf 30 festgeschrieben. Ändert sich künftig die Zahl der regulären Rookie-Draft-Slots, ändert sich auch `N_Fantasy`.

#### Dynamische NFL-Draft-Poolgröße

Für das NFL-Signal werden ausschließlich im realen NFL Draft ausgewählte Spieler der Positionen

- QB,
- RB,
- WR,
- TE

berücksichtigt.

Diese Spieler werden nach ihrem echten NFL Overall Pick sortiert und innerhalb dieses gefilterten Pools neu durchnummeriert. Die Salary-Kurve verwendet diesen **bereinigten NFL-Rang**, nicht unmittelbar den rohen NFL Overall Pick.

`N_NFL` ist deshalb die konkrete Zahl der in diesem NFL Draft ausgewählten QB/RB/WR/TE.

Für 2026 enthält der kanonische NFL Draft **80** solche Spieler:

```text
N_NFL = 80
```

Die Zahl 80 ist keine dauerhafte Konstante. Für jedes Draftjahr wird `N_NFL` aus dem realen Draft dieses Jahres neu bestimmt.

#### Verhältnis zum Year-1-Minimum

Das Draft-basierte Year-1-Modell liefert bereits das **vollständige Year-1-Salary inklusive des garantierten Year-1-Minimums**.

Das allgemeine Year-1-Minimum von **0,25 % des maßgeblichen Vorjahres-Salary-Caps** wird deshalb nicht noch einmal addiert.

Das ist notwendig, damit insbesondere gilt:

```text
Fantasy undrafted = 0,25 %
NFL undrafted     = 0,25 %

65 % × 0,25 % + 35 % × 0,25 %
= 0,25 %
```

Ein in beiden Signalen undrafted Rookie landet damit exakt beim garantierten Year-1-Minimum und nicht künstlich bei einem doppelten Base Salary.

### Rookie Contract: Year 1 bis Year 3 als geklärte Konzeptentscheidung

Das in Year 1 berechnete Draft-Salary bildet den **festen Dollar-Ausgangswert des dreijährigen Rookie Contracts**.

Die Contract-Eskalation lautet:

```text
Year 1 = 100 % × Year1Salary
Year 2 = 125 % × Year1Salary
Year 3 = 150 % × Year1Salary
```

Die Steigerungen sind ausdrücklich **nicht kumulativ**. Year 3 wird also nicht aus dem bereits erhöhten Year-2-Salary berechnet, sondern immer wieder aus demselben festen Year-1-Dollarvertrag.

Beispiel:

```text
Year 1: $10,0 Mio.
Year 2: $12,5 Mio.
Year 3: $15,0 Mio.
```

Damit gilt als direkte rechnerische Folge für den dreijährigen Rookie Contract:

```text
Gesamtkosten Year 1–3
= 3,75 × Year1Salary
```

Year 2 und Year 3 werden **nicht** anhand eines späteren Salary Caps, neuer Draftwerte oder der bis dahin erzielten NFL-Performance neu bepreist. Die festgelegten Faktoren 1,25 und 1,50 beziehen sich ausschließlich auf den bei Vertragsbeginn bestimmten Year-1-Dollarwert.

Die bereits bestehende allgemeine Minimum-Salary-Regel bleibt davon unberührt und weiterhin als ligaweite Untergrenze gültig; diese Contract-Regel verändert ausschließlich die Berechnungsbasis der Rookie-Salary-Eskalation.

### Übergang zum Performance-Salary ab Year 4

Der Rookie Contract endet nach Year 3.

Zu Beginn von **Year 4** liegen drei abgeschlossene NFL-Saisons vor. Ab diesem Zeitpunkt entfällt die Draft-/Rookie-Contract-Logik vollständig und das Salary wird erstmals nach dem normalen Drei-Saison-Performance-Modell aus den drei abgeschlossenen Seasons Year 1 bis Year 3 berechnet.

Damit gilt strukturell:

- **Year 1:** Draft-basiertes Rookie-Salary;
- **Year 2:** 125 % des festen Year-1-Salary;
- **Year 3:** 150 % des festen Year-1-Salary;
- **ab Year 4:** normales Performance-Salary aus drei abgeschlossenen NFL-Saisons.


---

## 2. Team Tenure für Dead Cap: geklärte Konzeptentscheidung

Die Dead-Cap-Höhe richtet sich nach der **ununterbrochenen Teamzugehörigkeit in League Seasons**.

Die Tenure wird bewusst einfach berechnet:

```text
Team Tenure
= aktuelle League Season − Acquisition Season
```

Dabei ist die `Acquisition Season` die League Season, in der die **aktuelle ununterbrochene Zugehörigkeit** zu diesem Fantasy-Team begonnen hat.

Die Staffel lautet:

| Team Tenure | Dead Cap beim Cut |
| ---: | ---: |
| 0 | 50 % |
| 1 | 30 % |
| 2 | 15 % |
| 3 oder mehr | 5 % |

### Beispiele

Ein Spieler wird in **Week 1 der Saison 2026** aufgenommen:

- in League Season 2026: Tenure **0**
- in League Season 2027: Tenure **1**
- in League Season 2028: Tenure **2**
- ab League Season 2029: Tenure **3+**

Ein Spieler wird erst in **Week 16 der Saison 2026** aufgenommen. Für die Dead-Cap-Staffel gilt trotzdem dieselbe Season-Logik:

- in League Season 2026: Tenure **0**
- in League Season 2027: Tenure **1**

Es wird bewusst **nicht** nach gehaltenen Wochen oder Spielen unterschieden.

### Offseason-Aufnahmen

Wird ein Spieler in der Offseason der League Season 2027 vor der Cap Deadline aufgenommen, gilt:

```text
2027 − 2027 = 0
```

Das bloße Passieren der Cap Deadline innerhalb derselben League Season erzeugt deshalb kein zusätzliches Tenure-Jahr.

### Unterbrechung und Re-Acquisition

Ein Cut oder Teamwechsel beendet die bisherige ununterbrochene Zugehörigkeit.

Kehrt der Spieler später zum selben Team zurück, beginnt eine neue Acquisition Season. Die frühere Teamhistorie wird für die Dead-Cap-Staffel nicht weitergezählt.

Damit misst die Staffel bewusst keine exakte Vertragsdauer in Tagen, sondern grobe Dynasty-Teamzugehörigkeit über aufeinanderfolgende League Seasons.

---

## 3. Dead Cap als Retained Salary

Der zentrale Konzeptgedanke lautet:

> **Dead Cap ist der Anteil des aktuellen Salaries, den ein früheres Team nach einem Cut bis zum nächsten Salary Check weiterbezahlt.**

Beispiel:

Ein Spieler besitzt ein aktuelles Salary von **20**.

Team A hat ihn noch keine abgeschlossene Saison gehalten und cuttet ihn deshalb mit **50 % Dead Cap**.

Dann gilt:

- Team A behält **10 Dead Cap**;
- der Spieler besitzt danach für ein neu aufnehmendes Team ein Salary von **10**;
- die gesamte ligaweite Salary-Belastung dieses Spielers bleibt **20**.

Das neue Team übernimmt also nur den noch nicht von früheren Teams getragenen Anteil des laufenden Vertrags.

---

## 4. Konzeptinvariante

Solange das für den Spieler geltende erfahrungsabhängige Minimum Salary nicht greift, gilt innerhalb eines laufenden Salary-Zyklus:

```text
aktuelles Salary des Spielers
+ Summe aller noch aktiven Dead-Cap-Anteile früherer Teams
= Salary des Spielers beim letzten Salary Check
```

Beispiel:

```text
Salary beim Salary Check: 20

Team A Dead Cap:       10
aktuelles Salary:      10
-------------------------
Gesamt:                20
```

Diese Invariante folgt aus der Retained-Salary-Logik und der vollständigen Salary-Reduktion: Kein Salary entsteht künstlich oder verschwindet. Der bestehende Vertrag wird lediglich zwischen dem aktuellen und früheren Teams verteilt.

**Ausnahme:** Würde die vollständige Salary-Reduktion das aktive Salary unter das für diesen Salary-Zyklus und den Spieler geltende erfahrungsabhängige Minimum Salary drücken, bleibt das aktive Salary auf diesem Floor. Der Dead Cap wird dadurch nicht nachträglich gekürzt. In diesem Floor-Fall darf die Summe aus aktivem Salary und Dead Caps deshalb oberhalb des ursprünglichen Salaries liegen.

---

## 5. Laufzeit des Dead Caps: geklärte Konzeptentscheidung

Dead Cap gilt ausschließlich innerhalb des Salary-Zyklus, in dem der jeweilige Cut stattfindet.

> **Die reguläre Salary-Überprüfung / Cap Deadline beendet den bisherigen Salary-Zyklus und resettet sämtliche bis dahin aktiven Dead-Cap-Anteile.**

Am Stichtag:

1. werden alle Dead-Cap-Anteile des alten Salary-Zyklus vollständig aufgelöst;
2. endet der bisherige aktive Salary-Anteil des Spielers;
3. wird das neue Salary anhand der dann geltenden Salary-Berechnung neu bestimmt;
4. beginnt ein neuer Salary-Zyklus ohne finanzielle Altlasten aus dem vorherigen Zyklus.

Dead Cap wird damit **nicht über mehrere Salary-Jahre fortgeschrieben**.

Die Salary-Überprüfung / Cap Deadline ist also nicht nur ein neuer Bewertungszeitpunkt für den Spieler, sondern zugleich ein harter Vertrags- und Dead-Cap-Reset.

---

## 6. Beispiel eines normalen Cuts

Ausgangslage:

- aktuelles Salary: **40**
- Spieler seit einer abgeschlossenen Saison beim Team
- Dead-Cap-Satz: **30 %**

Berechnung:

```text
40 × 30 % = 12 Dead Cap
```

Nach dem Cut:

- altes Team: **12 Dead Cap**
- Salary für ein neu aufnehmendes Team: **28**
- gesamte Salary-Belastung: weiterhin **40**

---

## 7. Beispiel eines langjährig gehaltenen Spielers

Ausgangslage:

- aktuelles Salary: **40**
- Spieler seit mindestens drei abgeschlossenen, ununterbrochenen Saisons beim Team
- Dead-Cap-Satz: **5 %**

Berechnung:

```text
40 × 5 % = 2 Dead Cap
```

Nach dem Cut:

- altes Team: **2 Dead Cap**
- Salary für ein neu aufnehmendes Team: **38**
- gesamte Salary-Belastung: weiterhin **40**

Ein langfristig gehaltener Vertrag lässt sich damit wesentlich sauberer beenden als ein kurzfristig aufgenommener Spieler.

---

## 8. Repeated Cuts: geklärte Konzeptentscheidung

Mehrere Cuts desselben Spielers innerhalb eines Salary-Zyklus sind **erlaubt**.

Jeder einzelne Cut erzeugt einen eigenen Dead-Cap-/Retained-Salary-Anteil. Dieser Anteil wird immer aus dem **zu diesem Zeitpunkt aktiven Salary** des Spielers berechnet.

Dadurch kann das aktive Salary eines Spielers nach mehreren Cuts weiter sinken. Das ist kein Salary-Verlust: Frühere Teams tragen die Differenz weiterhin als Dead Cap.

### Beispiel mit mehreren Teams

Ausgangslage:

- Salary beim Salary Check: **20**

Team A cuttet bei 0 abgeschlossenen Saisons:

- Team A übernimmt **10 Dead Cap**;
- aktives Salary sinkt auf **10**.

Team B nimmt den Spieler für 10 auf und cuttet ebenfalls bei 0 abgeschlossenen Saisons:

- Team B übernimmt zusätzlich **5 Dead Cap**;
- aktives Salary sinkt auf **5**.

Danach gilt:

```text
Team A Dead Cap: 10
Team B Dead Cap:  5
aktives Salary:   5
-------------------
Gesamt:           20
```

Die ursprüngliche Salary-Belastung bleibt vollständig erhalten. Sie wird lediglich auf mehrere Teams und den aktuellen Vertrag verteilt.

### Dasselbe Team kann mehrere Dead-Cap-Anteile besitzen

Auch eine spätere Wiederaufnahme durch dasselbe Team setzt diese Logik nicht zurück.

Beispiel:

- Salary beim Salary Check: **20**
- Team A cuttet den Spieler bei 50 % → **10 Dead Cap**, **10 aktives Salary**
- Team A nimmt ihn später für 10 wieder auf
- Team A cuttet ihn erneut bei 50 % des nun aktiven Salaries → weitere **5 Dead Cap**, **5 aktives Salary**

Team A trägt danach für denselben Spieler zwei getrennte Dead-Cap-Anteile:

```text
Team A Dead Cap aus Cut 1: 10
Team A Dead Cap aus Cut 2:  5
aktives Salary:              5
------------------------------
Gesamt:                     20
```

Ein Team kann somit innerhalb desselben Salary-Zyklus mehrere Dead-Cap-Anteile desselben Spielers gleichzeitig tragen.

### Keine zusätzliche Anti-Washing-Regel

Eine spezielle Regel gegen sogenanntes „Contract Washing“ ist nach aktuellem Konzeptstand nicht vorgesehen.

Der Grund:

Jede weitere Reduktion des aktiven Salaries wird durch eine reale zusätzliche Dead-Cap-Belastung des cuttenden Teams finanziert. Ein niedrigeres aktives Salary entsteht daher nicht kostenlos.

Ohne einen eingreifenden Salary-Floor ergibt sich bei wiederholten 50-%-Cuts beispielsweise:

```text
20 → 10 → 5 → 2,5 → 1,25 → ...
```

Sobald das für den Spieler in diesem Salary-Zyklus geltende erfahrungsabhängige Minimum Salary erreicht ist, sinkt das aktive Salary nicht weiter.

Während das aktive Salary sinkt, wächst die Summe der Dead-Cap-Anteile entsprechend an.

Solange das anwendbare erfahrungsabhängige Minimum Salary nicht greift, bleibt die zentrale Invariante erhalten:

```text
aktuelles Salary
+ Summe aller aktiven Dead-Cap-Anteile
= Salary beim letzten Salary Check
```

Greift der Salary-Floor, bleibt das aktive Salary stattdessen auf dem Minimum und die Gesamtbelastung darf entsprechend höher liegen.

Eine absichtliche Absprache mehrerer Teams zum Verschieben von Cap wäre gegebenenfalls eine allgemeine Fair-Play-/Collusion-Frage, aber kein Grund, die normale Vertragslogik technisch zu verändern.

## 9. Vollständige Salary-Reduktion: geklärte Konzeptentscheidung

Der bei einem Cut entstehende Dead Cap wird **vollständig vom zu diesem Zeitpunkt aktiven Salary des Spielers abgezogen**.

Beispiel:

- aktives Salary vor dem Cut: **20**
- Dead-Cap-Satz: **50 %**
- neuer Dead Cap: **10**
- verbleibendes aktives Salary: **10**

Damit gilt:

```text
Dead Cap:       10
aktives Salary: 10
-----------------
Gesamt:         20
```

Der Cut verteilt damit den bestehenden Vertrag zwischen dem cuttenden Team und dem verbleibenden aktiven Salary. Es entsteht keine zusätzliche ligaweite Cap-Belastung.

### Keine teilweise Reduktion

Eine zuvor diskutierte Variante hätte das aktive Salary nur um einen Teil des Dead Caps reduziert.

Beispiel:

- Salary: **20**
- Dead Cap: **10**
- aktives Salary würde nur auf **15** sinken

Dann entstünde:

```text
Dead Cap:       10
aktives Salary: 15
-----------------
Gesamt:         25
```

Diese Variante wird im aktuellen Konzept **nicht weiterverfolgt**, weil dadurch zusätzliches Salary entstehen würde. Dead Cap wäre dann nicht mehr nur Retained Salary, sondern gleichzeitig eine zusätzliche Cut-Strafe.

Wenn die Liga später bewusst eine zusätzliche Cut-Strafe einführen möchte, soll diese als **eigene Mechanik** diskutiert werden. Die Salary-Reduktion selbst bleibt vollständig und transparent.

### Konsequenz für die Vertragslogik

Bei jedem Cut gilt:

```text
neuer Dead Cap
= aktuelles Salary vor dem Cut × Dead-Cap-Satz

neues aktives Salary
= max(anwendbares Minimum Salary, aktuelles Salary vor dem Cut − neuer Dead Cap)
```

Solange das anwendbare Minimum Salary nicht greift, bleibt damit die zentrale Invariante innerhalb des Salary-Zyklus erhalten:

```text
aktuelles Salary
+ Summe aller aktiven Dead-Cap-Anteile
= Salary beim letzten Salary Check
```

Greift der Salary-Floor, wird das aktive Salary nicht weiter abgesenkt; der berechnete Dead Cap bleibt bestehen.

## 10. Kein mehrjähriger Dead Cap: geklärte Konzeptentscheidung

Dead-Cap-Anteile werden nicht über den nächsten regulären Salary Check / die Cap Deadline hinaus übertragen.

Die zuvor diskutierte Mehrjahresvariante wird im aktuellen Konzept nicht weiterverfolgt.

Der Hauptgrund ist die jährliche Neubewertung des Spielers: Ein alter Dead-Cap-Anteil soll nicht mit einem neu berechneten Salary vermischt werden, das aufgrund gestiegener oder gesunkener Leistung einen völlig anderen Wert haben kann.

Beispiel:

- alter Salary-Zyklus: Spieler-Salary **30**, davon **15 Dead Cap**
- neuer Salary Check: neu berechnetes Salary **12**

Mit einem mehrjährigen Dead Cap wäre unklar, ob die alten 15 unverändert weiterlaufen, begrenzt, proportional reduziert oder mit dem neuen Salary verrechnet werden müssten.

Durch den Reset ist die Behandlung eindeutig:

```text
vor Salary Check / Cap Deadline:
15 Dead Cap + 15 aktives Salary = 30

am Reset:
alte Dead Caps = 0
alter aktiver Salary-Anteil = 0

neuer Salary-Zyklus:
neu berechnetes Salary = 12
```

### Strategischer Effekt vor der Cap Deadline

Die Regel soll bewusst dazu führen, dass Cuts **vor** der Cap Deadline noch in den laufenden Cap einzahlen.

Ein Manager, der mehrere teure oder nicht mehr gewünschte Spieler bis kurz vor die Deadline hält, kann sie deshalb nicht kostenlos aus dem Kader entfernen. Jeder Cut erzeugt bis zum Reset Dead Cap.

Dadurch entstehen zwei echte Handlungsalternativen:

- früher cutten und den Dead Cap im laufenden Zyklus tragen;
- rechtzeitig aktiv versuchen, den Spieler zu traden und so einen Cut samt Dead Cap möglichst zu vermeiden.

Das erhöht den Wert von aktivem Roster- und Trade-Management vor der Cap Deadline.

Als konkretes Diskussionsbeispiel wurde Flo genannt: Unter diesem Modell hätte er in der aktuellen Saison voraussichtlich entweder mehr Spieler cutten und die entsprechende Dead-Cap-Belastung tragen oder früher versuchen müssen, diese Spieler aktiv zu traden.

## 11. Minimum Salary als erfahrungsabhängiges Base Salary: geklärte Konzeptentscheidung

Salary und Dead Cap werden in **vollen Dollarbeträgen ohne Dezimalstellen** geführt.

### Rundung

Prozentuale Dead-Cap- und Minimum-Salary-Berechnungen werden kaufmännisch auf den nächsten vollen Dollar gerundet.

Bei exakt 50 Cent wird auf den nächsten vollen Dollar aufgerundet.

### Staffel nach NFL-Erfahrung

Das Minimum Salary richtet sich nach `Player.Year` und damit nach der NFL-Erfahrung des Spielers. Die Fantasy-Team-Tenure spielt für die Höhe des Minimum Salaries keine Rolle; sie wird ausschließlich für die Dead-Cap-Staffel verwendet.

| Player.Year | Minimum Salary |
| ---: | ---: |
| 1 | 0,25 % des maßgeblichen Vorjahres-Salary-Caps |
| 2 | 0,30 % |
| 3 | 0,35 % |
| 4 | 0,40 % |
| 5–7 | 0,45 % |
| 8+ | 0,50 % |

Damit steigt das Base Minimum in gleichmäßigen Schritten von 0,25 % auf 0,50 % des maßgeblichen Salary Caps.

### Maßgebliche Cap-Basis: Vorjahres-Salary-Cap

Das Minimum Salary eines Salary-Zyklus wird aus dem **kanonisch berechneten Salary Cap des vorherigen Salary-Zyklus** abgeleitet.

Die Berechnungsrichtung lautet:

```text
Salary Cap des Vorjahres
→ Minimum Salaries des aktuellen Zyklus
→ aktuelle Player Salaries
→ aktuelles Salary Cap
```

Dadurch entsteht innerhalb desselben Salary-Zyklus keine Zirkularität zwischen Minimum Salary und Salary Cap. Das aktuelle Salary Cap wird weiterhin erst aus den bereits feststehenden aktuellen Player Salaries berechnet.

Beispiel bei einem Vorjahres-Cap von **$434.255.984**:

| Player.Year | Anteil | Base Minimum Salary |
| ---: | ---: | ---: |
| 1 | 0,25 % | $1.085.640 |
| 2 | 0,30 % | $1.302.768 |
| 3 | 0,35 % | $1.519.896 |
| 4 | 0,40 % | $1.737.024 |
| 5–7 | 0,45 % | $1.954.152 |
| 8+ | 0,50 % | $2.171.280 |

### Additives Base Salary statt nachträglichem Floor

Das Minimum Salary ist nicht nur eine Untergrenze, die nachträglich mit `max(...)` auf das normale Salary angewendet wird. Es ist ein **echtes Base Salary**, auf dem der variable Salary-Anteil aufbaut.

Für die normale Performance-Skalierung gilt deshalb konzeptionell:

```text
Player Salary
= Base Minimum Salary nach Player.Year
+ leistungsbasierter Salary-Anteil
```

Die bisherige Performance-Skala bleibt als variabler Anteil erhalten:

```text
0 Performance-Punkte  → $0 variabler Anteil
20 Performance-Punkte → $50.000.000 variabler Anteil
```

Damit gilt insgesamt:

```text
0 Performance-Punkte
→ Base Minimum Salary

20 Performance-Punkte
→ Base Minimum Salary + $50.000.000
```

Die bestehende quadratische Performance-Kurve wird dadurch nicht gestaucht oder neu skaliert, sondern lediglich um das jeweilige Base Minimum nach oben verschoben.

Diese Konstruktion verhindert außerdem, dass ein größerer Bereich unterschiedlicher Low-End-Performance durch ein nachträgliches `max(Minimum, Performance Salary)` auf exakt denselben Salary-Wert fällt. Nur ein Spieler ohne zusätzlichen variablen Salary-Anteil liegt exakt auf seinem Base Minimum.

### Verhältnis zum Rookie-/Young-Player-Modell

Das erfahrungsabhängige Base Minimum ist die garantierte unterste Salary-Schicht für alle Spieler.

Für das normale Performance-Modell wird dieses Base Minimum additiv mit dem leistungsbasierten Salary-Anteil kombiniert.

**Rookie Year 1 ist eine explizite Sonderbehandlung:** Die Draft-basierte Year-1-Formel enthält das Year-1-Minimum von 0,25 % bereits in ihren Draft-Komponenten und liefert direkt das vollständige Year-1-Salary. Das Minimum wird deshalb bei Rookies in Year 1 nicht ein zweites Mal addiert.

**Rookie Year 2 und Year 3 bleiben ebenfalls innerhalb des festen Rookie Contracts:** Die Salary-Werte werden als 125 % beziehungsweise 150 % des ursprünglichen Year-1-Dollarvertrags berechnet. Sie werden weder aus aktueller Performance noch aus einem späteren Salary Cap neu hergeleitet.

Die allgemeine Minimum-Salary-Regel bleibt parallel als ligaweite Untergrenze bestehen. Ab Year 4 endet der Rookie Contract; dann greift erstmals das normale Drei-Saison-Performance-Modell mit dem für Year 4 geltenden Base Minimum.

### Dead-Cap-Floor innerhalb eines Salary-Zyklus

Das beim Salary Check festgelegte erfahrungsabhängige Minimum bleibt während des laufenden Salary-Zyklus die Untergrenze des aktiven Salaries.

Bei einem Cut gilt:

```text
neuer Dead Cap
= aktuelles Salary vor dem Cut × Dead-Cap-Satz

neues aktives Salary
= max(anwendbares Minimum Salary, aktuelles Salary vor dem Cut − neuer Dead Cap)
```

Der Dead Cap wird nicht nachträglich reduziert, nur weil der Floor greift.

Dadurch darf im Floor-Fall gelten:

```text
aktives Salary + Summe aller Dead Caps
> Salary vor dem ersten Cut
```

Das ist eine bewusste Ausnahme von der sonst geltenden Retained-Salary-Invariante: Das zusätzliche Salary entsteht ausschließlich durch den garantierten Minimum Contract.

### Retroaktive Reproduzierbarkeit

Salary und Salary Cap werden historisch nach den jeweils aktuell gültigen Regeln reproduzierbar berechnet.

Wenn eine Salary-Regel rückwirkend geändert und die Historie neu berechnet wird, wird deshalb auch das kanonische Salary Cap der betroffenen Vorjahre mit den neuen Regeln neu bestimmt.

Die Minimum-Salary-Kette wird anschließend ebenfalls neu berechnet:

```text
historischer Vorjahres-Cap
→ Minimum des Folgejahres
→ Salary des Folgejahres
→ Cap des Folgejahres
→ nächstes Minimum
→ ...
```

Eine Regeländerung wirkt damit konsistent auf spätere Minimum Salaries, obwohl deren Basis jeweils das Vorjahres-Cap ist.

Für die erste Saison, ab der dieses Minimum-Salary-System angewendet wird, wird technisch ein definierter historischer Anchor beziehungsweise Startwert benötigt. Die Wahl und technische Speicherung dieses Anchors ist eine Implementierungsfrage und ändert die fachliche Regel nicht.

---

## 12. Team-Tenure-Regel: Zusammenfassung

Für die Dead-Cap-Staffel gilt:

```text
Team Tenure = aktuelle League Season − Acquisition Season
```

- dieselbe League Season = Jahr 0;
- nächste League Season = Jahr 1;
- danach Jahr 2 und Jahr 3+;
- Week 1 und Week 16 derselben Acquisition Season werden gleich behandelt;
- eine Offseason-Aufnahme vor der Cap Deadline zählt weiterhin als Jahr 0, wenn sie bereits der aktuellen League Season zugeordnet ist;
- Cut oder Teamwechsel unterbricht die Zugehörigkeit;
- eine spätere Re-Acquisition startet mit einer neuen Acquisition Season wieder bei Jahr 0.

---

## 13. Aktueller Konzeptstand

### Grundannahmen

- Salary basiert grundsätzlich auf einem Drei-Jahres-Horizont.
- Rookies erhalten in Year 1 ein vollständig Draft-basiertes Salary.
- Year 2 beträgt 125 % und Year 3 150 % des festen Year-1-Dollarvertrags; die Steigerungen sind nicht kumulativ und verwenden keine Performance-Neubewertung.
- Ab Year 4 endet der Rookie Contract und es gilt erstmals das vollständige Drei-Saison-Performance-Modell.
- Team Tenure wird als `aktuelle League Season − Acquisition Season` der ununterbrochenen Teamzugehörigkeit berechnet.
- Die Dead-Cap-Staffel lautet **50 % / 30 % / 15 % / 5 %** für Tenure 0 / 1 / 2 / 3+.
- Dead Cap bezieht sich auf das aktuelle Salary.
- Dead Cap gilt bis zum nächsten regulären Salary Check.

### Geklärte Rookie-Year-1-Entscheidungen

- Year 1 verwendet zwei Draft-Signale: Fantasy Rookie Draft und realen NFL Draft.
- Die Gewichtung lautet **65 % Fantasy Draft / 35 % NFL Draft**.
- Beide Signale verwenden dieselbe Kurve von **3,50 %** auf **0,30 %** mit Exponent **3,5**.
- Undrafted in einem Signal entspricht **0,25 %** für diese Komponente.
- `N_Fantasy` ist die konkrete Größe des jeweiligen Fantasy Rookie Drafts; 2026 gilt **30**.
- `N_NFL` ist die konkrete Zahl der im realen NFL Draft ausgewählten **QB/RB/WR/TE**; 2026 gilt **80**.
- NFL-Spieler werden innerhalb dieses Positionspools nach Overall Pick neu gerankt; dieser bereinigte Rang fließt in die Kurve ein.
- Das resultierende Year-1-Salary basiert auf dem maßgeblichen Vorjahres-Salary-Cap.
- Die Draft-basierte Year-1-Formel enthält das garantierte Year-1-Minimum bereits. Das 0,25-%-Minimum wird nicht zusätzlich addiert.
- Ein in der Fantasy-Liga undrafted Rookie darf aufgrund starken NFL Draft Capitals teurer als ein spät gedrafteter Fantasy-Rookie sein. Die 65/35-Gewichtung begrenzt den Einfluss des NFL-Signals, ohne eine künstliche Reihenfolge zu erzwingen.

### Geklärte Rookie-Contract-Entscheidungen für Year 2 und Year 3

- Das bei Vertragsbeginn bestimmte Year-1-Salary ist der feste Dollar-Ausgangswert für den gesamten dreijährigen Rookie Contract.
- Year 2 = **125 % des Year-1-Salary**.
- Year 3 = **150 % des Year-1-Salary**.
- Die Steigerungen sind **nicht kumulativ**; beide Faktoren werden direkt auf Year 1 angewendet.
- Year 2 und Year 3 werden nicht anhand späterer Salary Caps, neuer Draftwerte oder NFL-Performance neu bepreist.
- Die rechnerischen Gesamtkosten des dreijährigen Rookie Contracts betragen **3,75 × Year1Salary**.
- Die bestehende allgemeine Minimum-Salary-Regel bleibt davon unberührt.
- Ab Year 4 endet der Rookie Contract; das Salary basiert dann vollständig auf den drei abgeschlossenen NFL-Saisons Year 1 bis Year 3.

### Geklärte allgemeine Konzeptentscheidungen

- Dead Cap wird vollständig vom aktiven Salary des Spielers abgezogen.
- Das frühere Team übernimmt diesen Anteil als Retained Salary.
- Das neue Team zahlt nur den verbleibenden aktiven Salary-Anteil.
- Innerhalb eines Salary-Zyklus bleibt die ursprüngliche Gesamtbelastung erhalten, solange das anwendbare Minimum Salary nicht greift.
- Salary und Dead Cap werden in ganzen Dollarbeträgen ohne Dezimalstellen geführt.
- Das Minimum Salary ist ein erfahrungsabhängiges Base Salary nach `Player.Year`.
- Die Staffel beträgt **0,25 % / 0,30 % / 0,35 % / 0,40 % / 0,45 % / 0,50 %** des maßgeblichen Vorjahres-Salary-Caps für Year 1 / 2 / 3 / 4 / 5–7 / 8+.
- Für das normale Performance-Modell wird das Base Minimum additiv mit dem variablen Performance-Salary-Anteil kombiniert.
- Das Minimum eines Zyklus basiert auf dem kanonisch berechneten Salary Cap des vorherigen Zyklus.
- Greift der Floor nach einem Cut, darf aktives Salary plus Dead Caps oberhalb des ursprünglichen Salaries liegen.
- Die reguläre Salary-Überprüfung / Cap Deadline resettet sämtliche alten Dead-Cap-Anteile.
- Dead Cap wird nicht über mehrere Salary-Zyklen fortgeführt.
- Das Salary wird danach unabhängig vom alten Zyklus neu berechnet.

### Nächste fachliche Anschlussfrage

- **Draft-Pick-Kostenprognose:** Auf Basis des nun vollständig definierten dreijährigen Rookie Contracts soll als Nächstes geprüft werden, wie erwartete Salary-Kosten zukünftiger Rookie-Draftpicks vor dem Draft sinnvoll prognostiziert werden können.

### Technische Anschlussfrage

- Für die erste historische Saison des neuen Minimum-Salary-Systems muss ein reproduzierbarer Anchor-/Startwert für das Vorjahres-Cap festgelegt werden. Das ist eine Umsetzungsfrage, keine offene Grundsatzentscheidung des Salary-Modells.


---

## 14. Pflege dieses Dokuments

Dieses Dokument ist ein **lebendes Konzeptpapier**.

Bei weiteren materiellen Diskussionen zum Salary-/Dead-Cap-Modell soll:

1. der aktuelle Konzeptstand hier fortgeschrieben werden;
2. klar zwischen beschlossenen Regeln, bevorzugten Varianten und offenen Fragen unterschieden werden;
3. eine offene Frage erst dann aus dem offenen Bereich entfernt werden, wenn die Liga dazu tatsächlich eine Entscheidung getroffen hat;
4. keine technische Implementierung automatisch als Ligabeschluss interpretiert werden;
5. das Dokument weiterhin so formuliert bleiben, dass es direkt mit Ligamitgliedern geteilt werden kann.

Die spätere technische Umsetzung in der App ist ein eigener Schritt und nicht Teil dieses Konzeptdokuments.
