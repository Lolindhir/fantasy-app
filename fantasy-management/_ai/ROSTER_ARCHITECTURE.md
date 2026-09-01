# Mighty Giants Roster Architecture

Purpose: kanonische Guardrail für die funktionale Roster-Struktur der Mighty Giants. Dieses Dokument ergänzt die allgemeinen Regeln in `FANTASY_MANAGEMENT_RULES.md` um eine verbindliche Zwei-Achsen-Klassifikation, positionsspezifische Coverage und ein bewusst geschütztes Flexibilitätsbudget.

## 1. Grundprinzip

Roster Management darf nicht nur vom harten Liga-Limit und der aktuellen Cut-Line ausgehen. Ein regelkonformes Roster kann trotzdem operativ zu voll sein, wenn nahezu jeder Platz mit einem Spieler belegt ist, der als dauerhafter Hold behandelt wird. Umgekehrt darf Churn-Flexibilität nicht dadurch erzeugt werden, dass eine feste Starterposition strukturell unterbesetzt wird.

Deshalb werden vier Ebenen getrennt:

1. **Welche Funktion hat der Spieler im Team?**
2. **Wie sicher ist sein Rosterplatz?**
3. **Welche positionsspezifische Starter-/Backup-Coverage muss das Roster tragen?**
4. **Wie viel allgemeine operative Churn-Kapazität bleibt danach übrig?**

Ein Prospect ist nicht automatisch geschützt. Ein Starter ist nicht automatisch unantastbar. Ein Streamer ist keine dauerhafte Spielerrolle, sondern die Nutzung bewusst freigehaltener Roster-Kapazität. Ein nominell schwächerer Spieler kann wegen knapper Positions-Coverage wertvoller für die Roster-Struktur sein als ein isoliert höher gerankter Spieler auf einer bereits überversorgten Position.

## 2. Achse A: Roster Role

Verwende für jeden Mighty-Giants-Spieler genau eine primäre funktionale Rolle:

- `core_starter` – Teil des qualitativen Lineup-Kerns; soll regelmäßig starten, wenn gesund und verfügbar.
- `starter_rotation` – regelmäßig startbarer Spieler für feste Spots oder FLEX; nicht zwingend jede Woche gesetzt, aber klar oberhalb reiner Ersatzqualität.
- `backup` – belastbare Absicherung für Starter, Bye Weeks und Verletzungen; darf eigenständigen Markt-/Trade-Wert besitzen.
- `prospect` – primär gehalten wegen zukünftiger Rollen-, Talent- oder Marktwert-Upside; unmittelbare Weekly Utility ist sekundär.
- `specialist` – positionsspezifischer Spezialplatz, aktuell insbesondere Kicker.

`streamer` ist **keine** Roster Role.

Trade Chip, Cap Risk, Injury Insurance, Coverage Reserve oder ähnliche Begriffe können zusätzliche Kontext-Tags sein, ersetzen aber nicht die primäre Rolle.

## 3. Achse B: Roster Security

Verwende separat genau eine aktuelle Sicherheitsstufe:

- `locked` – kein realistischer Add/Drop-/FA-Draft-Fall rechtfertigt einen Cut; nur fundamentale neue Information oder großer Trade-Kontext kann die Einstufung ändern.
- `strong_hold` – klar oberhalb der normalen Cut-/Streamer-Schwelle; ein Abgang benötigt einen materiellen Gegenwert oder eine starke neue Negativentwicklung.
- `hold` – aktuell sinnvoll zu halten, aber bei verändertem Rollen-, Markt-, Verletzungs- oder Roster-Kontext neu bewertbar.
- `conditional` – wertvoll genug für einen Rosterplatz, aber nahe genug an der Opportunity-Cost-Grenze, dass jeder relevante Add, Draft Pick oder Streaming-Bedarf einen direkten Vergleich auslöst.
- `churn` – bewusst austauschbarer Rosterplatz/-spieler; darf ohne Grundsatzänderung für klar bessere Free Agents, kurzfristige Streamer oder Notfallbedarf repurposed werden.

