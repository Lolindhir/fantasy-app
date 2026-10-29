# League Economy Redesign – Optionen für die Offseason

> **Status:** frühes Synthese- und Diskussionspapier  
> **Stand:** 02.10.2026
>
> Dieses Dokument soll später als gemeinsame, ligaweit lesbare Entscheidungsgrundlage dienen. Es fasst drei Detaildiskussionen zusammen, ersetzt deren kanonische Konzeptpapiere aber nicht.
>
> **Aktuell ist keine Gesamtvariante beschlossen.**

## 1. Was wollen wir eigentlich simulieren?

Die Ausgangsidee hinter Salary, Rookie Contracts und Dead Cap ist eine stärker NFL-artige Franchise-Ökonomie.

"NFL-artig" darf dabei nicht bedeuten, reale NFL-Regeln möglichst wörtlich zu kopieren.

Unsere Liga besitzt:

- nur 6 Teams;
- aktuell 4 Playoffplätze;
- hohe Startertiefe pro Team;
- konzentrierten NFL-Spielerpool;
- eigene Draft-, Salary- und Trade-Mechaniken.

Deshalb muss jede Mechanik beantworten:

> **Welches strategische Verhalten wollen wir erzeugen – und funktioniert dieses Verhalten in unserer Fantasy-Struktur überhaupt?**

Die drei derzeit getrennten Designfragen sind:

1. **Contracts / Dead Cap:** Wie lange und zu welchen Kosten bindet ein Team einen Spieler?
2. **Performance Salary / Criticality:** Welche Produktion soll wie viel Cap kosten?
3. **Team Windows:** Soll die Liga primär Reloads, echte Rebuilds oder einen Hybrid erzeugen?

Diese drei Fragen hängen zusammen, sollten aber nicht in einer einzigen Formel vermischt werden.

---

## 2. Team Windows: Reload, Rebuild oder Hybrid?

Detailpapier:

`fantasy-management/league-economy/team-window-strategy-concept.md`

### Aktueller struktureller Befund

Die Liga besitzt aktuell 6 Teams und 4 Playoffplätze.

Bei symmetrisch gleich starken Teams entsprechen vier von sechs Plätzen zunächst einem Anteil von:

```text
66,7 %
```

Zusätzlich gibt es keine normale In-Season-Trade-Deadline.

Damit besitzt Competitive Bleiben einen hohen Optionswert:

- ein Team kann zunächst um die Playoffs kämpfen;
- erst bei klarer Eliminierung verkaufen;
- Käufer können sehr spät aufrüsten.

Die kleine Liga konzentriert zudem NFL-Talent und begünstigt schnelle Reparaturen.

Gegenläufig wirken die Zwei-Wochen-Playoffs: Sie reduzieren Single-Week-Varianz und geben echter Rosterqualität mehr Gelegenheit, sich durchzusetzen.

### Bestätigtes Preserve-Prinzip: Draftorder + Legacy-Anreize

Die aktuelle Rookie-Draft-Reihenfolge ist ein bewusst gekoppelter Bestandteil der Ligaökonomie:

| Vorjahresplatz | eigener Rookie-Pick |
| ---: | ---: |
| 5. | 1.01 |
| 6. | 1.02 |
| 4. | 1.03 |
| 3. | 1.04 |
| 2. | 1.05 |
| 1. | 1.06 |

Sie soll gleichzeitig Competitive Balance und sportliche Motivation erhalten.

- Platz 5 wird gegenüber Platz 6 mit 1.01 belohnt; ganz unten besteht damit weiterhin ein Anreiz, besser abzuschneiden.
- Platz 3 erhält bewusst einen späteren Pick als Platz 4, weil der Third Place langfristigen Franchise-/Legacy-Wert besitzt.
- Die vom User bestätigte gewünschte All-Time-Erfolgshierarchie lautet: **Championships -> Runner-Ups -> Third Places -> Regular Season Kings**.

Damit tauscht ein besseres Finish teilweise Draftposition gegen dauerhaften historischen Erfolg.

**Folgerung für die Offseason-Diskussion:** Die Rookie-Draft-Reihenfolge wird zunächst nicht als isolierter Rebuild-Hebel behandelt. Ein Paket, das mehr Rebuild-Anreize erzeugen soll, muss zuerst zeigen, dass die bereits vorhandenen Zukunftsanreize aus Picks, Rookie Contracts, Salary/Cap und Trades nicht ausreichen.

Eine technische Abweichung im aktuellen All-Time-Generator wird separat in #810 geprüft; sie ändert die hier dokumentierte beabsichtigte Ligalogik nicht.

### Drei Grundrichtungen

#### A. Reload-first

