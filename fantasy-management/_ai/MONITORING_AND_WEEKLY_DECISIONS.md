# Daily Monitoring vs. Weekly Lineup + Waiver Decisions

## Zweck

Diese Datei definiert die dauerhafte Trennung zwischen laufender Fantasy-Operations-Beobachtung und konkreten wöchentlichen Entscheidungen.

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

## Season-aware Aktivität und Signal-Criticality

Daily Monitoring ist kein ganzjährig identischer Prozess. Vor jeder Event-Interpretation ist der veröffentlichte `source-freshness.json`-State einschließlich `season_context`, `monitoring.active` und `signal_family_relevance` zu lesen.

Der v1-Season-Context unterscheidet ausschließlich `pre_regular_season`, `regular_season` und `post_regular_season`, weil diese Grenzen aus dem kanonischen REG-Schedule belastbar ableitbar sind. Eine feinere Postseason-/Offseason-Semantik darf später ergänzt, aber nicht aus Sleeper oder Kalenderheuristiken erfunden werden.

Für Daily Free-Agent Monitoring gilt aktuell:

- vor Beginn der Regular Season ist `redraft_adp` ein erforderliches Signal;
- während der Regular Season ist `redraft_adp` sekundärer Markt-/Kostenkontext und darf allein eine No-Event-Aussage nicht blockieren;
- nach Ende der Regular Season ist das Daily Free-Agent-Monitoring im v1-Vertrag inaktiv.

Technische Source-Probleme und reduzierte Dataset-Coverage bleiben sichtbar und dürfen nicht als Spielersignale interpretiert werden.

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


### Drop-Handoff aus dem Managed Roster

Wenn ein zuvor über den Managed-Roster-Pfad qualitativ beobachteter Spieler aus dem verwalteten Roster gedroppt wird, darf seine bereits bestätigte Rollen-/Opportunity-These nicht allein durch den Ownership-Wechsel aus dem qualitativen Blickfeld verschwinden.

Der Übergang wird als eigener **Handoff-Kandidat** behandelt:

1. Aktuellen Ownership-/Availability-Status vollständig neu auflösen. Eine Free-Agent-Begründung ist nur zulässig, wenn der aktuelle fail-closed Availability-Gate den Spieler positiv als verfügbar bestätigt.
2. Die bisherige Managed-Roster-Baseline als historischen Kontext und Evidenz lesen. Der qualitative State darf dabei nicht doppelt kanonisch geführt werden: Der Storage-Contract erlaubt pro `entity_fingerprint` genau einen aktiven Target-Shard.
3. Prüfen, ob die vor dem Drop bestehende These nach aktuellem Rollen-, Usage-, Injury-, Competition-, Markt- und Replacement-Kontext weiterhin materiell genug ist, um eine spätere Re-Add-/Stash-/Waiver-Entscheidung neu öffnen zu können.
4. Wenn ja, ein stabiles `player-role-watch`-Target mit passender Free-Agent-Rationale, relevanten Profilen und Beobachtungshorizont vorschlagen. Bei einem Target-ID-Wechsel muss der Handoff als kontrollierte Migration des **einen** kanonischen Shards erfolgen: neuer Ziel-Shard und Entfernung des bisherigen aktiven Shards gehören in denselben freigegebenen logischen Vorgang; die frühere Version bleibt über Git-Historie nachvollziehbar. Alternativ kann die bestehende stabile Target-ID weiterverwendet werden, wenn sie semantisch tragfähig bleibt.
5. Wenn nein, keinen dauerhaften Watch nur aus Besitzhistorie, Sunk Cost oder früherem Nutzerinteresse erzeugen.
6. Ein Handoff-Vorschlag darf Research und eine konkrete Persistierungsänderung vorbereiten, aber Scheduled Monitoring darf Target-Konfiguration, Shard-Migration oder qualitative Baseline niemals autonom schreiben. Die dauerhafte Aufnahme bleibt ausdrücklich genehmigungspflichtig.
7. Der Handoff selbst ist keine Re-Add-, Waiver- oder Roster-Empfehlung. Eine spätere Transaktion gehört weiterhin in den übergeordneten Weekly-/Roster-Entscheidungsprozess und muss den tatsächlichen Drop-/Slot-Preis des Gesamtrosters berücksichtigen.

