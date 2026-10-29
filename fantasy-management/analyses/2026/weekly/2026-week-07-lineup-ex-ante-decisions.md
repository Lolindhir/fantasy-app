# Mighty Giants — Week 7 2026: Ex-ante-Lineup-Entscheidungen

**Entscheidungsstand:** Sonntag, 25.10.2026, ca. **14:12 MEZ** (Europe/Berlin; vor dem Paris-Kickoff um 14:30 MEZ).  
**Team/Gegner:** Mighty Giants (TeamID 1, 4–2) gegen Team DennisLACards (TeamID 5, 0–6).  
**Format:** Full PPR; 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K. Aktuell maximal drei AutoSubs.  
**Typ:** Vom Nutzer ausdrücklich zur Speicherung freigegebene, zeitgenössische **Ex-ante-Analyse** mit Entscheidungsrationale; **kein** formell versiegelter Decision Record, kein finales Week-7-Postmortem und keine neue Decision-Set-Architektur.  
**Outcome-Firewall:** Die Donnerstagspunkte von Colston Loveland sind bereits bekannt; alles ab dem heutigen International Game wird ausdrücklich nicht als damaliges Entscheidungswissen vorweggenommen.

## 1. Quellen und Grenzen der Rekonstruktion

- **Nutzer-/Chat-Evidenz:** Week-7-Start/Sit-Diskussionen vom 24.–25.10.2026 einschließlich der nach mehrmaliger Abwägung ausdrücklich gewählten Variante Waddle **starten**, Barkley und Hall **benchen**. Die von Robert bestätigte Puka-zu-Tre-Tucker-AutoSub-Paarung ist eine direkte Nutzerangabe.
- **Liga-/Starterstand:** Beobachtetes öffentliches Repo-League-Readmodel public/data/League.json (Blob beim Cutoff: cf0d5a953d010cf73041309beabd454b2b9d619a); aktuelles 13-Spieler-Starter-Set, reguläre Slotstruktur, Roster, Reserve/Taxi, Ligaeinstellungen und Gegnerstarter. Nutzerintention und technisch aus dem League-Readmodel nachgewiesene Startbelegung sind getrennt zu beurteilen.
- **Injury-/Rolleninformationen:** fantasy-management/generated/operations/managed-roster-signals.json, zuletzt für unsere Analyse mit Materialisierungszeit 2026-10-25T10:15:01Z herangezogen. Das ist ein technischer Zwischenstand, **kein** offizielles Game-Day-Inactive- oder Snaplimit-Versprechen.
- **Matchup-Fakten:** public/data/Matchups.json und der damalige Sleeper-Week-7-Matchup-Stand: Mighty Giants **19,90** Punkte, Dennis **19,00**, jeweils ein abgeschlossener Starter. Zwölf Starts pro Team stehen noch aus.
- **Externe Evidenz:** Die im Gespräch angeführten Previews/Week-Rankings und Rollen-/Injury-Begründungen von CBS/Jamey Eisenberg, NBC/Rotoworld, Sports Illustrated, FantasyPros/Derek Brown, 4for4 und DraftSharks wurden qualitativ gegeneinander gewichtet. Dieser Text konserviert den **diskutierten damaligen Evidenzstand**; dynamisch aktualisierte Webseiten oder exakte Ranking-Revisionen sind hier nicht als revisionssichere Originalveröffentlichung gesichert. Nicht belegte genaue Veröffentlichungs- oder Updatezeitpunkte werden nicht nachträglich erfunden.
- **Interne Projektionen:** public/data/MatchupProjections.json ist eine sekundäre Modell-/Szenario-Orientierung. Keine modellierte Team-Punktedifferenz, kein Intervall und keine Sleeper-Einzelprojection ist die primäre Start/Sit-Autorität. Entscheidend bleiben reales gegnerisches und eigenes Lineup, Byes/Availability, Opportunity/Usage, Verletzungsrisiken, NFL-Matchup und nachvollziehbare Expertenargumente.

