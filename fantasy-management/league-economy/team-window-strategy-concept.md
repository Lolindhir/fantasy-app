# Team Windows – Reload, Rebuild oder Hybrid?

> **Status:** offenes Research-/Designpapier  
> **Stand:** 02.10.2026
>
> Dieses Dokument untersucht eine grundlegende Frage der Ligaökonomie. Es trifft **keine** Entscheidung zugunsten von Reload, Rebuild oder Hybrid und führt **keine** neue Ligaregel ein.

## 1. Ausgangsfrage

Bei klassischen Dynasty-Ligen und in der NFL wird häufig mit klaren Franchise-Zeitfenstern gearbeitet:

- ein Team ist im **Win-Now-Fenster** und investiert kurzfristig in Produktion;
- ein Team befindet sich im **Rebuild** und tauscht kurzfristige Produktion gegen Picks, junge Spieler oder zukünftige Cap-/Asset-Vorteile;
- dazwischen existieren Teams, die eher **retoolen** oder **reloaden**, ohne eine Saison vollständig aufzugeben.

Für unsere Liga ist offen, ob diese klassische Zweiteilung überhaupt natürlich entsteht.

Die zentrale Designfrage lautet deshalb nicht:

> Wie bauen wir einen Rebuild ein?

Sondern zunächst:

> **Wollen wir eine Ligaökonomie, in der echte mehrjährige Rebuilds regelmäßig eine rationale Strategie sein können – oder soll die Liga primär Reloads und kurzfristige Käufer-/Verkäuferfenster erzeugen?**

Erst nach dieser Grundsatzentscheidung sollte geprüft werden, welche Mechaniken dafür nötig oder kontraproduktiv sind.

---

## 2. Aktuelle Struktur

Die aktuelle Ligastruktur wird bei jeder späteren Analyse aus `public/data/League.json` neu abgeleitet.

Stand 29.09.2026:

- 6 Teams;
- 4 Playoffplätze;
- Playoffstart Week 14;
- zwei feste QB-, RB-, WR- und TE-Spots;
- vier FLEX-Spots;
- ein Kicker;
- insgesamt 13 wöchentliche Starter pro Team;
- Trades sind durch `trade_deadline = 99` nicht durch eine normale In-Season-Deadline begrenzt;
- die Playoff-Runden werden als Zwei-Wochen-Runden gespielt.

Diese Kombination unterscheidet sich strukturell stark von einer größeren 10-, 12- oder 14-Team-Dynasty-Liga.

### Bestätigtes Incentive-Design: Rookie-Draft und All-Time-Standings gemeinsam betrachten

Die Rookie-Draft-Reihenfolge ist bewusst nicht nur eine Competitive-Balance-Regel. Sie ist zusammen mit den All-Time-Standings als gekoppeltes Anreizsystem gedacht.

Aus der finalen Vorjahresplatzierung ergibt sich:

| Vorjahresplatz | eigener Rookie-Pick |
| ---: | ---: |
| 5. | 1.01 |
| 6. | 1.02 |
| 4. | 1.03 |
| 3. | 1.04 |
| 2. | 1.05 |
| 1. | 1.06 |

Die Reihenfolge verfolgt zwei Ziele gleichzeitig.

**Außerhalb der Playoffs bleibt Gewinnen wertvoll.** Platz 5 erhält 1.01 und Platz 6 nur 1.02. Maximales Verlieren wird damit nicht automatisch maximal belohnt.

**Innerhalb der Playoffs bleibt auch das Spiel um Platz 3 relevant.** Platz 4 erhält zwar mit 1.03 den etwas besseren Rookie-Pick als Platz 3 mit 1.04, aber der Third Place besitzt dauerhaften Franchise-/Legacy-Wert.

Vom User bestätigte gewünschte Reihenfolge der All-Time-Erfolgskriterien:

```text
Championships
-> Runner-Ups
-> Third Places
-> Regular Season Kings
```

Damit ist der Unterschied zwischen Platz 3 und Platz 4 bewusst ein Tausch zwischen zwei Arten von Wert:

```text
Platz 3:
mehr dauerhafter Franchise-/Legacy-Erfolg
+ 1.04

Platz 4:
kein Third Place
+ 1.03
```

