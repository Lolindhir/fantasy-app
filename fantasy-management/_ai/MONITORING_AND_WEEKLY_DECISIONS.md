# Daily Monitoring vs. Weekly Lineup + Waiver Decisions

## Zweck

Diese Datei definiert die dauerhafte Trennung zwischen laufender Fantasy-Operations-Beobachtung und konkreten wöchentlichen Entscheidungen.

Für qualitative `entity-observation`-Baselines ist `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md` der autoritative Storage-Vertrag. Daily Monitoring muss für Baseline-Vergleiche den effektiven Base+Shard-State verwenden; vorhandene Target-Shards haben Vorrang vor dem entsprechenden Target im großen Migration-Base-Snapshot. Geplante dauerhafte Baseline-Änderungen werden nach Freigabe als kleiner Target-Shard vorgeschlagen, nicht als Full-Replacement von `entity-observation.json`.

Die zentrale Architekturregel lautet:

> Positionsspezifische Analysebausteine liefern strukturierte Signale, Vergleichslogik und Research-Priorität. Daily Monitoring erkennt materielle Veränderungen. Die endgültige Start-/Sit-, Add-/Drop-, Waiver- und Roster-Entscheidung gehört in einen übergeordneten Entscheidungsworkflow, der alle Positionen und die Opportunity Cost des gesamten Rosters gemeinsam bewertet.

Damit wird verhindert, dass ein positionsspezifisches Modul — etwa Kicker Streaming — isoliert eine Transaktion empfiehlt, obwohl der notwendige Drop eines anderen Spielers für das Gesamtsystem teurer wäre als der erwartete Positionsgewinn.

## 1. Ebenenmodell

### Ebene A: Source Refresh und deterministische Materialisierung

Aufgabe:

- interne League-/Roster-Daten aktuell halten;
- externe Rankings, ADP, Projections und Activity-Signale aktualisieren;
- provider-neutrale Derived Datasets materialisieren;
- Fantasy-Ownership, Identitäten, Freshness und Datenqualität deterministisch vorbereiten.

Diese Ebene darf keine Fantasy-Empfehlung treffen.

Beispiele:

- `source-freshness.json`;
- `player-signals.json`;
- `free-agent-signals.json`;
- `kicker-streaming-inputs.json`;
- externe Ranking-/Projection-Snapshots;
- Sleeper Trending Relevance.

### Ebene B: Daily Monitoring

Aufgabe:

- den zuletzt erfolgreich veröffentlichten kanonischen Operations-State lesen;
- vor jeder Event-Interpretation `source-freshness.json` als Readiness-Gate auswerten;
- Veränderungen gegenüber einem vorherigen guten Zustand erkennen;
- nur materielle Änderungen melden;
- Ursache und betroffene Entscheidungsklasse benennen;
- Research-Priorität setzen;
- bei Bedarf frische qualitative Verifikation auslösen.

Für den Freshness-Guardrail gilt:

- `decision = block`: normales Monitoring unterlassen und nur die blockierende Freshness-/Datenqualitätsursache sichtbar machen;
- `decision = proceed_degraded`: nur weiterhin frisch unterstützte Signalbereiche interpretieren und `affected_signal_families` beachten;
- `no_event_conclusion_allowed = false`: einen leeren Event-Contract niemals als belastbaren „keine Änderung“-Befund ausgeben;
- Readiness niemals aus Uhrzeit, geplantem 06:45-Materializer oder dessen erwartetem Abschluss ableiten.

Daily Monitoring beantwortet:

> Was hat sich seit der letzten relevanten Beobachtung verändert und welche spätere Entscheidung könnte dadurch neu bewertet werden müssen?

Daily Monitoring beantwortet nicht:

> Wen soll ich diese Woche starten, adden oder droppen?

### Ebene C: Positionsspezifische Analysebausteine

Diese Module modellieren Speziallogik einer Position oder Entscheidungskomponente.

Beispiele:

- Kicker Streaming;
- später mögliche QB-/TE-Ersatzniveau- oder Matchup-Komponenten;
- Usage-/Opportunity-Bewertung;
- Injury-/Availability-Gates.

Ein Modul darf:

- Kandidaten vergleichen;
- positionsspezifische Scores erzeugen;
- Eligibility-Gates anwenden;
- konkrete Research-Shortlists liefern.

