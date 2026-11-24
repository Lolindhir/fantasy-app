# Mighty Giants — NFL Week 11 (2026): Roster + Lineup Postmortem

**Review und ausdrückliche Persistierungsfreigabe:** 24.11.2026, erneuter Abendabgleich nach Monday Night (MEZ).  
**Team:** Mighty Giants, TeamID 1, CanonicalLeagueRosterID clr-a8e576139994570d82e9ea2ed3f42b1b. Gegner: Tim / Team TimpaBay, TeamID 6.  
**Ergebnis:** 190,52 : 184,78 (+5,74); 6–5, Tabellenplatz 2.  
**Format:** 6 Teams, Full PPR, 2 QB / 2 RB / 2 WR / 2 TE / 4 RB-WR-TE-FLEX / 1 K.  
**Status:** `league_scoring_verified__derived_pending`. Abgeschlossene retrospektive Analyse, kein versiegelter Decision Record, keine Änderung der [zeitgenössischen Ex-ante-Akte](2026-week-11-lineup-ex-ante-decisions.md), keine Transaktionen oder Regel-/Modelländerungen.

## 1. Evidenz und Finalitätsbrücke

| Ebene | Periodenstabile Quelle (Blob-SHA) | Status |
|---|---|---|
| NFL-Finality | `data-source/nfl/game-finality/2026.json` — 3cb00d0aaf28bf7502d77d76b134dece4438362f | REG W11: 13/13 final, WeekFinal=true |
| Liga-Matchup | `data-source/leagues/nfl-reise/seasons/2026/matchups/week-11.json` — fbaecebc52bd2e95d25389dc638b42a804b65559 | 13/13 gewertete Starter, Summe exakt 190,52; 37 kontrollierte Spieler; Tim 184,78 |
| Best Ball | `data-derived/team-week-performance/nfl-reise/2026/11.json` — 7b83822113cf225b63fcc9b10fdc0f3182dd8f67 | finaler Teamvergleich, 222,42; 85,6578 % |
| PlayerWeekFantasy | `data-derived/player-week-fantasy/nfl-reise/2026/11.json` — 3bc342f9c415e46231f8dbf0f7532993531066ac | ActualScoringEvidenceFinalized=false; 685 unavailable, TargetWeeklyRosterFinalized=false; kein finaler Cross-Source-Actual-Abgleich möglich |
| Snaps | `data-source/nfl/snap-counts/2026/11.json` — feadcef6cabe756956d18eed595fa2017d9b4dfa | Finalized=false, 12/13 Spiele; CIN@WAS fehlt |
| Wochenbesitz / Transaktionen | `data-source/leagues/nfl-reise/seasons/2026/transactions/week-11.json` — 5836da328e969efc684c8518a4a197313dc98704 | zwei erfolgreiche eigene Waiver, ein gescheiterter Claim ohne Drop |
| Rosterbereiche / Follow-ups | `fantasy-management/generated/operations/managed-roster-overview.json` — 664bdb029985d3c3ec1ba20329beb9e8f445781a (24.11., 04:46 UTC) | heutige Buckets mit Wochenpool und Ex-ante abgeglichen; Klassifikation vom 14.11., nicht historischer minutengenauer Lock-Snapshot |
| Ex-ante | [Week 11](2026-week-11-lineup-ex-ante-decisions.md) — c36c3d02cda791de09ea937ac49ec59dfd2f1e81 | Sonntag 22.11. vor 19:00 MEZ; Thursday bereits gelockt; nicht umschreiben |

Abendlicher erneuter Abruf zeigt unveränderte Blobs bei den vier Haupt-Gates. Offizielle Liga-Punkte haben Vorrang; kein fehlender Derived-Wert wird mit einer Projektion ersetzt. Keine Behauptung vollständiger Route-/Target-/Snap-Finality. Die externe Monday-Night-Evidenz schließt wichtige fachliche Lücken, nicht die internen technischen Gates. AutoSub-Paarungen/Prioritäten sind nicht unabhängig verifiziert; 13/13 geplante Starter sind tatsächlich gewertet.

### Externe Quellen (nach dem Lock bzw. nach dem Spiel, sofern nicht anders markiert)

