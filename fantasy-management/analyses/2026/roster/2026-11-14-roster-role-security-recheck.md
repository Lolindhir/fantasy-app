# Mighty Giants – Vollkader-Recheck / Role & Security

**Fachlicher Stand:** 2026-11-14 (Samstag vor NFL Week 10); **TeamID:** 1; **Saison:** 2026; **Status:** manueller datierter Bewertungs-Checkpoint, keine Sleeper-Transaktion.

## Daten und Trennung von Fakten/Interpretation

- Aktueller Kader aus `public/data/League.json` und kanonisch abgeleiteten `managed-roster-signals.json`: **37 Spieler**; aktive Belegung **30/30**, Reserve **5/5**, Taxi **2/2** (locked). Identische TeamID-1-Membership wie beim letzten November-Recheck.
- Ligastarter: 1 K, 2 QB, 2 RB, 2 TE, 2 WR, vier FLEX; zusätzlich 17 Benchplätze. Sechs Teams, Full PPR.
- Publiziertes Operations-Input-Snapshot: `2026-11-14T04:21:50.640409Z`; aktuelle externe Injury-Recherche 2026-11-13/14. Der Input-Snapshot kann eine 2026-11-14-Abendmeldung noch nicht enthalten; diese steht dann nur in der fachlichen Begründung.
- Der aktuelle automatische Startable-Skill-Pool von **18/10** ist **Rollen-/Talent-Coverage, keine gesunde Week-10-Startaufstellung**: etwa Puka (IR), Jeremiyah Love (IR), Waddle (Out), Marvin Harrison Jr. (Out) zählen nominell als Starterrolle.
- Projected Salary aller kontrollierten Spieler als reiner Rohwert: 597.1 Mio. $; tatsächliches Salary-Cap-Modell und mögliche Reserve-Ausnahmen separat prüfen. Liga-Cap: 427.7 Mio. $. Salary ist kein Talent-Ranking.
- Menschliche Interpretation/Role/Security, Injury-/Usage-Prognose, externe Experteneinschätzung und Cap-Bewertung bleiben explizit getrennt. Kein User-Override verändert.

## Neue vollständige Klassifikation