Die Draftorder verteilt also Zukunftsassets an weniger erfolgreiche Teams, ohne sportlichen Erfolg auf den relevanten Platzierungsstufen wertlos zu machen.

### Konsequenz für die Rebuild-Diskussion

Die Rookie-Draft-Reihenfolge soll **nicht isoliert als zusätzlicher Rebuild-Hebel optimiert werden**.

Bevor an ihr etwas verändert würde, müsste die Liga ausdrücklich auch die gekoppelte Achievement-/All-Time-Logik neu öffnen.

Für die aktuelle League-Economy-Forschung gilt deshalb als Arbeitsschutz:

> Erst prüfen, ob Rookie-Pick-Akkumulation, dreijährige Rookie Contracts, Salary/Cap und offene Trades bereits genügend freiwillige Zukunftsanreize erzeugen. Die bestehende Draft-/Achievement-Struktur wird dabei zunächst als bewusst zu bewahrender Teil des Systems behandelt.

### Technischer Abgleich

Die hier beschriebene All-Time-Reihenfolge ist die vom User bestätigte **beabsichtigte Ligalogik**.

Der aktuelle Standings-Generator verwendet nach Championships, Runner-Ups und Third Places derzeit offenbar kumulierte Regular-Season-Wins statt der Anzahl der Regular Season Kings. Diese technische Abweichung wird separat in **#810** untersucht und ist keine Änderung dieses Research-Papiers.

---

## 3. Mathematischer Ausgangspunkt: 4 von 6

Bei sechs gleich starken Teams und vier Playoffplätzen besitzt jedes Team symmetrisch einen Anteil von:

```text
4 / 6 = 66,7 %
```

an den Playoffplätzen.

Das bedeutet nicht, dass jedes reale Team zu Saisonbeginn exakt 66,7 % Playoffwahrscheinlichkeit besitzt. Teamstärke, Schedule, Verletzungen und Tiebreaker verändern die individuelle Chance.

Die Struktur erzeugt aber eine wichtige Hürde für einen klassischen Rebuild:

> Ein Team muss lediglich zwei andere Teams hinter sich lassen, um die Playoffs zu erreichen.

Dadurch bleibt auch für ein unterdurchschnittliches Team länger ein plausibler Pfad in die Postseason offen als in einer Liga, in der nur etwa die Hälfte oder weniger der Teams die Playoffs erreicht.

### Konsequenz

Die Schwelle, ab der ein Manager rational sagen kann

> "Diese Saison ist sportlich so unwahrscheinlich, dass ich kurzfristige Produktion bewusst abgebe"

liegt strukturell später und niedriger als in größeren Ligen.

---

## 4. Kleine Liga und Replacement Level

Sechs Teams konzentrieren NFL-Talent auf wenige Fantasy-Roster.

Das führt nicht automatisch dazu, dass jeder Waiver Wire stark ist. Starterzahl, Bench, Taxi, Reserve und Positionsanforderungen bleiben relevant.

Trotzdem gilt grundsätzlich:

- weniger Fantasy-Teams teilen sich denselben NFL-Spielerpool;
- mehr brauchbare NFL-Spieler bleiben außerhalb der unmittelbaren Starting Lineups;
- einzelne Rosterlücken können leichter durch Ersatz oder Trades geschlossen werden;
- wenige echte Difference Maker können ein Team schnell deutlich verändern.

Das spricht eher für schnelle **Reloads** als für zwangsläufig mehrjährige Wiederaufbauten.

Diese Beobachtung passt zum bereits dokumentierten Replacement-Level-Grundsatz in den Fantasy-Management-Regeln: In einer flachen Liga zählt obere Qualität stärker als bloße Rosterbarkeit.

---

## 5. Offene Trades erhöhen den Optionswert des Wartens

Die fehlende normale Trade Deadline erzeugt bewusst einen späten Käufer-/Verkäufermarkt.

Ein ausgeschiedenes Team kann noch Veteranen oder kurzfristige Produktion abgeben.

Ein Playoff- oder sogar Super-Bowl-Team kann noch gezielt kurzfristig aufrüsten.

Das erzeugt eine sinnvolle In-Season-Dynamik.

