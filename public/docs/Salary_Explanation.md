# 🏈 Wie berechnet sich das Spieler-Salary?

Das Salary eines Spielers basiert ausschließlich auf seiner **Fantasy-Leistung**.
Es gibt **keinen Bonus für Namen, Draftstatus oder Beliebtheit** – nur produzierte Punkte zählen.

Dabei gibt es zwei Werte:

- **Salary** → basiert auf den letzten **3 abgeschlossenen Saisons**
- **SalaryProjected** → berücksichtigt **zusätzlich die aktuelle Saison**

---

## 1️⃣ Wie wird die Saisonleistung bewertet?

Für jede Saison wird ein **Leistungswert** berechnet, der zwei Dinge kombiniert:

- **Wie viele Punkte ein Spieler im Verhältnis zu allen möglichen Spielen erzielt hat**  
  → misst **Konstanz**

- **Wie viele Punkte er im Schnitt gemacht hat, wenn er tatsächlich gespielt hat**  
  → misst **reine Performance**

Diese beiden Werte werden **gewichtet kombiniert**.  
So werden sowohl **Verlässlichkeit** als auch **Explosivität** berücksichtigt.

Das Ergebnis ist ein **Fantasy-Leistungswert pro Saison**.

---

## 2️⃣ Warum fallen Spieler nicht komplett ab? (Floor-System)

Um extreme Ausreißer zu verhindern, greift ein **Schutzmechanismus**:

1. Von den letzten **3 Jahren wird das beste Jahr ermittelt**.
2. Dieses beste Jahr legt einen **Mindestwert („Floor“) fest**.
3. Kein anderes Jahr darf **unter einen bestimmten Prozentsatz dieses besten Jahres fallen**.

Je **aktueller das beste Jahr ist**, desto **stärker wirkt dieser Schutz**.

Das verhindert, dass ein Spieler wegen:

- einer **Verletzungssaison**
- oder eines **einzelnen schlechten Jahres**

komplett im Wert einbricht.

---

## 3️⃣ Wie entsteht daraus das Salary?

Nachdem die drei Jahre bereinigt wurden:

1. Es wird der **Durchschnitt dieser 3 Leistungswerte** gebildet.
2. Dieser Wert wird auf ein **Salary zwischen 0 und 50 Mio. skaliert**, wobei 50 Mio. für einen Durchschnitt von 20 Punkten genommen wird (höherer Durchschnitt = höher als 50 Mio.).
3. Die Skalierung ist **quadratisch**, nicht linear.

Das bedeutet:

- **Gute Spieler** werden deutlich teurer als Durchschnittsspieler  
- **Elite-Spieler** steigen überproportional stark im Wert  
- **Mittelmaß** bleibt bezahlbar  

So entsteht eine **realistische Marktspreizung**.

---

## 🔮 Unterschied: Salary vs. Projected Salary

**Salary**

→ basiert nur auf den **letzten drei abgeschlossenen Jahren**

**Projected Salary**

→ ersetzt das **älteste Jahr durch die aktuelle Saison**

---

# 📊 Wie entstehen Rankings?

Spieler werden auf Basis ihrer **Fantasy-Leistung** gerankt:

- **Gesamtleistung über alle möglichen Spiele**
- **Durchschnitt pro gespieltem Spiel**

Beides wird kombiniert zu einem **Gesamt-Ranking**.

Danach werden zusätzlich **Positionsrankings** erstellt:

- QB
- RB
- WR
- TE
- K

Je besser der **Rang innerhalb der Position**, desto besser die Bewertung.

---

# 💰 Wie berechnet sich das Salary Cap?

Das Salary Cap ergibt sich **nicht aus einer festen Zahl**, sondern wird **jede Saison automatisch aus dem aktuellen Spielermarkt berechnet**.

Damit passt sich die Liga **dynamisch an die reale Leistungsentwicklung an**.

---

## 1️⃣ Welche Spieler werden berücksichtigt?

Zuerst wird bestimmt, wie viele Spieler theoretisch in der Liga **„relevant“** sind:

> Anzahl Teams × SalaryRelevantTeamSize

Für uns: 6 Teams × 20 relevante Spieler = 120 Spieler

Genau **diese Anzahl an Spielern** wird für die Berechnung herangezogen:

- Die **Top-Spieler nach aktuellem Salary**
- Separat die **Top-Spieler nach SalaryProjected**

---

## 2️⃣ Was passiert mit diesen Spielern?

Von diesen Top-Spielern wird jeweils der **Durchschnittswert** berechnet:

- Durchschnitt **Salary**
- Durchschnitt **SalaryProjected**

Damit entsteht ein **realistischer Markt-Durchschnittswert pro Spieler**.

---

## 3️⃣ Wie entsteht daraus das Salary Cap?

Der Durchschnitt wird anschließend:

1. Mit der **SalaryRelevantTeamSize** multipliziert
2. Danach mit einem **Faktor von 0,9** versehen

Dieser **0,9-Faktor** sorgt bewusst für eine **leichte Marktspannung**.

Das bedeutet:

Selbst wenn alle Teams exakt fair verteilen würden, wäre das Cap **leicht unter der theoretisch perfekten Verteilung**.

Das erzeugt:

- **Trade-Druck**
- **Strategische Entscheidungen**
- **Wertigkeit von günstigen Verträgen**

---

## 🔮 Warum gibt es ein „Projected Salary Cap“?

Analog zum normalen Cap wird zusätzlich ein Wert berechnet:

**SalaryCapProjected**

Hier basiert alles auf **SalaryProjected** statt auf **Salary**.

Das zeigt:

- **Wie sich der Markt entwickeln würde**
- **Wenn die aktuelle Saison vollständig einberechnet wird**

---

## 📌 Wichtig

Das Salary Cap ist also:

- **Dynamisch**
- **Marktgetrieben**
- **Nicht manuell festgelegt**
- **Nicht willkürlich**

Es basiert **rein auf der tatsächlichen Fantasy-Leistung aller Spieler in der Liga**.