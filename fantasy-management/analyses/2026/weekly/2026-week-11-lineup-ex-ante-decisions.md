# Mighty Giants – Week 11 (2026): Ex-ante-Lineup-Entscheidungen gegen Team TimpaBay

**Entscheidungsstand:** Sonntag, 22.11.2026, vor dem ersten Sonntags-Lock (19:00 Uhr MEZ, Europe/Berlin). **Web-Evidenz-Capture:** 22.11.2026, während der Erstellung dieser Analyse, vor dem Sonntag-Lock; exakte Abrufminute nicht protokolliert.  
**Team und Gegner:** Mighty Giants (Robert, TeamID 1; vor Week 11: 5–5) gegen Team TimpaBay (Tim, TeamID 6; 5–5).  
**Liga:** 6 Teams, Full PPR, 2 QB / 2 RB / 2 WR / 2 TE / 4 gemeinsame RB-WR-TE-FLEX / 1 K, 13 Starter.  
**Status:** Zeitgenössische Ex-ante-Entscheidungsakte; am 22.11.2026 als manuelle Ex-ante-Dokumentation im Repository archiviert, kein formell versiegelter Decision Record, keine Sleeper-Mutation. Die aktuell **technisch gesetzten 13 Starter** sind im Repo-Readmodel und im Sleeper-Provider-Snapshot nachgewiesen. Konkrete AutoSub-Paarungen sind **nicht verifiziert**.  
**Outcome-Firewall:** Die Thursday-Partie IND @ HOU ist bereits abgeschlossen. Bekannt gewordene Punkte dieser Partie fließen ausschließlich in den aktuellen Matchup-Zustand ein, **nicht** rückwirkend in die damals begründete Starterentscheidung. Für noch ausstehende Spiele sind sämtliche Angaben Pregame-Prognosen bzw. Evidenz.

## 1. Technischer Snapshot und Datenqualität

| Datenbasis | Git-Blob-SHA / Stand | Zweck |
| --- | --- | --- |
| `public/data/League.json` | `2d2609bab76ae61f36ca418289b29256ba3e3150` | Aktuelle 13 Starter, Ligaformat, Owner, AutoSub-Limits |
| `data-source/providers/sleeper/leagues/1354177383984267264/matchups/week-11.json` | `79b5ee0fd6d6304714bb3924313580164add4d5f` | Unabhängiger Provider-Beleg für gesetzte Starter und Thursday-Punkte |
| `public/data/Matchups.json` | `003543fae4a04eb14568225a42496151745cabfa` | Matchup-State, 6,0 : 20,3 vor den Sonntagsspielen |
| `public/data/PlayerWeekFantasy.json` | `b2fcdd4e3af5e08a3e70abe05ffb6566095cf1c1` | Experimentelle V4-C-Projektionen, konditional auf Teilnahme |
| `public/data/MatchupProjections.json` | `273ababe37dea536a4076e059c1f520705b81469` | Sekundäres, nicht hinreichend extern kalibriertes Szenariomodell |
| `fantasy-management/generated/operations/managed-roster-overview.json` | `8269a43dbb72f75946ed5909a645333e64c369c0`; generiert 22.11., 05:22 MEZ | Roster-Snapshot, 37 kontrollierte Spieler, Verletzungsflags |
| `public/data/Schedule.json` | `2ae95f1b3202d54fae424f8055f6635955af10cb` | Enthält **veraltete Kickoff-Zeiten** für zwei Week-11-Spiele; unten nach offizieller NFL korrigiert |

**Quellenhierarchie:** Offizielle NFL-/Team-Injury- und Kickoff-Meldungen vor dynamischen Repository-Flags; aktuelle externe PPR-Week-Rankings und begründete Rollenanalysen vor isolierten V4-C-Werten. Die Ausgangsdiskussion am 19.–22.11. ist **Gesprächsevidenz**, keine nachträglich als unveränderliches Ranking-Snapshot ausgegebene Website-Version. *Roster Role* und *Roster Security* sind langfristige Dynasty-Dimensionen und nicht gleich der wöchentlichen Startberechtigung.

**Besonderer Datenfehler:** Die NFL hat am 09.11. ausdrücklich **JAX @ NYG von 19:00 auf 22:25 MEZ** und **PIT @ PHI von 22:25 auf 19:00 MEZ** verschoben. `public/data/Schedule.json` und das daraus erzeugte `FantasyGameContext.json` führen noch die früheren Zeiten. Für die folgenden Decision-Locks gelten die **offiziellen** Zeiten: https://www.nfl.com/news/week-11-schedule-change und https://www.nfl.com/schedules/2026/by-week/week-11. Die fehlerhafte App-Zeit ist keine autoritative Deadline.

