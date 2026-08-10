# Kicker Daily Monitoring Workflow

## Zweck und klare Grenze

Dieses Modul bringt Kicker-spezifische Signale in das bestehende tägliche `entity-observation`-Monitoring.

Es beantwortet ausschließlich die Frage:

> Hat sich bei einem aktuell gehaltenen oder tatsächlich verfügbaren Fantasy-Free-Agent-Kicker etwas materiell verändert, das für eine spätere Roster-, Waiver- oder Lineup-Entscheidung relevant sein kann?

Es beantwortet ausdrücklich **nicht** die Frage, welcher Kicker in einer konkreten NFL-Woche gestartet oder aufgenommen werden soll. Matchup, Offense-Scoring-Environment, Field-Goal-Opportunity, Stadion/Wetter, Bye und die endgültige Hold-/Stream-Entscheidung gehören in den übergeordneten **Weekly Lineup + Waiver Workflow**. Die bestehende Kicker-Streaming-Engine bleibt dessen positionsspezifischer Entscheidungsbaustein.

Daily Monitoring ist damit Veränderungserkennung und Research-Priorisierung, keine automatische Transaktion und keine Wochenaufstellung.

## Kanonischer täglicher Input

Primärer Contract:

```text
fantasy-management/generated/operations/kicker-streaming-inputs.json
```

Dieser Contract ist bereits liga-spezifisch und enthält:

- den aktuell gehaltenen Kicker des verwalteten Teams;
- alle tatsächlichen Fantasy-Free-Agent-Kicker;
- Ownership auf Basis der Union aller `Roster`-/`Reserve`-/`Taxi`-IDs;
- FFC-Kicker-ADP;
- FFToday-Kicker-Projections;
- CBS-Sports-Kicker-Projections;
- Sleeper Add/Drop Activity;
- strukturiertes Injury-Signal;
- nominale Sleeper-Depth-Chart-Rolle;
- liga-spezifische Projection-Reconciliation und Scoring-Bounds.

`Players.json -> IsFreeAgent` ist auch hier kein Fantasy-Liga-Verfügbarkeitssignal.

Das Profil darf die Kicker-Provider nicht erneut separat joinen, wenn der aktuelle Kicker-Streaming-Contract verwendbar ist. Damit bleiben Source-Join-Regeln, Fantasy-Ownership und Liga-Scoring an einer Stelle definiert.

## Freshness und Fail-Closed

Der tägliche Monitoring-Lauf darf den Contract nur verwenden, wenn:

1. die Datei existiert und nicht leer ist;
2. `dataset_id == kicker-streaming-inputs` gilt;
3. `population.candidate_count` exakt der Länge von `candidates` entspricht;
4. genau die im Contract erlaubten Availability-Werte `held` und `free_agent` auftreten;
5. der Contract nicht älter als die im Profil erlaubte Freshness ist;
6. keine Upstream-Qualität einen fail-closed Zustand signalisiert.

Wenn aktuell andere abgeleitete Zwischenfiles leer oder unvollständig sind, werden daraus keine fehlenden Kicker-Signale zurückgerechnet. Ein noch frischer, vollständig validierter veröffentlichter Kicker-Contract bleibt für seine definierte Freshness ein eigenständiger konsumierbarer Snapshot. Nach Ablauf seiner Freshness wird nicht aus veralteten Daten weiterbeobachtet.

Ein technischer Datenfehler ist keine Spielerabwertung und darf keine Kicker-Empfehlung auslösen.

## Dynamische Target-Auflösung

Target Set:

```text
fantasy-management/automation/target-sets/kicker-daily-monitoring.json
```

Selector `actionable-kicker-candidates`:

1. lädt den Kicker-Streaming-Contract einmal pro Monitoring-Lauf;
2. prüft Position `K` und die Population;
3. wählt jeden Candidate mit `availability == held` oder `availability == free_agent`;
4. verwendet `player_id` als stabilen Spieler-Identifier;
5. erzeugt `kicker-monitor-{player_id}` als Target-ID;
6. dedupliziert IDs fail-closed;
7. schreibt die dynamisch aufgelöste Target-Liste nicht zurück in die Konfiguration.

Die Population bildet bewusst den **aktuell handlungsrelevanten Kicker-Markt** ab: eigener Kicker plus tatsächlich verfügbare Kicker. Gegnerisch gehaltene Kicker werden nicht als Streaming-Kandidaten bewertet.