Roster Security ist dynamisch. Sie muss bei materiellen Änderungen neu abgeleitet werden und darf nicht aus einer alten Analyse fortgeschrieben werden.

## 4. Positionsspezifische Coverage-Guardrail

### 4.1 Starter-Minimum immer dynamisch ableiten

Vor jeder Roster-, Cut-, Waiver-, FA-Draft- oder Lineup-Entscheidung werden die festen Starteranforderungen aus dem aktuellen `League.json -> RosterSize` neu abgeleitet.

Für jede Position gilt:

- `fixed_starter_requirement` = Anzahl der festen Starter-Slots dieser Position in `RosterSize`;
- FLEX-Slots werden separat mit ihrer tatsächlichen Eligibility behandelt;
- Kicker und andere Spezialpositionen werden separat betrachtet;
- keine früher dokumentierte Starterzahl wird als dauerhaft kanonisch fortgeschrieben.

Das harte Minimum ist nur die Unterkante. Ein Roster mit exakt so vielen Spielern wie feste Starterplätze ist strukturell fragil, sobald Injury oder Bye auftreten.

### 4.2 Coverage Floor und Preferred Coverage

Für Positionen mit festen Starterplätzen wird zusätzlich zur Starterzahl eine aktuelle Coverage-Zone bestimmt:

- `coverage_floor` – niedrigste vertretbare aktive Positionsabdeckung, unter die Mighty Giants ohne bewusst geplanten Stream-/Notfallpfad nicht gehen sollen;
- `preferred_coverage` – aktuell gewünschte Positionsabdeckung, wenn der zusätzliche Spieler gegenüber seiner Roster-Opportunity-Cost sinnvoll ist.

Diese Werte sind **keine statischen Liga-Konstanten**. Sie werden aus folgenden Faktoren abgeleitet:

- Anzahl fester Starterplätze;
- FLEX-Einfluss und Positions-Elastizität;
- aktueller Free-Agent-Replacement-Level der Position;
- Qualität der vorhandenen Backups;
- Injury- und Bye-Risiko mehrerer gleichzeitiger Ausfälle;
- wie teuer ein kurzfristiger Streamer realistisch verfügbar wäre;
- Dynasty-/Trade-Wert der Coverage-Spieler;
- Gesamt-Roster-Druck und verfügbare Churn-Kapazität.

Ein Coverage-Spieler ist nicht automatisch `strong_hold`. Seine Positionsfunktion ist ein zusätzlicher Opportunity-Cost-Faktor, der zusammen mit Qualität, Marktwert und Replacement Level bewertet wird.

### 4.3 QB-/TE-artige knappe Pflichtpositionen

Bei Positionen mit mehreren festen Starterplätzen und begrenzter interner Substituierbarkeit ist Backup-Coverage besonders wichtig.

Wenn das Entfernen eines Spielers dazu führen würde, dass bereits eine normale Kombination aus Injury + Bye oder zwei parallelen Ausfällen mehrere externe Streamer erzwingt, muss dieser zusätzliche strukturelle Preis ausdrücklich in die Cut-/Trade-Entscheidung eingehen.

Ein Spieler darf nicht allein deshalb zum Churn-Spieler werden, weil er isoliert schwächer bewertet ist, wenn sein Abgang die Position unter den aktuellen `coverage_floor` drücken würde.

### 4.4 Gemeinsamer FLEX-/Skill-Pool

RB, WR, TE und andere aktuell FLEX-eligible Positionen dürfen nicht nur getrennt nach Positionszahl bewertet werden.

Zusätzlich wird ein gemeinsamer `startable_skill_pool` betrachtet:

- `required_skill_lineup_slots` = feste Starter-Slots der FLEX-eligible Skill-Positionen plus aktuelle FLEX-Slots;
- `startable_skill_pool` = Mighty-Giants-Spieler dieser Positionen, die nach aktueller Bewertung als `core_starter` oder `starter_rotation` tatsächlich realistisch startbar sind;
- `skill_pool_margin` = `startable_skill_pool` minus `required_skill_lineup_slots`.