## 2. Aktuell gesetzte und empfohlene Startaufstellung (13/13)

| Slot | Spieler (Sleeper-ID) | Gegner | Tatsächlicher Kickoff (MEZ) | V4-C, vor Einsatz | Ex-ante-Entscheidung |
| --- | --- | --- | --- | ---: | --- |
| QB1 | **Patrick Mahomes** (`4046`) | KC vs ARI | So., 22.11., 19:00 | 20,14 | START – hohe QB-Sicherheit |
| QB2 | **Jayden Daniels** (`11566`) | WAS vs CIN | Di., 24.11., 02:15 | 19,78 | START – gegenüber Shough bevorzugt |
| RB1 | **Chase Brown** (`9224`) | CIN @ WAS | Di., 24.11., 02:15 | 14,86 | START – etablierter Full-PPR-Case |
| RB2 | **D'Andre Swift** (`6790`) | CHI vs NO | So., 22.11., 19:00 | 17,08 | START – etablierte Rolle, günstiger Gegner; Monangai-Rückkehr beachten |
| WR1 | **George Pickens** (`8137`) | DAL vs TEN | So., 22.11., 19:00 | 15,83 | START – höherer Weekly-Tier als Bench-WR |
| WR2 | **Malik Nabers** (`11632`) | NYG vs JAX | So., 22.11., **22:25** | 15,51 | START – **offiziell späterer Lock** |
| TE1 | **Colston Loveland** (`12517`) | CHI vs NO | So., 22.11., 19:00 | 9,60 | START – vor dem am Donnerstag gelockten Warren |
| TE2 | **Trey McBride** (`8130`) | ARI @ KC | So., 22.11., 19:00 | 17,35 | START – klarer TE-Start |
| FLEX1 | **Cam Skattebo** (`12481`) | NYG vs JAX | So., 22.11., **22:25** | 14,79 | START – relevante RB-Opportunity |
| FLEX2 | **Tetairoa McMillan** (`12526`) | CAR vs BAL | So., 22.11., 19:00 | 14,08 | START – konstante Receiver-Opportunity |
| FLEX3 | **Breece Hall** (`8155`) | NYJ @ LAC | So., 22.11., 22:05 | 13,12 | START – Receiving-Wert, geteilte Backfield-Rolle als Risiko |
| FLEX4 | **Jaylen Waddle** (`7526`) | DEN vs LV | So., 22.11., 22:25 | 8,67 | **START KNAPP** – externe PPR-Rankings und offizielle Einsatzfreigabe wichtiger als kleine/interne Modellabweichungen |
| K | **Ka'imi Fairbairn** (`3451`) | HOU vs IND | Fr., 20.11., 02:15; abgeschlossen | 11,08 vor Spiel | **GESTARTET – 6,0 Ist-Punkte**, seit Thursday gelockt |

Die V4-C-Spalte enthält **modellierte Wochenwerte, keine bestätigten Expected Points bei Verletzungen**. Sie wurde nicht nach dem Ergebnis „korrigiert“: insbesondere Fairbairns ursprüngliche 11,08 Punkte und die tatsächlichen 6,0 Punkte sind getrennte Felder. Kein Starter ist aktuell auf Bye gelistet.

## 3. Thursday-Cutoff: was bereits entschieden und gelockt ist

**Zeitfenster:** Freitag, 20.11.2026, 02:15 MEZ – IND @ HOU.

- **Fairbairn: START**. Zum heutigen Sonntag-Cutoff sind **6,0 Punkte** im offiziellen Liga-Matchup gewertet. Ein nachträglicher Kickerwechsel ist keine verfügbare Alternative.
- **Tyler Warren: BENCH**. Die zuvor besprochene Begründung war Lovelands bessere externe Week-11-Einschätzung gegenüber Warrens Houston-Matchup, **obwohl** V4-C Warren mit ca. 10,76 vor Loveland mit ca. 9,60 sieht. Die damalige Gesprächszusammenfassung zitierte 4for4 mit **Loveland 13,9 versus Warren 11,4** PPR, aber keine separat archivierte Ranking-Revision; Evidenzstatus: `pre_lock_referenced_unarchived`. Die nun sichtbaren **3,2 Bench-Punkte Warrens** sind ausschließlich Outcome, kein nachträglicher Beleg für die damalige Start/Sit-Prozessqualität.
- **Seth McGowan, Marvin Harrison Jr. und Alec Pierce** wurden nicht gestartet; Harrison war Out, Pierce Reserve. Bereits gelockte Colts-/Texans-Alternativen dürfen **nicht** rückwirkend in die Sonntags-Grenzentscheidung eingeschleust werden.
- Der frühere Entscheidungsstand enthält **keine bestätigte konkrete AutoSub-Paarung** für Warren. Nicht nachträglich eine als eingerichtet behaupten.