- [RotoWire, Week 11 Box Score Breakdown, 23.11.](https://www.rotowire.com/football/article/nfl-box-score-breakdown-week-11-recap-usage-stats-147809): Snap-/Route-/Opportunity-Kontext, insbesondere Bears-RB-Verteilung und Broncos-WR-Routes. Provider-Snap-Zähler können von nflverse abweichen. Einzelne Suchauszüge waren abrufbar, vollständiger Seitenabruf nicht durchgehend möglich.
- [PFF, Sunday Week 11 Takeaways, 22.11.](https://www.pff.com/news/nfl-week-11-recap-immediate-fantasy-football-takeaways-from-sundays-games), [PlayerProfiler Usage Report, 23.11.](https://www.playerprofiler.com/article/the-fantasy-football-usage-report-week-11-2026/): ergänzende Rollenanalysen, kein Ersatz für historische Pregame-Rankings.
- [PFR CIN@WAS](https://www.pro-football-reference.com/boxscores/202611230was.htm), [Reuters, 24.11.](https://www.reuters.com/sports/nfl/commanders-rally-past-bengals-last-minute-drive-produces-winning-fg--flm-2026-11-24/): Daniels und Williams; Washington 22:20.
- [PFR JAX@NYG](https://www.pro-football-reference.com/boxscores/202611220nyg.htm), [Saints offizieller Boxscore NO@CHI](https://www.neworleanssaints.com/game-day/2026/reg-week11/bears-vs-saints/box-score), [PFR NYJ@LAC](https://www.pro-football-reference.com/boxscores/202611220sdg.htm), [Chargers Boxscore](https://www.chargers.com/game-day/2026/reg-week11/jets-at-chargers/box-score), [PIT@PHI FantasyData](https://fantasydata.com/nfl/boxscore/19616-pittsburgh-steelers-vs-philadelphia-eagles-week-11-2026): tatsächliche Ball-Opportunity/Produktion.
- [DraftSharks Barkley, 23.11.](https://www.draftsharks.com/fantasy-football-news/84406/good-news-in-saquon-barkleys-week-11-and-maybe-some-bad), [NBC Barkley, 22.11.](https://www.nbcsports.com/fantasy/football/player-news/2026-11-22/saquon-barkley-scores-td-in-week-11-slog): Rückkehr des Carry-Volumens, neue Armverletzung, geringe Passing-Game-Rolle.
- [FantasyPros McConkey Active, 22.11., 14:49 EST = 20:49 MEZ](https://www.fantasypros.com/nfl/news/621873/ladd-mcconkey-back-officially-active-week-11.php), [NBC erwartete Teilnahme, 22.11.](https://www.nbcsports.com/fantasy/football/player-news/2026-11-22/ladd-mcconkey-back-expected-to-play-against-nyj): historisch vor individuellem Lock publiziert, **erst in diesem Review erneut geprüft**, keine Behauptung zeitgenössischen Captures.
- [Rams Injury Update, 20.11.](https://www.therams.com/news/injury-updates-puka-nacua-out-for-couple-months-as-he-will-undergo-mcl-surgery-kobie-turner-expected-to-return-to-practice-latest-on-terrance-ferguson-davante-adams-and-justin-dedich), [Reuters Nacua, 20.11.](https://www.reuters.com/sports/rams-wr-puka-nacua-has-mcl-surgery-likely-out-season--flm-2026-11-20/), [FFToday Usage Notes, 23.11.](https://www.fftoday.com/articles/krueger/26-usage-notes-wk11.html): Verletzungen, kein pauschaler Rückkehrtermin.
- [NFL Pro W11 Insights](https://pro.nfl.com/games/game/8522d92f-e9e3-11f0-9442-5911216651e2): Williams-/McConkey-Ausreißer; [NFL Pro BAL@CAR](https://pro.nfl.com/games/game/aab58261-4feb-11f1-abca-2c54536568a9): McMillan-Performance.

Nicht separat re-verifizierte Detailwerte aus der früheren Chatantwort werden hier nicht als gesicherte Fakten übernommen. Externe Pregame-Zeilen stammen primär aus der unveränderten Ex-ante-Akte; heutige dynamische Rankings sind nicht automatisch deren damalige Revision.

## 2. Ergebnis und Liga

| Manager | Ist W11 | Best Ball | Effizienz | Bilanz nach W11 | PF |
|---|---:|---:|---:|---|---:|
| Flo | 212,16 | 232,66 | 91,19 % | 10–1 | 2368,00 |
| Dennis | 190,62 | 202,62 | 94,08 % | 3–8 | 1766,04 |
| Robert | 190,52 | 222,42 | 85,66 % | 6–5 | 2144,22 |
| Tim | 184,78 | 210,98 | 87,58 % | 5–6 | 2109,32 |
| Jan | 152,64 | 202,06 | 75,54 % | 4–7 | 2132,76 |
| Marcel | 131,52 | 159,74 | 82,33 % | 5–6 | 1982,42 |

Dritthöchster tatsächlicher Score und zweithöchstes Kaderpotenzial. Tabellenplatz 2 vor Tim und Marcel; zwei verbleibende Regular-Season-Wochen, Playoffs ab W14. W12 gegen Dennis; +34,90 PF gegenüber Tim. W10/W11 221,08/190,52, Mittel 205,80; beide direkte Duelle gegen Jan bzw. Tim gewonnen. Kein garantierter Playoff-Einzug oder kalibrierter Titelwahrscheinlichkeitswert.

## 3. Vollständiger historischer Wochenpool

Snaps = interner nflverse Offense-Anteil (nicht final), — = kein entsprechender Beleg, nicht automatisch null. S = tatsächlich gewerteter Starter, B = aktive Bank, R = Reserve, T = Taxi. Rolle/Security sind die am 14.11. gesetzten Readmodel-Einstufungen (sofern vorhanden); die aktuelle Interpretation ersetzt diese nicht. Externe konkrete Opportunities ergänzen die Tabelle, ohne fehlende Routes zu schätzen.

| Spieler | Pos/Area | Ist | Snap % | Role / Security | Interpretation |
|---|---|---:|---:|---|---|
| Patrick Mahomes | QB/S | 24,96 | 85 | core_starter/locked | Stabiler QB-Anker; hohe Produktion |
| Jayden Daniels | QB/S | 17,06 | — | core_starter/locked | 23/35, 289 Pass-Yards, 6/55 Rush, kein Pass-TD; gute Basis trotz begrenzter TD-Ausbeute |
| Tyler Shough | QB/B | 15,28 | 100 | starter_rotation/strong_hold | Tatsächliche QB-Utility, Coverage |
| Jaxson Dart | QB/R | 0 | — | backup/strong_hold | IR, kein aktiver Backup |
| Chase Brown | RB/S | 8,60 | — | starter_rotation/strong_hold | Carry-/Receiving-Verteilung im Monday-Spiel prüfen |
| D'Andre Swift | RB/S | 11,90 | 46 | starter_rotation/strong_hold | 13/51 Rush; Receiving-TD, Fumble; geteiltes Backfield |
| Cam Skattebo | RB/S | 5,80 | 84 | starter_rotation/strong_hold | 14/34 Rush, 7 Targets, 3/14 Receiving, verlorener Fumble; schwache Effizienz statt belegtem Rollenverlust |
| Breece Hall | RB/S | 19,00 | 63 | core_starter/locked | 20/86 Rush, 3 Targets/3 Catches/14 Yards/TD; weiterhin erhebliche Opportunity |
| Saquon Barkley | RB/B | 13,50 | 64 | starter_rotation/strong_hold | 17/75/TD Rush, 0 Targets, 10 Routes laut DraftSharks; Armverletzung |
| Kyle Monangai | RB/B | 1,80 | 38 | backup/hold | 8/18 Rush; Rückkehr hinter Swift; eigenständiger Rotationswert plus Injury-Contingency |
| Seth McGowan | RB/B | 1,80 | 18 | backup/hold | 3 Carries laut RotoWire, 5 Routes dort; Hamstring, geringe Opportunity; hinter Taylor |
| Kenneth Walker III | RB/B | 0 | — | core_starter/locked | Ex ante offiziell Out, Leiste |
| Jeremiyah Love | RB/B | 0 | — | core_starter/locked | IR; kein aktueller Starter |
| Dylan Sampson | RB/B | 0 | — | backup/hold | CLE-Bye |
| Jonathon Brooks | RB/R | 0 | — | prospect/conditional | Reserve/IR |
| George Pickens | WR/S | 23,80 | 75 | starter_rotation/strong_hold | Zweite starke Woche; weiterhin hoch in Starterrotation |
| Malik Nabers | WR/S | 18,50 | 76 | core_starter/locked | 12 Targets, 7/55/TD; starke Opportunity |
| Tetairoa McMillan | WR/S | 19,10 | 83 | starter_rotation/strong_hold | Erholung nach W10, hohe Feldbeteiligung |
| Jaylen Waddle | WR/S | 9,10 | 53 | starter_rotation/hold | 28 Routes, 6 Targets, 3/61; 19 % Target Share, RotoWire |
| Ladd McConkey | WR/B | 20,70 | 78 | starter_rotation/strong_hold | 8 Targets, 5/37/2 TD; Gesundheit/Opportunity besser, TD-Ausreißer |
| Pat Bryant | WR/B | 6,20 | 55 | unclassified | 20 Routes, 4 Targets, 3/32, 13 % Target Share; Waddle-Coverage/Prospect prüfen |
| Adonai Mitchell | WR/B | 5,00 | 62 | unclassified | 3 Targets, 2/30; bislang begrenzter Floor |
| Germie Bernard | WR/B | 10,00 | 94 | prospect/conditional | 10 Targets, 6/40; W10 nur 3 Targets und 0 Catches |
| Brian Thomas Jr. | WR/B | 8,80 | 51 | prospect/hold | 3 Targets, 1/18/TD; Einsatz steigt, Targets noch gering |
| Travis Hunter | WR/B | 2,20 | 8 | prospect/hold | 1 Catch und 1 Carry; offensive Opportunity strukturell sehr klein |
| Antonio Williams | WR/T | 21,20 | — | prospect/hold | 11 Targets, 9/122, kein TD; stärkstes neues Prospect-Signal |
| Chris Bell | WR/T | 1,80 | 63 | prospect/hold | Brustverletzung laut FFToday; kein Aktivierungsdruck |
| Marvin Harrison Jr. | WR/B | 0 | — | starter_rotation/strong_hold | Out, keine W11-Produktion |
| Puka Nacua | WR/B | 0 | — | core_starter/locked | NFL-IR; MCL-OP, für Fantasy-Playoffs nicht einplanen |
| Davante Adams | WR/R | 0 | — | starter_rotation/hold | Reserve/IR, Rückkehr offen |
| Alec Pierce | WR/R | 0 | — | backup/hold | Reserve/IR |
| De'Zhaun Stribling | WR/R | 0 | — | prospect/strong_hold | Reserve/IR |
| Trey McBride | TE/S | 14,80 | 80 | core_starter/locked | Hohe Rolle, QB-Kontext beachten |
| Colston Loveland | TE/S | 11,90 | 93 | starter_rotation/strong_hold | 3/29/TD; hohe Beteiligung |
| Tyler Warren | TE/B | 3,20 | 76 | starter_rotation/strong_hold | schwache Produktion zweite Woche, Opportunity prüfen |
| Harold Fannin Jr. | TE/B | 0 | — | starter_rotation/strong_hold | CLE-Bye |
| Ka'imi Fairbairn | K/S | 6,00 | — | specialist/churn | kein automatischer Wechsel; Kicker-Slot kein allgemeiner Churn |

### Positionsübergreifende Rollenbewertung

**QB:** Mahomes/Daniels bleiben bevorzugtes Duo; Shough sichert die zwei Pflichtslots ab, Dart ist nicht unmittelbar verfügbar. Daniels' 344 kombinierte Yards und fehlende Passing-TDs sprechen gegen eine reine Punkteabwertung. Keine überzählige gesunde QB-Coverage.

**RB:** Hall hat trotz Konkurrenz durch Allen ein substantielles Touchprofil; Swift führte laut RotoWire während der ersten sieben Drives bei RB-Opportunity (14 von 21). Monangais geringerer Einsatz bestätigt das Rückkehrrisiko, nicht den Verlust jeglichen eigenständigen Werts. Ein Doppelstart braucht eine eigene PPR-/Workload-Begründung. Barkleys 17 Carries sind positiv nach Hamstring-Problemen, aber 0 Targets und die neue Armverletzung begrenzen Floor und Verfügbarkeit. Skattebos 17 Touches, 7 Targets und 84 % Snaps sprechen für einen vertretbaren Start trotz schlechter Effizienz und Fumble. Brown als PPR-Starter weiter prüfen, speziell Carry-Anteil/Perine. McGowan bleibt ein Contingency-Kandidat, kein gesicherter eigenständiger Starter; W10 12 Carries/77 Yards/TD versus W11 begrenzte Usage und Injury. Sampson-Bye und IR/Out nicht als Leistungsverlust interpretieren.

**WR:** Pickens nach 43,50 W10 erneut 23,80; Nabers 12 Targets, McMillan wieder 19,10. McConkeys 8 Targets sind deutlich aussagekräftiger als seine zwei TDs allein; vor W12 ernsthaft in FLEX-Vergleich aufnehmen. Waddle vs Bryant: nflverse 53/55 % Snaps, RotoWire 28/20 Routes und 6/4 Targets. Unterschiedliche Snap-Anteile/Provider-Nenner transparent halten. Waddle ist als Receiver trotz leicht weniger nflverse Snaps die bessere aktuelle Opportunity-Option. Bernard mit 10 statt 3 Targets bei 94 % Snaps: positiv, aber Konkurrenz/Injury-bedingt frei gewordene Opportunity prüfen, nicht als automatisch dauerhaft gewonnene Rolle werten. Thomas' Snap-Trend W9 34 %, W10 48 %, W11 51 % (frühere Reviews) ist positiv, doch nur drei Targets und TD-getriebene Punkte; nicht vorschnell abschreiben. Hunter mit sechs Offense-Snaps und zwei offensiven Ballkontakten; NFL-Defensivwert ist nicht Fantasy-WR-Wert. Trade-Liquidität prüfen, kein unbegründeter Cut. Mitchell/Bryant erst nach sauberer Role-/Security-Klassifikation als mögliche Boundary vergleichen.

**Taxi:** Antonio Williams 21,20 ohne TD, 11 Targets / 9 Catches / 122 Yards; W10 2/42/TD (12,20 Punkte) und bereits hohe Snap-Beteiligung laut W10-Review. Die beiden langen Receptions im entscheidenden Drive belegen konkrete Opportunity, keine Garantie für 11 Targets pro Woche. Jetzt ernsthafter Aktivierungskandidat; nächster Schritt: Konkurrenz, Route-/Target-Trend, Week-12-Utility und Kosten des erforderlichen Drops prüfen. Promotion ist irreversibel hinsichtlich Rückkehr auf Taxi nach Lock; aktiver Kader voll, daher kein kostenloser Swap. Kombination mit Daniels erzeugt gemeinsame Offense-Abhängigkeit, nicht automatisch höheren erwarteten Wert. Bell nach Brustverletzung beobachten.

**TE:** McBride klarer Core; Lovelands 93 % Snaps stärken seine Rolle, während Warren zweiten schwachen Score in Folge liefert. Fannin hatte Bye und darf nicht abgewertet werden. Vier TEs sind sinnvolle Coverage für zwei Pflichtslots.

**K:** Fairbairn sechs Punkte, kein aus dem Score allein abgeleiteter Jobverlust oder Streamer-Vorrang; nächster Vergleich gegen tatsächliche FA-Kicker inklusive Opportunitätskosten. Vollständige Kicker-Attempt-Evidenz hier nicht erneut verifiziert.

## 4. Best Ball, Outcome Regret und echte Alternativen

| Vergleich | Punkte | Effizienz | Gap |
|---|---:|---:|---:|
| Tatsächlich | 190,52 | — | — |
| Active-only Oracle | 211,22 | 90,20 % | 20,70 |
| Voller kontrollierter Pool (inkl. Taxi/Reserve) | 222,42 | 85,66 % | 31,90 |

Gesamtoracle: Brown/Skattebo/Waddle raus; Barkley/McConkey/Williams rein, Pflichtslots durch Umsortierung erfüllt. Active-only: Bernard (10,00) statt Williams (21,20), also 11,20 weniger als Gesamtoracle. Beide QBs, beide TEs und der Kicker bleiben optimal. Die 31,90 sind keine bewiesene Management-Schuld. Active-only nutzt den abgeglichenen Wochen-/Rosterbucket-Pool, nicht einen bewiesenen atomaren Eligibility-Snapshot; einzelne Wechsel waren nur in bestimmten Lock-Epochen legal.

Direkte ex-post Swaps: Waddle→McConkey +11,60; Skattebo→McConkey +14,90; Brown→Barkley +4,90 (vor Barkleys frühem Lock); Waddle→Barkley +4,40 (vor 19:00). Williams statt Waddle +12,10 setzt echte vorherige Promotion/Slotfreigabe voraus. Loveland statt Warren brachte +8,70; Warren hätte bei sonst unverändertem Lineup zum Verlust (181,82:184,78) geführt. Das ist ein kausaler Score-Gegenvergleich, nicht Beweis, dass die Quelle immer besser ist.

## 5. Ex-ante Review und Decision-Opportunity-Matrix

Die archivierte Sonntag-Akte dokumentiert 13/13 Starter, die tatsächlich so gewertet wurden. Sie enthält keine verifizierten konkreten AutoSub-Paarungen. Die spätere Ergebnisinformation darf die Thursday-Rationale nicht ersetzen. W11-Transaktionen: zwei abgeschlossene Waiver (Sleeper IDs 11625 für 5947 und 12492 für 11559), verarbeitet 19.11. vor Thursday-Lock; fehlgeschlagener separater 11625-Claim ohne Drop erzeugt keinen Besitz. Die damalige Sonntags-Akte enthält Mitchell und Bryant bereits. Für frühere Dropped-Spieler keine nachträgliche Startoption behaupten.

| Zeitpunkt (MEZ) | Verfügbare Entscheidung / Lock | Same-information Review |
|---|---|---|
| 20.11. 02:15 | IND@HOU: Fairbairn Start, Warren Sit; McGowan/Harrison/Pierce keine spätere freie Alternative | Loveland vor Warren durch externe damalige Matchup-/TE-Einschätzung vertretbar, erneut wählen; keine nachträgliche Kicker-Waiver-Zeitreise |
| 22.11. vor 19:00 | Mahomes, Swift, Pickens, Loveland, McBride, McMillan; Barkley, Monangai, Bernard sind ab 19:00 gelockt | Swift vor Monangai, Mahomes/Daniels vor Shough gut; Waddle/Barkley knapp und externe Divergenz; kein klarer Decision Regret |
| 22.11. 20:49 | FantasyPros publiziert McConkey offiziell Active; 22:05 Jets@Chargers-Lock | Neuer relevanter Recheck-Trigger. Waddle/Skattebo/Nabers noch offen; tatsächliches Recheck-Handeln nicht belegt. Activation ist nicht gleich volle Belastbarkeit. |
| 22.11. 22:05 | Hall, McConkey, Mitchell gelockt | Hall behalten; McConkey hätte zuvor an offener FLEX-Grenze geprüft werden können |
| 22.11. 22:25 | JAX@NYG und LV@DEN gelockt, Waddle/Bryant, Skattebo/Nabers | Späte Ersatzpfade nur bis hier; Waddle aktiv, kein ergebniswirksamer AutoSub; Paarung unbestätigt |
| 24.11. 02:15 | CIN@WAS: Brown/Daniels, Williams Taxi | Brown bleibt plausibler PPR-Start; Williams nur über frühere legale Aktivierung samt Kosten, nicht rückwirkend |

Offizielle NFL [Schedule-Änderung](https://www.nfl.com/news/week-11-schedule-change) vom 09.11.: JAX@NYG später, PIT@PHI früher; Ex-ante erkannte die veraltete App-Zeit. Diese Review legt die offiziellen Locks zugrunde; keine Behauptung, welcher App-/Sleeper-Lock konkret beim Nutzer angezeigt wurde. Tim hatte 13 belegte Slots; der frühere vermeintlich leere QB-Slot war bereits im Ex-ante korrigiert. Konkrete AutoSub-Paarungen auf beiden Seiten unbekannt.

### Materielle Grenzfälle

| Spieler | Archiviertes Athlon PPR FLEX | DraftSharks PPR FLEX | V4-C | Ist |
|---|---:|---:|---:|---:|
| Waddle | 46 | 45 | 8,67 | 9,10 |
| Hall | 47 | — | 13,12 | 19,00 |
| Monangai | 50 | — | 12,98 | 1,80 |
| Barkley | 64 | 48 | 8,26 | 13,50 |
| Mitchell | 86 | — | 9,04 | 5,00 |

Athlon/DraftSharks: konkrete Zeilen in Ex-ante vor Sonntag-Lock dokumentiert, siehe dortige URL/Quellenzeitangaben. Footballguys 10,5/10,9/11,6 für Waddle/Barkley/Monangai und 4for4 Loveland 13,9/Warren 11,4 sind **pre_lock_referenced_unarchived**, keine revisionssichere Originalerhebung. Quellen sind redaktionell getrennt, nicht statistisch unabhängig. Die externe Evidenz war uneinheitlich. Waddle statt Monangai war gut begründet wegen Rückkehr-Workload; Waddle statt Barkley bleibt knapp vertretbar, selbst wenn Barkley 4,40 mehr erzielte. Barkleys neue Armverletzung ist späteres Wissen.

- **Loveland/Warren:** V4-C 9,60 vs 10,76 favorisierte Warren; externe damalige Einschätzung stützte Loveland, beide waren zeitlich vor Thursday zu vergleichen. Same-information erneut Loveland, mittlere Confidence wegen unarchivierter Originalrevision; +8,70 Outcome.
- **Skattebo/Hall/McMillan:** vorab plausible Opportunity-Anker. Skattebo 84 % Snaps und 7 Targets, aber geringe Effizienz/Fumble; Hall 23 Touches, McMillan hohe Feldbeteiligung. Kein automatischer Decision Regret wegen Einzeloutcome.
- **McConkey:** Sunday-Cutoff Questionable, später bestätigte Teilnahme vor 22:05. Der explizite Recheck von nun aktiven Bench-Spielern an noch offenen FLEX-Slots ist der stärkste Prozessverbesserungspunkt. Keine beweisbare falsche ursprüngliche Wahl oder unterlassene Aktion ohne konkreten späteren Entscheidungssnapshot. Beide TDs nicht rückwirkend als bekannt behandeln.
- **Williams:** Taxi-Hold war vertretbar; ein vorab nicht bewiesener 21,20-Ausreißer legitimiert keinen rückwirkenden Cut. Neue Rollen-Evidenz, kein bewiesener Decision Regret.
- **Portfoliokontext:** Vermeidung von Swift+Monangai-Konzentration plausibel; Hall-Split und Waddle-Rückkehr als bewusstes Risiko. Nach Thursday 6,0:20,3 bei ungleicher Zahl gelockter Starter kein Zwang zur maximierten Varianz. Ex-ante Modell 186,8 vs 180,0/57 % war sekundäres Szenario, keine kalibrierte Siegchance.

## 6. Modell nur als Diagnose

| Starter | Archivierter V4-C | Offizielles Ist | Ist minus Prognose |
|---|---:|---:|---:|
| Mahomes | 20,14 | 24,96 | +4,82 |
| Daniels | 19,78 | 17,06 | -2,72 |
| Brown | 14,86 | 8,60 | -6,26 |
| Swift | 17,08 | 11,90 | -5,18 |
| Pickens | 15,83 | 23,80 | +7,97 |
| Nabers | 15,51 | 18,50 | +2,99 |
| Loveland | 9,60 | 11,90 | +2,30 |
| McBride | 17,35 | 14,80 | -2,55 |
| Skattebo | 14,79 | 5,80 | -8,99 |
| McMillan | 14,08 | 19,10 | +5,02 |
| Hall | 13,12 | 19,00 | +5,88 |
| Waddle | 8,67 | 9,10 | +0,43 |
| Fairbairn | 11,08 | 6,00 | -5,08 |
| Summe | 191,89 | 190,52 | -1,37 |

Die geringe Nettoabweichung ist Kompensation großer individueller Fehler, nicht Modellvalidierung. Fairbairn-Vorhersage stammt aus vor seinem Spiel ausgewiesenem Wert, der Score war Sonntag bereits bekannt. Monangai 12,98 vs 1,80 illustriert Workload-Ungewissheit. Walker 23,64 trotz bestätigtem Out illustriert die Teilnahme-Konditionierung (nicht erwartete tatsächlich erzielte Punkte). Die richtige Verwendung des Modells verlangt vorgelagertes Availability-Gate. Kein Modell-Fit, kein finaler Benchmark vor Derived-Reconciliation; Forschung bleibt separat.

## 7. Kaderarchitektur, Playoff-Follow-ups

30/30 aktiv, 5/5 Reserve, 2/2 Taxi (Williams/Bell; locked). Drei aktive QBs (Floor 3, bevorzugt 4), vier TEs (Floor 3, bevorzugt 4). Zehn RB/WR/TE-Startslots. Readmodel meldet 18 startable skill players, Margin 8, enthält aber derzeit auch verletzte Core-Spieler (Nacua, Walker, Love, Harrison); nicht mit gesunder W12-Coverage gleichsetzen. 37 kontrolliert laut Wochenpool; keine zusätzliche kontrollierte Draft-Kapazität belegt, keine laufenden Draft-Picks in dieser Wochenanalyse angenommen. Zwei allgemeine Churn-Slots Ziel, aktuell **0**, zwei aktive Spieler unklassifiziert (Bryant/Mitchell), decision_readiness=review_required. Boundary Hunter (20), Bernard (40), Thomas (50) gemäß gespeicherter Klassifikation; nicht automatisch Cut-Reihenfolge oder echte Churn-Slots. Fairbairn ist Spezialslot.

W12-Prioritäten:
1. Williams-Aktivierung mit voller Retention-/Cut-Kostenrechnung prüfen; besonders Bryant/Mitchell erst klassifizieren, Hunter-Rollenrisiko und Thomas/Bernard Opportunity neu bewerten. Keine automatische Promotion.
2. McConkey nach Rückkehr aktiv in Starter-Boundary einbeziehen; Barkley Arm/Workload, Walker Leiste, Harrison Availability, Bell/McGowan Injury vor Waiver prüfen.
3. Brown Carry-/Receiving-Split und Skattebo Effizienz vs Opportunity, Swift/Monangai Backfield neu evaluieren.
4. Warren vs Loveland/Fannin mit aktuellen externen TE-Rankings neu vergleichen; McBride Core.
5. Nacua aufgrund MCL-OP nicht für Playoff-Lineup einplanen; Adams-Rückkehr nicht als sicher voraussetzen.
6. Kicker nur bei materiellem tatsächlich verfügbarem Upgrade streamen. Kein blindes Droppen eines Dynasty-Assets.
7. Salary-/Trade-Liquidität und reale FA-Availability in nächster separater Waiver-/Roster-Entscheidung prüfen. Hier keine konkreten Adds/Drops oder Marktpreise behauptet; kein neuer Trade-Decision-Record.

**Prozess-/Quellenvorschläge (nicht umgesetzt):** Active-only und Full-controlled Best Ball parallel zeigen; bei nachträglich bestätigtem Active eines relevanten Bankspielers erneut die noch offene Starter-Boundary prüfen (bestehenden Reversal-/Recheck-Standard schärfen); RotoWire/NFL Pro ergänzend für Route-/Target-/Touch-Kontext verwenden; Taxi-Aktivierungsprüfung vor Playoffs. Die vierteilige Finalitätsbrücke und fehlende Monday-Usage bei nächstem neuen Reviewstand prüfen; keine stillen Änderungen am archivierten Ex-ante oder an diesem Stand.

**Fazit:** Gute, nicht perfekte Management-Woche. Der Sieg gegen Tim ist real und die Loveland-Entscheidung war wichtig. Der stärkste neue Dynasty-Hinweis ist Antonio Williams; McConkey und Barkley erhöhen bei Gesundheit die FLEX-Tiefe. Hunter und Thomas bleiben offene Rollen-/Retention-Fragen. McConkey ist ein Recheck-Lernfall, nicht automatisch ein bewiesener Fehler. Zwei Wochen bis Playoffs: kurzfristige Starterqualität erhöhen, langfristige Assets nicht für unbelegte marginale Upgrades opfern.