Ein Modul darf nicht isoliert den globalen Rosterpreis einer Transaktion ignorieren.

### Ebene D: Weekly Lineup + Waiver Decision Workflow

Diese Ebene kombiniert alle relevanten Positionsmodule und entscheidet aus Sicht des vollständigen verwalteten Rosters.

Sie beantwortet:

- Welche Spieler sollen diese Woche starten?
- Welche Bench-Spieler sind als Injury-/Bye-Absicherung wichtig?
- Gibt es auf dem Waiver/Free-Agent-Markt einen materiellen Upgrade?
- Welcher aktuelle Spieler müsste für einen Add gedroppt werden?
- Ist der erwartete Wochen- oder Mehrwochenvorteil größer als der Wert des verlorenen Roster-Slots?
- Welche Entscheidung ist zeitkritisch und welche kann beobachtet werden?

## 2. Daily Monitoring: fachlicher Zielzustand

Der Daily-Monitoring-Workflow soll langfristig vier Populationen abdecken:

1. vollständiger Managed Roster;
2. relevante Fantasy Free Agents;
3. gegnerische Fantasy-Roster und für Trades/Knappheit relevante Spieler;
4. NFL-Team-/Positionsgruppen-Kontext, wenn eine gemeinsame Ursache mehrere Spieler verändert.

### Beobachtungsdimensionen

Je nach Position und Verfügbarkeit:

- Injury und Availability;
- Rolle und Opportunity;
- Usage;
- Dynasty-Marktbewegung;
- Redraft-/Short-Term-ADP;
- Projections;
- Transactions und NFL-Teamwechsel;
- Liga-Ownership;
- Sleeper Activity und andere aktuelle Plattformaktivität;
- positionsspezifische Signale.

### Materialitätsprinzip

Daily Monitoring soll nicht jede Zahlenänderung melden.

Meldenswert sind nur Veränderungen, die wahrscheinlich mindestens eine dieser Fragen neu öffnen:

- Muss ein eigener Spieler ersetzt oder anders priorisiert werden?
- Ist ein Free Agent neu relevant geworden?
- Hat sich ein Trade-/Market-Fenster materiell verändert?
- Hat ein Gegner eine wichtige Ressource verloren oder gewonnen?
- Hat sich eine Rolle, Verletzung oder Availability so verändert, dass eine baldige Entscheidung neu bewertet werden muss?

### No-op-Prinzip

Unveränderte Zustände bleiben still.

Eine neue Quelle, ein neues Target oder eine neue Baseline ist nicht allein deshalb ein Nutzer-Event.

### Research-Prinzip

Teure oder qualitative Live-Recherche wird nicht blind für jede Entität jeden Tag wiederholt.

Sie wird priorisiert bei:

- konkreten Datenänderungen;
- neuen Injury-/Role-/Transaction-Signalen;
- fehlender oder unsicherer Baseline;
- starkem Ranking-/ADP-/Projection-/Activity-Signal;
- bereits bekannter Competition/Uncertainty, deren Auflösung entscheidungsrelevant ist.

### Positionsübergreifende Free-Agent-Movement-Discovery

Free-Agent-Discovery soll nicht davon abhängen, dass ein Spieler zuvor manuell als Target ausgewählt wurde oder in einer Sleeper-Add-/Drop-Liste auftaucht.

Der Discovery-Lauf verwendet die vollständige tatsächliche Fantasy-Free-Agent-Population aus `free-agent-signals.json` für QB, RB, WR, TE und K und leitet daraus deterministisch alle sinnvoll berechenbaren Veränderungssignale ab.

Zielbild:

- historische Snapshot-Stände werden verwendet, um ADP-, Ranking-, Marktwert-, Tier- und Projection-Deltas über sinnvolle Vergleichsfenster zu berechnen;
- bestehende Normalisierungen und Materialitätsschwellen aus `redraft-adp-movement`, `market-movement` und `season-projection-movement` werden wiederverwendet, statt parallele zweite Regeln zu erfinden;
- gleichgerichtete Bewegungen mehrerer unabhängiger Signalfamilien erhöhen die Research-Priorität;
- Divergenzen wie Projection-Anstieg bei flachem ADP, Redraft-Anstieg bei flachem Dynasty-Markt oder widersprüchliche Marktquellen werden als eigener Research-Grund sichtbar;
- die tatsächliche kleine Liga wird über positionsspezifische Replacement-Relevanz berücksichtigt, damit Bewegungen weit unterhalb des ligaeigenen Ersatzniveaus nicht dieselbe Priorität erhalten wie Bewegungen an der Roster- oder Startergrenze;
- Sleeper Adds/Drops sind ein Activity- und Bestätigungssignal, aber weder Discovery-Voraussetzung noch dominanter alleiniger Priorisierungstreiber;
- die Derived-Schicht erzeugt Research-Priorität und Materialitätsereignisse, aber keine finale Add-/Drop-Empfehlung.