## 4. Gemeinsamer Starter-Boundary-Stresstest: vier FLEX und die wichtigsten Alternativen

**Ziel:** Die vier tatsächlich eingesetzten FLEX-Spieler bilden einen gemeinsamen RB/WR/TE-Pool. Nicht der bestehende Starterstatus, sondern liga-spezifische Rolle, PPR-Opportunity, Floor/Median/Ceiling, Injury, unabhängige Rankings und Lock-/Ersatzpfade begründen die Reihung.

| Spieler | Rolle | V4-C | Externe datierte Evidenz | Tragender Case und Gegenhypothese |
| --- | --- | ---: | --- | --- |
| **Cam Skattebo** | FLEX START | 14,79 | Bereits im Week-11-Gespräch als klarer Starter bewertet; genaue Original-Rangzeile hier nicht neu archiviert | Gute Lead-Back-Opportunity; gegen JAX kann Effizienz schwanken. Späterer NYG-Lock ist echte Flexibilität, **kein** Startbonus. |
| **Tetairoa McMillan** | FLEX START | 14,08 | Vorangehende externe PPR-WR-Rankings ordneten ihn klar vor der Boundary ein | Target-/Route-Rolle stützt Floor; BAL-Matchup und QB-Effizienz begrenzen Upside. |
| **Breece Hall** | FLEX START | 13,12 | **Athlon Week-11 PPR-FLEX #47** | PPR-Receiving, reale Touch-Chance; Allen/Backfield-Split kann Carries und Goal-Line-Potenzial senken. |
| **Jaylen Waddle** | FLEX START | 8,67 | **Athlon #46**, **DraftSharks PPR-FLEX #45**; Broncos: Full Practice und am 20.11. **keine Game Designation** | Gegen LV plausibler Receiving-Floor; nach Concussion-Rückkehr bleiben aktive Snap-/Workload- und In-Game-Risiken. |
| **Kyle Monangai** | BENCH, sehr knapp | 12,98 | **Athlon #50**; Bears am 20.11. offiziell: Full Practice, keine Game Designation | Positiv: Saints-Run-Matchup, vor Verletzung echte Carries; gegen Start: Rückkehr nach fünf verpassten Spielen, Swift-Backfield geteilt. Gegenhypothese: Bei sofort normaler Volumenverteilung wäre Monangai gegenüber Waddle besser. |
| **Saquon Barkley** | BENCH, sehr knapp | 8,26 | **Athlon #64**; **DraftSharks PPR-FLEX #48**; volles Training, ohne Game Designation | Positiv: mehrwöchige Elite-Touch-/TD-Upside und möglicher Erholungseffekt nach Bye; gegen Start: zuletzt nur ungefähr 58 % Snaps und 13 Carries, weiter spürbare Hamstring-Folgen, schwierige Steelers-Run-Defense. **Korrekt 19:00 Uhr Lock!** |
| **Adonai Mitchell** | BENCH | 9,04 | **Athlon #86** | Big-Play-Ceiling vorhanden; Rollen-/Target-Stabilität schwächer als die etablierte FLEX-Gruppe. |
| **Pat Bryant** | BENCH; späte Waddle-Ersatzoption | 9,09 | In der vorigen Quellenprüfung hinter Waddle; Week-11-Rangzeile hier nicht direkt neu verifiziert | Gleicher Denver-Lock 22:25; technisch möglicher Backup, aber begrenztere eigene Rolle und dieselbe Offensive. Eine **tatsächliche AutoSub-Zuordnung ist unbestätigt**. |
| **Germie Bernard** | BENCH | 9,31 | Vorherige Week-11-Expertenprüfung hinter den Hauptkandidaten; keine frische Original-Rangzeile gespeichert | Gute Snap-Beteiligung, unsichererer Target-Floor; **wegen PIT @ PHI schon um 19:00 Uhr gelockt**. |
| **Ladd McConkey** | BENCH | 8,97 | App-Injury-Snapshot: **Questionable** (Rücken/Spasmen), offizielle finale Inactives vor Spiel erneut prüfen | 22:05-Uhr-Alternative nur falls wirklich spielberechtigt und rechtzeitig umgestellt; höheres Availability-Risiko. |
| **Kenneth Walker III** | **OUT** | **23,64 (nicht startfähig)** | Chiefs offizieller Injury Report, 20.11.: **Out (groin)** | Wichtigster Modell-Availability-Konflikt. Die höchste V4-C-FLEX-Projektion ist gegen einen bestätigten Ausfall **nicht entscheidungsfähig**. |