Ein Handoff-Vorschlag soll mindestens enthalten:

- Spieleridentität und bisherigen Managed-Roster-Target-/Baseline-Bezug;
- aktuellen bestätigten Ownership-/Availability-Status;
- die fortbestehende oder neu bewertete Rollen-/Opportunity-These;
- den konkreten Grund, warum eine dauerhafte Free-Agent-Beobachtung nach dem Drop weiterhin sinnvoll ist;
- vorgeschlagene Target-ID, Priorität, Profile und Exit-/Recheck-Bedingung.


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

Free-Agent Daily Monitoring ist ein gemeinsamer Discovery- und Materialitätspfad für QB, RB, WR, TE und K. Kicker werden hier nicht als separate Population oder als eigener Discovery-Workflow behandelt.

### Population

Der gemeinsame Free-Agent-Pfad beobachtet alle tatsächlichen Fantasy Free Agents aus `free-agent-signals.json`, soweit sie zu den aktiven Fantasy-Positionen QB, RB, WR, TE oder K gehören.

Die gleiche Ownership- und Availability-Logik gilt für alle Positionen. Ein Spieler, der von einem Gegner aufgenommen oder wieder freigegeben wird, wechselt über dieselbe ligaweite Ownership-Schicht in oder aus der Free-Agent-Population.

### Gemeinsame Signalfamilien

Je nach Positions- und Quellenabdeckung werden insbesondere beobachtet:

- Injury und Availability;
- NFL-Team und relevante Transactions;
- Rolle und Opportunity;
- Usage;
- Dynasty-Ranking und Marktwert;
- Redraft-ADP;
- Season Projections und liga-spezifisch neu berechnete vergleichbare Core Points;
- Projection Consensus und Provider Spread;
- Sleeper Activity;
- Cross-Signal-Confirmation und -Divergence;
- positionsspezifische Replacement-Relevanz.

Positionsspezifische Signale dürfen denselben Spielerrecord ergänzen. Für Kicker können dazu insbesondere FFC-Kicker-ADP, nominaler K1-Status, Job Security, bestehender Kicker-Baseline-Score oder eine Kicker-spezifische Projection-Auswertung gehören. Diese Features bleiben Teil derselben Discovery- und Priorisierungsarchitektur.

### Bestehende Kicker-Implementierung

Die bereits implementierten Dateien

```text
fantasy-management/automation/target-sets/kicker-daily-monitoring.json
fantasy-management/automation/profiles/kicker-signal-movement.json
fantasy-management/automation/workflows/kicker-daily-monitoring.md
```

bleiben als vorhandene technische und fachliche Bausteine nutzbar. Sie definieren jedoch nicht mehr die Zielarchitektur für Free-Agent-Discovery.

Beim Ausbau sollen Kicker-Signale in den gemeinsamen positionsübergreifenden Movement- und Monitoring-Pfad einfließen, ohne parallele Discovery-Baselines, doppelte Ownership-Logik oder separate Kicker-Benachrichtigungen für denselben materiellen Sachverhalt zu erzeugen.

Die Kicker-Streaming-Engine bleibt ein nachgelagertes positionsspezifisches Analysemodul für Weekly Decisions; sie ist keine Discovery-Schicht.

### Was Daily Free-Agent Monitoring nicht macht

Es bewertet im normalen täglichen Lauf nicht automatisch:

- konkrete Weekly Matchups;
- konkrete Stadion-/Roof-/Weather-Bedingungen einer einzelnen Spielwoche;
- finale Start/Sit-Entscheidungen;
- finale Add/Drop-Entscheidungen;
- die globale Opportunity Cost eines Roster-Moves.

Diese Faktoren sind Weekly Decision Context oder gehören in andere übergeordnete Entscheidungsprozesse.

## 4. Weekly Lineup + Waiver Workflow: Zielbild

Der Weekly Workflow ist kein Kicker-Workflow, sondern ein Gesamtteam-Entscheidungsprozess.

### Kerninputs

Mindestens:

- aktuelles `League.json`;
- vollständiger aktueller Managed Roster;
- tatsächliche Fantasy-Free-Agent-Population;
- NFL Schedule und aktuelle Week;
- aktuelle Injury-/Availability-Daten;
- aktuelle Usage- und Opportunity-Daten, sobald materialisiert;
- aktuelle Rankings/ADP/Projections;
- positionsspezifische Module;
- Roster-/Bench-/Taxi-/Reserve-Regeln;
- aktuelle AutoSub-/Substitute-Regeln aus den League Settings, insbesondere erlaubte Anzahl, Timing-/Eligibility-Regeln und Lock-Verhalten;
- Kickoff-Zeit und aktueller Lock-State aller für Starter- und Substitute-Entscheidungen relevanten Spieler;
- gegebenenfalls Waiver-/Transaction-Deadlines.

### Entscheidungsreihenfolge

1. **Availability klären**
   - Bye;
   - Out/Doubtful/Questionable;
   - Suspension/IR/PUP;
   - aktuelle NFL- und Fantasy-Ownership.

2. **Startbare Population bestimmen**
   - nur tatsächlich verfügbare Spieler;
   - Positions- und Flex-Berechtigung beachten.

3. **Weekly Projection + Opportunity bewerten**
   - Matchup;
   - Team-Scoring-Environment;
   - Usage;
   - Rolle;
   - Injury-Kontext;
   - relevante positionsspezifische Faktoren.

   **In-Season-Usage-Guardrail für Grenzentscheidungen:** Sobald Regular-Season-Spiele der aktuellen Saison vorliegen, müssen bei knappen Start/Sit-Entscheidungen aktuelle Usage-Signale ausdrücklich neben Rankings und Projektionen ausgewiesen und für die relevante Vergleichsgruppe nach denselben Kriterien bewertet werden. Soweit belastbar verfügbar, gehören dazu insbesondere:
   - Snaps bzw. Snap Share;
   - Routes bzw. Route Participation;
   - Targets und Target Share;
   - bei Passfängern Air Yards und Air-Yards-Share;
   - positionsabhängig Carries, Goal-Line-, Third-Down-, Two-Minute- oder andere rollenrelevante Opportunities.

   Diese Signale sind ein eigenständiger Evidenzblock und dürfen eine Abweichung von Consensus Rankings oder Projektionen begründen, ersetzen diese aber nicht automatisch. Ein einzelnes Spiel bleibt eine kleine Stichprobe; Game Script, Verletzungen oder Ausfälle von Mitspielern, Opportunity-Provenance, aktuelle Practice-/Availability-Evidenz und das Matchup müssen gemeinsam berücksichtigt werden. Alte Preseason-, Camp- oder nominale Depth-Chart-Annahmen dürfen aktuelle belastbare Regular-Season-Usage nicht ungeprüft überstimmen. Wenn Usage und Rankings/Projektionen materiell auseinanderlaufen, muss die Weekly-Analyse den Konflikt und die daraus entstehende Unsicherheit sichtbar machen. Neue Usage-Evidenz darf außerdem nicht nur den gerade diskutierten Spieler verschieben; der vollständige relevante Start/Sit-Vergleichspool ist konsistent neu zu bewerten.

   **Starter-Boundary-Stresstest für Grenzentscheidungen:** Vor Festlegung der finalen Startaufstellung müssen Spieler an der Start/Sit-Grenze als gemeinsamer Kandidatenpool neu bewertet werden. Die aktuell gesetzte Sleeper-Aufstellung erhält dabei keinen Bestandsschutz oder Incumbency-Bonus.

   Mindestens die letzten zwei bis drei voraussichtlichen Starter und die ersten zwei bis drei realistischen Bench-Alternativen sollen bei einem engen Grenzfall nach denselben Kriterien direkt gegeneinander geprüft werden. Soweit für die jeweilige Position sinnvoll und belastbar verfügbar, gehören dazu:
   - liga-spezifischer Scoring-Fit;
   - aktuelle Regular-Season-Usage und Opportunity;
   - erwarteter Floor, Median und Ceiling;
   - Team-Scoring-Environment;
   - Matchup und wahrscheinlicher Game Script;
   - Injury-/Workload-Risiko;
   - aktuelle Rankings und Projections einschließlich relevanter Divergenzen;
   - zusätzliche situative Faktoren wie außergewöhnliche Reise-/Rest-Konstellationen, relevante Personnel-Veränderungen oder andere besondere Spielumstände nur bei belastbarer aktueller Evidenz.

   Bei einer echten Grenzentscheidung muss zusätzlich mindestens eine plausible Gegenhypothese geprüft werden: **Unter welchen realistischen Annahmen wäre der aktuell zurückliegende Kandidat die bessere Startentscheidung?** Wird diese Gegenhypothese durch aktuelle Evidenz plausibel gestützt, muss die Unsicherheit sichtbar gemacht und der vollständige Boundary-Pool erneut konsistent geprüft werden. Narrative Faktoren ohne belastbare Evidenz dürfen eine Entscheidung nicht allein drehen.

