# Mighty Giants Roster Architecture

Purpose: kanonische Guardrail für die funktionale Roster-Struktur der Mighty Giants. Dieses Dokument ergänzt die allgemeinen Regeln in `FANTASY_MANAGEMENT_RULES.md` um eine verbindliche Zwei-Achsen-Klassifikation und ein bewusst geschütztes Flexibilitätsbudget.

## 1. Grundprinzip

Roster Management darf nicht nur vom harten Liga-Limit und der aktuellen Cut-Line ausgehen. Ein regelkonformes Roster kann trotzdem operativ zu voll sein, wenn nahezu jeder Platz mit einem Spieler belegt ist, der als dauerhafter Hold behandelt wird.

Deshalb werden zwei Fragen getrennt:

1. **Welche Funktion hat der Spieler im Team?**
2. **Wie sicher ist sein Rosterplatz?**

Ein Prospect ist nicht automatisch geschützt. Ein Starter ist nicht automatisch unantastbar. Ein Streamer ist keine dauerhafte Spielerrolle, sondern die Nutzung bewusst freigehaltener Roster-Kapazität.

## 2. Achse A: Roster Role

Verwende für jeden Mighty-Giants-Spieler genau eine primäre funktionale Rolle:

- `core_starter` – Teil des qualitativen Lineup-Kerns; soll regelmäßig starten, wenn gesund und verfügbar.
- `starter_rotation` – regelmäßig startbarer Spieler für feste Spots oder FLEX; nicht zwingend jede Woche gesetzt, aber klar oberhalb reiner Ersatzqualität.
- `backup` – belastbare Absicherung für Starter, Bye Weeks und Verletzungen; darf eigenständigen Markt-/Trade-Wert besitzen.
- `prospect` – primär gehalten wegen zukünftiger Rollen-, Talent- oder Marktwert-Upside; unmittelbare Weekly Utility ist sekundär.
- `specialist` – positionsspezifischer Spezialplatz, aktuell insbesondere Kicker.

`streamer` ist **keine** Roster Role.

Trade Chip, Cap Risk, Injury Insurance oder ähnliche Begriffe können zusätzliche Kontext-Tags sein, ersetzen aber nicht die primäre Rolle.

## 3. Achse B: Roster Security

Verwende separat genau eine aktuelle Sicherheitsstufe:

- `locked` – kein realistischer Add/Drop-/FA-Draft-Fall rechtfertigt einen Cut; nur fundamentale neue Information oder großer Trade-Kontext kann die Einstufung ändern.
- `strong_hold` – klar oberhalb der normalen Cut-/Streamer-Schwelle; ein Abgang benötigt einen materiellen Gegenwert oder eine starke neue Negativentwicklung.
- `hold` – aktuell sinnvoll zu halten, aber bei verändertem Rollen-, Markt-, Verletzungs- oder Roster-Kontext neu bewertbar.
- `conditional` – wertvoll genug für einen Rosterplatz, aber nahe genug an der Opportunity-Cost-Grenze, dass jeder relevante Add, Draft Pick oder Streaming-Bedarf einen direkten Vergleich auslöst.
- `churn` – bewusst austauschbarer Rosterplatz/-spieler; darf ohne Grundsatzänderung für klar bessere Free Agents, kurzfristige Streamer oder Notfallbedarf repurposed werden.

Roster Security ist dynamisch. Sie muss bei materiellen Änderungen neu abgeleitet werden und darf nicht aus einer alten Analyse fortgeschrieben werden.

## 4. Allgemeine Churn-Slot-Guardrail

Die Mighty Giants halten standardmäßig **zwei allgemeine aktive Churn-Slots** als operatives Flexibilitätsbudget frei.

Diese zwei Slots:

- müssen nicht leer sein;
- dürfen mit Upside-Spielern oder kurzfristigen Holds besetzt sein;
- müssen aber so besetzt sein, dass bei einem klaren Add-/Streaming-Bedarf zwei aktive Plätze ohne Opfer eines `locked`-, `strong_hold`- oder normalen `hold`-Kerns repurposed werden können;
- werden nach jeder relevanten Roster-Änderung neu zugewiesen.

Die Guardrail ist ein **Soft Cap für dauerhaft gebundene aktive Plätze**. Ein Roster, das das harte Liga-Limit einhält, aber keine zwei realistisch repurposable aktive Plätze mehr besitzt, gilt als operativ roster-clogged.