**Besondere zeitliche Grenze:** Dies ist ein *pregame* Entscheidungsstand für die noch ausstehenden Week-7-Spiele, **kein** vollständiges Pregame-Archiv vor der Woche. Loveland war bereits am Donnerstag gelockt und erzielte 19,90 Punkte. Das bekannte Ergebnis darf die vor Donnerstag begründete Loveland-vs.-Fannin-Entscheidung nicht rückwirkend umformen.

## 2. Favoritenrolle und beabsichtigtes Risikobudget

Mighty Giants stehen 4–2, Dennis 0–6. Die aktuelle Team-/Rosterqualität spricht für eine plausible Favoritenrolle, **aber** Dennis' konkrete verbliebene Starter sind nicht aus dem 0–6-Record abzuleiten und bei vollständiger Besetzung nicht automatisch wertlos. Bereits bekannte Punkte: 19,90 gegen 19,00 nach Donnerstag, je zwölf offene Starter.

Für **enge** Starter-/FLEX-Grenzen soll deshalb regelmäßig verfügbare Opportunity und die Vermeidung zusätzlicher Inactive-/Comeback-/Snaplimit-Downside mehr zählen als ein geringer theoretischer Ceiling-Vorteil. Nicht bedeutet dies, produktive Stars ohne nachgewiesenen Grund zu benchen. Das Risiko muss im Verhältnis zum **tatsächlich erwartbaren** Punktegewinn stehen.

Das interne Repo-Matchup-Modell wurde **ausdrücklich nicht zum Hauptkriterium** für Favoritenstatus, Win Probability oder Ausrichtung auf Floor/Ceiling erhoben.

## 3. Aktueller Starter-Snapshot und festgehaltene Begründung

Aus public/data/League.json, beobachtet am 25.10.2026. Die genaue physische Zuordnung unter austauschbaren FLEX-Äquivalenten kann UI-spezifisch sein; der vollständige Starter-Pool ist sicherer belegt als individuelle visuelle FLEX-Reihenfolgen.

| Slot | Spieler / Sleeper-ID | Entscheidung / Status zum Cutoff |
| --- | --- | --- |
| QB | Patrick Mahomes / 4046 | Start trotz schwieriger Seattle-Defense; individueller Vorteil gegen die realen QB-Alternativen |
| QB | Tyler Shough / 12545 | Start vor Michael Penix Jr.; **früher Paris-Kickoff 14:30 MEZ** |
| RB | Chase Brown / 9224 | Start; Passing-Game-Rolle trotz Samaje-Perine-Konkurrenz stützt den Week-Wert |
| RB | Kenneth Walker III / 8151 | Klarer Start, hohe Opportunity/Qualität |
| WR | Germie Bernard / 13274 | Start im frühen PIT–NO-Spiel; nachziehende Targets/Routen und verfügbare Rolle |
| WR | Malik Nabers / 11632 | Kernstarter |
| TE | Colston Loveland / 12517 | bereits **19,90 PPR** am Donnerstag abgeschlossen |
| TE | Trey McBride / 8130 | Klarer zweiter TE-Start |
| FLEX | George Pickens / 8137 | Start; etwaige späte Monday-Night-Verfügbarkeit separat kontrollieren |
| FLEX | Tetairoa McMillan / 12526 | Klarer Start mit belastbarer Rolle |
| FLEX | Jaylen Waddle / 7526 | **Bewusst gewählter Start nach Abwägung gegen Barkley/Hall** |
| FLEX | Puka Nacua / 9493 | Start, Questionable wegen Wade; Tre Tucker als vom Nutzer bestätigter AutoSub |
| K | Ka'imi Fairbairn / 3451 | Halten, kein überzeugender Streamer-Mehrwert |

**FLEX-/Lock-Optimierung:** Bernard wurde auf einen frühen regulären WR-Slot gestellt; Waddle und andere später startende Spieler verbleiben in den FLEX-Möglichkeiten. Die tatsächliche Aufstellung soll möglichst viel legale Late-Swap-Flexibilität erhalten.