4. **Beste legale Startaufstellung gemeinsam optimieren**
   - feste Positionsslots und FLEX-Slots als Gesamtproblem behandeln statt relevante Spieler positionsweise isoliert zu entscheiden;
   - die aktuelle Starter-/FLEX-Struktur dynamisch aus den aktuellen Ligaregeln im Repo ableiten;
   - nach Besetzung zwingender Positionsslots alle verbleibenden FLEX-eligible Kandidaten als gemeinsamen Pool bewerten;
   - den Starter-Boundary-Stresstest auf knappe letzte Starter-/FLEX-Plätze anwenden;
   - aktuell in Sleeper gesetzte Starter erhalten keinen Incumbency-Bonus;
   - die resultierende Aufstellung muss positions- und FLEX-legal sein.

5. **Matchup-State und Risikobudget kalibrieren**
   - den aktuellen Rohpunktestand nie isoliert als Begründung für konservativere oder aggressivere Start/Sit-Entscheidungen verwenden;
   - für beide Teams die bereits abgeschlossenen Starter, deren erzielte Punkte und die verbleibenden Starter-/Lineup-Slots bestimmen;
   - Punkte pro bereits abgeschlossenem Starter und die erwartbare verbleibende Produktion gemeinsam mit dem absoluten Punktestand betrachten;
   - einen optischen Rückstand, der primär daraus entsteht, dass der Gegner mehr Spieler bereits absolviert hat, nicht als echten Comeback-Zwang behandeln;
   - Floor-/Median-orientierte Entscheidungen bleiben der Default, solange kein materiell belastbarer Rückstand in der verbleibenden Siegchance vorliegt;
   - Varianz und Ceiling gezielt erhöhen, wenn Gegner-Outperformance und verbleibende Projektionen einen echten Aufholbedarf zeigen; bei einem belastbaren Vorsprung darf unnötige Downside stärker vermieden werden;
   - kleine Stichproben einzelner bereits gespielter Spieler nicht übergewichten: Matchup-State ist ein Kalibrierungsfaktor für enge Entscheidungen, kein Ersatz für Player-, Usage-, Injury- und Projection-Evaluation.

