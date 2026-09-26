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

### Rookie-Salary

Bei einem Rookie existiert noch keine ausreichende NFL-Leistungshistorie.

Sein initiales Salary soll deshalb anteilig aus zwei Draft-Komponenten entstehen:

- seiner realen NFL Draft Position;
- seiner Draft Position in unserer Fantasy-Liga.

Die genaue Gewichtung dieser beiden Komponenten ist Teil des Salary-Modells und nicht Gegenstand dieses Dead-Cap-Konzepts.

### Übergang vom Rookie zum Veteranen

Ab dem zweiten Jahr fließt zusätzlich die tatsächliche Leistung der bereits abgeschlossenen NFL-Saisons in das Salary ein.

Der Übergang ist damit gleitend:

- **Jahr 1:** Draft-basierte Rookie-Basis;
- **Jahr 2:** Draft-Basis plus Leistung aus einer abgeschlossenen Saison;
- **Jahr 3:** Draft-Basis plus Leistung aus zwei abgeschlossenen Saisons;
- **ab Jahr 4:** vollständiges normales Salary aus den letzten drei abgeschlossenen Saisons.

Damit erreicht ein Spieler nach drei abgeschlossenen Saisons vollständig das normale Veteranen-Salary-Modell.

---

## 2. Haltedauer für Dead Cap

Die Dead-Cap-Höhe richtet sich nach der Zahl der **aufeinanderfolgenden, ununterbrochenen abgeschlossenen Saisons**, die ein Spieler bei demselben Fantasy-Team gehalten wurde.

Aktueller Vorschlag:

| Abgeschlossene ununterbrochene Saisons beim Team | Dead Cap beim Cut |
| ---: | ---: |
| 0 | 50 % |
| 1 | 30 % |
| 2 | 15 % |
| 3 oder mehr | 5 % |

### Interpretation

**0 Saisons** bedeutet zum Beispiel:

Ein Team nimmt einen Spieler während eines laufenden Salary-Zyklus auf und cuttet ihn wieder, bevor mit ihm eine komplette Saison abgeschlossen wurde.

Die Haltedauer wird durch einen Teamwechsel unterbrochen. Ein neues Team beginnt für seine eigene spätere Dead-Cap-Berechnung wieder bei seiner eigenen Haltedauer.

Die Staffel soll zwei Dinge verbinden:

- kurzfristig aufgenommene Spieler sind relativ teuer wieder abzugeben;
- langfristig gehaltene Spieler können nach mehreren Jahren mit nur kleiner Restbelastung abgegeben werden.

Auch hier entsteht damit ein Drei-Jahres-Lifecycle: Nach drei gehaltenen Saisons erreicht der Spieler die niedrigste Dead-Cap-Stufe.

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

## 4. Aktuell bevorzugte Invariante

Innerhalb eines laufenden Salary-Zyklus soll nach aktuellem Diskussionsstand grundsätzlich gelten:

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

Diese Invariante ist aktuell die bevorzugte Richtung, weil dadurch kein Salary künstlich entsteht oder verschwindet. Der bestehende Vertrag wird lediglich zwischen dem aktuellen und früheren Teams verteilt.

---

## 5. Laufzeit des Dead Caps

Der Dead Cap gilt nur innerhalb des aktuellen Salary-Zyklus.

Aktuelle bevorzugte Richtung:

> **Beim nächsten regulären Salary Cut / Salary Check endet der bisherige Vertrag vollständig.**

Dann:

1. werden die alten Dead-Cap-Anteile aufgelöst;
2. wird das neue Salary des Spielers anhand der dann geltenden Salary-Berechnung neu bestimmt;
3. beginnt ein neuer Salary-Zyklus ohne mitgeschleppte Altlasten aus dem vorherigen Salary-Zyklus.

Das verhindert insbesondere komplizierte Wechselwirkungen zwischen einem alten Dead Cap und einem neuen Salary, das aufgrund der inzwischen geänderten Spielerleistung deutlich höher oder niedriger sein kann.

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

Bei wiederholten 50-%-Cuts ergibt sich beispielsweise:

```text
20 → 10 → 5 → 2,5 → 1,25 → ...
```

Während das aktive Salary sinkt, wächst die Summe der Dead-Cap-Anteile entsprechend an.

Die zentrale Invariante bleibt erhalten:

```text
aktuelles Salary
+ Summe aller aktiven Dead-Cap-Anteile
= Salary beim letzten Salary Check
```

Eine absichtliche Absprache mehrerer Teams zum Verschieben von Cap wäre gegebenenfalls eine allgemeine Fair-Play-/Collusion-Frage, aber kein Grund, die normale Vertragslogik technisch zu verändern.

