# Mighty Giants — Week 8 2026: Ex-ante-Lineup-Entscheidungen

**Saison/Woche:** NFL 2026, Week 8; Mighty Giants (TeamID 1).  
**Entscheidungszeitraum:** 29.10.–01.11.2026; finale Chat-Abwägung am Sonntag, 01.11.2026, um den ersten regulären Sunday-Kickoff herum. Kein einzelner vollständig vor allen Week-8-Spielen eingefrorener Snapshot.  
**Format:** Full PPR; 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K; ohne gesonderten TE-Premium-Bonus.  
**Typ/Status:** Auf ausdrückliche Nutzerfreigabe vom 01.11.2026 gespeicherte zeitgenössische Entscheidungsanalyse. **Kein** versiegelter Decision Record/Decision Set; **kein** Week-8-Postmortem.  
**Outcome-Firewall:** Ex-ante-Begründungen nicht anhand späterer Ergebnisse umdeuten. Tetairoa McMillans bereits bekanntes Donnerstagsergebnis wird als vor dem Sonntag vorhandener Spielstand behandelt, nicht als vor Donnerstag bekannte Prognose.

## 1. Evidenz, Provenienz und technische Grenzen

- **Direkte Nutzerentscheidung im Chat:** Robert hat die zuletzt vorgeschlagene Aufstellung übernommen, Cam Little über den Waiver eingestellt und Jeremiyah Love ausdrücklich als Hall-Ersatz gestartet. Am Ende des Gesprächs hat er die Speicherung des Week-8-Entscheidungsverlaufs freigegeben.
- **Verifizierter späterer Sleeper-/Liga-Readback:** `public/data/League.json`, Blob `6c47c79781d9043463504560a4213e9bfa9b6538`, laut `public/data/Timestamps.json` aktualisiert am `2026-11-01T17:26:23Z`. Der 13er-Starter-Pool enthält **Love statt Hall** sowie **Cam Little statt Fairbairn**; es handelt sich um einen **späteren Ausführungsnachweis**, nicht um einen Beleg dafür, dass alle Einzelentscheidungen bereits zu Beginn der Woche identisch feststanden.
- **Kicker-Transaktionsnachweis:** `public/data/Transactions.json`, Blob `3e52e67332b98691941de96932a5746f177068b1`; abgeschlossener Week-8-Waiver mit Add `11786` (Cam Little) und Drop `3451` (Ka'imi Fairbairn).
- **Operationales Verletzungssignal:** `fantasy-management/generated/operations/managed-roster-overview.json`, Blob `dbce5288892919060401b67713ccd020f8fbd088`, Materialisierung `2026-11-01T17:26:23Z`. Dort blieb Hall als **Questionable** markiert; dieses abgeleitete Signal ist ausdrücklich nicht mit dem im Chat herangezogenen späteren offiziellen Inactive-Bericht gleichzusetzen.
- **Externe Evidenz im damaligen Gespräch:** Injury-/Practice-Berichte, NFL-Inactive-Berichte und aktuelle Week-Rankings/Projektionen (u. a. FantasyPros, NBC/Rotoworld, 4for4, DraftKings) wurden diskutiert. Diese Datei konserviert die **damalige im Chat verwendete Bewertung**, nicht den unveränderlichen Originalinhalt dynamischer Drittseiten. Exakte Primärquellenrevisionen, Links oder Veröffentlichungstimestamps werden nicht nachträglich erfunden.
- **Abgrenzung:** Nicht in diesem Gespräch abschließend unabhängig validiert wurden die finale NFL-Inactive-Liste für jeden später startenden Spieler, alle AutoSub-Paarungen in Sleeper, ein vollständiges Gegnermodell oder ein punktgenauer aktueller Projektionskonsens. Keine fiktive Confidence-Skala oder nachträgliche Bewertung der realisierten Scores.

## 2. Finale gewählte Aufstellung und Bestätigung

Die Tabelle zeigt den **Starter-Pool**, dessen Zugehörigkeit durch den späteren Liga-Readback bestätigt ist. Die sichtbare Anordnung einzelner gleichberechtigter FLEX-Spieler kann in Sleeper abweichen.

| Slot | Spieler | Sleeper-ID | Ex-ante-Entscheidungsgrund |
| --- | --- | --- | --- |
| QB1 | Patrick Mahomes | `4046` | Start trotz nicht idealem Denver-Matchup; gegenüber den verfügbaren QB-Alternativen bevorzugt |
| QB2 | Jayden Daniels | `11566` | Wieder aus der Bye; klar vor der zusätzlichen QB-Reserve |
| RB1 | Kenneth Walker III | `8151` | Kernstarter; Rolle und Opportunity |
| RB2 | Chase Brown | `9224` | Startbarer RB mit Passing-Game-Beitrag und gegenüber den Grenzoptionen bevorzugter Rolle |
| WR1 | Puka Nacua | `9493` | Qualitäts-/Target-Kernstarter |
| WR2 | Tetairoa McMillan | `12526` | Donnerstag bereits gespielt; im Gespräch wurden **11,8 PPR-Punkte** als bekannt behandelt |
| TE1 | Trey McBride | `8130` | Klarer TE-Kernstarter |
| TE2 | Colston Loveland | `12517` | Knapp vor Tyler Warren nach Rolle/Form und Comeback-Risiko |
| FLEX1 | George Pickens | `8137` | Trotz Schulter-/Hamstring-Fragezeichen aufgrund des hohen Week-Werts gehalten |
| FLEX2 | Jeremiyah Love | `13287` | **Bewusste Upside-Wahl nach Halls Inactive-Meldung** vor McConkey/Warren |
| FLEX3 | Saquon Barkley | `4866` | Nach medizinischer Einsatzfreigabe gegenüber zusätzlichem TE bevorzugt |
| FLEX4 | Tre Tucker | `10213` | Jüngste Rolle/Form und relativ attraktive Week-Chance gegenüber verletzungsbehafteten WR-Alternativen |
| K | Cam Little | `11786` | Erfolgreicher Streamer-Add wegen Fairbairns Bye |

**Explizite Nutzerbestätigung:** Robert schrieb sinngemäß, er habe die empfohlene Aufstellung übernommen; später ausdrücklich „ich habe Love aufgestellt“. Dass Love und Little tatsächlich im final beobachteten Starter-Pool stehen, ist zusätzlich unabhängig aus `League.json` nachgewiesen. Es wurde **keine** AutoSub-Konfiguration für diese Woche explizit bestätigt.

## 3. Entscheidungsentwicklung und begründete Korrekturen

1. **Ursprüngliche Week-8-Empfehlung:** Trey McBride und Colston Loveland auf den festen TE-Slots, Tyler Warren nach der gemeldeten Rückkehr zunächst als dritter TE im FLEX. Im Kader war noch Ka'imi Fairbairn (HOU-Bye).
2. **Kicker-Lücke:** Cam Little wurde vor Reichard/Myers als Wochenstreamer bevorzugt. Ein zweiter Kicker hätte wegen des aktiven Rosterlimits einen Skill-Position-Drop erfordert; beschlossen wurde stattdessen Little **für** Fairbairn. Die Transaktion wurde erfolgreich ausgeführt.
3. **Nutzer-Einwand „drei TEs statt RB/WR?“:** Die isolierte Wertung von Warrens Comeback war ein unzureichender positionsübergreifender FLEX-Vergleich. Nach Neubewertung des gesamten FLEX-Grenzpools wurde **Saquon Barkley vor Warren** bevorzugt. Dies ist eine inhaltliche Korrektur des ursprünglichen Boundary-Vergleichs, kein Beweis, dass drei TEs grundsätzlich falsch wären.
4. **Loveland vs. Warren:** Nach direkter Rückfrage wurde Loveland **knapp** als zweiter fester TE bestätigt. Das im Chat besprochene Week-Ranking und der Form-/Usage-Trend gaben Loveland einen leichten Vorteil; die Entscheidung wurde ausdrücklich als knapp und unsicher markiert.
5. **Hall bis Sonntag:** Breece Hall war zunächst als Questionable/bedingter FLEX vorgesehen. Nach der am Sonntag im Chat herangezogenen **offiziellen Inactive-Meldung** wurde Hall gestrichen. Der operative Injury-Readmodel-Status war hier nicht mehr die maßgebliche finale Quelle.
6. **Ersatz für Hall:** Nach Vergleich von Love, McConkey, Warren und weiteren Kandidaten fiel die Wahl auf **Jeremiyah Love**, trotz ausdrücklicher Diskussion seines geteilten Backfields und seiner Rückkehr von einer Verletzung. Robert bestätigte den Start.
7. **Ausführungs-Readback:** Der später aus dem Repo gelesene Starter-Snapshot zeigt die komplette beabsichtigte Aufstellung einschließlich Love und Little. Frühere zwischenzeitliche Snapshots, in denen Hall noch Starter war, gelten dadurch nicht als finale Ausführung.

## 4. Zentrale Grenzentscheidungen

### 4.1 Jeremiyah Love vor Ladd McConkey und Tyler Warren

| Faktor | Love (RB, ARI @ DAL) | McConkey (WR, LAC @ LAR) | Warren (TE, IND @ JAX) |
| --- | --- | --- | --- |
| Pro-Argument | Attraktives Dallas-RB-Matchup, Lauf-/Touchdown-Ceiling | Gesund, WR-Opportunity, weniger Comeback-Risiko | Erwartete Rückkehr in eine relevante Colts-TE-Rolle |
| Kontra | Rückkehr nach Knöchelverletzung; Allgeier/Knight und unklarer Touch-/Snap-Anteil | Bislang enttäuschende Effizienz und nicht ideales Matchup | Zwei verpasste Spiele, mögliche reduzierte Nutzung |
| Im Chat diskutierte Projektion | Ungefähr 10–11 PPR in herangezogenen Modellen | Einzelnes Modell etwa 11,0 vs. Love 10,4 | Modellabhängig etwa 8–11 |
| Entscheidung | **Start wegen Ceiling** | Bewusste Bank, engste Alternative | Bank, kein dritter TE im FLEX |

**Wesentliche Unsicherheit:** In mindestens einem im Gespräch zitierten Prognosemodell lag McConkey **knapp vor Love** (ca. 11,0 vs. 10,4). Die Wahl von Love wurde deshalb **nicht** als Konsens- oder Median-Gewinner ausgegeben, sondern als bewusster Upside-Call. Der Argumentationskern ist ein günstiges Run-Matchup *unter der Annahme ausreichender Touches*; die Rückkehr-/Timeshare-Gegenhypothese bleibt real. Keine nachträglich erfundene präzise Wahrscheinlichkeit oder formelle Confidence-Note.

### 4.2 Colston Loveland vor Tyler Warren

Loveland wurde im Chat wegen des jüngsten Form-/Rollenanstiegs leicht bevorzugt, Warren wegen des Comebacks nach Leistenproblemen etwas vorsichtiger beurteilt. Besprochene Week-Rankings sahen beide teilweise unmittelbar nebeneinander; ein angeführtes 4for4-Modell lag ungefähr gleichauf. **Kein großer erwarteter Punkteabstand**, sondern eine knappe Abwägung bei zwei festen TE-Slots. McBride war dabei nicht auf der Grenze.

### 4.3 Saquon Barkley im FLEX statt drittem TE

Barkleys medizinische Einsatzfreigabe und sein Talent-/Touchdown-Ceiling rechtfertigten trotz vorheriger Hamstring-/Rückenprobleme einen FLEX-Start. Warrens mögliche Comeback-Beschränkung und das Fehlen eines TE-Premium-Bonus schwächten den zuvor vorgeschlagenen dritten TE. Es wurde **nicht** behauptet, Barkley sei ohne Active-but-limited- oder Reinjury-Risiko.

### 4.4 Tre Tucker, George Pickens und die WR-Reserve

Tucker blieb nach dem jüngsten Rollen-/Produktionsanstieg gesetzt. Pickens wurde wegen seines hohen Starterpotenzials trotz fraglicher Schulter/Hamstring im bevorzugten Pool gehalten. **Jaylen Waddle** war wegen Brust-/Einsatzunsicherheit keine bevorzugte FLEX-Wahl; **Ladd McConkey** blieb als plausibler vergleichsweise gesunder Bench-Kandidat; **Brian Thomas Jr.** wurde aufgrund unklarer jüngerer Nutzung zurückgestellt. Die damaligen Erwartungen zu Pickens wurden vor der finalen technischen Ausführung als wahrscheinlich spielend besprochen; eine separate lückenlos archivierte finale Dallas-Inactive-Bestätigung liegt in dieser Entscheidungsakte nicht vor.

### 4.5 Quarterbacks und übrige feste Slots

Mahomes/Daniels bleiben vor Penix und Shough; Shough hatte Week-8-Bye. Walker/Brown und Puka/McMillan besetzen die festen RB-/WR-Slots; McMillan war bereits gelockt. McBride ist der klare erste TE. Bei diesen Spielern wurde kein gleichgewichtiger Bench-Gegenkandidat wie am vierten FLEX identifiziert.

## 5. Waiver- und Rosterpreis

**Tatsächlich ausgeführter Move:** Cam Little (`11786`) hinzugefügt, Ka'imi Fairbairn (`3451`) gedroppt; Week-8-Transaktion `complete` und Starter-Readback bestätigt. Fairbairn hatte HOU-Bye. Ein zusätzlicher Kicker hätte den knappen aktiven Kaderplatz zulasten eines Skill-Spielers beansprucht. Verfügbare Alternativen wie Will Reichard, Jason Myers und Jake Bates unterstrichen, dass die Position in der Sechserliga gut streambar ist. Eine sichere langfristige Überlegenheit Littles gegenüber Fairbairn war **nicht** die These.

**Kein weiterer Skill-Position-Add:** Bei möglichen Alternativen wurde der tatsächliche Drop-Preis gegen vorhandene Starter-/Prospect-Tiefe gewichtet. In der League waren mehrere öffentlich attraktive Namen bereits vergeben; ein marginaler Ein-Wochen-FLEX-/QB-/TE-Gewinn rechtfertigte keinen Verlust eines brauchbaren Dynasty-Assets. Dies ist eine konkrete Week-8-Pass-Entscheidung, keine generelle Waiver-Sperre.

## 6. Timing, Availability und Lock-Grenzen

- **Vor Sonntag:** frühe Vorabentscheidung mit mehreren fraglichen Spielern; zunächst Hall als bedingter Starter, während Love/Warren/McConkey als Ersatzpool verblieben.
- **Sonntag, 01.11., um den Inactive-Check:** finale Hall-Ausfallinformation führte zu Hall → Love. Bei Pickens war der im Chat verfügbare Stand weiterhin „voraussichtlich spielend“; die empfohlene Absicherung bei einem späteren Ausfall war u. a. McConkey.
- **Donnerstag bereits abgeschlossen:** McMillans Score war am Sonntag bekannt; seine Startentscheidung wird nicht aus dem Ergebnis rückwärts begründet.
- **Späteres Spiel / Ersatzflexibilität:** Love und andere verbleibende Spieler haben unterschiedliche Kickoffs. Nicht behauptet wird, dass automatische Sleeper-Substitutes eingerichtet oder eine frühere Ersatzoption nach ihrem Lock noch verfügbar gewesen wären. Die tatsächliche Startaufstellung ist belegt, die AutoSub-Paarung nicht.
- **Technische Verzögerung:** Frühere Repo-Abfragen zeigten Hall noch als Starter, spätere Abfragen den user-bestätigten Wechsel Love. Diese Differenz ist als zeitversetzter Beobachtungsstand und nicht als widersprüchliche Nutzerentscheidung zu behandeln.
- **Kein nachträgliches Re-Ranking:** Nach Spielbeginn bekannte Punkte, Verletzungen während des Spiels und tatsächlich erzielte Scores dürfen die oben dokumentierte Ex-ante-Thesenwahl nicht verändern.

## 7. Entscheidungsfazit und spätere Review-Fragen

**Gewählte Week-8-Variante:** Zwei feste TEs (McBride/Loveland), vier FLEX-Spieler (Pickens/Love/Barkley/Tucker), keine dritte TE-FLEX-Besetzung, Hall wegen Inactive auf der Bank und Cam Little als erfolgreicher Kicker-Streamer.

Für ein **separates** Post-Week-Review sind zu prüfen:

1. Gab es für Love vor seinem tatsächlichen Lock neue Snap-/Usage-/Inactive-Informationen, die das Ceiling-/Timeshare-Verhältnis verändert hätten? War McConkey unter denselben bekannten Bedingungen die bessere Entscheidung?
2. Haben sich Lovelands aktuelle Routen-/Target-Anteile tatsächlich als belastbarer erwiesen als Warrens Comeback-Opportunity?
3. Wurden Pickens' Verfügbarkeit und eventuelle Active-but-limited-Risiken angemessen abgesichert?
4. Wie unterscheiden sich Resultat, Hindsight-Optimallineup und **Same-Information Decision Quality**? Ein höherer Bench-Score allein ist kein Prozessfehler.
5. War der Kicker-Tausch unter Rosterplatz-/Waiver-Betrachtung sinnvoll, unabhängig vom einmaligen Kicker-Punkteergebnis?
6. War unsere ursprüngliche dritte-TE-Empfehlung ein vermeidbarer **Boundary-Workflow-Fehler**, und welche minimale Checkliste hätte die frühere Gegenprobe erzwungen?

Dieses Dokument bleibt als datierte Entscheidungsbasis erhalten und wird **nicht** mit einem Week-8-Postmortem oder einem späteren versiegelten Decision Record überschrieben.

## 8. Kanonische Verweise

- `fantasy-management/analyses/2026/weekly/2026-week-07-lineup-ex-ante-decisions.md` — vorheriges Dokumentationsmuster.
- `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md` — Start/Sit-/Boundary-/Availability-/AutoSub-Guardrails.
- `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md` und `FANTASY_MANAGEMENT_SOURCES.md` — Quellen- und Liga-Kontext.
- `fantasy-management/_ai/ROSTER_ARCHITECTURE.md` — Drop-Opportunity-Cost und Kicker-Roster-Flexibilität.
- `public/data/League.json`, `public/data/Transactions.json`, `fantasy-management/generated/operations/managed-roster-overview.json` — die im Abschnitt 1 genannten Beobachtungsstände, kein eingefrorenes globales Source-Bundle.
- GitHub Issues **#206** (Weekly-Workflow), **#208** (separate Post-Week-Reviews) und **#629** (späterer allgemeiner Decision-Record-Contract).