Gleichzeitig reduziert diese Regel den Druck, bereits in der Offseason oder früh in der Regular Season einen Rebuild auszurufen.

Ein Manager kann zunächst:

1. seine Championship-Chance behalten;
2. zusätzliche Information über Teamstärke, Verletzungen und Breakouts sammeln;
3. später verkaufen, wenn die eigene Saison tatsächlich verloren ist.

Damit besitzt das **Warten einen Optionswert**.

Dieser Optionswert ist in einer Liga mit 4/6 Playoffplätzen besonders hoch.

### Mögliche Gegenwirkung

Spätes Warten kann auch Kosten haben:

- ein Veteran kann sich verletzen;
- sein Marktwert kann sinken;
- andere Käufer können ihren Bedarf bereits gedeckt haben;
- ein früherer Trade hätte eventuell ein besseres zukünftiges Asset gebracht.

Ob frühes Verkaufen attraktiv genug ist, hängt deshalb von der Stärke zukünftiger Assets und der Persistenz der Cap-/Contract-Vorteile ab.

---

## 6. Zwei-Wochen-Playoffs wirken teilweise in die Gegenrichtung

Breiter Playoffzugang erhöht den Wert, überhaupt die Postseason zu erreichen.

Zwei-Wochen-Runden reduzieren dagegen die Varianz eines einzelnen Fantasy-Wochenendes.

Über zwei Wochen hat ein objektiv stärkeres Team tendenziell mehr Gelegenheit, seinen Qualitätsvorteil auszuspielen.

Daraus entsteht ein gemischter Effekt:

- **4/6 Playoffplätze:** schwächere Teams bleiben lange relevant;
- **Zwei-Wochen-Runden:** reine Außenseiter-Runs werden etwas schwerer als bei One-and-Done über nur eine Woche.

Das spricht dafür, Playoffteilnahme und echte Championship-Stärke getrennt zu betrachten.

Ein Team kann rational um den vierten Platz kämpfen und trotzdem entscheiden, dass zusätzliche Investitionen für einen Titel nicht sinnvoll sind.

---

## 7. Arbeitsbegriffe

### Reload

Ein Reload bedeutet:

- das Team bleibt grundsätzlich wettbewerbsfähig;
- einzelne ältere, teure oder schlecht passende Assets werden ausgetauscht;
- Picks und junge Spieler werden ergänzt;
- die Starting Quality soll nicht für mehrere Jahre bewusst einbrechen;
- Turnaround-Ziel: eher Monate bis eine Saison als mehrere Jahre.

### Echter Rebuild

Ein Rebuild bedeutet:

- kurzfristige Winning Probability wird bewusst geopfert;
- Veteranen oder teure Produktion werden gegen zukünftige Assets getauscht;
- Picks, junge Verträge und zukünftige Cap-Flexibilität erhalten deutlich höheren Wert;
- mindestens ein Teil der Strategie ist auf ein späteres Championship-Fenster ausgerichtet;
- die Ligaökonomie muss genügend zukünftigen Mehrwert bieten, damit dieses Opfer rational sein kann.

### Hybrid

Ein Hybrid bedeutet:

- Reload bleibt der Normalfall;
- ein echter Rebuild ist möglich, aber nicht notwendiger Bestandteil jedes Franchise-Zyklus;
- nur bestimmte Roster-/Cap-/Asset-Situationen rechtfertigen das bewusste Opfern kurzfristiger Chancen;
- das System versucht nicht, künstlich regelmäßig schlechte Teams zu erzeugen.

---

## 8. Option A – Reload-first

### Leitidee

Die Liga akzeptiert ihre natürliche kleine Struktur.

Fast jedes Team soll über weite Teile einer Saison einen realistischen Weg zur Konkurrenzfähigkeit behalten.

Strategische Differenzierung entsteht vor allem durch:

- Qualität vs. Tiefe;
- Cap-Effizienz;
- Rookie-Contract-Surplus;
- Trades;
- kurzfristige Käufer-/Verkäuferfenster;
- richtige Konsolidierung und Timing.

### Mögliche Vorteile

