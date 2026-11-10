# Mighty Giants – Roster Role & Security Recheck (2026-11-10)

## Arbeitsstand und Entscheidung

- **Bezug:** TeamID 1, Saison 2026, Liga nach abgeschlossenem Week 9 (CurrentWeek 10), Mighty Giants 4–5 / Tabellenrang 5.
- **Faktensnapshot:** `public/data/League.json` und `fantasy-management/generated/operations/managed-roster-overview.json` (Operations-Readmodel vom 2026-11-08); hieraus 37 gehaltene Spieler, 30/30 aktiv, 5/5 Reserve, 2/2 locked Taxi.
- **Entscheidungsstand:** agentischer datierter Role/Security-Vorschlag auf Basis von aktueller Rolle/Usage, Verletzungen, relativen Dynasty-Marktständen (FantasyPros/FantasyCalc im Readmodel), realen Liga-Starteranforderungen und Roster-Opportunity-Cost. Keine Transaktion und kein User-Override.
- **Vorheriger Seed:** `2026-09-19`, 7 aktuelle Spieler ohne Klassifikation, mehrere nicht mehr gehaltene Spieler im Seed.
- **Format:** sechs Teams, 2 QB/2 RB/2 WR/2 TE/4 FLEX/1 K/17 BN (30 aktiv). Fünf Reserve-Slots und zwei locked Taxi-Slots sind keine generellen Churn-Plätze.
- **Security-Hinweis:** `locked` schützt Dynasty-Asset-Wert, **nicht** die aktuelle Einsatzfähigkeit; Injury/IR-Availability ist eine separate Dimension.
- **Bewertungsgrenze:** Keine behauptete Verfügbarkeit eines konkreten Free Agents und kein verbindlicher Cut ohne aktuellen positiven Availability-/Opportunity-Cost-Check.

## Neue vollständige Klassifikation