**Weitere Bench-/Verfügbarkeitsgrenzen:** Tyler Warren ist bereits am Donnerstag gelockt; Harold Fannin Jr. hat CLE-Bye; Puka Nacua ist im Repo-Injury-/Roster-Stand IR; Marvin Harrison Jr. ist Out. Aktive Bench-, Reserve- und Taxi-Spots dürfen nicht als beliebig verfügbare FLEX-Optionen zusammengeworfen werden.

### 4.1 Urteil an der letzten FLEX-Grenze

**Waddle leicht vor Monangai und Barkley; Entscheidungssicherheit mittel, nicht hoch.** Die direkt vergleichbare aktuelle **Athlon-PPR-FLEX-Liste** stellt Waddle auf 46, Hall auf 47, Monangai auf 50 und Barkley auf 64. **DraftSharks** sieht Waddle 45 und Barkley 48, also deutlich enger. Diese Quellen sind externe Week-Rankings, keine Garantie. Die in der vorigen Unterhaltung zitierten Footballguys-PPR-Projektionen (Waddle 10,5, Barkley 10,9, Monangai 11,6) sind als `pre_lock_referenced_unarchived` zu behandeln, weil hier kein unveränderlicher Quellensnapshot vorliegt; sie belegen eine **echte Meinungsdivergenz** und dürfen nicht verschwinden.

- **Warum gegen Monangai?** Seine Rückkehr ist offiziell, aber die Volumenverteilung mit Swift ist nach der Pause weniger vorhersehbar. Das kann die positive V4-C-Projektion von 12,98 entwerten. **Gegenhypothese:** Saints-Game-Script begünstigt zwei RBs und Monangai erhält sofort 10–15 hochwertige Touches; dann wäre Bench möglicherweise der schlechtere Call. Diese Gegenhypothese ist plausibel und begrenzt die Konfidenz.
- **Warum gegen Barkley?** Volltraining und kein Game Status sprechen für Einsatzbereitschaft, aber nicht automatisch für volle Belastbarkeit. RotoWire berichtete am 20.11. über verbliebene Hamstring-Effekte und ca. 58 % Snaps im jüngsten Spiel; der Steelers-Gegner erschwert die Floor-Prognose. **Gegenhypothese:** nach Bye kehrt sein Workhorse-Touchvolumen zurück; das eigene Ceiling kann Waddle klar überholen. Auch das ist plausibel.
- **Warum dennoch Waddle?** Medizinisch freigegeben und mehrere aktuelle, direkt vergleichbare **PPR-FLEX**-Quellen sehen ihn etwas vorn. Sein früherer Target Share von ungefähr 18,8 % aus der vorherigen Diskussion verhindert jedoch die Behauptung eines sicheren WR1-Floors. Die Wahl ist **eine bewusste Präferenz bei knapper Evidenz, kein eindeutiger Punktvorteil**.

**Modell-/Markt-Konflikt:** V4-C setzt Monangai (12,98) deutlich vor Waddle (8,67) und Walker (23,64) sogar über den gesamten Vergleichspool trotz offiziellen Outs. Weil das Modell auf Teilnahme konditioniert und Verfügbarkeit/Workload nicht zuverlässig korrigiert, wird diese Abweichung ausdrücklich für den späteren Modellcheck archiviert. Sie rechtfertigt **keine** heutige Blindoptimierung.

**Reversal Gate:** Die zuvor getroffene Waddle-Empfehlung bleibt bestehen, solange keine materiell neuen, verifizierten Informationen hinzukommen (z. B. überraschende Inactive-Meldung, konkreter Snap-Limit-Bericht, veränderter QB-/Rollenstatus oder erkannter Vergleichsfehler). Ein einzelner neuer niedriger/höherer Projektionswert ist kein hinreichender Reversal-Grund.