Backups und Prospects werden separat ausgewiesen und dürfen die Startable-Marge nicht künstlich aufblasen.

Wenn der Skill-Pool komfortabel über dem Bedarf liegt, darf das untere RB-/WR-/TE-Ende stärker nach Upside, Marktwert und Churnability optimiert werden. Wenn die Marge klein wird, steigt der Wert belastbarer Backups.

### 4.5 Kicker als Spezialfall

Der Default bleibt genau ein gehaltener Kicker.

- Der notwendige Kicker-Platz ist ein eigener Spezialplatz und zählt nicht als allgemeiner Churn-Slot.
- Der gehaltene Kicker kann `specialist | churn` sein.
- Ein zweiter Kicker wird nur temporär über einen allgemeinen Churn-Slot gehalten, wenn der Weekly-Kontext dies rechtfertigt.

### 4.6 Coverage vor Churn

Die strukturelle Reihenfolge lautet künftig:

1. feste Starteranforderungen aus `RosterSize` ableiten;
2. positionsspezifischen `coverage_floor` und `preferred_coverage` bestimmen;
3. gemeinsamen FLEX-/Skill-Pool und seine Startable-Marge prüfen;
4. Taxi nach aktueller Pre-Lock-/Locked-Mechanik optimieren;
5. erst danach allgemeine Churn-Slots und Churn-Boundary bestimmen.

Ein Platz kann nur dann als allgemeiner Churn-Slot gezählt werden, wenn seine Repurposierung die relevante Positions-Coverage nicht unter den aktuellen Floor drückt.

## 5. Allgemeine Churn-Slot-Guardrail

Die Mighty Giants halten standardmäßig **zwei allgemeine aktive Churn-Slots** als operatives Flexibilitätsbudget frei.

Diese zwei Slots:

- müssen nicht leer sein;
- dürfen mit Upside-Spielern oder kurzfristigen Holds besetzt sein;
- müssen aber so besetzt sein, dass bei einem klaren Add-/Streaming-Bedarf zwei aktive Plätze ohne Opfer eines `locked`-, `strong_hold`- oder normalen `hold`-Kerns repurposed werden können;
- dürfen nicht nur theoretisch frei sein, wenn ihr Verlust eine Position unter den aktuellen Coverage Floor drückt;
- werden nach jeder relevanten Roster-Änderung neu zugewiesen.

Die Guardrail ist ein **Soft Cap für dauerhaft gebundene aktive Plätze**. Ein Roster, das das harte Liga-Limit einhält, aber keine zwei realistisch repurposable aktive Plätze mehr besitzt, gilt als operativ roster-clogged.

## 6. Was nicht als allgemeiner Churn-Slot zählt

Folgende Kapazität erfüllt die Zwei-Slot-Guardrail **nicht**:

- Taxi-Slots, weil sie ein separates Rookie-Entwicklungsbudget sind und nicht als frei verfügbare Weekly-Streaming-Kapazität behandelt werden dürfen;
- Reserve-/IR-Slots, weil ihre Nutzbarkeit von aktueller Eligibility abhängt und nicht dauerhaft planbar ist;
- der verpflichtende Kicker-Platz, auch wenn der gehaltene Kicker selbst `specialist | churn` sein kann;
- ein scheinbar austauschbarer Spieler, dessen Entfernung die Position unter den aktuellen `coverage_floor` drücken würde.

Vor dem Taxi-Lock ist die **aktuelle Zuordnung** eines Rookies zu Taxi oder aktiver Bank austauschbar und deshalb kein Bewertungsargument. Trotzdem ersetzt die Taxi-Kapazität keinen allgemeinen Churn-Slot: Nach der jeweils optimalen virtuellen Taxi-Zuweisung müssen weiterhin zwei **aktive, positionsoffene** Plätze realistisch repurposable bleiben.

Der Kicker darf also ohne große Bindung ausgetauscht werden. Sein notwendiger Lineup-Platz ersetzt aber keinen der zwei allgemeinen, positionsoffenen Churn-Slots.