**Bewusst nicht gestartete weitere Optionen:**
- **Jayden Daniels** (WAS) hat **Week-7-Bye** und ist keine QB-Alternative; seine fehlende Erwähnung in der ersten Analyse wurde im Chat korrigiert.
- **Michael Penix Jr.** ist eine reale Alternative zu Shough, im konkreten Week-7-Pool aber nach Rolle, Expertengewichtung und Matchup leicht dahinter.
- **Tyler Warren** steht vor Week 7 auf Out und kann nicht als normaler Starter eingeplant werden.
- **Harold Fannin Jr.** bleibt TE-Alternative, nicht vor den bereits ausgewählten McBride und Loveland.
- **Breece Hall, Saquon Barkley** sind die materialsten FLEX-Gegenkandidaten zu Waddle und werden unten detailliert begründet verworfen.
- **Cam Skattebo** zeigte zuletzt problematischen Snap-/Touch-Rückgang; kein klarer Grenzgewinner.
- **Travis Hunter** und **Seth McGowan** sind zum Cutoff nach der Wave-One-Phase im Kader. Hunter (JAX) hat Bye, McGowan ist gegen Minnesota noch ein Colts-Backup-/Handcuff-Stash hinter Jonathan Taylor und kein hinreichend etablierter Week-7-FLEX-Starter. Der Waivererfolg darf nicht als heutige Starterberechtigung/Leistung missverstanden werden.

## 4. Die entscheidende Abwägung: Waddle vs. Barkley vs. Hall

### 4.1 Konkreter Vergleich

| Dimension | **Jaylen Waddle** (DEN @ ARI) | **Saquon Barkley** (PHI vs DAL) | **Breece Hall** (NYJ vs MIA) |
| --- | --- | --- | --- |
| Kickoff (MEZ) | Sonntag 21:05 | Dienstag 01:15, Monday Night US | Sonntag 18:00 |
| Ex-ante-Einsatzstatus | Keine aktuelle finale Injury Designation | Hamstring, Questionable; Samstag erstmals Full Practice | Quadrizeps/Oberschenkel, Questionable; eingeschränkte Trainingsberichterstattung |
| Relevante Chance | Hohe Route-/Target-Beteiligung + Arizona-Coverage-Matchup | Bei regulärem Comeback potenzielle Lead-RB-Touches + Dallas-Matchup | Attraktives Miami-Matchup, bei voller Rolle Touch- und Receiving-Wert |
| Materielles Risiko | Ineffizientes Broncos-Passing-Game, oft wenige Fantasy-Punkte | Active-but-limited, Schonung, Reinjury, unklare Effizienz nach Pause | Geteiltes Backfield mit Braelon Allen, ungewisses volles Einsatzvolumen |
| Nutzer-Entscheid | **Start** | **Bench** | **Bench** |

### 4.2 Warum Waddle in Week 7 sinnvoll sein kann

Waddle ist **nicht** als garantierter zweistelliger Scorer behandelt worden. Seine ersten Wochen enthielten mehrere magere Fantasy-Ergebnisse, wobei insbesondere die Verbindung mit Bo Nix und Denvers ineffiziente Passing-Offense als echtes Gegenargument identifiziert wurde. Dieser Negativtrend bleibt relevant.

**Positives Week-7-Argument:** Im Gespräch wurden eine sehr hohe Route Participation (ungefähr über 90 %), ungefähr **22 % Target Share** und ungefähr **35 % Air-Yards-Share** sowie Arizonas für Receiver teilweise günstige Man-Coverage-/Yards-per-Target-Konstellation angeführt. Das sind im Chat diskutierte **gerundete Evidenzsignale**, keine im Dokument neu kalibrierten Tracking-Werte. Sie sprechen dafür, dass Waddle **Opportunity besitzt, die bisher schlecht in Fantasy-Punkte übersetzt wurde**, und dass Week 7 echte Chancen auf Verbesserung bietet.