6. **Late-Swap-, AutoSub- und Late-Injury-Risiko gemeinsam absichern**
   - späte `Questionable`-/Game-Time-Decision-Spieler nicht nur nach nominaler Projektion bewerten, sondern auch nach dem Risiko von Inactive-Status, Snap-Limit oder reduzierter Rolle;
   - wenn ein unsicherer Spieler FLEX-eligible ist, ihn nach Möglichkeit in einen FLEX-Slot statt in einen früh blockierenden Positionsslot stellen, damit die spätere Ersatzmenge maximal bleibt;
   - aktuelle AutoSub-/Substitute-Regeln und deren konkrete Werte immer aus den aktuellen League Settings ableiten; keine feste Zahl erlaubter Subs oder dauerhaft angenommene Timing-/Lock-Regel in den Weekly Workflow hardcoden;
   - die beste Startaufstellung und die verfügbaren AutoSub-Paarungen gemeinsam optimieren: AutoSubs sind kein nachträgliches Anhängsel, dürfen aber auch nicht als Rechtfertigung dienen, zunächst den objektiv schwächeren Starter zu wählen;
   - AutoSub-Slots nach ihrem erwarteten Versicherungswert priorisieren, insbesondere anhand von Inactive-Risiko, Qualität des verfügbaren Ersatzes sowie Timing-/Reaktionsrisiko;
   - die Plattformmechanik des AutoSub-Triggers ausdrücklich von verbleibendem Injury-Risiko trennen: ein AutoSub kann einen nach den geltenden Plattformregeln nicht spielenden Starter absichern, schützt aber nicht automatisch vor einem aktiven, jedoch limitierten Spieler oder einer Verletzung während des Spiels;
   - dieselbe Bench-Alternative nicht gleichzeitig als Versicherung mehrerer Starter einplanen, wenn die Plattformmechanik dies nicht tatsächlich zulässt;
   - Kickoff- und Lock-Zeit von Starter und Substitute gemeinsam berücksichtigen; erlaubt die Liga einen früher spielenden Substitute, darf dieser nur unter Berücksichtigung des dadurch früher eintretenden Lock- bzw. Flexibilitätsverlusts verwendet werden;
   - einen unsicheren späten Starter nur dann bevorzugen, wenn entweder ein realistisch startbarer Backup-/AutoSub-Pfad mit passender Positions-/FLEX-Berechtigung und nach aktueller Ligaregel nutzbarem Timing verfügbar ist oder der Erwartungswertvorteil das zusätzliche Null-/Limitierungsrisiko klar rechtfertigt;
   - ohne belastbaren Late-Swap-/AutoSub-Pfad einen früheren gesunden Spieler mit etwas niedrigerer Ceiling bevorzugen, wenn der erwartete Floor-/Median-Verlust kleiner ist als das Downside-Risiko des späten unsicheren Spielers;
   - Practice Participation, offizielle Game Designation, glaubwürdige Snap-/Workload-Berichte und finale Inactive-Meldungen unterscheiden; `Questionable` allein ist weder automatische Bench- noch automatische Start-Begründung;
   - vor dem Lock des betroffenen Spiels die final verfügbare Injury-/Inactive-Evidenz revalidieren, wenn sie die Entscheidung materiell verändern kann;
   - der finale Output muss bei jedem bewusst gestarteten späten unsicheren Spieler den konkreten Late-Swap-/AutoSub-Backup, Trigger, relevanten Lock-/Timing-Punkt und verbleibendes nicht abgesichertes Risiko nennen.

7. **Free-Agent-Upgrades prüfen**
   - nicht nur Top Projection suchen;
   - tatsächliche Fantasy-Verfügbarkeit prüfen;
   - erwarteten Vorteil gegen aktuellen Starter/Bench-Spieler bewerten.

8. **Drop Opportunity Cost berechnen**
   - welcher Spieler müsste weichen?
   - verliert das Team dadurch wertvolle Upside, Injury Insurance, Scarcity oder Trade Value?
   - ist der Move nur für eine Woche oder auch mittelfristig sinnvoll?

9. **Waiver-/Add-/Drop-Empfehlung erzeugen**
   - nur wenn der Gesamtnutzen positiv ist;
   - Alternativen und Mindestvorteil nennen;
   - Unsicherheit explizit machen.

10. **Finale Lineup-Empfehlung erzeugen**
   - Starter;
   - Bench;
   - wichtigste Boundary Decisions mit Alternativen und Entscheidungskonfidenz;
   - nötige Moves davor;
   - AutoSub-/Substitute-Paarungen;
   - Backup-Plan bei Questionable-/Late-Game-Spielern einschließlich Trigger, Lock-/Timing-Punkt, verbleibendem Residual Risk und relevantem Next Check.

### Output

Der spätere Workflow soll mindestens liefern:

- empfohlene Startaufstellung;
- wichtigste Start/Sit- und Boundary-Entscheidungen einschließlich relevanter Alternativen und Entscheidungskonfidenz;
- empfohlene AutoSub-/Substitute-Paarungen einschließlich Trigger, Lock-/Timing-Punkt und nicht abgesichertem Residual Risk;
- empfohlene Waiver Adds;
- zugehörige Drops;
- priorisierte Alternativen;
- Injury-/Bye-Risiken;
- aktueller Matchup-State einschließlich absolvierte Starter und verbleibende Slots beider Teams, wenn bereits Spiele gelaufen sind;
- das daraus abgeleitete Risikobudget für enge Start/Sit-Entscheidungen;
- konkreter Late-Swap-/AutoSub-Backup-Pfad für bewusst gestartete späte Questionable-/Game-Time-Decision-Spieler;
- relevanter nächster Recheck-Zeitpunkt für Injury-/Inactive-/Lock-Evidenz, wenn die Entscheidung zeitabhängig bleibt;
- Kicker Hold/Stream;
- Entscheidungskonfidenz;
- zeitkritische nächste Aktion.