- hohe saisonale Relevanz für fast alle Teams;
- geringe Gefahr mehrjähriger Bedeutungslosigkeit;
- schnelle Turnarounds;
- hoher Wert guter In-Season-Entscheidungen;
- passt gut zur Talentkonzentration einer 6-Team-Liga;
- offene Trades können ihre gewünschte Funktion als später Markt erfüllen.

### Mögliche Nachteile

- Picks und sehr junge Assets können weniger strategisch dominant sein;
- Teamstrategien können sich in der Offseason stärker ähneln;
- "Win Now vs. Rebuild" als klassisches Dynasty-Thema entsteht nur schwach;
- langfristige Fehlentscheidungen können schneller reparierbar sein;
- die Liga kann sich weniger wie eine NFL-Franchise-Ökonomie anfühlen.

### Designimplikation

Unter diesem Ziel wäre es kein Problem, wenn das neue Salary-/Dead-Cap-System **keine starken mehrjährigen Cap-Hells oder Rebuildzwänge** erzeugt.

---

## 9. Option B – Rebuild-supportive

### Leitidee

Die Liga möchte bewusst echte mehrjährige Teamzyklen ermöglichen.

Ein Manager soll rational sagen können:

> "Ich gebe einen Teil meiner heutigen Championship-Chance auf, weil mein Team dadurch in ein oder zwei Jahren strukturell deutlich stärker werden kann."

Dafür reicht ein allgemeiner Dynasty-Label wie "jung" oder "alt" nicht.

Es muss einen **realen zukünftigen ökonomischen Vorteil** geben.

### Mechanikfamilien, die Rebuilds stärken könnten

Noch keine dieser Ideen ist beschlossen.

#### 1. Stärkere Zukunfts-Assets

Beispiele:

- wertvollere Rookie-Pick-Surplus-Verträge;
- länger anhaltende günstige Rookie-/Young-Player-Verträge;
- zusätzliche oder anders strukturierte Draftressourcen.

Effekt:

Zukünftige Produktion kann deutlich günstiger als heutige Veteranenproduktion erworben werden.

#### 2. Persistentere Vertrags- oder Cap-Folgen

Beispiele:

- längere Vertragsbindungen;
- Dead Cap über mehr als einen Salary-Zyklus;
- andere persistente Cap-Verpflichtungen;
- begrenztere Möglichkeit, schlechte Verträge jährlich vollständig zu resetten.

Effekt:

Fehlentscheidungen und ältere Roster können nicht sofort repariert werden.

Risiko:

Zu starke Persistenz kann ein 6-Team-Roster unnötig lange unspielbar machen.

#### 3. Stärkere Differenz zwischen kurzfristiger und zukünftiger Produktion

Beispiele:

- Veteranen stärker als kurzfristige Championship-Assets;
- junge Spieler/Picks stärker als günstige zukünftige Produktionsrechte;
- klarer Preis für den Tausch zwischen beiden Zeithorizonten.

#### 4. Playoff-/Wettbewerbsstruktur

Auch die Zahl der Playoffplätze beeinflusst den Optionswert des Competitive Bleibens.

Weniger Playoffplätze würden Teamfenster früher auseinanderziehen.

Das wäre jedoch eine massive Formatentscheidung und darf nicht als bloßes Hilfsmittel für Salary Design behandelt werden.

### Mögliche Vorteile

- klarere strategische Identitäten der Teams;
- höherer Wert langfristiger Planung;
- Picks und junge Verträge bekommen echte Portfoliofunktion;
- größere Konsequenzen für Cap-/Roster-Fehler;
- stärkeres Franchise-/NFL-Gefühl.

### Mögliche Nachteile

- höhere Tanking-Anreize;
- ein Fehlstart kann Manager früher zum Verkauf motivieren;
- schlechte Teams können mehrere Saisons uninteressant werden;
- kleine Liga kann extreme Talentkonzentration bei wenigen Contendern erzeugen;
- weniger Parität;
- höhere Komplexität;
- ein zu starker Rebuild-Vorteil kann Championship-Chancen künstlich binär machen.

---

## 10. Option C – Hybrid

### Leitidee

Die Liga bleibt grundsätzlich schnell reparierbar, aber einige Roster-/Cap-Situationen dürfen einen echten Rebuild rechtfertigen.