**Expertenkonflikt (damalige Gesprächswiedergabe):** CBS/Jamey Eisenberg und Sports Illustrated bewerteten Waddles Arizona-Chance eher positiv/als vertretbaren Start. 4for4 wurde mit positivem Matchup-Case angeführt. NBC/Rotoworld war deutlich skeptischer wegen Bo Nix und der Routen-/Throw-Kompatibilität. Der Widerspruch wurde nicht einfach gemittelt und keine der Stimmen ist alleinige Entscheidungsautorität.

**Risiko auch bei Start:** Ein durchgehend aktiver Waddle kann trotz voller Routes erneut wenig Punkte machen; die Entscheidung beruht **auf vergleichsweise vorhersagbarer Beteiligung**, nicht auf einem garantierten statistischen Floor.

### 4.3 Warum Barkley *trotz* des guten Matchups nicht startet

**Für Barkley:**
- Materiell positives Samstagssignal: **Full Practice** nach zuvor limitierten Einheiten.
- Angeblich dünneres Eagles-Backfield durch die diskutierten Ausfälle von Tank Bigsby/Will Shipley; unter voller Belastbarkeit Aussicht auf hohe Touch-Anteile.
- Günstig klingendes Dallas-Laufmatchup und mögliche Touchdown-Chancen.
- Ein normal eingesetzter Barkley kann als FLEX starken Erwartungswert und Ceiling besitzen.

**Gegen Barkley:**
- Die offiziell offene Verletzungssituation (Hamstring/Questionable) ist noch keine Garantie für **normale Snaps, Touches und Explosivität**.
- Auch ein aktiver Barkley kann früh erneut Beschwerden bekommen oder vorsichtig geschont werden; in beiden Fällen greift ein Inactive-only-AutoSub **nicht**.
- Die besprochene bis dahin geringe 2026er Produktivität, die angeschlagene Eagles-Offense/Offensive Line und möglicherweise bessere jüngere Dallas-Run-Defense erzeugen Zweifel an der Annahme „Barkley spielt also sicher 12–15 Punkte“.
- Die von Rotoworld diskutierte mögliche Lead-Rolle und die skeptischere FantasyPros/Derek-Brown-Einordnung wurden als **unterschiedliche Thesen** gewichtet, nicht als einheitlicher Expertenkonsens.

**Entscheidungsgrenze:** Barkleys theoretisches Upside ist real, aber die zusätzliche, gegen Dennis kaum notwendige **aktive Comeback-Ungewissheit** war Robert im Verhältnis zu Waddles plausibler Einsatzchance zu groß.

### 4.4 Warum Hall nicht der bevorzugte Gegenspieler ist

Hall trifft mit Miami auf einen attraktiven RB-Gegner. Seine frühere Lead-Back-Phase mit hohem Touch-/Receiving-Volumen macht ihn bei voller Belastbarkeit interessant. Aber die damaligen Injury-/Trainingsberichte beschrieben eine unsichere Rückkehr. **Braelon Allen** hatte in Halls Abwesenheit echte Arbeit übernommen; selbst eine aktive Hall-Meldung löst den möglichen Timeshare oder eine vorsichtige Wiedereingliederung nicht automatisch auf.

Einige Analysten (u. a. im Gespräch angeführter Derek Brown) sahen Hall **bei normaler Rolle** als brauchbaren RB2; skeptischere Vorschauen warnten vor der ersten Comeback-Woche und dem geteilten Workload. **Aktivierung ≠ regulärer Workload.**

**Entscheidung:** Hall ebenfalls bewusst Bench; nur substanziell neue, glaubwürdige Workload-Evidenz **vor seinem eigenen Lock** könnte den Vergleich erneut öffnen.

### 4.5 Der erwogene Barkley–Waddle-AutoSub und die bewusste Ablehnung