Die Liga akzeptiert, dass die meisten Teams lange konkurrenzfähig bleiben und dass Teamzyklen eher kurz sind.

#### B. Rebuild-supportive

Die Liga schafft bewusst genügend zukünftigen ökonomischen Vorteil und/oder persistente Verpflichtungen, damit das Opfer kurzfristiger Winning Probability regelmäßig rational sein kann.

#### C. Hybrid

Reload bleibt normal; echter Rebuild wird in bestimmten schlechten Roster-/Cap-Situationen sinnvoll, aber nicht zum Standardzyklus jedes Teams.

### Noch offen

Die Liga muss zuerst entscheiden, **welches strategische Verhalten sie überhaupt will**, bevor Mechaniken allein nach "mehr NFL" bewertet werden.

---

## 3. Rookie Contracts und Dead Cap

Detailpapier:

`fantasy-management/league-economy/salary/salary-dead-cap-concept.md`

### Bereits geklärte Konzeptbausteine

#### Rookie Year 1

Year 1 wird aus zwei Draft-Signalen bestimmt:

```text
65 % Fantasy Rookie Draft
35 % realer NFL Draft
```

Beide Signale verwenden eine fallende Draftkurve.

Das Salary basiert auf dem maßgeblichen Vorjahres-Salary-Cap.

#### Rookie Contract Year 1 bis Year 3

```text
Year 1 = 100 % × Year1Salary
Year 2 = 125 % × Year1Salary
Year 3 = 150 % × Year1Salary
```

Die Faktoren sind nicht kumulativ.

Ab Year 4 greift das normale Drei-Saison-Performance-Salary.

#### Minimum Salary

Das allgemeine Base Minimum steigt mit NFL-Erfahrung von 0,25 % bis 0,50 % des maßgeblichen Vorjahres-Salary-Caps.

#### Dead Cap

Der aktuelle Konzeptstand:

```text
Tenure 0   -> 50 %
Tenure 1   -> 30 %
Tenure 2   -> 15 %
Tenure 3+  -> 5 %
```

Dead Cap ist Retained Salary.

Der abgegebene Salary-Anteil bleibt beim alten Team, der verbleibende Anteil wird zum aktiven Salary des Spielers.

Beim nächsten regulären Salary Check werden alte Dead-Cap-Anteile zurückgesetzt.

### Strategische Wirkung

Dieses Modell erzeugt:

- echten Wert günstiger junger Verträge;
- Transaktionskosten bei kurzfristigen Aufnahmen und Cuts;
- einen Vorteil langfristiger Teamzugehörigkeit beim späteren Cut;
- aber bewusst **keine mehrjährige Dead-Cap-Schuld**.

Damit ist das Modell nicht automatisch ein Rebuild-System.

Es kann Reloads und einen Hybrid sehr gut unterstützen und liefert gleichzeitig mit günstigen Rookie Contracts einen potenziellen Baustein für echte Rebuilds.

---

## 4. Performance Salary und Positional Criticality

Detailpapier:

`fantasy-management/league-economy/salary/salary-system-redesign-concept.md`

### Ausgangsproblem

Das bisherige normale Salary monetarisiert absolute Fantasy-Produktion weitgehend positionsneutral.

Die bisherige Analyse zeigt, dass dies besonders bei Quarterbacks zu Verzerrungen führen kann:

- sehr hohe positionsbedingte Rohpunkte;
- gleichzeitig teilweise gute Ersatzverfügbarkeit;
- hoher Cap-Anteil mittlerer QBs;
- mehrere teure QB-Cuts vor der 2026 Cap Deadline;
- einige dieser QBs wurden danach erst spät oder gar nicht im Free-Agent-Draft genommen.

Gleichzeitig zeigte Brock Purdy als frühe Free-Agent-Draft-Auswahl:

> Elite-QB darf weiterhin teuer und knapp sein.

Die Schlussfolgerung ist deshalb nicht "QB billiger", sondern:

> Salary soll tatsächliche Fantasy-Kritikalität besser erfassen.

### Geklärte Architektur

Positional Criticality soll:

- nicht als feste Positionskonstante gespeichert werden;
- jährlich aus aktuellem Ligaformat und historischen Produktionskurven entstehen;
- FLEX-Nachfrage dynamisch berücksichtigen;
- Elite-Peaks und flache Mid-Tiers unterscheiden;
- auf Veränderungen der NFL-Leistungslandschaft reagieren.

Das Salary Cap bleibt endogen:

```text
Player Salaries
-> Top 120 Salaries
-> Salary Cap
```

### Noch offen

Noch nicht entschieden sind unter anderem:

- exakte Criticality-Funktion;
- Mehrjahresgewichtung;
- Verbindung von absoluter Performance und relativer Criticality;
- Form der Salary-Kurve;
- konkrete Dollar-Abbildung.