| Pos | Spieler | Bereich | Rolle | Security | Vorher | Grenzpriorität | Grund |
|---|---|---|---|---|---|---:|---|
| K | Ka'imi Fairbairn | active | `specialist` | `churn` | **unclassified** | – | Verlässlicher aktueller Kicker; Spezialplatz, kein allgemeiner Churn-Slot. |
| QB | Jaxson Dart | reserve | `backup` | `strong_hold` | backup/strong_hold | – | Langfristiges 2QB-Asset, aktuell Reserve/IR; zählt nicht als spielbare QB-Coverage. |
| QB | Jayden Daniels | active | `core_starter` | `locked` | core_starter/locked | – | Hochwertiger langfristiger QB-Kern. |
| QB | Michael Penix Jr. | active | `backup` | `conditional` | **unclassified** | 30 | Kurzfristige QB4-Versicherung bei Dart auf IR; realen Free-Agent-Replacement-Level und Bye-/Verletzungsfälle vor Cut prüfen. |
| QB | Patrick Mahomes | active | `core_starter` | `locked` | core_starter/locked | – | Elite-2QB-Starter, Cap-Last unabhängig von Spielerqualität beurteilen. |
| QB | Tyler Shough | active | `starter_rotation` | `strong_hold` | backup/strong_hold | – | New-Orleans-Starter: Week 9 265 Pass-Yards plus 50 Rush-Yards; echte dritte QB-Rotation, nicht nur Coverage. |
| RB | Breece Hall | active | `core_starter` | `locked` | core_starter/locked | – | Dynasty-Kern und Starter; jüngste Ausfallhistorie separat bei Availability berücksichtigen. |
| RB | Cam Skattebo | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Junger startbarer RB; Hamstring-Status für Week 10 erneut prüfen. |
| RB | Chase Brown | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Startbarer RB mit verlässlichem Flex-Einsatzpfad. |
| RB | D'Andre Swift | active | `starter_rotation` | `strong_hold` | **unclassified** | – | Bears-Lead-Back mit startbarer 2026-Rolle; in Week 10 Bye und damit keine Weekly-Option. |
| RB | Dylan Sampson | active | `backup` | `hold` | prospect/conditional | – | Aktuelle Receiving-/Change-of-Pace-Nutzung der Browns, eigenständiger Weekly- und zusätzlicher Contingency-Pfad; nicht länger bloß theoretischer Prospect. |
| RB | Jeremiyah Love | active | `core_starter` | `locked` | core_starter/locked | – | NFL-IR wegen Sprunggelenk; kein sofortiger Startable RB, bleibt geschützter langfristiger Dynasty-Kern. |
| RB | Jonathon Brooks | reserve | `prospect` | `conditional` | prospect/hold | – | IR/Recovery-Stash ohne aktuelle Spielbarkeit. Sein nächster aktiver Retention-Slot erfordert einen neuen Vergleich. |
| RB | Kenneth Walker III | active | `core_starter` | `locked` | starter_rotation/strong_hold | – | Elite-2026-Produktion in Kansas City, aber am 2026-11-13 wegen Groin tightness im Friday Practice fehlend/Week 10 questionable; hohe Security ist keine Start-Freigabe. |
| RB | Kyle Monangai | active | `backup` | `hold` | backup/strong_hold | – | Wert als Contingency-RB hinter eigenem D'Andre Swift, aber aktuelle Out-Bezeichnung und Chicagos Week-10-Bye separat behandeln. |
| RB | Saquon Barkley | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Win-now-Produktion mit zunehmendem Alters-, Verletzungs- und Cap-Risiko; kein unantastbarer Dynasty-Core. |
| RB | Seth McGowan | active | `backup` | `hold` | **unclassified** | – | Produktive Colts-RB2-Rolle hinter Jonathan Taylor, stärkeres Usage-/Contingency-Profil als hypothetischer reiner Stash. |
| TE | Colston Loveland | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Young-TE mit substanziellem Volumen und Premium-Marktwert; in Liga mit 2 Pflicht-TEs klarer Starter. |
| TE | Harold Fannin Jr. | active | `starter_rotation` | `strong_hold` | backup/strong_hold | – | Browns-TE mit substantieller Regular-Season-Usage; bei zwei festen TE-Spots relevante Starterrotation. |
| TE | Trey McBride | active | `core_starter` | `locked` | core_starter/locked | – | Hochwertiger TE-Kern bei zwei festen TE-Spots. |
| TE | Tyler Warren | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Junger hochrangiger Starter/Flex-TE; vierte TE-Option ist in diesem Ligaformat wertvoll. |
| WR | Alec Pierce | reserve | `backup` | `hold` | backup/hold | – | Reserve/IR: Recovery-/Return-Option; Recheck bei Aktivierung und knapper IR-Kapazität. |
| WR | Antonio Williams | taxi | `prospect` | `hold` | prospect/hold | – | Taxi locked; Receiving-Upside nach Ausfall vor ihm, aber noch kein gesicherter weekly Starter. |
| WR | Brian Thomas Jr. | active | `prospect` | `hold` | **unclassified** | 50 | Week 9 ohne Target, etwa 19 Offense-Snaps; drastischer Rollenverlust. Langfristige Talent- und Trade-Option rechtfertigt Hold statt kurzfristigem Cut. |
| WR | Chris Bell | taxi | `prospect` | `hold` | prospect/hold | – | Taxi locked; geringe aktuelle Dolphins-Produktion, Entwicklungshorizont und nächste Offseason entscheidend. |
| WR | Davante Adams | reserve | `starter_rotation` | `hold` | starter_rotation/hold | – | Veteran mit Win-now-Upside, aber Reserve/IR und Alters-/Salary-Retention-Risiko. |
| WR | De'Zhaun Stribling | reserve | `prospect` | `strong_hold` | prospect/strong_hold | – | Junges IR-/Reserve-Asset mit Draftkapital; ohne aktuellen aktiven Slotpreis. |
| WR | George Pickens | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Dallas-WR mit startbarer Rolle; nach Hamstring-Problematik laut aktuellem Week-10-Bericht Rückkehrwahrscheinlichkeit verbessert, aktive Teilnahme final prüfen. |
| WR | Germie Bernard | active | `prospect` | `conditional` | **unclassified** | 40 | Pittsburgh-Rookie mit realer Rolle; im tiefen sechs-Team-Format weiterhin unter der Premium-Lineup-Schwelle. |
| WR | Jakobi Meyers | active | `backup` | `conditional` | backup/hold | 10 | Aktuell nutzbare WR-Reserve, aber geringe Elite-Upside gegenüber Dynasty-Kern; erster Vergleichskandidat, kein automatischer Drop. |
| WR | Jaylen Waddle | active | `starter_rotation` | `hold` | starter_rotation/strong_hold | – | Denver-WR mit schwankender aktueller Usage, für Week 10 nach Concussion als Out gemeldet; langfristiger WR-Asset-Wert bleibt, kurzfristige Week-10-Availability fehlt. |
| WR | Ladd McConkey | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Junger Chargers-WR mit langfristiger Upside; für Week 10 questionable, kurzfristige Einsatzfähigkeit gesondert prüfen. |
| WR | Malik Nabers | active | `core_starter` | `locked` | core_starter/locked | – | Hochrangiger WR-Core mit nachhaltiger Ziel-/Dynasty-Rolle. |
| WR | Marvin Harrison Jr. | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Houston-WR mit jungem Talentprofil und Upside, Week 10 wegen Hamstring als Out; Security von 1-Wochen-Ausfall getrennt. |
| WR | Puka Nacua | active | `core_starter` | `locked` | core_starter/locked | – | NFL-IR seit 2026-11-12 (Rams offiziell 2026-11-13); mindestens bis Week 15 nicht einsetzbar. Hoher langfristiger Dynasty-Wert rechtfertigt Locked, Fantasy-Reserve aktuell voll. |
| WR | Tetairoa McMillan | active | `starter_rotation` | `strong_hold` | starter_rotation/strong_hold | – | Young-Premium-Dynasty-WR mit klarem Starterpotenzial. |
| WR | Travis Hunter | active | `prospect` | `hold` | **unclassified** | 20 | Jaguars-Einsatz weiterhin vornehmlich CB; Week 9 nur sechs Offense-Snaps und ein Target. Premium-Dynasty-Prospect, aber keine verlässliche WR-Weekly-Utility. |