Das Ziel wäre:

> **Rebuild möglich, aber nicht erforderlich.**

Ein Manager mit durchschnittlichem Team soll nicht automatisch verkaufen.

Ein Team mit ungünstiger Kombination aus:

- schwacher Top-End-Qualität;
- schlechter Cap-Effizienz;
- wenigen günstigen jungen Assets;
- wertvollen verkaufbaren Veteranen;
- starker zukünftiger Pick-/Contract-Position

könnte dagegen rational ein Jahr oder einen Zyklus opfern.

### Mögliche Vorteile

- bewahrt hohe saisonale Relevanz;
- eröffnet trotzdem unterschiedliche langfristige Strategien;
- passt möglicherweise besser zur kleinen Ligagröße als eine künstliche NFL-Kopie;
- Rookie Contracts und Cap-Effizienz können Teamfenster erzeugen, ohne sie zu erzwingen.

### Mögliche Nachteile

- schwieriger zu kalibrieren;
- Teamfenster können weniger offensichtlich sein;
- Gefahr eines Systems, das weder echte Rebuilds noch reine Reloads sauber erzeugt;
- mehr Abwägung nötig, ob zukünftige Assets tatsächlich stark genug sind.

---

## 11. Gemeinsame Bewertungsmatrix

Jede spätere Designvariante sollte anhand derselben Fragen geprüft werden.

| Dimension | Reload-first | Rebuild-supportive | Hybrid |
| --- | --- | --- | --- |
| Saisonale Relevanz aller Teams | tendenziell hoch | tendenziell niedriger | hoch bis mittel |
| Strategische Unterschiede in der Offseason | eher geringer | hoch | mittel bis hoch |
| Bedeutung von Rookie Picks | mittel | hoch | mittel bis hoch |
| Bedeutung günstiger Rookie Contracts | hoch, aber ergänzend | sehr hoch | hoch |
| Veteranen als Win-Now-Assets | situativ | stark differenziert | stark, wenn Fenster klar |
| Langfristige Fehlerfolgen | eher begrenzt | stärker | moderat |
| Turnaround | schnell | bewusst langsamer möglich | situationsabhängig |
| Tanking-Anreiz | gering | höher | kontrollierbar, aber vorhanden |
| Trade-Markt | eher spät/in-season | früher und stärker segmentiert | mehrere Marktphasen möglich |
| NFL-Franchise-Gefühl | teilweise | stärker | selektiv |
| Risiko mehrjähriger Bedeutungslosigkeit | niedrig | höher | begrenzt |
| Erklärbarkeit | hoch | abhängig von Mechaniken | mittel |

Die Tabelle ist eine qualitative Arbeitsmatrix und keine Bewertung oder Rangliste.

---

## 12. Zusammenspiel mit Rookie Salary und Dead Cap

Das aktuelle Rookie-/Dead-Cap-Konzept erzeugt bereits Zeitwerte.

### Rookie Contracts

Der aktuell dokumentierte Rookie Contract lautet:

- Year 1: Draft-basiertes Salary;
- Year 2: 125 % des festen Year-1-Salary;
- Year 3: 150 % des festen Year-1-Salary;
- ab Year 4: normales Performance Salary.

Dadurch kann erfolgreiche junge Produktion mehrere Jahre deutlich cap-effizienter als etablierte Performance sein.

Das stärkt zukünftige Assets und kann Rebuild- oder Reload-Strategien unterstützen.

### Dead Cap

Der aktuelle Dead Cap:

- hängt von ununterbrochener Team-Tenure ab;
- verteilt aktuelles Salary als Retained Salary;
- endet beim nächsten regulären Salary Check;
- wird bewusst nicht über mehrere Salary-Zyklen fortgeführt.

Damit erzeugt Dead Cap vor allem **Transaktionskosten innerhalb eines Zyklus**, aber nur begrenzte mehrjährige Cap-Narben.

Das passt besonders gut zu Reload-first oder einem milden Hybrid.

Für einen bewusst stark Rebuild-orientierten Entwurf müsste separat geprüft werden, ob diese geringe Persistenz ausreicht.