## 5. Was nicht als allgemeiner Churn-Slot zählt

Folgende Kapazität erfüllt die Zwei-Slot-Guardrail **nicht**:

- Taxi-Slots, weil sie ein separates Rookie-Entwicklungsbudget sind und nicht als frei verfügbare Weekly-Streaming-Kapazität behandelt werden dürfen;
- Reserve-/IR-Slots, weil ihre Nutzbarkeit von aktueller Eligibility abhängt und nicht dauerhaft planbar ist;
- der verpflichtende Kicker-Platz, auch wenn der gehaltene Kicker selbst `specialist | churn` sein kann.

Vor dem Taxi-Lock ist die **aktuelle Zuordnung** eines Rookies zu Taxi oder aktiver Bank austauschbar und deshalb kein Bewertungsargument. Trotzdem ersetzt die Taxi-Kapazität keinen allgemeinen Churn-Slot: Nach der jeweils optimalen virtuellen Taxi-Zuweisung müssen weiterhin zwei **aktive, positionsoffene** Plätze realistisch repurposable bleiben.

Der Kicker darf ohne große Bindung ausgetauscht werden. Sein notwendiger Lineup-Platz ersetzt aber keinen der zwei allgemeinen, positionsoffenen Churn-Slots.

Wenn zur Bye-Überbrückung temporär ein zweiter Kicker gehalten wird, verbraucht dieser zusätzliche Kicker einen allgemeinen Churn-Slot.

## 6. Temporärer Drei-Slot-Modus

Der Standard bleibt zwei allgemeine Churn-Slots.

Ein temporärer Zielwert von **drei** ist sinnvoll, wenn aktuelle In-Season-Bedingungen mehrere parallele kurzfristige Moves plausibel machen, zum Beispiel:

- starke Bye-Week-Konzentration;
- mehrere Verletzungen auf derselben knappen Position;
- gleichzeitiger QB- und Kicker-Streaming-Bedarf;
- außergewöhnlich aktiver Waiver-/Breakout-Zeitraum;
- Playoff-/Late-Season-Situationen, in denen kurzfristige Weekly Utility deutlich mehr wert ist als ein marginaler Prospect-Stash.

Der dritte Slot wird nicht pauschal dauerhaft erzwungen. Seine Opportunity Cost gegen den schwächsten Prospect/Hold muss positiv sein.

## 7. Transaktions-Guardrail

Vor jedem Add, Waiver Claim, Free-Agent-Draft-Pick oder ähnlichen Roster-Zugang:

1. aktuelle aktive Kapazität dynamisch aus `League.json` ableiten;
2. Taxi/Reserve separat nach aktueller Eligibility und aktueller Saisonphase behandeln;
3. solange der Taxi-Lock noch nicht erfolgt ist, alle Taxi-eligible Rookies gemeinsam ranken und die Taxi-Slots für die Rosterrechnung virtuell optimal zuweisen, statt die aktuelle Sleeper-Platzierung als fest anzunehmen;
4. Rolle und Security des eingehenden Spielers bestimmen;
5. den aktuell schwächsten realistisch repurposable aktiven Platz bestimmen;
6. prüfen, wie viele allgemeine Churn-Slots nach der Transaktion verbleiben;
7. wenn ein Churn-Slot in einen dauerhaften Hold umgewandelt wird, den **neuen** Churn-Boundary-Spieler explizit benennen;
8. den Move ablehnen, traden oder verschieben, wenn ein marginaler Zugang nur dadurch möglich wäre, dass operative Flexibilität ohne ausreichenden Mehrwert geopfert wird.

Für den Free-Agent Draft gilt insbesondere: Ein später Pick muss nicht genutzt werden, wenn der beste verfügbare Spieler den nächsten Mighty-Giants-Roster-Cut und den Verlust eines Churn-Slots nicht rechtfertigt.

## 8. Notfall- und Timing-Ausnahme

Eine kurzfristige Unterschreitung des Zwei-Slot-Ziels ist erlaubt, wenn Draft-/Waiver-/Transaction-Timing oder ein echter Notfall dies sinnvoll macht.

Dann muss die Analyse ausdrücklich festhalten:

- warum die Flexibilität vorübergehend unterschritten wird;
- welcher Spieler oder Slot der nächste Churn-Boundary-Kandidat ist;
- wann bzw. durch welchen Trigger die Zwei-Slot-Struktur wiederhergestellt werden soll.

Eine temporäre Ausnahme darf nicht stillschweigend zum neuen Normalzustand werden.

## 9. Taxi-Verhältnis und Lock

Taxi bleibt ein separates Rookie-Entwicklungsbudget mit zwei unterschiedlichen Phasen.

### Vor dem ersten Ligaspiel / vor dem Taxi-Lock

Bis zum ersten Ligaspiel können die Mighty Giants die Taxi-Belegung noch verändern. Für diese Pre-Lock-Phase gilt:

- alle aktuell Taxi-eligible Rookies können zwischen aktivem Roster/Bank und Taxi neu zugeordnet werden;
- die aktuelle Sleeper-Platzierung eines Rookies auf Taxi oder Bank besitzt **keinen Schutz- oder Bewertungswert**;
- alle Taxi-eligible Rookies werden als ein gemeinsamer Prospect-Pool gerankt;
- Cut-/Keep-/FA-Draft-Analysen entscheiden zuerst, welche Rookie-Assets insgesamt gehalten werden sollen;
- danach werden die verfügbaren Taxi-Slots **virtuell** den zwei sinnvollsten Entwicklungs-Stashes zugewiesen;
- Roster- und Churn-Rechnungen sollen in dieser Phase mit dieser optimalen virtuellen Taxi-Zuweisung arbeiten, nicht mit einer zufälligen aktuellen Taxi-Belegung;
- die zwei virtuellen Taxi-Spieler sind Entwicklungs-Stashes und zählen weiterhin nicht als die zwei allgemeinen aktiven Churn-Slots.

### Taxi-Entscheidung vor dem Lock

Unmittelbar vor dem ersten Ligaspiel muss eine explizite Taxi-Entscheidung getroffen werden:

1. alle dann Taxi-eligible Rookies mit aktuellen Rollen-, Injury-, Markt-, Draftkapital- und Opportunity-Daten neu ranken;
2. die zwei besten Spieler auswählen, deren kurzfristige Lineup-Utility am ehesten verzichtbar ist und deren Entwicklungs-/Upside-Wert durch Taxi am sinnvollsten konserviert wird;
3. prüfen, welche Rookies wegen erwarteter früher Weekly Utility besser aktiv bleiben sollten;
4. erst danach die finale Taxi-Belegung festlegen.

### Nach dem Taxi-Lock

Nach Beginn des ersten Ligaspiels sind die zwei Taxi-Slots für die weitere Saison **nicht mehr frei austauschbar**. Ab diesem Zeitpunkt:

- wird die tatsächliche Taxi-Zuordnung zu einer realen Roster-Restriktion;
- darf eine Analyse nicht mehr stillschweigend einen anderen Rookie in einen Taxi-Slot umsortieren;
- müssen spätere Änderungen nach den dann geltenden Liga-/Sleeper-Mechaniken bewertet werden statt nach der Pre-Lock-Flexibilität.

Taxi ersetzt in keiner Phase allgemeine aktive Churn-Kapazität.

## 10. Anwendung auf Analysen

Roster Audits, Cut-Analysen, FA-Boards und Weekly Waiver/Lineup Decisions sollen künftig mindestens ausweisen:

- `roster_role` je relevanter Mighty-Giants-Spieler;
- `roster_security` je relevanter Mighty-Giants-Spieler;
- aktuelle harte aktive Kapazität;
- aktuelle Taxi-Phase: `pre_lock` oder `locked`;
- bei `pre_lock`: den gemeinsam bewerteten Taxi-eligible Rookie-Pool und die aktuell optimale **virtuelle** Taxi-Zuweisung;
- bei `locked`: die tatsächliche bindende Taxi-Zuweisung;
- aktuelle Anzahl allgemeiner Churn-Slots;
- aktuelle Churn-/Conditional-Boundary;
- ob die Zwei-Slot-Guardrail eingehalten wird;
- welcher Spieler bei einem geplanten Zugang zum neuen Boundary-Spieler würde.

Aktuelle Spielerzuordnungen gehören in datierte Analysen unter `fantasy-management/analyses/` und nicht als permanente Wahrheit in dieses Dokument.