Eine ligaweite Ownership-/Transaction-Beobachtung bleibt ein separater Daily-Monitoring-Baustein. Wenn ein bisher verfügbarer Kicker von einem Gegner aufgenommen wird, soll dieser allgemeine Ownership-Monitor die Availability-Änderung melden; dieses Kicker-Profil soll keine zweite, konkurrierende Liga-Transaction-Logik erfinden.

## Baseline-Engine wiederverwenden

Für jeden Daily-Monitoring-Lauf wird die bestehende Baseline-Engine genau einmal gegen den aktuellen Contract ausgeführt:

```text
fantasy-management/_ai/scripts/analyze_kicker_streaming.py
```

Ohne Weekly Context bleibt der Analyzer im Baseline-Modus und darf keine Add-/Drop-Empfehlung erzeugen. Das erwartete Recommendation-Ergebnis bleibt `weekly_context_required`.

Aus dem Analyzer werden ausschließlich Beobachtungssignale übernommen:

- `baseline_score`;
- `baseline_rank`;
- `baseline_confidence`;
- Zugehörigkeit zu `research_shortlist_ids`.

Dadurch existiert keine zweite Daily-Kicker-Formel neben der bereits getesteten Baseline-Methodik.

## Normalisierte Daily-Signale

Das Profil `kicker-signal-movement` normalisiert insbesondere:

### Liga- und Rollenstatus

- held vs. Fantasy Free Agent;
- NFL-Team;
- nominaler K1-Status aus Sleeper;
- positives strukturiertes Injury-Signal.

Nominaler Sleeper-K1-Status ist nur ein Trigger. `SleeperDepthChartOrder = 1` ist kein ausreichender Beweis für aktuelle Job-Sicherheit.

### Kicker-ADP

- FFC-Kicker-Rang;
- FFC-Kicker-Perzentil;
- `times_drafted` als Sample-Guard.

Kleine Rangbewegungen ohne belastbare Stichprobe sind kein materielles Ereignis.

### Projektionen

- FFToday-Projektionsperzentil;
- CBS-Projektionsperzentil;
- provider-neutral vorbereiteter Consensus-Percentile;
- Provider-Count;
- Percentile Spread als Unsicherheitssignal.

Provider-Fantasy-Punkte werden weiterhin nicht gemittelt und nicht als Ligapunkte des verwalteten Teams ausgegeben.

### Sleeper Activity

- Eintritt in Top 20 Adds;
- Eintritt in Top 10 Adds.

Sleeper Activity ist ausschließlich Research-Priorität. Die rollierenden Counts werden nicht als neue Adds seit dem letzten Monitoring-Lauf interpretiert und dürfen keinen Spieler allein qualitativ aufwerten.

### Kicker-Baseline

- Baseline Score;
- Baseline Rank;
- Research-Shortlist-Status.

Ein Shortlist-Eintritt bedeutet: **bei der nächsten Entscheidung genauer prüfen**, nicht: **jetzt adden**.

## Selektive externe Job-Verifikation

Eine vollständige Live-Recherche für jeden verfügbaren Kicker an jedem Tag wäre unnötig teuer und würde das Daily Monitoring mit unverändertem Kontext belasten.

Deshalb gilt:

### Keine externe Einzelrecherche bei stabilem No-op

Wenn Material-Contract, nominaler K1-Status, Injury-Signal, NFL-Team, Baseline, ADP, Projektionen und Activity keinen konkreten Änderungstrigger zeigen, darf `kicker.job_security = not_checked` bleiben.

### Frische externe Prüfung bei konkretem Trigger

Aktuelle offizielle NFL-/Team-/Transaction-/Injury-Quellen werden priorisiert, wenn mindestens einer dieser Fälle eintritt:

- der gehaltene Kicker verliert nominal K1;
- beim gehaltenen Kicker erscheint ein neues Injury-Signal;
- das NFL-Team ändert sich;
- ein Free Agent steigt neu in die Kicker-Research-Shortlist;
- ein Free Agent erhält eine starke neue Activity-/Projection-/ADP-Priorität und könnte für eine baldige Entscheidung relevant werden;
- ein früherer Jobstatus war `competition` oder `uncertain` und eine Auflösung ist entscheidungsrelevant.

Für eine user-facing Meldung über Jobverlust, Competition oder einen neu gewonnenen Starterjob soll die externe Job-Evidenz grundsätzlich höchstens 24 Stunden alt sein.

Erlaubte normalisierte Statuswerte:

- `confirmed_starter`;
- `probable_starter`;
- `competition`;
- `uncertain`;
- `not_current_starter`;
- `not_checked`.

`not_checked` ist kein negativer Status.

## Materialität

Die Profilkriterien sind absichtlich deutlich gröber als normale tägliche Datenbewegungen.