**Zwischenlösung im Entscheidungsprozess:** Nach Barkleys Full Practice war die vorläufige Empfehlung zeitweise:
1. **Barkley** auf den FLEX setzen.
2. **Waddle** als seinen AutoSub verwenden, obwohl Waddle schon Sonntag **21:05 MEZ** spielt und Barkley erst Dienstag **01:15 MEZ**.
3. Wenn Barkley nach Sleeper-Regeln **inaktiv** ist, würden Waddles Punkte eintreten; beide wären ab dem **früheren** Kickoff gesperrt.
4. Wenn Barkley dagegen **aktiv, aber deutlich eingeschränkt** ist oder sich während des Spiels verletzt, **greift die AutoSub-Versicherung nicht**.

Die Liga erlaubt nach aktuell gelesenen Settings einen früheren Substitute (die operative Sleeper-Semantik und Lock-Details sind jeweils zur Anwendung separat zu prüfen). Der Nutzer wollte jedoch gerade das Restrisiko eines aktiven, geschonten/verletzten Barkley **nicht** tragen.

**Explizite Nutzerentscheidung nach ausführlichem externen Argumentvergleich:** *Waddle direkt starten, Barkley und Hall auf der Bank lassen.* Roberts Begründung: Bei beiden Running Backs wisse man nach der Verletzung nicht, wie sie zurückkommen, ob sie geschont werden oder sich wieder verletzen. Waddle hat gegen Arizona einen nachvollziehbaren Bounce-back-Case. Das ist eine bewusste Gewichtung der Risiken und des erwarteten Einsatzumfangs, nicht eine pauschale Aussage über den höheren absoluten Talentwert.

**Die Entscheidungskette ist daher transparent:** Erst Waddle als relativ berechenbare Teilnahme-/Opportunity-Wahl; Barkley nach Full Practice und Backfield-Kontext zeitweise mit AutoSub leicht bevorzugt; nach tieferer Prüfung der **active-but-limited**-Downside und Roberts ausdrücklich formulierter Präferenz **Waddle endgültig für diesen Ex-ante-Cutoff bestätigt**. Kein nachträgliches Auswählen des Gewinner-Narrativs anhand des Ergebnisses.

**Nicht erhoben:** Ein numerischer, formell vom Nutzer bestätigter Decision-Confidence-Score, Outcome-Uncertainty-Score oder ein versiegelter Decision-Record-State. Diese Felder werden nicht rückwirkend erfunden.

## 5. Weitere konkrete Grenz- und Sicherheitsentscheidungen

### 5.1 Puka → Tre Tucker als bestätigter AutoSub

Puka Nacua bleibt bei großer normaler Target-/Qualitäts-Upside im FLEX; im materialisierten Stand war er wegen einer Wadenproblematik **Questionable**. Tre Tucker ist als gesundheitlich weniger bedenkliche Option aus demselben Spiel (Rams @ Raiders, Sonntag **21:25 MEZ**) die gewählte Versicherung gegen eine Puka-Inaktivität. **Robert hat ausdrücklich bestätigt, dass diese Paarung korrekt in Sleeper eingerichtet ist.** Das Repository zeigt nur die Starter, nicht zuverlässig die aktive AutoSub-Konfiguration; die Quelle der Paarungsbestätigung ist deshalb die Nutzerangabe.

**Residual Risk:** Puka kann aktiv spielen und trotzdem durch die Wade limitiert sein; das löst nicht automatisch einen Substitute aus. Dieses Risiko wurde im Gespräch ausdrücklich angesprochen.

### 5.2 Shough vs. Penix und Daniels-Bye