---

## 5. Wie die drei Systeme zusammenwirken

Die größte Designwirkung entsteht nicht aus einer einzelnen Regel.

Sie entsteht aus dem Zusammenspiel:

```text
heutige Spielerqualität
+
heutiges Salary
+
zukünftige Salaryentwicklung
+
Rookie-Contract-Surplus
+
Cut-/Dead-Cap-Kosten
+
Persistenz von Verpflichtungen
+
Rookie Picks
+
Playoffzugang
+
Trade-Liquidität
=
tatsächliche Teamstrategie
```

### Beispiel: junger Breakout

Ein junger Spieler kann:

- hohe Produktion liefern;
- noch auf einem günstigen Rookie Contract stehen;
- mehrere Jahre Surplus Value besitzen.

Damit ist er gleichzeitig:

- Win-Now-Spieler;
- langfristiger Building Block;
- wertvolles Trade Asset.

"Jung = Rebuild" wäre deshalb zu simpel.

### Beispiel: teurer Veteran

Ein Veteran kann:

- aktuell hohe Punkte liefern;
- viel Cap binden;
- wenig zukünftige Vertragskontrolle besitzen.

Für einen Finalisten kann er wertvoller sein als für ein eliminiertes Team.

Dadurch entsteht ein echter Markt zwischen Zeithorizonten.

### Beispiel: Dead Cap

Dead Cap kann einen schnellen Cut bestrafen.

Wenn Dead Cap aber am nächsten Salary Check vollständig verschwindet, erzeugt er eher kurzfristige Friktion als mehrjährige Cap Hell.

Ob das gewollt ist, hängt unmittelbar von der Team-Window-Entscheidung ab.

---

## 6. Kohärente Designpakete

Die Offseason-Diskussion sollte möglichst nicht aus 30 isolierten Schaltern bestehen.

Stattdessen sollten wenige komplette Pakete verglichen werden.

Die folgenden Pakete sind **Arbeitsrahmen, keine Beschlussvorlagen**.

### Paket A – Competitive Reload

**Ziel:** Möglichst viele Teams bleiben saisonal relevant; Teamumbauten sind schnell möglich.

Grundrichtung:

- 4/6 Playoffstruktur bleibt Teil der Identität;
- offene späte Trades bleiben;
- aktuelles dreijähriges Rookie-Contract-Konzept;
- Dead Cap bleibt auf einen Salary-Zyklus begrenzt;
- Performance Salary wird über dynamische Criticality verbessert;
- keine zusätzliche Mechanik wird nur eingeführt, um absichtlich mehrjährige Rebuilds zu erzwingen.

Was dieses Paket optimiert:

- hohe jährliche Relevanz;
- schnelle Turnarounds;
- In-Season-Management;
- Cap-Effizienz und Konsolidierung statt absichtlicher langer Schwäche.

Was es akzeptiert:

- klassische Dynasty-Rebuilds bleiben selten;
- Teamstrategien unterscheiden sich in der Offseason möglicherweise weniger stark.

### Paket B – Franchise Cycles

**Ziel:** Klare mehrjährige Win-Now- und Rebuild-Fenster sollen häufiger rational werden.

Dafür müsste die Liga zusätzliche Hebel prüfen, zum Beispiel:

- stärkere Zukunfts-Asset-Surpluses;
- persistentere Contract-/Cap-Verpflichtungen;
- eventuell strukturelle Änderungen an Wettbewerb oder Playoffzugang.

Wichtig:

Keine dieser Mechaniken ist aktuell beschlossen.

Was dieses Paket optimiert:

- langfristige Planung;
- strategisch deutlich verschiedene Teams;
- stärkere Konsequenzen für Roster-/Cap-Entscheidungen;
- höheres Franchise-Gefühl.

Was es akzeptiert:

- höhere Tanking-Anreize;
- längere schlechte Phasen;
- höhere Komplexität;
- größere Gefahr, dass eine kleine Liga in wenige starke und wenige schwache Teams zerfällt.

### Paket C – Controlled Hybrid

**Ziel:** Reload bleibt Standard, aber echter Rebuild wird in klar schlechten Ausgangslagen rational möglich.

Grundrichtung:

- breite Playoffrelevanz grundsätzlich erhalten;
- günstige Rookie-/Young-Player-Verträge als echten Zukunftsvorteil nutzen;
- Salary Criticality soll ineffiziente teure Mittelklasse reduzieren;
- nur begrenzte zusätzliche Persistenz oder Zukunftsprämie, falls empirisch nötig;
- Rebuild soll aus einer schlechten Roster-/Cap-/Asset-Kombination entstehen, nicht aus einer künstlichen Pflichtrotation.

