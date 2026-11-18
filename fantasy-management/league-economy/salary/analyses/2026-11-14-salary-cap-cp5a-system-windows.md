# CP5a – Systemvergleich: Cap-Kontrollfenster, Marktfolgen und operativer Vollzug

> **Forschungsstand:** 14.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status:** CP5a als historischer und operativer Systemvergleich; **CP5 insgesamt bleibt für echte Mehrjahres-/Robustheitsprüfung offen**. Keine aktive Liga-, Salary-, Cap-, Trade-, App- oder Workflow-Regel geändert.  
> **Nordstern:** [Geschützte sechs Liga-Ziele](../../../league-context/league-philosophy.md), Version 1.0. Ziele 1–5 durch Marcel bestätigt, Ziel 6 von Robert ergänzt; volle Liga-Ratifizierung weiterhin offen.  
> **Quellen:** [CP2a](2026-11-05-salary-cap-cp2-abc-stress-test.md), [CP2b](2026-11-06-salary-cap-cp2b-historical-compliance.md), [CP3](2026-11-14-salary-cap-cp3-market-retention.md), [CP4](2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md), datierte Git-Artefakte und die parallele [maschinenlesbare CP5a-Metrikdatei](2026-11-14-salary-cap-cp5a-metrics.json). Historie, Modell, Interpretation und Beschluss strikt getrennt.

## 1. Entscheidungsrelevante Befunde

1. **Ein einzelner jährlicher Cap-Check wirkt, hält aber nicht vor:** Am 29.06.2026 waren **0/6** Teams über dem echten veröffentlichten Cap; am 09.09. **4/6**, am 05.11. **5/6**. Das ist unter dem heute aktiven Offseason-only-Cap **kein Regelverstoß**.
2. **Wiederholung im anderen Jahr:** Im archivierten 2025er Markt lagen am 05.11., 05.12. und 21.12. jeweils dieselben **3/6 Teams** über dem damals veröffentlichten Cap. Die 2025er Salaries und die Cap-Berechnung sind anders strukturiert als 2026; das ist Evidenz für *wiederholt mögliche In-Season-Überhänge*, nicht für einen kausalen Trend oder eine konkrete Titelauswirkung.
3. **Auch ohne November-Repricing:** Derselbe beobachtete 05.11.2026-Kader wäre bei den **eingefrorenen echten September-Salaries und dem September-Cap** noch bei **5/6** Teams über der Grenze, aggregiert um **176.958.042 $**. Mit dem tatsächlichen November-Preisstand sind es **5/6** und **217.960.296 $**. Die wieder erreichte Over-Cap-Struktur entsteht also nicht ausschließlich durch ein späteres Salary-Repricing; die Dollar-Differenz zwischen den Preiswelten darf nicht als isolierter Manager- oder Produktivitäts-Effekt interpretiert werden.
4. **Event-Gates betreffen nicht nur Trades:** Im lückenlos gegen das November-Roster abgeglichenen Transaktions-Replay vom 09.09. bis 05.11. gab es **54** abgeschlossene Ereignisse, darunter **46** mit Spielerzugang und **3 Trades**. Mit den *echten eingefrorenen Septemberpreisen* erhöhen **10** Transaktionspakete das Top-20-Salary eines danach über dem Cap liegenden Teams: **7 Waiver**, **3 Trades**. Ein nur auf Trades gerichteter Compliance-Prozess würde die beobachteten sieben Waiver-Signale auslassen. Ausgangskader waren bereits teilweise über dem hypothetischen Cap, daher sind das **diagnostische Zusatzbelastungen**, keine rückwirkend ungültigen Transaktionen.
5. **Wenige feste Prüfungen versus permanent:** Ein zusätzlicher Check **nach dem FA-Draft** würde die dokumentierten September-Überhänge adressieren, **nicht** jedoch automatisch die späteren zehn belastenden Pakete verhindern. Ein weiterer **Midseason-Check** würde einen späteren Zustand beurteilen, aber ebenfalls keine zwischenzeitliche Transaktionslegalität garantieren. Permanenter Vollzug braucht dagegen verlässliche Transaktions- und Abrechnungs-Gates; realer *manueller* Aufwand ist noch ungemessen.
6. **Teurere Sterne sind nicht automatisch verkäuflich:** CP3s echter Juni-Käufermarkt lässt für Flos acht damalige Cuts **13/40** direkte Einzelszenarien ohne Käufer-Cut zu, aber bei gemeinsamer Verteilung nur **4/8** gleichzeitig. Strengere Caps können deshalb mehr Angebotsdruck und zugleich geringere Käuferliquidität erzeugen. Ohne belegte Gebote keine Behauptung neuer Trades.
7. **Dead Cap kann am Prüftermin verschwinden:** CP4 zeigt für acht historische Flo-Cuts **37.551.933 $** hypothetisch reteniertes Salary. Je nach *nicht entschiedener* Top-20-Abrechnung und Reset-Reihenfolge kann sich die Juni-Belastung um mehr als 26 Mio. unterscheiden – oder unmittelbar vor dem einzigen Check ohne Dead-Cap-Wirkung sein. Eine Empfehlung muss die Reihenfolge **Cut → Retention → Compliance → Reset** eindeutig definieren.