| Pos | Spieler | Bereich | Roster Role | Roster Security | Boundary | Vorher | Begründung |
|---|---|---|---|---|---:|---|---|
| K | Ka'imi Fairbairn | active | `specialist` | `churn` | – | unclassified | Verlässlicher aktueller Kicker; Spezialplatz, kein allgemeiner Churn-Slot. |
| QB | Jaxson Dart | reserve | `backup` | `strong_hold` | – | backup/strong_hold | Langfristiges 2QB-Asset, aktuell Reserve/IR; zählt nicht als spielbare QB-Coverage. |
| QB | Jayden Daniels | active | `core_starter` | `locked` | – | core_starter/locked | Hochwertiger langfristiger QB-Kern. |
| QB | Michael Penix Jr. | active | `backup` | `conditional` | 30 | unclassified | Aktueller QB4 ohne sicheren Mighty-Giants-Startpfad; QB-Coverage vor Cut gegen realen Free-Agent-Replacement-Level prüfen. |
| QB | Patrick Mahomes | active | `core_starter` | `locked` | – | core_starter/locked | Elite-2QB-Starter, Cap-Last unabhängig von Spielerqualität beurteilen. |
| QB | Tyler Shough | active | `starter_rotation` | `strong_hold` | – | backup/strong_hold | Saints-Starter und laut Week-9-FantasyPros QB12 nach Fantasy-Punkten pro Spiel; echte QB3-Rotation. |
| RB | Breece Hall | active | `core_starter` | `locked` | – | core_starter/locked | Dynasty-Kern und Starter; jüngste Ausfallhistorie separat bei Availability berücksichtigen. |
| RB | Cam Skattebo | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Junger startbarer RB; Hamstring-Status für Week 10 erneut prüfen. |
| RB | Chase Brown | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Startbarer RB mit verlässlichem Flex-Einsatzpfad. |
| RB | D'Andre Swift | active | `starter_rotation` | `strong_hold` | – | unclassified | Aktueller klarer Bears-Lead-Back mit hoher Snap-/Carry-Beteiligung; kein unklassifizierter Grenzfall mehr. |
| RB | Dylan Sampson | active | `backup` | `hold` | – | prospect/conditional | Browns-Change-of-Pace/Receiving-Rolle: Weeks 7-9 ca. 55 % Snaps und 5,7 Targets pro Spiel; nicht länger rein theoretischer Prospect. |
| RB | Jeremiyah Love | active | `core_starter` | `locked` | – | core_starter/locked | Elite-Dynasty-Asset, aktuell auf NFL-IR wegen Sprunggelenk; kein sofortiger Startable-Player. |
| RB | Jonathon Brooks | reserve | `prospect` | `conditional` | – | prospect/hold | Langfristiger Recovery-Stash mit erheblichem Gesundheits-/Rollenrisiko; Reserve belegt keinen aktiven Platz. |
| RB | Kenneth Walker III | active | `core_starter` | `locked` | – | unclassified | Kansas-City-Lead-Back und elite aktuelle TD-/Scrimmage-Produktion; Upgrade von Rotation/Strong Hold. |
| RB | Kyle Monangai | active | `backup` | `hold` | – | backup/strong_hold | Bears-RB2 mit Kontingenz-Upside hinter eigenem Swift, derzeit Verletzungs-/Verfügbarkeitsrisiko; kein automatischer Premium-Hold. |
| RB | Saquon Barkley | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Win-now-Produktion mit zunehmendem Alters-, Verletzungs- und Cap-Risiko; kein unantastbarer Dynasty-Core. |
| RB | Seth McGowan | active | `backup` | `hold` | – | unclassified | Von Colts bestätigter RB2 hinter Jonathan Taylor: 20-33 % Snaps in den letzten Wochen, 4,8 YPC bei 43 Läufen; starker Contingency-Pfad. |
| TE | Colston Loveland | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Young-TE mit substanziellem Volumen und Premium-Marktwert; in Liga mit 2 Pflicht-TEs klarer Starter. |
| TE | Harold Fannin Jr. | active | `starter_rotation` | `strong_hold` | – | unclassified | Reale Browns-TE-Usage ca. 86 % Snaps und 6,5 Targets im jüngsten Fenster; Upgrade von Backup. |
| TE | Trey McBride | active | `core_starter` | `locked` | – | core_starter/locked | Hochwertiger TE-Kern bei zwei festen TE-Spots. |
| TE | Tyler Warren | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Junger hochrangiger Starter/Flex-TE; vierte TE-Option ist in diesem Ligaformat wertvoll. |
| WR | Alec Pierce | reserve | `backup` | `hold` | – | backup/hold | Reserve/IR: Recovery-/Return-Option; Recheck bei Aktivierung und knapper IR-Kapazität. |
| WR | Antonio Williams | taxi | `prospect` | `hold` | – | prospect/hold | Taxi locked; Receiving-Upside nach Ausfall vor ihm, aber noch kein gesicherter weekly Starter. |
| WR | Brian Thomas Jr. | active | `prospect` | `hold` | 50 | unclassified | NFL-Offense-Rolle stark eingebrochen (Week 9 null Targets, elf Routes); Dynasty-Talent/Trade-Option noch vor nacktem Cut schützen. |
| WR | Chris Bell | taxi | `prospect` | `hold` | – | prospect/hold | Taxi locked; geringe aktuelle Dolphins-Produktion, Entwicklungshorizont und nächste Offseason entscheidend. |
| WR | Davante Adams | reserve | `starter_rotation` | `hold` | – | starter_rotation/hold | Veteran mit Win-now-Upside, aber Reserve/IR und Alters-/Salary-Retention-Risiko. |
| WR | De'Zhaun Stribling | reserve | `prospect` | `strong_hold` | – | prospect/strong_hold | Junges IR-/Reserve-Asset mit Draftkapital; ohne aktuellen aktiven Slotpreis. |
| WR | George Pickens | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Startbarer Dallas-WR, kurzfristige Verletzung gesondert prüfen. |
| WR | Germie Bernard | active | `prospect` | `conditional` | 40 | unclassified | Rookie mit produktiver NFL-Rolle (32 Receptions in acht Spielen), aber noch schwaches Elite-Lineup-Profil in Sechserliga. |
| WR | Jakobi Meyers | active | `backup` | `conditional` | 10 | backup/hold | Verlässliche NFL-Rolle, aber relativ geringe Dynasty-Upside und hoher ligaeigener WR-Replacement-Level; erster aktiver Add-Vergleich. |
| WR | Jaylen Waddle | active | `starter_rotation` | `hold` | – | starter_rotation/strong_hold | Dynasty-Wert bleibt relevant, aber Broncos-Usage zuletzt begrenzt und Week-9-Concussion; Strong Hold vorläufig zu Hold. |
| WR | Ladd McConkey | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Junger startbarer WR; Back-Spasmen/kurzfristige Availability separat prüfen. |
| WR | Malik Nabers | active | `core_starter` | `locked` | – | core_starter/locked | Hochrangiger WR-Core mit nachhaltiger Ziel-/Dynasty-Rolle. |
| WR | Marvin Harrison Jr. | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Schwankende aktuelle HOU-Performance, aber Talent-/Draftkapital- und Rebound-Pfad schützen. |
| WR | Puka Nacua | active | `core_starter` | `locked` | – | core_starter/locked | MCL/PCL/Turf-Toe-Verletzung, wahrscheinlicher IR-Ausfall; Dynasty-Security unverändert, Week-10-Utility null/hochfraglich. |
| WR | Tetairoa McMillan | active | `starter_rotation` | `strong_hold` | – | starter_rotation/strong_hold | Young-Premium-Dynasty-WR mit klarem Starterpotenzial. |
| WR | Travis Hunter | active | `prospect` | `hold` | 20 | unclassified | Sehr hohes Draft-/Talent-Upside, derzeit überwiegend Cornerback (2026 ca. 43 Offense- vs. 406 Defense-Snaps); kein aktueller Fantasy-Starter. Halten/Tradewert prüfen vor Cut. |

## Einordnung der Churn-Boundary