Wenn zur Bye-Überbrückung temporär ein zweiter Kicker gehalten wird, verbraucht dieser zusätzliche Kicker einen allgemeinen Churn-Slot.

## 7. Temporärer Drei-Slot-Modus

Der Standard bleibt zwei allgemeine Churn-Slots.

Ein temporärer Zielwert von **drei** ist sinnvoll, wenn aktuelle In-Season-Bedingungen mehrere parallele kurzfristige Moves plausibel machen, zum Beispiel:

- starke Bye-Week-Konzentration;
- mehrere Verletzungen auf derselben knappen Position;
- gleichzeitiger QB- und Kicker-Streaming-Bedarf;
- außergewöhnlich aktiver Waiver-/Breakout-Zeitraum;
- Playoff-/Late-Season-Situationen, in denen kurzfristige Weekly Utility deutlich mehr wert ist als ein marginaler Prospect-Stash.

Der dritte Slot wird nicht pauschal dauerhaft erzwungen. Seine Opportunity Cost gegen den schwächsten Prospect/Hold muss positiv sein und darf die Coverage Floors nicht verletzen.

## 8. Transaktions-Guardrail

### 8.1 Free-Agent-Draft Availability Gate (fail-closed)

Für den Free-Agent Draft werden **Discovery** und **Availability** strikt getrennt.

Preboards, Monitoring-/Watchlists, externe Rankings/ADPs, FantasyCalc-/ECR-Signale, Free-Agent-Movement-Discovery, News und In-Draft-Cuts dürfen Kandidaten **finden und priorisieren**, sind aber keine kanonische Quelle dafür, ob ein Spieler tatsächlich noch verfügbar ist.

Ein Spieler darf für einen laufenden Free-Agent Draft nur dann den Status `available` erhalten und in einer verfügbaren Shortlist oder Pick-Empfehlung erscheinen, wenn beide Prüfungen positiv abgeschlossen sind:

1. **Ownership-Check gegen aktuelles `public/data/League.json`:** Die PlayerID steht bei **keinem** Team in `Roster`, `Taxi` oder `Reserve`.
2. **Draftstatus-Check gegen aktuelles `public/data/Drafts.json`:** Die PlayerID ist im aktuellen Free-Agent-Draft nicht bereits mit `Status: Picked` einem früheren Pick zugeordnet.

Die Prüfung ist **fail-closed**:

- fehlt eine der beiden kanonischen Quellen, ist sie erkennbar veraltet, unvollständig oder lässt sich die PlayerID nicht eindeutig auflösen, lautet der Availability-Status `unknown` und **nicht** `available`;
- `unknown`-Spieler dürfen nicht als freie Optionen, Value-Falls oder Pick-Empfehlungen dargestellt werden, bis die Unsicherheit aufgelöst ist;
- externe Ranking-, ADP-, Marktwert-, Depth-Chart- oder Monitoring-Daten dürfen Ownership niemals überschreiben oder implizieren;
- ein Spieler, der in `League.json` rostered/taxi/reserve ist, bleibt unabhängig von externen Free-Agent-Listen **nicht verfügbar**;
- ein Spieler, der noch nicht im League-Roster materialisiert ist, aber im laufenden `Drafts.json` bereits gepickt wurde, bleibt ebenfalls **nicht verfügbar**.

Vor **jedem eigenen FA-Draft-Pick** und nach jedem materiellen gegnerischen Pick/Cut muss die relevante Shortlist erneut gegen beide kanonischen Quellen validiert werden. Bei dynamischen Drafts darf ein früher im Chat bestätigter Availability-Status nicht ungeprüft fortgeschrieben werden.

Erst nach bestandener Availability-Prüfung wird die eigentliche Mighty-Giants-Opportunity-Cost gegen Rosterstruktur, Coverage, Taxi/Reserve, Churn-Slots und nächsten Cut bewertet.

### 8.2 Roster- und Opportunity-Cost-Prüfung

Vor jedem Add, Waiver Claim, Free-Agent-Draft-Pick oder ähnlichen Roster-Zugang:

1. aktuelle Starterstruktur und aktive Kapazität dynamisch aus `League.json` ableiten;
2. aktuellen `coverage_floor` / `preferred_coverage` je relevante Position bestimmen;
3. gemeinsamen `startable_skill_pool` und seine Marge gegen die benötigten Skill-Lineup-Slots prüfen;
4. Taxi/Reserve separat nach aktueller Eligibility und aktueller Saisonphase behandeln;
5. solange der Taxi-Lock noch nicht erfolgt ist, alle Taxi-eligible Rookies gemeinsam ranken und die Taxi-Slots für die Rosterrechnung virtuell optimal zuweisen, statt die aktuelle Sleeper-Platzierung als fest anzunehmen;
6. Rolle und Security des eingehenden Spielers bestimmen;
7. den aktuell schwächsten realistisch repurposable aktiven Platz bestimmen, der keine Coverage-Grenze verletzt;
8. prüfen, wie viele allgemeine Churn-Slots nach der Transaktion verbleiben;
9. wenn ein Churn-Slot in einen dauerhaften Hold umgewandelt wird, den **neuen** Churn-Boundary-Spieler explizit benennen;
10. den Move ablehnen, traden oder verschieben, wenn ein marginaler Zugang nur dadurch möglich wäre, dass Coverage oder operative Flexibilität ohne ausreichenden Mehrwert geopfert wird.

Für den Free-Agent Draft gilt insbesondere: Ein später Pick muss nicht genutzt werden, wenn der beste **validiert verfügbare** Spieler den nächsten Mighty-Giants-Roster-Cut, die Positions-Coverage und den Verlust eines Churn-Slots nicht rechtfertigt.

### 8.3 Folgejahres-Retention- und Salary-Guardrail

Bei finalen Cut-/Keep-, Roster-Limit- und FA-Draft-Opportunity-Cost-Entscheidungen wird nicht nur eine aktuelle `cut_line`, sondern zusätzlich eine **Retention-Line** für den nächsten relevanten Cap-/Roster-Zyklus bewertet.

Für jeden Spieler an oder nahe dieser Grenze müssen mindestens folgende Dimensionen gemeinsam betrachtet werden:

1. **Current-season Mighty-Giants utility:** Wie wahrscheinlich ist es, dass der Spieler in der aktuellen Saison tatsächlich einen festen Starter-, FLEX-, Coverage- oder wertvollen Injury-Insurance-Beitrag für Mighty Giants liefert?
2. **Dynasty-/Trade-Asset-Wert:** Welchen langfristigen Markt-, Trade- und Replacement-Wert verliert Mighty Giants bei einem Abgang?
3. **Folgejahres-Salary-Risiko:** Wie hoch ist das aktuelle `SalaryProjected` relativ zum dann relevanten League-Cap und zur erwartbaren Teamrolle? Die Berechnung des League-Caps und `SalaryRelevantTeamSize` wird aus den aktuellen League-/App-Daten übernommen und nicht aus einer alten Annahme fortgeschrieben.
4. **Cap-adjustierte Alternative:** Welchen Spieler oder Rosterplatz könnte Mighty Giants stattdessen mit geringerem Salary-Risiko halten, insbesondere einen Rookie/Prospect mit noch unvollständiger Salary-Historie?
5. **Retention-Horizon:** Ist der Spieler bei unverändertem Rollen-/Marktbild realistisch auch im nächsten Cap-Zyklus ein sinnvoller und finanzierbarer Hold, oder wird sein Rosterplatz sehr wahrscheinlich ohnehin wieder freigesetzt?
6. **Exit-Option:** Besteht vor einem Cut ein realistischer Trade-, Package- oder späterer Cut-Pfad, mit dem aktueller Produktions-/Asset-Wert noch genutzt werden kann?

Die Retention-Line kann deshalb von einer reinen Redraft-, Dynasty- oder Marktwert-Reihenfolge abweichen. Insbesondere darf ein etablierter Veteran trotz höherem aktuellen Redraft-Rank unter einen günstigeren jungen Asset-Hold fallen, wenn seine **marginale** Mighty-Giants-Lineup-Utility klein, sein Folgejahres-Salary-Risiko hoch, seine langfristige Retention-Wahrscheinlichkeit niedrig und die Alternative als Prospect-Asset attraktiver ist.