## 5. Kicker als Sonderfall im Weekly Workflow

### Default-Rosterstrategie

Normalfall:

> genau einen Kicker halten.

Grund:

- die Liga hat nur einen Kicker-Starterplatz;
- Replacement Level ist in einer 6-Team-Liga hoch;
- ein zweiter Kicker verbraucht einen Bench-Slot, der häufig wertvollere RB-/WR-/TE-/QB-Upside oder Injury Insurance tragen kann.

### Stabiler Kicker vs. Streamer

Ein stabil guter Kicker soll nicht automatisch jede Woche gedroppt werden, nur weil ein anderer Kicker minimal höher projiziert ist.

Die bestehende Kicker-Engine verwendet deshalb eine materielle Wechselhürde.

Der Weekly Workflow soll:

1. den gehaltenen Kicker vollständig bewerten;
2. die besten tatsächlich verfügbaren Alternativen bewerten;
3. nur bei materiellem Wochenvorteil streamen;
4. Job Security als Eligibility-Gate behandeln;
5. Sleeper Activity nur als Research-Priorität verwenden.

### Bye

Ein Bye ist ein eigener Schedule-Fall.

- kein künstlicher Null-Score;
- keine falsche Job-Security-Abwertung;
- beste verifizierte spielende Alternative bestimmen.

Danach muss der übergeordnete Workflow entscheiden:

- Kicker droppen und Streamer aufnehmen;
- oder wertvollen Kicker behalten und einen anderen Bench-Spieler für genau eine Woche opfern.

### Zwei Kicker

Zwei Kicker sind kein Default.

Sie können sinnvoll sein, wenn:

- der gehaltene Kicker längerfristig deutlich über Replacement Level liegt;
- sein Bye nur kurzfristig überbrückt werden muss;
- der zu opfernde Bench-Slot aktuell wenig langfristigen Wert trägt;
- das Risiko, den gehaltenen Kicker nach einem Drop nicht zurückzubekommen, höher ist als die Opportunity Cost des zweiten Kicker-Slots.

Diese Entscheidung kann die Kicker-Engine allein nicht treffen, weil sie den Wert des zu droppenden Nicht-Kickers nicht kennt.

## 6. Verhältnis zu anderen geplanten Workflows

### Weekly Roster Review

Strategischer als Weekly Lineup + Waiver.

Fragen:

- Hold/Shop/Cut/Stash/Package;
- Salary-/Cap-Risiko;
- mittelfristige Rollenentwicklung;
- Roster Construction.

### Free-Agent Board

Breiter Marktüberblick unabhängig von der konkreten Startwoche.

Fragen:

- beste verfügbaren Talente;
- Upside;
- Handcuffs;
- Stashes;
- mittelfristiger Marktwert.

### Weekly Lineup + Waiver

Kurzfristiger, konkreter Entscheidungsworkflow.

Fragen:

- diese Woche starten;
- diese Woche ersetzen;
- jetzt adden/droppen;
- welches Lineup maximiert die aktuelle Siegchance ohne unverhältnismäßigen Roster-Schaden?

Diese drei Prozesse dürfen dieselben Derived Datasets wiederverwenden, müssen aber unterschiedliche Zeithorizonte und Outputs behalten.

## 7. Automationsgrenze

Daily Monitoring darf regelmäßig laufen und bei materiellen Änderungen benachrichtigen.

Der Weekly Lineup + Waiver Workflow benötigt später eine separat definierte Ausführungszeit und Orchestrierung.

Vor einer automatischen Aktivierung müssen festgelegt werden:

- Waiver-Zeitfenster;
- gewünschter Hauptanalysezeitpunkt;
- spätester Recheck vor den Spielen;
- Umgang mit Thursday-/Saturday-/International-Games;
- technische Umsetzung der Matchup-State-/Risikobudget-Neukalibrierung nach bereits absolvierten Spielen;
- Late-Swap-/Late-Injury-Logik einschließlich konkreter Backup-Pfade;
- ob ein zusätzlicher Spieltags-Recheck nur ereignisgesteuert oder immer ausgeführt wird;
- ob Empfehlungen nur gemeldet oder irgendwann technisch in der App vorbereitet werden.

Änderungen an `.github/workflows/**` benötigen weiterhin eine separate ausdrückliche Freigabe.