- **Mahomes** bleibt QB1 trotz des schwierigen Seattle-Matchups; der verbesserte Gesamtkandidatenvergleich stützt den Start stärker als ein einzelner negativer Analystentake.
- **Tyler Shough** bleibt knapper QB2 über **Michael Penix Jr.**. Relevante Argumente: damaliger NFL-Fantasy-Ausblick, Rushing-/TD-Upside und in den diskutierten unabhängigen Week-Rankings leicht bessere Einstufung; dagegen Steelers-Defense, teilweise TD-lastige jüngste Produktion und das Risiko, einen Einzelscore als stabilen Floor misszuverstehen.
- **Jayden Daniels**: Washington hat Week-7-Bye. Seine zunächst fehlende Besprechung war eine Auslassung, **keine bewusst schlechtere QB-Einstufung**. Kein Wechsel in Week 7 möglich.
- **Paris-Lock:** PIT @ NO startet **Sonntag 14:30 MEZ**. Shough und Bernard sind zum Decision-Cutoff regulär als Starter gesetzt.

### 5.3 Walker, Brown, Bernard und restlicher Grenzpool

- **Kenneth Walker III:** klare RB-Wahl, hohe Rolle und Talent/Opportunity.
- **Chase Brown:** angesichts Perine-Konkurrenz, Baltimore-Matchup und möglichem Run-Down-/Red-Zone-Split kein blind sicherer RB1, aber durch Passing-Game-Nutzung, Routes und Targets gegenüber den unsicheren Bench-RBs der bevorzugte fixe RB.
- **Germie Bernard:** gutes jüngstes Target-/Usage-Signal, Wachstum der Rolle und diskutierte Steelers-Personalausfälle. Er bleibt im **festen WR-Slot**, um späteren FLEX-Spielern Optionen zu bewahren.
- **Malik Nabers, Tetairoa McMillan, George Pickens, Trey McBride:** keine ausreichend starke Gegenhypothese aus der Bank für einen vorschnellen Startwechsel; Pickens' später Lock bleibt separat relevant.
- **Colston Loveland statt Fannin:** Vor Thursday gab es eine ausführliche Abwägung von aktuellen Routes/Targets, Rolle und Expertenbewertungen. Eine nachträgliche Schwankung wegen kleiner Sleeper-Expected-Points-Differenz war nicht tragfähig; Loveland wurde schließlich *vor* dem Lock bevorzugt. Seine **19,90 Punkte** sind bereits bekannt, aber **kein Beweis**, dass jede damalige Modellannahme richtig war.
- **Tyler Warren** (Out) und **Harold Fannin Jr.** sind keine überzeugenden aktuell frei wählbaren Verbesserungen gegenüber dem gesetzten TE-Duo. Tre Tucker hat primär die AutoSub-Rolle hinter Puka.
- **Ka'imi Fairbairn** bleibt gesetzt; keine wesentliche Kicker-Streaming-These.

## 6. Zeit-/Lock-Matrix und weitere Informationsgrenzen

| Zeitpunkt (MEZ) | Was wusste/entschied man und was bleibt legal? |
| --- | --- |
| Donnerstag/Friday-Auswertung | Loveland vor dem Spiel bewusst gesetzt, anschließend 19,90 Punkte bekannt; danach kein retroaktives Austauschen mit Fannin. |
| Samstag 24.10. | Barkleys Full Practice erhöht real die erwartete Teilnahmechance. Zwischenzeitlich Barkley + Waddle AutoSub favorisiert. |
| Sonntag 25.10. vor ca. 14:12 | Nutzer wählt nach ausführlicher Abwägung **Waddle direkt**, **Barkley/Hall Bench**; bestätigt **Puka/Tre Tucker AutoSub**. |
| Sonntag 14:30 | **Shough / Bernard:** Paris PIT–NO. Kein nachträglich neu verfügbarer Spieler kann sie rückwirkend ersetzen. |
| Sonntag bis 18:00 | Hall-Inactives/Workload könnten zusätzliche Evidenz liefern, verändern aber nicht die hier dokumentierte damalige Entscheidung. |
| Sonntag bis 21:05 | Letzter potenzieller Zeitpunkt für ein hypothetisches Barkley/Waddle-Pairing (Waddles Kickoff); **nicht** der gewählte Plan. |
| Sonntag bis 21:25 | Puka/Tucker-Kickoff: eigene Paarung/Inactive-Informationen prüfen; active-but-limited-Risiko bleibt. |
| Dienstag 01:15 | PHI–DAL: Barkley ist gemäß besprochener Entscheidung Bench. Ein später guter Score wäre kein automatischer ex-ante Decision Regret. |