## Vergleichsgrenze und Churn

- **Comparison Boundary** (nur Vergleichsreihenfolge, **keine** autonome Cut-Freigabe): Jakobi Meyers (10) → Travis Hunter (20) → Michael Penix Jr. (30) → Germie Bernard (40) → Brian Thomas Jr. (50).
- **Echter allgemeiner Churn: 0/2.** Der Kicker `specialist | churn` zählt wegen des Pflicht-Kicker-Slots nicht als allgemeine Kapazität; `conditional`/ `hold` sind nicht automatisch Drop-Slots.
- Penix bleibt wegen 2QB, Dart-IR und aktueller NFL-Starteroption eine echte Coverage-Prüfung. Hunter und Brian Thomas Jr. haben negative Current-Usage, aber eigenständige Dynasty-/Trade-Optionen. Bei einem konkreten Add muss die gesamte Grenzgruppe gegen tatsächlichen ligaeigenen Free-Agent-Ersatz geprüft werden.
- RB-Contingency getrennt: Monangai → eigener Swift, McGowan → fremder Jonathan Taylor, Sampson → Receiving-Role plus Verletzungs-Upside. Kein pauschales Own-Handcuff-Primat.

## Availability und Abhängigkeiten – wichtige neue Befunde

- Puka Nacua: **NFL-IR bestätigt am 12. November**, Rückkehr frühestens Week 15; Rams-Bestätigung vom 13. November. Im Fantasy-Roster bisher **aktiv**, weil alle fünf Reserve-Slots belegt sind: keine imaginäre freie IR-Capacity.
- Kenneth Walker III: Freitagtraining 13. November wegen Groin tightness verpasst, Week 10 **Questionable**. Kein automatischer Start trotz `locked`.
- Jaylen Waddle und Marvin Harrison Jr.: Week 10 **Out**. Chicagos Week-10-Bye verhindert zusätzlich einen Swift-Start, ohne dass dies die Dynasty-Security verändert.
- George Pickens / Ladd McConkey: Rückkehr bzw. Game-Status vor Kickoff verifizieren; Signal-Dataset und jüngster Pressebericht unterscheiden möglicherweise Zeitpunkte.
- Fünf Reserve-Slots sind ausgelastet (Dart, Brooks, Pierce, Adams, Stribling). Jegliche Puka-IR-Umlagerung braucht einen vollständigen Eligibility- und Roster-Cost-Vergleich.

## Verifizierte externe Quellen

- [Los Angeles Rams, Puka IR offiziell (2026-11-13)](https://www.therams.com/news/mcvay-rams-placed-puka-nacua-on-ir-because-they-needed-the-roster-spot-week-10-2026-cardinals).
- [NFL offizieller Week-10-Injury-Report, Stand 2026-11-13](https://amp.nfl.com/news/nfl-week-10-injury-report-2026-season).
- [Reuters: Walker groin/questionable, 2026-11-13](https://www.reuters.com/sports/chiefs-rb-kenneth-walker-iii-nursing-groin-injury--flm-2026-11-13/).
- [FantasyPros: Travis Hunter und Brian Thomas, Week-9-Usage](https://www.fantasypros.com/2026/11/beyond-the-waiver-wire-fantasy-football-moves-to-make-week-10-advice//?amp=1).
- [RotoBaller: Tyler Shough Week-9-Usage / Week-10 outlook](https://www.rotoballer.com/player-news?pid=2506121&sport=nfl).
- Dynasty-Marktwerte im aktuellen Operations-Signal aus FantasyPros und FantasyCalc, formatabhängig interpretiert. Quelle und Zeitstempel über `managed-roster-signals.json` verankert.

## Nächster fachlicher Recheck

Week-10-Game-Day-Inactives/Walker, Puka-Injury-/Fantasy-IR-Eligibility, Rückkehr von Adams/Dart/Pierce, tatsächliche Jaguars-WR-Offense-Snaps, McGowan-/Sampson-Usage, nächste Add-/Drop-Chance. Die bestehende Klassifikationsautomatisierung bleibt **manuell/hybrid** und ist weiterhin Gegenstand von Issue #203.