**Vorläufige Richtung, ausdrücklich kein Beschluss:** Ein **zusätzlicher verbindlicher Check nach dem FA-Draft** verdient im CP5b-Vergleich Priorität als gering komplexe Gegenprobe zur heutigen Regel. Er ist **kein Ersatzbeweis** für ganzjährigen Vollzug, solange Trade- und Waiver-Zugänge zwischen den Terminen unbeschränkt bleiben. Ein automatisierbares Event-Gate könnte die Lücke grundsätzlich schließen, seine Integration und die Kosten müssen dafür real belegt werden. Criticality, Rookie Contracts und Dead Cap sind **separate Hebel**; aus CP5a folgt noch keine Einführung.

## 2. Historische Quellenprüfung über zwei Saisons (alle sechs Teams, keine Fallauswahl Flo)

### 2.1 Jahr 2025 – tatsächliche damalige Preiswelt

Der damalige Spieler-Vertrag heißt **`SalaryDollars`**, nicht das 2026er Feld `Salary`. Mit genau der damaligen Player-Population ergibt **`round_half_up(sum(top120 SalaryDollars) / 6)`** für alle drei Zeitpunkte dollar-genau das publizierte Cap **581.658.383 $**. Je Team zählen die 20 teuersten einzigartigen Roster-IDs. Der Faktor 0,9 aus 2026 wird **nicht rückwirkend** auf 2025 angewendet.