**Zeitumstellung:** Deutschland stellt am 25.10.2026 auf MEZ um, die USA später. Paris **14:30 MEZ**, normale Sonntagsspiele ab **18:00 MEZ**, Waddle **21:05**, Puka/Tucker **21:25**, Barkley **Dienstag 01:15**.

## 7. Entscheidungsfazit und Post-Week-Prüfplan

**Besprochene gewählte Aufstellung:** Das gespeicherte 13er-Starterset einschließlich **Waddle FLEX** gilt zum Cutoff als gewünschte Week-7-Aufstellung. **Barkley und Hall** bleiben bewusst Bench. **Puka startet**; Tre Tucker ist laut Nutzer als AutoSub korrekt eingetragen. Shough/Bernard bleiben für das frühe Paris-Spiel gesetzt. Hunter und McGowan sind zunächst Stashes, nicht neue Week-7-Starter.

**Tragende These:** Waddles tatsächlich laufende Routes/Targets und günstiger Arizona-Matchup-Pfad liefern eine vertretbare Chance auf Erholung von schwachen Fantasy-Ausbeuten. Barkley und Hall besitzen Upside, aber zusätzlich zum normalen Scoring-Risiko unklaren Comeback-Workload und ein nicht von AutoSub versichertes **aktives Limitierungs-/Reinjury-Risiko**. Gegen Dennis priorisiert Robert deshalb Waddles besser vorhersagbare Einsatzbeteiligung. Das ist eine reflektierte Prozessentscheidung, **keine Garantie, dass Waddle mehr Punkte erzielt**.

**Späteres eigenständiges Postmortem (Issue #208) sollte prüfen:**
1. Welche Starter/AutoSubs tatsächlich gewertet wurden – ohne nachträglich falsche Ausführung zu unterstellen?
2. Welche Injury-/Workload-Berichte zu Hall, Barkley, Puka und Pickens **bis zu ihren jeweiligen Locks** vorlagen?
3. Ob Waddles angenommene Route-/Target-Beteiligung und das Coverage-Matchup belastbar waren und angemessen gegenüber Bo-Nix-Risiken gewichtet wurden?
4. Ob ein anderer Spieler **zum selben realen Entscheidungszeitpunkt** eine plausibel bessere Wahl war, nicht einfach der hindsight-punktstärkste spätere Spieler?
5. Was Outcome Regret vs. Same-Information Decision Regret ist, unabhängig von jungen Repo-Projektionen?

Diese Datei ist ein **zeitlich begrenzter, nicht versiegelter Ex-ante-Beleg** und soll mit späteren Ergebnissen **nicht überschrieben** werden. Neue Erkenntnisse und Wertungen gehören in ein separates Week-7-Postmortem. Das offene generische Decision-Record-/Set-Konzept wird weiterhin durch Issue #629 gestaltet; diese Dokumentation etabliert kein konkurrierendes Schema.

## 8. Kanonische Referenzen

- fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md — Weekly-Guardrails, Reversal Gate, Matchup-Risikobudget, AutoSub, Modellrangfolge und spätere Outcome-Firewall.
- fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md und fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md — Quellendisziplin und Dynamic-League-Context.
- public/data/League.json — aktuelle Starter, Liga-/Slot-/Roster-Regeln (Stand siehe oben).
- public/data/Matchups.json — Donnerstagsspielstand.
- fantasy-management/generated/operations/managed-roster-signals.json — materialisierter Availability-Status (nicht finale NFL-Inactives).
- GitHub Issues #206 (Weekly Workflows), #629 (noch offener allgemeiner Decision-Record-/Set-Contract) und #208 (separates Post-Week-Review).