## 9. Offene Alternative: Salary nur teilweise reduzieren

Eine diskutierte Alternative wäre, das aktive Salary des Spielers nicht um den vollständigen Dead Cap zu reduzieren, sondern beispielsweise nur um die Hälfte des Dead Caps.

Beispiel:

- Salary: **20**
- Dead Cap: **10**
- aktives Salary würde nur auf **15** sinken.

Dann entstünde jedoch:

```text
Dead Cap:       10
aktives Salary: 15
-----------------
Gesamt:         25
```

Damit wäre Dead Cap nicht mehr nur eine Aufteilung des bestehenden Vertrags, sondern zusätzlich eine echte Cut-Strafe, durch die neue Cap-Belastung entsteht.

Diese Variante ist **nicht verworfen**, aber aktuell weniger elegant als die vollständige Retained-Salary-Logik.

Falls eine zusätzliche Cut-Strafe gewünscht ist, sollte geprüft werden, ob sie besser als eigene Mechanik modelliert wird, statt die Vertragsinvariante aufzubrechen.

---

## 10. Offene Alternative: Dead Cap über mehrere Salary-Jahre

Eine weitere denkbare Variante wäre, Dead-Cap-Anteile über mehrere Jahre fortzuführen.

Aktuell spricht gegen diese Variante vor allem die Interaktion mit neu berechnetem Salary.

Beispiel:

- alter Dead Cap aus dem vorherigen Salary-Zyklus: **15**;
- neues Salary aufgrund eines Leistungseinbruchs: **12**.

Dann entstehen unmittelbar Folgefragen:

- darf alter Dead Cap größer als das neue Salary sein?
- bleibt der alte absolute Betrag bestehen?
- wird er proportional an das neue Salary angepasst?
- welche Entlastung erhält das aktuelle Team?
- wie werden mehrere frühere Teams behandelt?

Aktuelle Tendenz deshalb:

> **Dead Cap endet am nächsten Salary Check und wird nicht über mehrere Salary-Zyklen mitgenommen.**

Diese Entscheidung ist noch nicht final, ist derzeit aber die deutlich einfachere und nachvollziehbarere Variante.

---

## 11. Aktueller Konzeptstand

### Grundannahmen

- Salary basiert grundsätzlich auf einem Drei-Jahres-Horizont.
- Rookies erhalten zunächst ein Draft-basiertes Salary.
- In Jahr 2 und 3 wird schrittweise echte NFL-Leistung ergänzt.
- Ab Jahr 4 gilt das vollständige Drei-Saison-Salary-Modell.
- Dead Cap basiert auf ununterbrochenen abgeschlossenen Saisons beim jeweiligen Fantasy-Team.
- Vorgeschlagene Staffel: **50 % / 30 % / 15 % / 5 %**.
- Dead Cap bezieht sich auf das aktuelle Salary.
- Dead Cap gilt bis zum nächsten regulären Salary Check.

### Aktuell bevorzugte Richtung

- Dead Cap wird vollständig vom aktiven Salary des Spielers abgezogen.
- Das frühere Team übernimmt diesen Anteil als Retained Salary.
- Das neue Team zahlt nur den verbleibenden aktiven Salary-Anteil.
- Innerhalb eines Salary-Zyklus bleibt die ursprüngliche Gesamtbelastung erhalten.
- Beim nächsten Salary Check werden alle alten Retained-Salary-Anteile aufgelöst und das Salary vollständig neu berechnet.

### Noch offen

- vollständige versus nur teilweise Salary-Reduktion;
- Dead Cap nur bis zum nächsten Salary Check versus mehrjährige Übernahme;
- Details zu Rundung und Mindest-Salary;
- genaue Stichtagsdefinition für „abgeschlossene Saison“ und Salary Check.

---

## 12. Pflege dieses Dokuments

Dieses Dokument ist ein **lebendes Konzeptpapier**.

Bei weiteren materiellen Diskussionen zum Salary-/Dead-Cap-Modell soll:

1. der aktuelle Konzeptstand hier fortgeschrieben werden;
2. klar zwischen beschlossenen Regeln, bevorzugten Varianten und offenen Fragen unterschieden werden;
3. eine offene Frage erst dann aus dem offenen Bereich entfernt werden, wenn die Liga dazu tatsächlich eine Entscheidung getroffen hat;
4. keine technische Implementierung automatisch als Ligabeschluss interpretiert werden;
5. das Dokument weiterhin so formuliert bleiben, dass es direkt mit Ligamitgliedern geteilt werden kann.

Die spätere technische Umsetzung in der App ist ein eigener Schritt und nicht Teil dieses Konzeptdokuments.