Gleichzeitig gilt ausdrücklich:

- Salary bleibt ein Cap-/Roster-Management-Signal und **kein** primäres Talent-, Qualitäts- oder Player-Rank-Signal;
- ein Salary- oder `SalaryProjected`-Wert von `0` bei Rookies/Young Players kann aus fehlender Dreijahreshistorie entstehen und ist kein automatischer Surplus-Value-Beweis;
- ein produktiver Veteran wird nicht allein wegen eines hypothetisch hohen Folgejahres-Salary früh geopfert, wenn er aktuell materiell zur Championship-Wahrscheinlichkeit beiträgt oder noch sinnvollen Trade-Wert besitzt;
- bei einem möglichen „jetzt cutten vs. später cutten“-Fall muss der Nutzen des zusätzlichen aktuellen Jahres gegen den Verlust des günstigen Alternativ-Assets und gegen die Exit-Option abgewogen werden;
- bei sehr tiefen Mighty-Giants-Positionsgruppen zählt nicht die generische Startbarkeit des Veteranen, sondern seine **wahrscheinliche tatsächliche Nutzung im Mighty-Giants-Lineup**;
- Coverage Floors, Taxi-Regeln und notwendige Spezialplätze dürfen durch Salary-Optimierung nicht stillschweigend verletzt werden.

Kernfrage der Retention-Line:

**Welcher Spieler liefert Mighty Giants über den aktuellen und nächsten Cap-/Roster-Zyklus den höheren erwarteten Teamwert pro gebundenem Rosterplatz und Cap-Risiko, nachdem aktuelle Weekly Utility, Asset-Liquidität, Coverage, Upside und Exit-Option gemeinsam berücksichtigt wurden?**

## 9. Notfall- und Timing-Ausnahme

Eine kurzfristige Unterschreitung des Zwei-Slot-Ziels oder einer Preferred-Coverage-Zone ist erlaubt, wenn Draft-/Waiver-/Transaction-Timing oder ein echter Notfall dies sinnvoll macht.

Dann muss die Analyse ausdrücklich festhalten:

- warum Coverage oder Flexibilität vorübergehend unterschritten wird;
- welcher Spieler oder Slot der nächste Churn-/Coverage-Boundary-Kandidat ist;
- welcher Stream-/Waiver-Pfad die Position im Bedarfsfall absichert;
- wann bzw. durch welchen Trigger die Zielstruktur wiederhergestellt werden soll.

Eine temporäre Ausnahme darf nicht stillschweigend zum neuen Normalzustand werden.

## 10. Taxi-Verhältnis und Lock

Taxi bleibt ein separates Rookie-Entwicklungsbudget mit zwei unterschiedlichen Phasen.

### Vor dem ersten Ligaspiel / vor dem Taxi-Lock

Bis zum ersten Ligaspiel können die Mighty Giants die Taxi-Belegung noch verändern. Für diese Pre-Lock-Phase gilt:

- alle aktuell Taxi-eligible Rookies können zwischen aktivem Roster/Bank und Taxi neu zugeordnet werden;
- die aktuelle Sleeper-Platzierung eines Rookies auf Taxi oder Bank besitzt **keinen Schutz- oder Bewertungswert**;
- alle Taxi-eligible Rookies werden als ein gemeinsamer Prospect-Pool gerankt;
- Cut-/Keep-/FA-Draft-Analysen entscheiden zuerst, welche Rookie-Assets insgesamt gehalten werden sollen;
- danach werden die verfügbaren Taxi-Slots **virtuell** den zwei sinnvollsten Entwicklungs-Stashes zugewiesen;
- die virtuelle Taxi-Auswahl muss berücksichtigen, ob ein Rookie für die aktive Positions-Coverage oder frühe Weekly Utility gebraucht wird;
- Roster-, Coverage- und Churn-Rechnungen sollen in dieser Phase mit dieser optimalen virtuellen Taxi-Zuweisung arbeiten, nicht mit einer zufälligen aktuellen Taxi-Belegung;
- die zwei virtuellen Taxi-Spieler sind Entwicklungs-Stashes und zählen weiterhin nicht als die zwei allgemeinen aktiven Churn-Slots.