### 4.2 FLEX-Portfolio (Skattebo + McMillan + Hall + Waddle)

- **Getragene Volumenbasis:** Skattebo (RB-Lead-Rolle), McMillan (Receiving-Opportunity) und Hall (zusätzlich Passspielbeiträge) sind nachvollziehbar startbar; jeder trägt dennoch Matchup-/Game-Script-Downside.
- **Erhöhte Risiken:** Halls geteilter RB-Workload und Waddles Concussion-Rückkehr erhöhen die Unsicherheit. Gegenüber dem Doppelstart Swift + Monangai wird bewusste Bears-Backfield-Konzentration vermieden. Das ist ein relevanter **Portfolio-Trade-off**, keine automatisch „schlechte“ gemeinsame Offense.
- **Timing:** Skattebo, Hall und Waddle spielen erst im späteren Sonntagsfenster. Dies wahrt Information für echte späte Swaps; früh gelockte Barkley/Monangai sind spätestens 19:00 Uhr keine frei austauschbaren Ersatzspieler mehr.
- **Rest-Risiko:** Ein offiziell aktiver Waddle kann trotzdem limitiert spielen oder sich im Spiel erneut verletzen. **AutoSub schützt nicht gegen Active-but-limited oder In-Game-Injury.** Dass Bryant im selben Team spielt, begründet außerdem keine garantierte unabhängige Risikodiversifikation.

## 5. Pflichtpositionen und weitere Start/Sit-Fragen

**QB:** Mahomes + Daniels bleiben gegen Shough gesetzt. Im Zwei-QB-Format zählen zwei reale Starter; Mahomes/Daniels sind auch in den in der vorangehenden Sitzung geprüften 4for4/FantasyPros-Week-11-Einschätzungen klar bevorzugt. Die konkreten Ranking-Revisionen jener Sitzung sind `pre_lock_referenced_unarchived`, nicht hier als neuer URL-Snapshot ausgegeben.

**RB:** Swift + Brown bilden die beiden festen RBs. Monangais Rückkehr reduziert potenziell Swifts absolutes Touch-Ceiling, nicht ohne Weiteres seine Startwürdigkeit gegen New Orleans. Brown spielt erst Monday Night in WAS und bleibt ein stabiler PPR-Start.

**WR:** Pickens + Nabers werden gegen den vorhandenen Receiver-Bench-Pool beibehalten; McMillan ist als dritter WR im FLEX. Nabers' Giants-Spiel wurde offiziell nach hinten verlegt, ohne seine Qualität als Startentscheidung zu ändern.

**TE:** McBride + Loveland. Warren ist bereits gelockt. Der damalige Loveland-over-Warren-Entschluss weicht vom kleinen V4-C-Vorsprung Warrens ab, ist durch externe Week-Rankings und Gegenmatchup begründet. Sein tatsächliches Thursday-Ergebnis darf nicht als Ex-ante-Quelle dienen.

**Kicker:** Fairbairn bleibt als bereits eingesetzter Spezialstarter mit 6 Punkten. Kein nachträgliches „Hätten wir einen anderen Kicker geholt“-Argument ohne zeitkonforme Add-/Drop-/Roster-Kosten.

**Waiver/Add/Drop:** Für diese 13er-Aufstellung **kein neuer Add oder Drop erforderlich**; ein unbewiesener Streaming-Vorteil soll keinen Dynasty-Asset-Cut auslösen. Eine vollständige neue Free-Agent-Marktprüfung liegt diesem begrenzten Ex-ante-Dokument nicht zugrunde. Daher **keine Behauptung**, sämtliche möglichen externen Upgrades seien abschließend ausgeschlossen.

## 6. Gegneranalyse und aktuelles Risikobudget

**Matchup nach dem bereits gewerteten Thursday-Spiel:** Mighty Giants **6,0** (1 abgeschlossener Starter) gegen Team TimpaBay **20,3** (2 abgeschlossene Starter). Der optische Rückstand von 14,3 Punkten ist **kein belastbarer Comeback-Zwang**, weil Tim einen zusätzlichen Starter bereits verbraucht hat.