| Tatsächlicher Git-/League-Stand | Über Cap (von sechs) | Team-IDs | Summe positiver Cap-Überhänge |
|---|---:|---|---:|
| [05.11.2025](https://github.com/Lolindhir/fantasy-app/tree/ea9d7666ad655ccf9a45dafb3463046cb0c49908) | 3 | 2, 3, 4 | 75.118.784 $ |
| [05.12.2025](https://github.com/Lolindhir/fantasy-app/tree/e7afd83ab8f141397d05d151362a1f64409c153f) | 3 | 2, 3, 4 | 63.709.322 $ |
| [21.12.2025](https://github.com/Lolindhir/fantasy-app/tree/0ede4b63ab6f424bd854112ca7f2c551b68af0d7) | 3 | 2, 3, 4 | 51.349.556 $ |

Die konkreten Teams zeigen zugleich, warum **Anzahl über Cap** nicht gleich Kapazitäts- oder Titelstärke ist: Der Überhang sinkt im Zeitverlauf, aber dieselben drei Teams bleiben über der Grenze. Für diese Quellen existiert hier kein gleichartiger, rekonstruiert legaler 2025er Cap-Deadline-Start. Die Gründungsphase 2024 hat andere Draft-/Marktmechanik und wird nicht mit einem erfundenen historischen Salary-Snapshot aufgefüllt.

### 2.2 Jahr 2026 – jeweils echtes as-of-Salary und as-of-Cap

Das 2026er Marktfeld heißt `Salary`, das veröffentlichte Cap wird **`round_half_up(0,9 × sum(top120 Salary) / 6)`** gebildet. Die unten stehenden vier Paare `League.json` und `Players.json` kommen jeweils **aus demselben historischen Commit**. Für alle vier gilt: Cap auf Dollar genau reproduziert; **0 fehlende Roster-ID-Salaries**.

| Snapshot | Team-IDs über Cap | Anzahl | Summe positiver Überhänge |
|---|---|---:|---:|
| [29.06.2026](https://github.com/Lolindhir/fantasy-app/tree/85e22feb064fdaf2257d6c3149c8d1655ada0908) | – | 0/6 | 0 $ |
| [25.08.2026](https://github.com/Lolindhir/fantasy-app/tree/539aae40da3de444000805cea3170a116fae129d) | – | 0/6 | 0 $ |
| [09.09.2026](https://github.com/Lolindhir/fantasy-app/tree/b40956172a704ff616008d7835f527b86f128063) | 2, 3, 4, 6 | 4/6 | 122.567.015 $ |
| [05.11.2026](https://github.com/Lolindhir/fantasy-app/tree/799be2a25203f18face8185303f32b31be3d40a7) | 1, 2, 3, 4, 6 | 5/6 | 217.960.296 $ |
| 05.11.-Roster **zum eingefrorenen 09.09.-Markt** | 1, 2, 3, 4, 6 | 5/6 | 176.958.042 $ |

**Preisrobustheit:** Zwischen 25.08. und 09.09. besitzen alle **1.242** gemeinsamen PlayerIDs identisches Salary (**0** Änderungen). Der spätere 05.11.-Kader kann zudem vollständig zu den 09.09.-Salaries bewertet werden (**0 fehlende IDs**), wobei die Überhang-Anzahl 5/6 bleibt. Juni, September und November sind dennoch **keine** gemeinsame Kontrafaktik mit bereits angepassten Kadern.

### 2.3 Neu durchgerechnetes Event-Replay mit echtem September-Freeze (nicht CP2a-Oktoberproxy)

Rekonstruiert wurde der tatsächlich archivierte 09.09.-Kader mit **54** danach abgeschlossenen Transaktionspaketen bis zum 05.11., sortiert nach `EffectiveAt`, bei Gleichstand `TransactionID`. Alle `Drops` und `Adds` eines Bundles werden atomar pro Team übernommen; **alle sechs** November-Endroster stimmen mit dem archivierten Snapshot **exakt** überein, **0** widersprüchliche Adds/Drops.

| Kennzahl | Echter Sep-Salary-Freeze |
|---|---:|
| Komplette Transaktionspakete | **54** |
| Davon mit Spielerzugang | **46** |
| Davon Trades | **3** |
| Pakete mit zusätzlicher Top-20-Belastung **bei einem danach über Cap liegenden Team** | **10** |
| Davon Waiver | **7** |
| Davon Trades | **3** |
| Neue Überquerung der Grenze aus zuvor legalem Zustand | **1** |
| Vollständig legaler Post-Event-Cap-Zustand für alle Beteiligten | **20** |

**Zeitliche Verteilung der zehn Zusatzbelastungen:** September **2**, Oktober **5**, November **3**. Team-ID 1: 1; ID 2: 3; ID 3: 5; ID 4: 1. Die drei dokumentierten Trades mit Cap-Zusatzeffekt lagen **alle im November**.

In CP2a wurden unter der **anderen** Oktober-Proxy-Preispopulation **11** belastende A/B- und **15** belastende Criticality-C-Pakete ermittelt. Diese Zahlen dürfen **nicht** als exakter Zwei-Formel-Vergleich mit den **10** aus unserem September-Freeze gelesen werden. Ein Preismodell- oder Cap-Resultat ist nur bei seinem jeweils **eigenen** vollständigen Marktvektor aussagefähig.

**Kausalitätsgrenze:** September beginnt bereits mit 4/6 Teams oberhalb des **hypothetischen** permanenten Caps, weil die Manager nach dem heute erlaubten Modell gespielt haben. Striktes „alle Teams nach jeder Transaktion unter Cap“ würde deshalb auch manche verbessernden oder neutralen Moves treffen; `20/54` ist keine Zahl „illegaler Deals“. Das Replay ist ein **Warnsignal-/Regelbedarfs-Stresstest**, keine ex-post-Disqualifikation oder Vorhersage nach einem legalen B-Start.

## 3. Vier Vollzugsmodelle – gleiche Preise, unterschiedliche Kontrollfenster

Diese **operativen** Modelle werden getrennt von den formalen CP2a-Salary-Szenarien A/B/C/D betrachtet. *F2/F3 sind reine Prüfkalender-Varianten mit denselben aktuellen Salaries; sie sind weder eingeführt noch vollständig spezifiziert.*

| Vollzugsvariante | Mögliche Prüfpunkte / Ereignisse | Belegbare historische Diagnose | Was bleibt ungesichert? |
|---|---|---|---|
| **A – Istzustand** | 1 verpflichtender Offseason-Cap-Termin | Juni 2026 0/6 über Cap, September 4/6, November 5/6; 2025er Over-Cap-Phasen | Ungedeckte Neuzugänge nach der Deadline |
| **F2 – zwei Termine** | Bestehende Deadline **und** abschließender Cap-Check nach dem FA-Draft samt Ausgleichsfenster | Am archivierten 09.09.-Anker 4/6 über dem unveränderten August-Cap | Zehn September–November-Zusatzeffekte bleiben ohne laufendes Gate möglich |
| **F3 – drei Termine** | F2 **plus** sinnvoll platzierter Midseason-Check *vor* den späten Win-now-Trades (genaue Frist offen) | Im Replay liegen 2 belastende Ereignisse im September, 5 im Oktober, 3 im November | Ein Check vor November verhindert nicht automatisch die drei November-Trades; ein Check danach wirkt ggf. zu spät |
| **B – dauerhaft bindender Cap** | Nach jedem wirtschaftlich relevanten Add/Drop-/Trade-Bundle, Draft-Settlement und Salary-Refresh; von einem **legalen** Startzustand | 54 Events mit 46 Zugängen in untersuchtem Fenster; 10 Zusatzlast-Signale; 7 davon Waiver | Rechtssicheres atomisches Clearing, Integration, Audit, Grace und tatsächlicher Arbeitsaufwand noch offen |

**Schlussfolgerung zur operativen Modellwahl:** Eine bloße **Trade-Gate-only**-Variante ist keine funktionsgleiche Ersatzlösung für B, weil sieben der zehn historisch identifizierten Zusatzlasten Waiver-Ereignisse waren. Ein `No-Worsening`-Prinzip ist für überfällige Übergangskader denkbar, darf aber den echten legalen Start und Draft-Settlement nicht umgehen. Stichtagsprüfungen benötigen explizite Fristen, Grace, gleichzeitige Gegenabgänge, eine abgesicherte Salary-Freeze-Version und klare Folgen, falls Teams später wieder über Cap gehen.

**Arbeitslast als Umfang, nicht als Zeitkosten:** B müsste im untersuchten Zeitraum bis zu **54** komplette Event-Bundles validieren, bei Dead Cap möglicherweise auch reine Cuts; F2/F3 würden primär **zwei/drei geplante Prüfereignisse für jeweils sechs Teams** voraussetzen. Das ist *kein* realistischer Minuten-/Personalkostenvergleich: automatische Gates, Nacharbeiten, Konflikte und Prüfungen der Fristfenster sind nicht gemessen.

### 3.1 Sleeper-Fähigkeiten – eng begrenzt verifiziert

Aktuelle offizielle Sleeper-Hilfe dokumentiert u. a. [Custom Daily Waivers und Locked-Tage](https://support.sleeper.com/en/articles/3978868-waivers-for-regular-season-playoffs), [Lock Free Agent and Waiver Moves](https://support.sleeper.com/en/articles/4037431-why-can-t-i-drop-players), [Trade Review/Commissioner-Veto](https://support.sleeper.com/en/articles/3188802-how-to-trade) und [direkte Commissioner-Trade-Verarbeitung](https://support.sleeper.com/en/articles/4033467-how-do-i-force-a-trade-through). Diese belegen **Zeit-/Bewegungskontrollen und moderierte Trades**, aber *in diesen Quellen* keine native, frei konfigurierbare Durchsetzung unserer individuellen Top-20-Dollar-Salary-Formel. Das Fehlen des Nachweises ist **kein** technischer Unmöglichkeitsbeweis: API/Capabilities und die konkreten derzeit aktiven Liga-Einstellungen müssten vor einem produktiven Event-Gate separat verifiziert werden.

## 4. Salary- und Vertragshebel **isoliert** von A/F2/F3/B halten

| Preis-/Kontrakt-Hebel | Historisch nachweisbares Signal | Limit / Systemrisiko |
|---|---|---|
| **Aktuelles Performance-Salary** | Im 2026er Sep-Freeze 10 Event-Zusatzeffekte; B braucht keine neue Formel, um erstmals den laufenden Cap-Vollzug zu ändern | Marktliquidität: 2026 Juni 13/40 direkte Käuferpaare und maximal 4/8 gemeinsam ohne Cuts |
| **C – Positional Criticality (k=1,5-Proxymodell)** | CP2a: Elite-Salary-Konzentration und **15** Zusatzlast-Events bei Oktoberpreisen, deutlich mehr Druck auf manche Kerne | Nicht gleiche Preiswelt wie Sep-Freeze; mehr Kernkosten sind weder belegte mehrjährige Durchlässigkeit noch bessere Liquidität |
| **R60 – 2025/26-Rookie-Overlay** | CP4: 60/60 Picks, endogenes 05.11.-Cap **431.964.895 $** vs. **427.653.631 $** heute; unverändert **5/6** über Cap | Proxy-Vorjahresanker, unvollständige Young-Player-Population, keine belegte 2027/28-Y4-Auflösung |
| **MIN – gleitendes Veteranenminimum** | CP4: **292/483** geprüfte Veteranensalaries erhöht, **0 $** Änderung für Top120-Cap und sechs Team-Top20-Belegungen im getesteten November-Snapshot | Sinn für Floor/Repeated Cuts möglich, aber keine isoliert belegte Elite-Balance-Wirkung |
| **Dead Cap – ein Zyklus** | Flo 8 Juni-Cuts: **37.551.933 $** hypothetische Belastung; **465.281.512 $** additiv vs. **439.197.718 $** virtuelle Top20-Slots am 29.06. | Abrechnung und Reset vs. Prüfung ungeklärt; nach Cut vergünstigter aktiver Markt kann Käuferliquidität erhöhen und Trade-Anreiz senken |
| **Franchise-Claim / Schutzrecht** | Marcels Hypothese ist als Vergleichspfad erfasst | Erzwungener Verlust eines verdienten Stars, möglicherweise doppelte Cap-Kompensation, Tanking-Risiko; kein isolierter Zusatznutzen nachgewiesen |

**Strikte Trennung:** Für C niemals A-Cap bei C-Preisen verwenden. Für R60 und MIN Cap aus der jeweils vollständigen modifizierten Population neu berechnen. Juni-Dead-Cap-Szenarien nicht mit November-Rookie-Preisen mischen. Es gibt **keinen** in CP5a gemessenen vollständigen A+R60+MIN+DeadCap+C+Claim-2027-Pfad.

## 5. Gemeinsame Bewertung gegen die sechs geschützten Ziele

| Nordstern-Ziel | A jährlich | F2/F3 feste Prüfungen | B permanent | C / zusätzliche Kontrakte |
|---|---|---|---|---|
| **1 Langfristige Aufholbarkeit** | Keine dauerhafte Garantie für wiederkehrende Konkurrenz durch die einzelne Deadline belegt | Zusätzliche Preis-/Roster-Checks können zeitliche Schlupflöcher verkleinern; **Titel- und Erholungseffekt offen** | Verhindert ohne Ausnahmeregel laufende neue Cap-Überhänge ab legalem Start; **Aufholzeit offen** | Mehr Youth-/Elite-Kosten möglich; **mehrjährige Titel- und Asset-Wirkung offen** |
| **2 Management belohnen** | Günstige Trades/Drafts wirken während der Saison ohne Cap-Nachkosten | Manager müssen gezielter finanzieren und vorausschauend planen; Wirkung je Frist | Stärkerer permanenter Optimierungsdruck, auch mehr Optionswert von vorgehaltenem Cap | Kann Entwicklung/Elite richtig bepreisen, aber auch starke eigene Draftarbeit verteuern |
| **3 Keine zementierten Gratisvorteile** | 2025/26 beobachtete In-Season-Überhänge nach jährlichem Termin | Zwischen Terminen können weiterhin einseitige Vorteile anwachsen | Relevante Adds/Trades bedürfen kontinuierlicher wirtschaftlicher Finanzierung; weder Picks noch Stars müssen dadurch zwangsweise verteilt werden | Drei Jahre Rookie-Surplus und Y4-Neubewertung sind konzeptionell begrenzt, empirisch noch nicht bis Y4 getestet |
| **4 Wirtschaftliche Konsequenzen** | Positiv an Deadline, danach keine bindende Grenze | Mehrfacher Termin schafft begrenzte neue Settlement-Kosten | Jeder erfasste Vorgang mit verlässlichem Gate cap-wirksam | Criticality verteilt Kosten anders; Dead-Cap-Reihenfolge und R60-Zyklus entscheidend |
| **5 Strategische Freiheit** | Hohe Freiheit, aber mögliche Überakkumulation | Planbare Trade-/Kaderfenster, Chancen auch für Kompromissmodelle | Starker Cap-Optimierungsdruck, aber mögliche Engpässe der Käuferseite | Star-Claim kann selbstentwickelte Assets entwerten; Dead Cap kann Cut-/Trade-Timing verzerren |
| **6 Operativer Vollzug** | Ein etablierter Deadline-Prozess | Wenige fixe Termine, aber klare Settlement-/Waiver-/Trade-Grenzen erforderlich | Vollständiger zeitnaher Check für Adds, Drops bei Dead Cap, Draft und Trades nötig; Automationfähigkeit unbewiesen | Mehr Zustände, Roster- und Preis-Versionskontrollen; nur bei Zusatznutzen gerechtfertigt |

**Keine Punktwertung oder „Gewinner“-Benennung:** Die notwendige übergeordnete Zielgröße **langfristiger legitimer Titelzugang trotz Wissens- und Aktivitätsunterschieden** ist aus den vorhandenen statischen und kurzfristigen Daten nicht ausreichend messbar. Wiederholte Titel eines Managers wären **für sich allein** kein Versagen. Eine Regel, die Fans faire Trades erzwingt oder talentierte Manager gezielt schwächt, würde Ziel 2 verletzen.

## 6. Harte Design- und Daten-Gates für CP5b / spätere CP6-Entscheidung

1. **Mehrjährige Wirkung:** Historische 2024-Gründungs-/2025-/2026er Kader, Rookie-Picks, Rollen, Verletzungs-/Einsatzkontext und Manager-/Asset-Verläufe mit **jeweils zur Zeit gültigen** Preismodellen verbinden; kein 2024-Kausalbacktest aus einer aktuellen Rückrechnung erfinden. 2025 ist erstmals hier mit originalem `SalaryDollars` quellenstimmig, aber bisher nur 3 späte Snapshots.
2. **Verhaltensreaktionen:** Für F2/F3/B aus einem **legalen Startkader** mindestens plausible, vollständig als kontrafaktisch deklarierte Manager-Optionen testen (Cuts/Trades, Ersatz/Taxi, Markt-Clearing). Eine bereits unter A realisierte Roster-/Trade-Historie darf nicht als unter B zulässige echte Entscheidung gelten.
3. **Checkpoints definieren:** Post-FA-Draft, Salary-Refresh, Deadline, Midseason-/Trade-Fenster und ggf. Grace-/Settlement-Reihenfolge einschließlich gleichzeitiger Moves, Taxi-/IR- und Waiver-Claims. Zeitpunkt des Dead-Cap-Resets **nach** der Prüfung festlegen, falls seine Wirkung gewollt ist; keine unbemerkte Neutralisierung.
4. **Rookie-Portabilität:** Unterscheiden zwischen jährlichem Rookie-Contract auf dem Spieler, ursprünglicher Owner-Tenure, Trading, Re-Acquisition nach Cut und Year-4-Neupreisung; 2024/undrafted-Verträge und echte Vorjahres-Cap-Dollar-Anker noch offen.
5. **Operative Kosten messen:** Für F2/F3/B genau identifizieren, welche Aktionen Sleeper nativ sperrt, was in der App nur *anzeigbar* wäre, welche Vorgänge Commissioner-Freigabe benötigen und wie viele tatsächliche Ausnahme-/Nachbesserungsfälle entstehen. Aus 54 Event-Bundles **nicht** 54 Minuten oder 54 manuelle Commissioner-Aktionen ableiten.
6. **Nur bedarfsorientiert Claim simulieren:** Erst dann einen geschützten Spieler-Claim mit und ohne Cap-Kompensation separat testen, wenn die wirtschaftlichen Varianten nach belastbaren Kriterien eine unerwünschte, nicht anders lösbare Persistenzlücke zeigen. Rookie-Draftorder 5.→1.01, 6.→1.02 und bestehende Anti-Tanking-/All-Time-Anreize erhalten.

### Priorität und Handoff

**CP5a abgeschlossen als reproduzierbarer historischer Fenster- und Event-Gate-Vergleich; CP5 insgesamt weiter offen.** Die Daten sprechen für eine ernsthafte Prüfung eines **Post-FA-Draft-Checks** als einfache Gegenvariante und zeigen zugleich, warum solche wenigen Termine die Nachrüstung durch späte Trades und Waiver **nicht vollständig** deckeln. Keine der Varianten hat bisher belegte mehrjährige Dominanz-/Aufhol- oder messbare Operator-Kosten; **keine** Änderung aktiver Regeln und **kein** ligaweiter Beschluss. Die direkte Folgestufe CP5b muss die sechs Nordstern-Ziele und operativen Kosten mit glaubwürdigen mehrjährigen legalen Start-/Settlement-Szenarien konfrontieren, bevor CP6 eine ligaweite Empfehlung mit belastbarer Unsicherheit formuliert.

## 7. QA / Reproduktionsvertrag

- **2025:** Historische Commits 05.11. `ea9d7666…`, 05.12. `e7afd83a…`, 21.12. `0ede4b63…`; pro Commit `League.json` und **dessen** `Players.json` zusammen laden. `Players[].SalaryDollars`, **Top120/6 ohne 0,9**, auf ganzen Dollar kaufmännisch runden; Cap-Assertion **581.658.383 $** in allen drei Snapshots. Team-Top20 aus einzigartigen `Teams[].Roster`, 0 fehlende ID-Salaries; Over-Cap-Team-IDs **[2,3,4]** für jedes Datum. Historische 2025er `SalaryDollarsCurrent` und `SalaryDollarsProjected` nicht mit `SalaryDollars` verwechseln.
- **2026:** 29.06. `85e22feb…`, 25.08. `539aae40…`, 09.09. `b4095617…`, 05.11. `799be2a2…`. Jeweils `Players[].Salary` und `round_half_up(0,9 × sum(top120)/6)`; Caps **434.255.984 $** für Juni/August/September und **427.653.631 $** im November, 0 fehlende IDs. Sums of positive deltas: **0, 0, 122.567.015, 217.960.296**.
- **Frozen:** November-Roster mit **September-Players-Salary**, September-Cap: **5/6** über Cap und **176.958.042 $** positive Überhänge; August→September 1.242 gemeinsame PlayerIDs ohne verändertes Salary.
- **Transaktionen:** `Transactions.json` zum Ref `799be2a2…` (Blob `0aa85766…`), `Status=complete`, `EffectiveAt > Date.parse("2026-09-09T20:33:55Z")`, sortiert nach `EffectiveAt`/ID. Alle `Drops` zuerst, alle `Adds` danach, gesamten Trade atomar für beide Teams bewerten; 54 Events, 46 mit Adds, 3 Trades, 10 zusätzlichen Belastungs-Bundles (7 waiver/3 trade), 1 neue Grenzquerung, 20 all-participant post-event compliant, 0 Start-/End-Roster-Differenzen.
- **Unterschied zur Oktober-Criticality-Proxy-Reihe aus CP2a dokumentieren:** Hier **September-Freeze** als tatsächlicher historischer Preisstand; dort Oktober-Simulation. Keine Dollar-/Effekt-Mischung. `2026-11-14-salary-cap-cp4-metrics.json` ist getrennte Vertragssensitivität.
- **Nicht nachgewiesen:** persönliche Bewertungen einzelner Trades, tatsächliche Gebote, automatisierte Sleeper-Cap-Funktion, Zeitkosten, validierte Gegenwart-/Zukunftsroster unter neuen Regeln oder Championship-Wahrscheinlichkeiten.
