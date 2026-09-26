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

Solange das League Minimum Salary nicht greift, gilt innerhalb eines laufenden Salary-Zyklus:

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

**Ausnahme:** Würde die vollständige Salary-Reduktion das aktive Salary unter das gültige League Minimum Salary drücken, bleibt das aktive Salary auf diesem Floor. Der Dead Cap wird dadurch nicht nachträglich gekürzt. In diesem Floor-Fall darf die Summe aus aktivem Salary und Dead Caps deshalb oberhalb des ursprünglichen Salaries liegen.

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

Sobald das gültige League Minimum Salary erreicht ist, sinkt das aktive Salary nicht weiter.

Während das aktive Salary sinkt, wächst die Summe der Dead-Cap-Anteile entsprechend an.

Solange das League Minimum Salary nicht greift, bleibt die zentrale Invariante erhalten:

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
= max(League Minimum Salary, aktuelles Salary vor dem Cut − neuer Dead Cap)
```

Solange das League Minimum Salary nicht greift, bleibt damit die zentrale Invariante innerhalb des Salary-Zyklus erhalten:

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

## 11. Rundung und Salary-Floor: teilweise geklärte Konzeptentscheidung

Salary und Dead Cap werden in **vollen Dollarbeträgen ohne Dezimalstellen** geführt.

### Rundung

Prozentuale Dead-Cap-Berechnungen werden kaufmännisch auf den nächsten vollen Dollar gerundet.

Beispiel:

```text
$1.234.567 × 30 % = $370.370,10
Dead Cap = $370.370
```

Bei exakt 50 Cent wird auf den nächsten vollen Dollar aufgerundet.

### Harter Minimum-Salary-Floor

Ein aktiver Spieler darf niemals unter das gültige **League Minimum Salary** fallen.

Der Dead Cap wird zunächst normal aus dem aktiven Salary vor dem Cut und dem geltenden Prozentsatz berechnet. Würde die anschließende vollständige Reduktion das aktive Salary unter den Floor drücken, bleibt das aktive Salary stattdessen beim League Minimum Salary.

Beispiel mit einem angenommenen Minimum Salary von **$250.000**:

```text
aktives Salary vor Cut: $300.000
Dead-Cap-Satz:          50 %
Dead Cap:               $150.000
rechnerischer Rest:     $150.000
Salary-Floor:           $250.000

neues aktives Salary:   $250.000
Dead Cap:               $150.000
Gesamtbelastung:        $400.000
```

Der Floor ist damit eine bewusste Ausnahme von der sonst geltenden Salary-Invariante. Er verhindert, dass ein aktiver Spieler durch wiederholte Cuts unter das ligaweit gültige Mindestgehalt fällt.

### Aktueller Referenzwert, aber noch keine finale Fixierung

Im bestehenden Salary-Mapping wird derzeit ein Minimum von **$250.000** verwendet.

Für dieses Konzept ist damit geklärt, **dass es einen harten Minimum-Salary-Floor geben muss**. Noch nicht entschieden ist, ob **$250.000 dauerhaft als fixer Betrag** die richtige Regel ist oder ob das Minimum anders bestimmt werden sollte.

Diese konkrete Minimum-Salary-Frage bleibt der nächste Diskussionspunkt.

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
- Rookies erhalten zunächst ein Draft-basiertes Salary.
- In Jahr 2 und 3 wird schrittweise echte NFL-Leistung ergänzt.
- Ab Jahr 4 gilt das vollständige Drei-Saison-Salary-Modell.
- Team Tenure wird als `aktuelle League Season − Acquisition Season` der ununterbrochenen Teamzugehörigkeit berechnet.
- Die Dead-Cap-Staffel lautet **50 % / 30 % / 15 % / 5 %** für Tenure 0 / 1 / 2 / 3+.
- Dead Cap bezieht sich auf das aktuelle Salary.
- Dead Cap gilt bis zum nächsten regulären Salary Check.

### Geklärte Konzeptentscheidungen

- Dead Cap wird vollständig vom aktiven Salary des Spielers abgezogen.
- Das frühere Team übernimmt diesen Anteil als Retained Salary.
- Das neue Team zahlt nur den verbleibenden aktiven Salary-Anteil.
- Innerhalb eines Salary-Zyklus bleibt die ursprüngliche Gesamtbelastung erhalten, solange der Minimum-Salary-Floor nicht greift.
- Salary und Dead Cap werden in ganzen Dollarbeträgen ohne Dezimalstellen geführt.
- Ein aktiver Spieler darf niemals unter das gültige League Minimum Salary fallen.
- Greift der Floor, darf aktives Salary plus Dead Caps oberhalb des ursprünglichen Salaries liegen.

### Geklärte weitere Konzeptentscheidung

- Die reguläre Salary-Überprüfung / Cap Deadline resettet sämtliche alten Dead-Cap-Anteile.
- Dead Cap wird nicht über mehrere Salary-Zyklen fortgeführt.
- Das Salary wird danach unabhängig vom alten Zyklus neu berechnet.

### Noch offen

- Ob der aktuell verwendete Minimum-Salary-Wert von **$250.000** dauerhaft als fixer League-Wert beibehalten oder anders bestimmt werden soll.

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