Was dieses Paket optimiert:

- saisonale Relevanz plus strategische Tiefe;
- unterschiedliche Wege ohne regelmäßige absichtliche Bedeutungslosigkeit.

Was es akzeptiert:

- schwieriger zu kalibrieren;
- weniger klare Teamlabels;
- Gefahr eines zu milden Systems, wenn zukünftige Assets nicht genügend Differenz erzeugen.

---

## 7. Gemeinsame Bewertungsfragen für die Liga

Vor einer Entscheidung sollten alle Pakete mit denselben Fragen beurteilt werden:

1. Wie oft wollen wir echte Rebuilds sehen?
2. Wie lange darf ein schlecht geführtes Team realistisch brauchen, um wieder konkurrenzfähig zu sein?
3. Wie wichtig ist uns die Relevanz jedes Teams während der laufenden Saison?
4. Wie stark sollen Rookie Picks und günstige Rookie Contracts sein?
5. Wie stark sollen falsche Veteranen-/Salary-Entscheidungen in Folgejahre nachwirken?
6. Wie früh sollen sich Käufer und Verkäufer unterscheiden?
7. Wie viel Tanking-Risiko akzeptieren wir?
8. Wie viel zusätzliche Komplexität ist für mehr strategische Tiefe vertretbar?
9. Welche Mechaniken fühlen sich tatsächlich sinnvoll NFL-artig an und welche wären in einer 6-Team-Liga nur künstlich?
10. Welche Teile des aktuellen Ligaformats sind selbst verhandelbar und welche sollen als feste Identität bestehen bleiben?

---

## 8. Welche Evidenz noch fehlt

Vor einer finalen Offseason-Abstimmung sind weitere Analysen sinnvoll.

### Team-Window-Evidenz

- historische Playoff-Races;
- Stärke von #4/#5/#6 über die Saison;
- tatsächliche Käufer-/Verkäuferzeitpunkte;
- Geschwindigkeit realer Reloads.

### Contract-/Rookie-Evidenz

- historische Rookie-Klassen unter dem neuen Year-1-Modell;
- erwarteter Surplus Value guter Rookie Contracts;
- Folgen unterschiedlicher Contract-Persistenz.

### Salary-Evidenz

- formale Criticality-Funktion;
- Backtests 2024/2025;
- historische Cap-/Cut-Simulation;
- Robustheit bei veränderten Starter-/FLEX-Einstellungen.

### Systemweite Simulation

Am Ende sollten nicht nur Einzelregeln, sondern komplette Pakete simuliert werden:

```text
Roster
+ Picks
+ Rookie Contracts
+ Performance Salary
+ Dead Cap
+ Playoffstruktur
+ Tradefreiheit
-> erwartbares Managerverhalten
```

---

## 9. Vorgeschlagener Offseason-Prozess

### Phase 1 – Ziele klären

Zuerst Teamfenster diskutieren:

- Reload-first?
- Rebuild-supportive?
- Hybrid?

Noch keine Detailformel abstimmen.

### Phase 2 – bestehende Detailpapiere prüfen

Danach:

- Rookie Salary / Dead Cap;
- Performance Salary / Criticality.

Prüfen, ob die Mechaniken zum gewünschten Teamfenster passen.

### Phase 3 – komplette Pakete vergleichen

Wenige kohärente Pakete definieren und mit identischen Kriterien bewerten.

### Phase 4 – Backtests und Simulation

Nur die ernsthaften Kandidaten quantitativ testen.

### Phase 5 – Ligabeschluss

Erst danach konkrete Regeln beschließen.

### Phase 6 – technische Umsetzung

Implementierung in App/Generator/Frontend ist ein separates Work Package und folgt dem beschlossenen fachlichen Modell.

---

## 10. Aktueller Gesamtstand

Bereits relativ weit geklärt:

- Rookie Year 1;
- Rookie Contract Year 2/3;
- Minimum Salary;
- Dead-Cap-Grundlogik;
- Performance-Salary-Problemstellung;
- dynamische statt statische Positional Criticality.

Noch fundamental offen:

- exakte Performance-/Criticality-Mathematik;
- gewünschte Team-Window-Ökonomie;
- ob echte Rebuilds überhaupt ein explizites Designziel werden;
- ob dafür zusätzliche persistente Mechaniken nötig sind;
- welche vollständige Kombination die Liga in der Offseason bevorzugt.

Die wichtigste Reihenfolge lautet deshalb:

> **Zuerst entscheiden, welches strategische Verhalten die Liga ermöglichen soll. Danach die Mechaniken darauf kalibrieren.**

Nicht umgekehrt.