Materiell sind insbesondere:

- bestätigtes oder stark indiziertes Jobrisiko des gehaltenen Kickers;
- neues positives Injury-Signal beim gehaltenen Kicker;
- NFL-Teamwechsel;
- neuer Eintritt eines verfügbaren Kickers in die bestehende Research-Shortlist;
- mindestens 10 Baseline-Score-Punkte Bewegung;
- mindestens 20 Baseline-Score-Punkte Bewegung als hohe Schwere;
- mindestens 15 FFC-Perzentilpunkte Bewegung bei mindestens 50 beobachteten Drafts;
- mindestens 15 Punkte Bewegung im Projection Consensus bei mindestens zwei gelisteten Projektionsprovidern;
- neuer Eintritt in die Sleeper-Add-Top-20 beziehungsweise Top-10;
- frisch verifizierter Job-Downgrade des gehaltenen Kickers;
- frisch verifizierter Job-Upgrade eines verfügbaren Kickers.

Erste Beobachtungen bleiben still. Unveränderte Zustände werden nicht wiederholt gemeldet.

## Notification-Inhalt

Eine Daily-Monitoring-Meldung soll klar trennen:

1. **Was hat sich verändert?**
2. **Welche Quelle oder welches vorbereitete Signal zeigt die Änderung?**
3. **Ist zusätzliche Job-/Injury-Verifikation erfolgt?**
4. **Warum ist die Änderung für das verwaltete Team relevant?**
5. **Welche Folgeprüfung wird priorisiert?**

Die Meldung darf formulieren:

- „für die nächste Weekly Lineup + Waiver Analyse priorisieren“;
- „Jobstatus jetzt verifizieren“;
- „Kicker-Streaming-Baseline deutlich gestiegen“;
- „gehaltener Kicker hat neues Job-/Injury-Risiko“.

Sie darf nicht ohne den Weekly Decision Context formulieren:

- „jetzt droppen“;
- „diese Woche starten“;
- „besten verfügbaren Kicker sofort aufnehmen“.

## Kein Weekly Context im Daily Monitoring

Folgende Daten gehören nicht in den normalen täglichen Kicker-Material-State:

- aktueller Wochengegner;
- erwartetes Team-Scoring der konkreten Woche;
- Field-Goal-Opportunity der konkreten Woche;
- Stadion/Roof für das konkrete Spiel;
- Wetterforecast;
- QB-/Injury-Kontext der konkreten Woche;
- Bye als konkrete Wochenentscheidung.

Diese Faktoren sind zeitabhängige Decision Inputs und werden nur im Weekly Lineup + Waiver Prozess beziehungsweise bei einem bewusst ausgelösten Spieltags-Recheck verwendet.

## Beziehung zum Weekly Lineup + Waiver Workflow

Der spätere übergeordnete Weekly Workflow soll für alle Positionen gleichzeitig entscheiden:

- beste Startaufstellung;
- sinnvolle Bench-Zuordnung;
- notwendige Injury-/Bye-Ersatzmaßnahmen;
- Waiver Adds und Drops;
- Opportunity Cost eines Drops;
- Alternativen und Konfidenz.

Kicker ist darin ein Sondermodul:

- Normalfall: genau einen Kicker halten;
- einen stabil starken Kicker behalten, solange die beste verifizierte Alternative keinen materiellen Wochenvorteil hat;
- bei klarem Weekly-Vorteil streamen;
- bei Bye, Jobverlust oder disqualifizierender Verletzung den expliziten Sonderpfad nutzen;
- zwei Kicker nur ausnahmsweise halten, wenn das Behalten des längerfristig wertvollen Kickers den verlorenen Bench-Slot rechtfertigt.

Die Kicker-Engine entscheidet dabei den Kicker-gegen-Kicker-Vergleich. Der übergeordnete Weekly Workflow entscheidet zusätzlich, **welcher Spieler für einen Waiver-Move gedroppt werden müsste und ob dieser Roster-Preis den Kicker-Vorteil überhaupt rechtfertigt**.

## Persistenzgrenze

Das aktuelle Scheduled Monitoring ist read-only.

- kein automatischer Add/Drop;
- kein automatischer Start/Sit-Write;
- keine autonome qualitative Baseline-Persistenz;
- keine Observation-Event-Persistenz ohne ausdrückliche Freigabe;
- No-op bleibt still.

Eine spätere automatische Weekly Decision Orchestration ist ein eigener freizugebender Ausbau und darf nicht aus diesem Daily-Kicker-Profil implizit abgeleitet werden.