Die aktive Comparison Boundary ist **Jakobi Meyers (10) → Travis Hunter (20) → Michael Penix Jr. (30) → Germie Bernard (40) → Brian Thomas Jr. (50)**. Das ist eine **Vergleichsreihenfolge**, keine Cut-Empfehlung und kein zwingendes Asset-Ranking. Hunter steht trotz aktuell geringster WR-Usage hinter Meyers, da die Entwicklungs-/Draftkapital-Option explizit geschützt bleibt. Bei Penix muss ein realer aktueller 2QB-Replacement-Check vor einem Cut erfolgen. Brian Thomas wird trotz enttäuschender NFL-Rolle wegen verbliebener Prospect-/Trade-Upside nicht pauschal freigegeben.

Der **General-Churn-Stand bleibt 0/2**, weil derzeit niemand außer dem Kicker-Spezialisten als `churn` markiert ist. Auch `conditional` ist kein freier Slot. Keine künstliche Zwei-Slot-Erfüllung durch einen unbegründeten Drop.

## Coverage und Injury-Interpretation

- Strukturelle Belegung: aktive Plätze 30/30, Reserve 5/5, Taxi 2/2 locked. Ein möglicher Wechsel von Puka Nacua auf NFL-IR ist noch keine automatisch freie Fantasy-Reserve-Kapazität.
- QB: 2 feste Starter, Mahomes und Daniels als Kern, Shough als reale kurzfristige Rotation, Penix als QB4, Dart auf IR. Vor einem QB-Abgang aktuellen FA-Replacement-Level, Bye-Überlappung und Verletzungen prüfen.
- TE: 2 feste Starter. McBride, Loveland, Warren und jetzt auch Fannin bleiben stark geschützt. Für diese Liga ist die vierte TE-Option kein gewöhnlicher überflüssiger Backup.
- FLEX/Skill: Ein bloßes `core_starter`-/`starter_rotation`-Label darf verletzte Spieler nicht als sofortige Start-Option zählen. Love (IR), Adams (IR) und Nacua (wahrscheinliche IR) aktuell bei weekly Einsatzfähigkeit gesondert abziehen; weitere Q/Concussion-Fälle prüfen.
- RB-UpSide: Sampson = eigener Receiving-/Change-of-Pace-Pfad, McGowan = echtes RB2 plus Contingency für fremden Jonathan Taylor, Monangai = Contingency für eigenen Swift. Diese Pfade sind nicht gleichwertig und müssen für jeden neuen RB-Add gemeinsam gegengeprüft werden.
- Keine Gehalts-/Cap-Entscheidung aus Role/Security allein; Projected Salary bleibt eigener Retention-Layer.

## Quellen-/Evidenzanker (Stand 2026-11-10)

- [Colts offiziell, Seth McGowan RB2 und tatsächliche Snap-Beteiligung](https://www.colts.com/news/5-colts-things-adetomiwa-adebawore-seth-mcgowan-flash-vs-cowboys-why-shane-steichen-went-for-the-win-late-in-week-9), 2026-11-09.
- [Colts offizielles Depth Chart Week 9](https://www.colts.com/news/colts-release-unofficial-depth-chart-for-week-9), 2026-11-03.
- [RotoWire, Browns aktuelle Roles inklusive Dylan Sampson und Harold Fannin](https://www.rotowire.com/football/position-roles.php?team=CLE), 2026-11-09.
- [FantasyPros, Week-9-Primer und Tyler Shough QB12/FPPG](https://www.fantasypros.com/2026/11/the-primer-week-9-edition-2026-fantasy-football/2/), 2026-11.
- [Jaguars Wire, Travis-Hunter-Snap- und Offense/Defense-Split](https://staging-aws.sports.yahoo.com/articles/evaluating-travis-hunters-snap-counts-151431464.html), 2026-11-06.
- [CBS, Brian Thomas Jr. nach Week 9](https://www.cbssports.com/fantasy/football/news/jaguars-brian-thomas-not-targeted-in-week-9-win/), 2026-11-06.
- Zusätzlich: aktuelle Dynasty-Position-Ranks und FantasyCalc-Werte aus dem im Repository materialisierten Operations-Overview; keine generischen Superflex-Ranks direkt als Sechserliga-Asset-Board übernommen.

## Recheck-Auslöser

1. Offizielle IR-/Reserve-Bewegung und neues Week-10-Injury-Update für Puka, Love, Waddle, Pickens, Skattebo, McConkey.
2. Tatsächliche 2026er WR-Snap-Verteilung von Travis Hunter und Brian Thomas bei Jacksonville über mehrere weitere Wochen.
3. Veränderung der Browns-RB-Snap-/Targets-Verteilung (Sampson/Judkins) und Indianapolis RB2-Touches (McGowan/Taylor).
4. Rückkehr von Dart, Adams, Pierce, Brooks und Stribling aus IR; dann aktive Retention-Kosten neu ermitteln.
5. Jeder konkrete Add/Drop/Trade gegen die geordnete Boundary und den bestätigten realen Free-Agent-Pool.