Kicker gehören ausdrücklich in dieselbe Discovery-Population und denselben Delta-/Materialitäts-/Priorisierungspfad wie QB, RB, WR und TE. Positionsspezifische Quellen, Skalierungen, Schwellen und Features bleiben zulässig; sie rechtfertigen aber keinen separaten Kicker-Discovery-Workflow.

Ein Zielcontract wie `free-agent-movement-signals.json` soll pro auffälligem Spieler mindestens aktuelle Werte, Vergleichsstände, Deltas, überschrittene Schwellen, Evidenz/Freshness, Cross-Signal-Bestätigung oder -Divergenz, Replacement-Relevanz und Research-Priorität bereitstellen.

### Free-Agent-Eskalation in dauerhaftes Monitoring

Fantasy Free Agents können zunächst nur durch aktuelle Derived Signals, Sleeper Activity, Markt-/ADP-/Projection-Bewegung oder qualitative Recherche auffallen, ohne bereits als dauerhaftes `player-role-watch`-Target konfiguriert zu sein.

Daily Monitoring muss deshalb zwischen **temporärer Auffälligkeit** und **dauerhaft beobachtungswürdigem Kandidaten** unterscheiden.

Ein Fantasy Free Agent soll zur dauerhaften Aufnahme in `fantasy-management/automation/target-sets/player-role-watch.json` vorgeschlagen werden, wenn mindestens einer dieser Pfade erfüllt ist:

1. **wiederholte relevante Auffälligkeit**
   - der Spieler fällt in mehr als einem erfolgreichen Monitoringlauf mit weiterhin relevanten Signalen auf; und
   - die Auffälligkeit lässt sich nicht nur durch normales Plattformrauschen oder eine einmalige Add-/Drop-Welle erklären; und
   - Rolle, Opportunity, Injury-Kontext, Usage, Markt, ADP, Projections oder ein anderer belastbarer Faktor rechtfertigen weitere Beobachtung auch dann, wenn das ursprüngliche Trending-Signal wieder verschwindet.

2. **ein einzelnes klar materielles Ereignis**
   - ein belastbares neues Ereignis verändert den erwartbaren Fantasy-Pfad deutlich genug, dass weiteres tägliches Beobachten unabhängig von Wiederholung sinnvoll ist;
   - Beispiele sind ein neu geöffneter Starter-/Rotationspfad durch Verletzung oder Transaction, wiederholte First-Team-Usage, ein klarer Preseason-/Game-Usage-Sprung, eine relevante NFL-Verpflichtung oder eine andere strukturelle Opportunity-Veränderung.

Ein einzelnes schwaches Sleeper-Trending-, Ranking-, ADP- oder Projection-Signal reicht **nicht** automatisch für die Aufnahme ins dauerhafte Watch-Set. Solche Signale dürfen Research auslösen, müssen aber qualitativ gegen Rolle, Usage, Teamkontext und tatsächliche Fantasy-Verfügbarkeit plausibilisiert werden.

Ein Vorschlag zur dauerhaften Aufnahme soll mindestens enthalten:

- Spieleridentität und aktuelle Fantasy-Verfügbarkeit;
- den konkreten Auslöser oder die wiederholte Signalkette;
- warum kurzfristige Signalbeobachtung nicht mehr ausreicht;
- welche Profile dauerhaft relevant sind, insbesondere `role-opportunity`, `injury-status`, `market-movement`, `redraft-adp-movement` und/oder `season-projection-movement`;
- den empfohlenen Monitoring-Horizont oder die Bedingung, unter der die Watch wieder beendet werden kann;
- die vorgeschlagene stabile Target-ID.

Die Aufnahme selbst ist eine **dauerhafte Konfigurationsänderung** und bleibt genehmigungspflichtig:

- Scheduled Daily Monitoring darf ein neues `player-role-watch`-Target niemals autonom schreiben;
- nach ausdrücklicher Nutzerfreigabe sollen Target-Konfiguration und bestätigte qualitative Erstbaseline nach Möglichkeit im selben kontrollierten Persistierungsvorgang hergestellt werden;
- eine Erstbaseline allein erzeugt kein Nutzer-Event;
- ein Spieler wird nicht automatisch wieder aus dem Watch-Set entfernt, nur weil sein Sleeper-Trending-Signal nachlässt;
- eine spätere Entfernung oder Deaktivierung soll auf gelöster Opportunity, klar verlorener Relevanz, abgelaufenem Beobachtungsfenster oder ausdrücklicher Nutzerentscheidung beruhen.

Diese Regel soll insbesondere verhindern, dass neu entdeckte Kandidaten nach einem einzelnen Daily Run wieder aus dem qualitativen Blickfeld fallen, obwohl sich eine echte Rollen- oder Opportunity-These entwickelt hat.

### Preseason-Usage-Signal-Klassifizierung

Preseason-Ergebnisse werden nicht primär nach Boxscore-Produktion bewertet, sondern danach, ob sie belastbare Information über Rolle, Hierarchie oder Opportunity liefern. Das Monitoring soll Preseason-Evidenz deshalb mit stabilen Signaltypen erfassen und unterschiedliche Evidenzstärken nicht vermischen.

Verwende insbesondere folgende Klassifizierungen:

- `first_team_snap_share`: numerisch belastbarer Snap-Anteil mit der ersten Einheit oder klar dokumentierte vollständige Teilnahme an einem First-Team-Drive. Starkes Usage-Signal, aber keine regulärsaisonale Startergarantie.
- `held_out_with_starters`: ein Spieler wird gemeinsam mit etablierten Startern geschont, während direkte Konkurrenten spielen. Relevantes indirektes Hierarchie-Signal, aber allein kein Beweis für eine feste Starter- oder Backup-Rolle; Verletzung, Belastungssteuerung und Sonderteams-Kontext müssen gegengeprüft werden.
- `starter_drive_targets`: Targets, Routes, Carries oder andere Opportunities auf Drives der ersten Einheit. Wiederholte oder strukturell passende Nutzung wiegt deutlich stärker als reine Yards oder Touchdowns gegen spätere Units.
- `backup_hierarchy_change`: belastbare Veränderung der unmittelbaren Backup- oder Rotationsreihenfolge, etwa klarer RB2-, WR3- oder TE2-Einsatz. Bei verletzungsbedingt fehlender Konkurrenz muss die Hierarchie als vorläufig gekennzeichnet werden.
- `injury_opened_opportunity`: zusätzliche Opportunity entsteht durch Verletzung, Ausfall oder Abwesenheit eines Konkurrenten. Nach der allgemeinen Opportunity-Provenance-Regel muss zwischen verdienter Rolle und vorübergehend freigewordener Rolle unterschieden werden; die Rückkehr des Konkurrenten ist ein eigener Recheck-Trigger.
- `box_score_splash`: auffällige Yards, Touchdowns oder einzelne Big Plays ohne belastbaren Rollen- oder Hierarchiekontext. Dieses Signal ist allein schwach und darf weder ein dauerhaftes Watch-Target noch eine Draft-/Add-Empfehlung begründen.

Gewichtungsregel:

> belastbare First-Team-/Hierarchie-Evidenz > wiederholte Starter-Drive-Opportunity > indirekte Schonungs-/Camp-Evidenz > reine Boxscore-Produktion.

Zusätzliche Leitplanken:

- Ein einzelnes Big Play darf nicht als Rollenaufstieg behandelt werden.
- Wiederholte First-Team-Nutzung über Training und Spiel oder über mehrere Spiele kann einen einzelnen schwächeren Datenpunkt deutlich aufwerten.
- `held_out_with_starters` muss immer gegen Verletzungsstatus und bekannte Belastungssteuerung plausibilisiert werden.
- Bei `injury_opened_opportunity` darf aktuelles Volumen nicht automatisch auf die Zeit nach Rückkehr des fehlenden Konkurrenten fortgeschrieben werden.
- Preseason-Usage kann Research-Priorität, Watch-Status und spätere Board-Priorität verändern, trifft aber im Daily Monitoring keine finale Add-/Drop- oder Draft-Entscheidung.