Das ist ausdrücklich **keine** Empfehlung, Dead Cap zu verlängern.

---

## 13. Zusammenspiel mit Performance Salary und Criticality

Das Performance-Salary-Redesign verfolgt ein anderes Ziel:

> Produktion soll danach bepreist werden, wie kritisch sie in dieser konkreten Liga wirklich ist.

Die geplante dynamische Positional Criticality kann:

- echte Difference Maker teuer machen;
- leicht ersetzbare Mid-Tier-Produktion komprimieren;
- sich an Ligaformat und NFL-Leistungslandschaft anpassen.

Diese Logik bestimmt aber noch nicht automatisch, ob Teams rebuilden.

Sie beeinflusst lediglich:

- wo Cap knapp wird;
- welche Spieler Surplus Value besitzen;
- welche Rosterstrukturen teuer werden;
- wie attraktiv günstige Ersatzproduktion ist.

Teamfenster entstehen erst aus dem Zusammenspiel von:

```text
Spielerqualität
+ Vertrags-/Salary-Kosten
+ Persistenz der Verpflichtungen
+ zukünftige Assetqualität
+ Playoffzugang
+ Trade-Markt
```

---

## 14. Zentrale offene Fragen

Vor einer Ligaentscheidung sollten insbesondere diese Fragen diskutiert werden:

1. **Wollen wir echte mehrjährige Rebuilds überhaupt regelmäßig sehen?**
2. Oder reicht es, wenn ein Rebuild nur in extremen Roster-/Cap-Situationen rational wird?
3. Wie wichtig ist uns, dass Teams bereits in der Offseason klar unterschiedliche Zeitfenster besitzen?
4. Wie viel saisonale Relevanz wollen wir einem schwächeren Team erhalten?
5. Wie stark sollen schlechte Cap-/Contract-Entscheidungen in Folgejahre hineinwirken?
6. Wie stark sollen Rookie Picks und günstige Rookie Contracts gegenüber Veteranen sein?
7. Wollen wir mehr strategische Differenzierung auch dann, wenn dadurch Tanking-Anreize steigen?
8. Ist der aktuelle 4-von-6-Playoffzugang selbst Teil des gewünschten Produkts oder grundsätzlich ebenfalls diskutierbar?
9. Soll offene Trade-Freiheit bis in die Playoffs primär spätes Kaufen/Verkaufen ermöglichen oder soll früheres Positionieren stärker belohnt werden?
10. Welche Turnaround-Dauer fühlt sich für ein schlecht aufgestelltes Team noch fair und unterhaltsam an?

---

## 15. Nächste Research-Schritte

Bevor Mechaniken geändert werden, sollte die Diskussion mit Daten ergänzt werden.

Mögliche spätere Analysen:

- historische Verteilung der Teamstärke innerhalb der sechs Teams;
- wie häufig #5/#6 tatsächlich noch spät realistische Playoffchancen hatten;
- Unterschiede zwischen Regular-Season-Qualität und Zwei-Wochen-Playofferfolg;
- historische Pick-/Rookie-Surplus-Werte unter dem neuen Salary-Modell;
- wie schnell schlechte Roster aktuell durch Free Agents, Draft und Trades repariert werden können;
- wie stark verschiedene Dead-Cap-/Contract-Persistenzen einen realen Teamumbau verzögern würden;
- Simulation vollständiger Designpakete statt isolierter Regeln.

---

## 16. Aktuelle Arbeitshypothese

Der derzeitige strukturelle Befund lautet:

> Die bestehende 6-Team-/4-Playoff-Liga erzeugt natürlicherweise eher hohe Competitive Optionality, schnelle Reloads und späte Käufer-/Verkäuferfenster als regelmäßige mehrjährige Rebuilds.

Das ist **noch keine Designentscheidung**.

Die Liga muss bewusst entscheiden, ob sie:

- diese Eigenschaft als passende Identität akzeptiert;
- echte Rebuilds aktiv stärker ermöglichen möchte;
- oder einen Hybrid anstrebt, in dem Rebuilds möglich, aber selten sind.

Erst danach sollte geprüft werden, welche der bestehenden oder neuen Salary-/Contract-/Formatmechaniken zu diesem Ziel passen.