**Wichtige Korrektur gegenüber dem früheren Chatstand:** Das aktuell abgerufene `League.json` und der Sleeper-Week-11-Snapshot enthalten bei **beiden Teams sämtliche 13 belegten Starter**, einschließlich **zweier QB-Slots bei Tim**. Ein angeblich leerer Tim-Quarterbackplatz darf nicht mehr als Vorteil für uns eingerechnet werden. Dies ist eine **neue bzw. korrigierte Repo-Beobachtung**, keine Behauptung über die Ursache der Änderung.

**Gegnerische Upside:** Die zuvor besprochenen Hoch-Ceiling-Spieler Gibbs, Lamb und Higgins bleiben für die Matchup-Varianz relevant; ohne aktuelle individuelle Start-/Injury-Vollprüfung kann daraus keine konkrete genaue Siegwahrscheinlichkeit abgeleitet werden.

**Modellszenario nur sekundär:** `MatchupProjections.json` zeigt derzeit ungefähr **186,8 Punkte Mighty Giants gegenüber 180,0 Team TimpaBay**. Es weist zusätzlich eine eigene 57%-Win-Probability aus, aber das zugrunde liegende Modell ist nicht ausreichend kalibriert und enthält Teilnahme-/Verfügbarkeitsannahmen. Deshalb wird **kein tatsächlicher 57%-Favoritenstatus behauptet**. Für knappe FLEX-Calls ist ein ausgewogenes Floor-/Median-Profil vernünftig; eine absichtliche maximal-riskante Upside-Aufstellung ist aufgrund des bloßen Thursday-Rohscores nicht gerechtfertigt.

## 7. Chronologische Decision-Opportunity-Timeline und AutoSubs

| Cutoff (MEZ) | Faktisch verfügbare Entscheidung | Gewählte/empfohlene Handlung und offene Nachweise |
| --- | --- | --- |
| **Fr. 20.11., 02:15** | IND @ HOU, alle Spieler dieses Spiels gelockt | Fairbairn START, Warren BENCH; zu diesem damaligen Cutoff keine nachträglichen Sunday-Argumente. Ergebnis jetzt Fairbairn 6,0; Warren 3,2 auf Bench. |
| **So. 22.11., vor 19:00** | Frühe Spieler: Mahomes, Swift, Pickens, Loveland, McBride, McMillan; **Barkley und Monangai** wären nur bis dahin echte alternative FLEX-Starts | Aktuelles 13er-Lineup beibehalten. Finale 19-Uhr-Inactives/Practice-Kontext idealerweise ca. 17:30–18:00 kontrollieren. **Die offizielle Flex-Verschiebung macht Barkley bereits jetzt zu einem frühen Lock.** |
| **So. 22.11., 22:05** | NYJ @ LAC: Hall; alternative Mitchell und der fragliche McConkey | Hall START; mögliche Game-Status-Nachrichten vor diesem Lock prüfen; kein bereits früher gelocktes Spiel als späteren Ersatz verwenden. |
| **So. 22.11., 22:25** | LV @ DEN: Waddle und möglicher Backup Bryant; **JAX @ NYG**: Skattebo und Nabers | Waddle START, Skattebo/Nabers START. Finale Inactives voraussichtlich ab ca. **20:55** beachten; konkrete **Waddle → Bryant**-AutoSub-Konfiguration ist **nicht belegt**. Falls Waddle unerwartet inactive ist, rechtzeitig legalen direkten Swap oder nachweislich konfigurierte Paarung nutzen. |
| **Di. 24.11., 02:15** | CIN @ WAS: Daniels und Chase Brown | Beide derzeit START; Last-Minute-Status und tatsächliche Restslots beachten. |

**AutoSub-Regelstand im Repo:** `max_subs=3`, `sub_start_time_eligibility=0`, `sub_lock_if_starter_active=0`. Diese Werte beweisen nicht, **welche** Paarung der Manager eingerichtet hat. Der heutige Ex-ante-Stand enthält daher **`AutoSub-Konfiguration: unconfirmed`**. Bei früher einsetzbaren Bench-Spielern ist außerdem deren eigener Lock zu beachten. Keine fiktive „Versicherung“ ins Postmortem übernehmen.

## 8. Datierte externe Quellen und Evidenzstatus

Die folgenden **tatsächlich für dieses Dokument konsultierten** Webdaten wurden am **22.11.2026 vor den Sonntagsspielen** gelesen. Wo die Website keine eindeutige Veröffentlichungs- oder Änderungszeit zeigt oder kein unveränderliches Archiv existiert, bleibt das ausdrücklich offen. Alle Links zu dynamischen Rankings können später andere Werte anzeigen.