## 3. Positionsübergreifendes Free-Agent Daily Monitoring

Free-Agent Daily Monitoring ist ein positionsübergreifender Discovery- und Research-Priorisierungspfad. Es ist kein autonomer Transaktionsworkflow.

Der normale tägliche Pfad ist:

1. `source-freshness.json` prüfen;
2. `free-agent-movement-events.json` als Event-first-Schicht lesen;
3. nur bei freigegebenem Freshness-Gate relevante `new`, `changed`, `structural_change` und gegebenenfalls `resolved` Events weiter untersuchen;
4. `free-agent-movement-signals.json` nur als Detail-/Current-State-Ansicht für diese Events verwenden;
5. qualitative Recherche gezielt auslösen;
6. bei echter dauerhafter Relevanz die Aufnahme in `player-role-watch` vorschlagen;
7. keine finale Add-/Drop-Empfehlung aus Daily Monitoring allein ableiten.

`event_count = 0` ist nur dann ein belastbarer No-Event-Befund, wenn `source-freshness.json -> monitoring.no_event_conclusion_allowed = true` ist. Bei degradiertem oder blockiertem Freshness-State gelten die dort definierten Einschränkungen.

## 4. Persistierte qualitative Baselines

Persistierte qualitative `entity-observation`-Baselines dienen als Vergleichsgedächtnis für spätere Monitoringläufe. Sie sind nicht Generated Data und bleiben genehmigungspflichtig.

Der effektive State folgt `fantasy-management/_ai/OBSERVATION_STATE_STORAGE.md`:

- Base: `fantasy-management/automation/state/entity-observation.json`;
- Target-Shards: `fantasy-management/automation/state/entity-observation-targets/{target_id}.json`;
- vorhandener Shard gewinnt gegenüber dem Base-Target;
- normale genehmigte Updates schreiben nur den vollständigen betroffenen Target-Shard;
- der große Base-Snapshot wird bei normalen Baseline-Updates nicht ersetzt;
- der Scheduled Monitoring Task bleibt read-only und darf nur den konkreten späteren Shard-Write vorschlagen.

Damit muss ein Monitoringlauf beim Vergleich eines Spielers immer zuerst prüfen, ob für dessen Target ein Shard existiert. Nur wenn kein Shard existiert, wird die entsprechende Baseline aus dem Base-Snapshot verwendet.

## 5. Weekly Lineup + Waiver

Weekly Lineup + Waiver ist der konkrete Entscheidungsworkflow für den vollständigen aktuellen Kader.

Er kombiniert:

- aktuelle Roster- und League-Regeln;
- Injury/Availability;
- Rolle/Usage/Opportunity;
- Matchup und Schedule;
- Projections;
- Free-Agent-Alternativen;
- positionsspezifische Module;
- Drop-/Bench-Slot-Opportunity-Cost.

Eine positionsspezifische Verbesserung reicht nicht automatisch für eine Transaktion. Der Gesamtroster-Nutzen muss positiv sein.

### Kicker innerhalb des Weekly Workflows

Kicker Streaming ist ein Untermodul. Es darf Kandidaten vergleichen und einen positionsspezifischen `switch_recommended`- oder `no_switch_recommended`-Befund liefern. Die finale Entscheidung muss zusätzlich prüfen, welcher Spieler für den Move den Roster-Slot verliert und ob dieser Preis gerechtfertigt ist.

## 6. Dauerhafte Änderungen

Daily Monitoring selbst bleibt read-only. Dauerhafte Änderungen benötigen die jeweils geltende ausdrückliche Freigabe.

Insbesondere:

- neue oder geänderte `player-role-watch`-Targets;
- qualitative `entity-observation`-Baselines;
- Knowledge;
- Decisions;
- Boards;
- gespeicherte Reviews.

Für genehmigte qualitative `entity-observation`-Baseline-Writes ist ausschließlich `OBSERVATION_STATE_STORAGE.md` maßgeblich. Ein interaktiver Folge-Write muss den vollständigen aktuellen Target-State übernehmen, nur die genehmigten Profile ändern, vorhandene andere Profile erhalten, Hashes neu berechnen und den kleinen Target-Shard schreiben. Ein Full-Replacement der großen Base-Datei ist dafür nicht zulässig.