### Taxi-Entscheidung vor dem Lock

Unmittelbar vor dem ersten Ligaspiel muss eine explizite Taxi-Entscheidung getroffen werden:

1. alle dann Taxi-eligible Rookies mit aktuellen Rollen-, Injury-, Markt-, Draftkapital- und Opportunity-Daten neu ranken;
2. die zwei besten Spieler auswählen, deren kurzfristige Lineup-/Coverage-Utility am ehesten verzichtbar ist und deren Entwicklungs-/Upside-Wert durch Taxi am sinnvollsten konserviert wird;
3. prüfen, welche Rookies wegen erwarteter früher Weekly Utility oder Positions-Coverage besser aktiv bleiben sollten;
4. erst danach die finale Taxi-Belegung festlegen.

### Nach dem Taxi-Lock

Nach Beginn des ersten Ligaspiels sind die zwei Taxi-Slots für die weitere Saison **nicht mehr frei austauschbar**. Ab diesem Zeitpunkt:

- wird die tatsächliche Taxi-Zuordnung zu einer realen Roster-Restriktion;
- darf eine Analyse nicht mehr stillschweigend einen anderen Rookie in einen Taxi-Slot umsortieren;
- müssen spätere Änderungen nach den dann geltenden Liga-/Sleeper-Mechaniken bewertet werden statt nach der Pre-Lock-Flexibilität.

Taxi ersetzt in keiner Phase allgemeine aktive Churn-Kapazität.

## 11. Anwendung auf Analysen

Roster Audits, Cut-Analysen, FA-Boards und Weekly Waiver/Lineup Decisions sollen künftig mindestens ausweisen:

- `roster_role` je relevanter Mighty-Giants-Spieler;
- `roster_security` je relevanter Mighty-Giants-Spieler;
- aktuelle harte aktive Kapazität;
- dynamisch abgeleitete feste Starteranforderungen je Position;
- aktuellen `coverage_floor` und `preferred_coverage` je relevante feste Position;
- aktuellen `startable_skill_pool`, `required_skill_lineup_slots` und `skill_pool_margin`;
- aktuelle Taxi-Phase: `pre_lock` oder `locked`;
- bei `pre_lock`: den gemeinsam bewerteten Taxi-eligible Rookie-Pool und die aktuell optimale **virtuelle** Taxi-Zuweisung;
- bei `locked`: die tatsächliche bindende Taxi-Zuweisung;
- aktuelle Anzahl allgemeiner Churn-Slots;
- aktuelle Churn-/Conditional-Boundary;
- ob Coverage- und Zwei-Slot-Guardrails eingehalten werden;
- bei Free-Agent-Draft-Boards: `availability_status` (`available`, `unavailable`, `unknown`) und die für die Verfügbarkeitsprüfung verwendeten `League.json`-/`Drafts.json`-Stände;
- bei finalen Cut-/Keep- und FA-Draft-Opportunity-Cost-Entscheidungen für alle Grenzfälle: aktuelles `SalaryProjected`, erwartete Mighty-Giants-Lineup-/Coverage-Utility, Dynasty-/Trade-Asset-Wert, `retention_risk` und realistische Exit-Option;
- bei Salary-relevanten Entscheidungen den aktuellen League-Cap-/`SalaryRelevantTeamSize`-Kontext ausweisen und Salary klar von Spielerqualität trennen;
- welcher Spieler bei einem geplanten Zugang zum neuen Coverage-, Churn- oder Retention-Boundary-Spieler würde.

Aktuelle Spielerzuordnungen und konkrete Coverage-, Salary- und Retention-Bewertungen gehören in datierte Analysen unter `fantasy-management/analyses/` und nicht als permanente Wahrheit in dieses Dokument.