| Herausgeber / Titel / Link | Quelltyp / Zeitpunkt | Konkret notierte Week-11-Evidenz | Evidenzstatus |
| --- | --- | --- | --- |
| [NFL: Week-11-Schedule-Change](https://www.nfl.com/news/week-11-schedule-change) | Offizielle NFL-Spielplanänderung, Mitteilung **09.11.2026** | JAX @ NYG 16:25 ET / **22:25 MEZ**; PIT @ PHI 13:00 ET / **19:00 MEZ** | `pre_lock_captured` für Sonntagsentscheidungen |
| [NFL: Week-11-Schedule](https://www.nfl.com/schedules/2026/by-week/week-11) | Offizieller Week-Schedule; dynamische Seite, Updatezeit unbekannt | Bestätigt korrigierte Spielzeiten | `pre_lock_captured` |
| [Chiefs: Week-11-Injury-Report](https://www.chiefs.com/news/week-11-injury-report-cardinals-vs-chiefs-2026) | Offizieller Team-Injury-Report, **20.11.2026** | Kenneth Walker III **OUT (groin)** | `pre_lock_captured` |
| [Broncos: Final Week-11-Injury-Report](https://www.denverbroncos.com/news/injury-report-s-talanoa-hufanga-among-broncos-not-assigned-game-statuses-s-brandon-jones-questionable-for-week-11-vs-raiders) | Offizieller Team-Injury-Report, **20.11.2026** | Jaylen Waddle Full Practice, **keine Game Designation** | `pre_lock_captured` |
| [Bears: Monangai ready vs. Saints](https://www.chicagobears.com/news/jeffery-simmons-kyle-monangai-good-to-go-against-saints-injury-update) | Offizieller Team-Status, **20.11.2026** | Monangai Full Practice, **keine Game Designation** | `pre_lock_captured` |
| [Athlon / Cory Bonini: Week-11 PPR FLEX](https://athlonsports.com/fantasy/fantasy-football-flex-ppr-rankings-2026-nfl-week11) | Gemeinsames RB/WR/TE-PPR-Ranking, **Update 21.11. 22:54 EST = 22.11. 04:54 MEZ** | Waddle **46**, Hall **47**, Monangai **50**, Barkley **64**, Mitchell **86** | `pre_lock_captured` |
| [DraftSharks: Week-11 PPR FLEX](https://www.draftsharks.com/weekly-rankings/11/flex/ppr) | Gemeinsames PPR-FLEX-Ranking; Seite „updated today“ am 22.11., **genaue Update-Minute unbekannt** | Waddle **45**, Barkley **48**; geringe Trennung | `pre_lock_captured` |
| [RotoWire: Barkley cleared](https://www.rotowire.com/football/headlines/saquon-barkley-news-in-clear-for-week-11-action-648850) | Injury-/Rollenbericht, **20.11.2026** | Volles Training, ohne Game Designation, verbliebene Hamstring-Folgen; letztes Spiel ca. **58 % Snaps, 13 Carries** | `pre_lock_captured` |
| [NBC Sports: Monangai on track](https://www.nbcsports.com/fantasy/football/player-news/2026-11-16/monangai-back-at-practice-on-track-for-week-11) | Fantasy-Rollenbericht, **16.11.2026** | Frühere RB-Snap-Anteile ca. 31–54 % und Rückkehr ins Swift-Timeshare | `pre_lock_captured` (Rollenannahme bleibt unsicher) |
| Week-11-Gespräch vom 19.–22.11.: 4for4, Footballguys, FantasyPros, NBC, Stoned Lack | Frühere Gesprächsrecherche; einzelne Originalrevisionen hier nicht vollständig archiviert | 4for4 Loveland 13,9/Warren 11,4; Footballguys Waddle 10,5/Barkley 10,9/Monangai 11,6; QB-/WR-/TE-Einordnung | `pre_lock_referenced_unarchived`; frühere Thursday-Zeilen ebenfalls vor diesem Thursday-Lock referenziert, aber nicht als Originalquelle gesichert |

**Quellenunabhängigkeit:** Athlon und DraftSharks sind getrennte Redaktionen/Prognosen, benutzen aber teilweise dieselben NFL-Rohdaten. Footballguys-Zahlen aus dem Gespräch sind ein zusätzlicher, **nicht direkt neu archivierter** Stand. Der kombinierte Befund ist daher Evidenz mit mittlerer, nicht absoluter Sicherheit; ein konsensbasiertes Drittportal wäre keine völlig unabhängige vierte Stimme.

**Offene evidenzrelevante Usage-Felder:** Für den gesamten Grenzpool wurden hier **keine gleichwochen- und quellenharmonisierten Tabellen mit Snaps, Routes, Targets, Carries, Red-Zone/Two-Minute-Einsätzen** neu materialisiert. Einzelne Usage-Werte sind explizite externe/gesprächsbasierte Belege, **keine** vollständige Neuvermessung. Diese Lücke begrenzt die Entscheidungssicherheit. Insbesondere nicht aus Snap Share automatisch Targets oder Catch Floor herleiten.

## 9. Einzufrierende Ex-ante-Testthesen für Week-11-Postmortem

1. **Waddle vor Monangai/Barkley:** Unterstützen die heutigen begründeten PPR-Rankings die tatsächlich verfügbare Opportunity besser als die interne V4-C-Reihung? Gegenprobe anhand Waddles Routes/Targets/Snaps und Monangais Carries/Passing Down im Verhältnis zu Swift, Barkleys gesundheitsbereinigtem Workload. **Nicht** allein die Punkte vergleichen.
2. **FLEX-Portfolio:** Wie viel Downside ergab sich aus Halls geteilter Rolle und Waddles Rückkehr? Waren McMillan/Skattebo tatsächlich der stabilere Opportunity-Anker? Nur ex-ante nachvollziehbare Korrelationen werten.
3. **Warren vs. Loveland:** War die Thursday-Sit-Entscheidung bei damals bekannter Matchup-/Usage-/Ranking-Lage vertretbar? Warrens 3,2 Punkte gehören zum **Outcome** und nicht zur ursprünglichen Rationale.
4. **Availability-Modellfehler:** Weshalb meldete V4-C einen sehr hohen Walker-Wert trotz **OUT**? Separat überprüfen, ob das erwartete Projektionsdesign „conditional on participation“ korrekt angezeigt und in Entscheidungen hinreichend abgefangen wurde.
5. **Schedule-Freshness:** Wurden die echten 19:00- und 22:25-Locks genutzt oder hat die veraltete App-Quelle eine Entscheidung fälschlich möglich/gesperrt dargestellt? **Technischer Reparaturbedarf**, kein Grund, vergangene Entscheidungen umzuschreiben.
6. **Matchup-State / Tim:** War Tim tatsächlich mit 13 gesetzten Startern startklar, wann genau wurden diese gesetzt und welche AutoSubs wurden real wirksam? Der früher vermutete leere QB-Slot darf nicht unbesehen weiter gelten.
7. **Separate Outcome-Firewall:** Historische aktive Starter, benutzte AutoSubs, Fantasy-Punkte, NFL-Usage, PlayerWeekFantasy-Actuals und den offiziell finalisierten Liga-Score getrennt mit den vier Finalitäts-Gates prüfen. Same-Information-Re-Decision und Outcome Regret strikt trennen.

**Abschließendes Urteil (Cutoff Sonntag vor 19:00 MEZ):** **Die in Sleeper gesetzten 13 Starter unverändert lassen.** Waddle gegenüber Monangai/Barkley knapp favorisieren; Walker ist OUT. Kein Waiver/Drop nötig für das bestehende Lineup. Vor dem 19:00-Lock mögliche neue Inactives prüfen, und vor den 22:25-Locks Waddle/Bryant sowie die korrekt verschobenen Giants-Spieler berücksichtigen. **AutoSub-Paarung nicht als ausgeführt behaupten, solange sie nicht belegt ist.**

**Geltende Projektregeln:** `fantasy-management/AGENTS.md`, `_ai/FANTASY_MANAGEMENT_RULES.md`, `_ai/FANTASY_MANAGEMENT_SOURCES.md`, `_ai/ROSTER_ARCHITECTURE.md`, `_ai/MONITORING_AND_WEEKLY_DECISIONS.md`, `_ai/WORKFLOWS.md`; Referenzformat der zuvor ausdrücklich persistierten Week-9-/Week-10-Ex-ante-Akten. Keine Änderungen an Sleeper, Liga-Regeln, Data-Pipeline oder Repository-Dokumentation außerhalb dieses Ex-ante-Analyseartefakts.