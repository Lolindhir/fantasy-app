# Trade Decision Record – D'Andre Swift für Tre Tucker + 2027 Rookie-4th

> **Status: ENTWURF (`draft`) — noch nicht versiegelt.** Dieser aus zeitnahen Gesprächen rekonstruierte Entscheidungszustand dient dem späteren Review ohne Hindsight Bias. Numerische subjektive Ratings wurden damals nicht ausdrücklich erfasst und bleiben bis zu Roberts Kalibrierung offen. Alle Aussagen unter „Erwartungen“ sind **ex ante**, keine beobachteten Ergebnisse.

## Metadaten

- Record-ID: `trade-2026-11-05-dennis-dandre-swift`
- Trade-ID: `sleeper-1424008779854282752`
- Trade-Abschluss in Sleeper: **05.11.2026**, Week 9 (Einigung im Chat am **04.11.2026, 22:11 MEZ**).
- Erstellt: 06.11.2026
- Ursprung: `reconstructed` (aus Chat und Quellen unmittelbar nach der Ausführung).
- Rekonstruktions-Confidence: **4/5** für die Gesamtrekonstruktion; Transaktions- und Pick-Fakten **5/5**.
- Outcome-Firewall: **ja**. Keine späteren Spiele oder Wertentwicklungen in die ursprüngliche Entscheidungsbegründung eingerechnet.
- Kanonische strukturierte Fassung: [decision-record.json](decision-record.json).

## 1. Exakte Transaktion

| Mighty Giants erhalten | Mighty Giants geben ab |
|---|---|
| **D'Andre Swift** · RB · Sleeper `6790` | **Tre Tucker** · WR · Sleeper `10213` |
| | **2027 Rookie-4th, ursprünglich Ruhr Valley Packers / Marcel** · `2027_Rookie_R4_OO2` |

- Gegenpartei: **Dennis / Team DennisLACards**, TeamID 5.
- Der Pick stammt ursprünglich von **Marcel (TeamID 2)**, wurde am 02.09.2026 von Marcel zu Robert transferiert und ging jetzt an Dennis. **Roberts eigener 2027 Rookie-4th blieb erhalten.**
- Exakte Draftposition des Picks ist noch offen; in der Sechserliga liegt Runde 4 insgesamt bei **#19–24**, nicht bei einem typischen Zwölferliga-Fourth.
- Kanonischer Beleg: `public/data/Transactions.json#TransactionID=1424008779854282752`; Pick-Verlauf: `public/data/Drafts.json#PickKey=2027_Rookie_R4_OO2`; ursprünglicher Erwerb: `public/data/Transactions.json#TransactionID=1400904559005532160`.

## 2. Entscheidungsproblem und Ex-ante-Kontext

**Ziel:** Aus einer großen Sammlung von WR-Upside-Wetten einen sofort besser einsetzbaren RB machen – **ohne den Kern für 2027 aufzugeben**.

Nach Week 8 stand Mighty Giants bei **4–4**; Flo hatte sein Team durch Christian McCaffrey weiter verstärkt. Robert bezweifelte, ob Flo noch schlagbar sei, wollte sich aber nicht zu einem großen All-in-Trade drängen lassen. Mighty Giants hatte ausreichend hochpreisige oder entwicklungsfähige WRs. Tucker war selbst erst in Week 7 über Waiver zurückgeholt worden, wurde aber **nicht als wertlos** gesehen: Robert sah altersbedingtes Upside und hatte Angst, ihn genau vor einem Breakout zu verkaufen.

### Warum Swift?

- Swift versprach **unmittelbar nutzbare RB-Punkte**. Die damalige, vereinfachte Week-9-Lineup-Optimierung erwartete **ungefähr +6,7 projizierte Punkte** bei optimierter Aufstellung. Das war **keine** verlässlich realisierte Wochensteigerung.
- Mighty Giants hatte bereits **Kyle Monangai**. Robert sagte Dennis ausdrücklich, dass er den Trade **ohne Monangai vermutlich nicht machen würde**: Als Absicherung bei Swift-Verletzung oder späterem Altersrückgang war Monangai ausschlaggebend.
- Zwei RBs desselben Backfields sind **keine zwei unabhängig produzierenden RB1s**; bei Gesundheit können sie sich die Chancen teilen.
- 30/30 aktive Rosterplätze: Ein **WR gegen RB** erhält den aktiven Personalstand; ein reiner Pick-Kauf hätte erst einen separaten Cut/Abgang erfordert, und Brooks auf IR abzugeben hätte das Problem nicht gelöst.

### Salary / Ligaformat

- Sechserliga mit 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K und vier Playoffplätzen.
- Salary Cap war **während der laufenden Saison keine bindende Trade-Hürde**. 2027er Salary-/Cap-Folgen waren nicht der Haupttreiber und bleiben eine separate spätere Prüfung.
- Externe FantasyCalc-, KTC- und Dynasty-Daddy-Rechner waren Referenzen, **keine exakt kalibrierten Werte für unsere Sechserliga**.

## 3. Historische Evidenz (nicht spätere Resultate)

| ID | Quelle | Was sie belegt |
|---|---|---|
| E1 | `public/data/Transactions.json#TransactionID=1424008779854282752` | Swift → Mighty Giants; Tucker + exakt benannter Rookie-4th → Dennis; abgeschlossen. |
| E2 | `public/data/Drafts.json#PickKey=2027_Rookie_R4_OO2` | Ursprünglicher Pickbesitzer Marcel, Pick-Kette und noch nicht feststehender Overall Slot. |
| E3 | WhatsApp-Auszug von Robert vom 04.11.2026 | Direkte Ziele, Gefühle, Grenzen und „Deal 🤝“; keine numerischen Selbstratings. |
| E4 | `league-context/trade-negotiation-history.md` | Dennis' Tucker-Bedenken, Value-Rechner, Nabers-Gegenfrage und Rückkehr zum unveränderten Eröffnungsangebot. |
| E5 | FantasyCalc Dynasty 8-Team SF/PPR Snapshot **03.11.2026** | Swift **3.076**, Tucker **1.509**, 2027 Rookie-4th (mid) **850**; Basismarkt, nicht 6er-fair value. |
| E6 | Damalige Week-9-Lineup-Diskussion | Grobe +6,7-Punkte-Projektion; kein Outcome und keine belastbare Championship-Wahrscheinlichkeit. |
| E7 | Sleeper #1400904559005532160 vom 02.09.2026 | Historische Herkunft des an Dennis abgegebenen Marcel-Picks. |
| E8 | `public/data/League.json` | Sechs Teams; besondere Starter- und FLEX-Struktur. |

## 4. Ex-ante-Thesen (noch nicht bewertet)

| ID | Erwartung | Horizont | Woran wir sie prüfen |
|---|---|---|---|
| **T1** | Swift erhöht den echten startbaren RB-/FLEX-Nutzen gegenüber dem Tucker-Roster. | Rest 2026 | Tatsächliche Einsätze, Swift-Workload, Lineup-Entscheidungen, Vergleich gegen ersetzte FLEX-Spieler. |
| **T2** | Monangai reduziert unser Swift-Ausfallrisiko und behält 2027 optionalen Wert. | 2026–27 | Backfield-Hierarchie, Ausfallszenarien, eigenständige oder kontingente Rolle. |
| **T3** | WR→RB beseitigt den Engpass ohne zusätzlichen Cut und erhält genügend WR-Coverage. | Sofort | Roster-Slots, FLEX- und WR-Abdeckung, Bedarf an Folgebewegungen. |
| **T4** | Die aufgegebene Tucker-Wette + ein Rookie-4th ist als Preis für Swift vertretbar. | Mehrjährig | Tuckers Breakout-Pfad, erhaltene Swift-Nutzung, Wert/Slot des Rookie-4ths; nicht nur retrospektive Punkte. |
| **T5** | Wir stärken den Playoff-Anlauf kontrolliert, ohne Nabers, Brooks, Fannin, Waddle oder einen frühen Rookie-Pick preiszugeben. | 2026 | Tatsächlich behaltene Kernassets und realisierter kurzfristiger Startnutzen. |

Die Thesen sind **zu prüfen**, nicht als richtig vorausgesetzt. Ihre jeweiligen numerischen Confidence-Werte bleiben bis zur Kalibrierung `null`. Die vollständigen Falsifikationsbedingungen stehen im JSON.

## 5. Bewusste Alternativen und geschützte Assets

- **Gar kein Trade:** Tucker + Pick als Zukunftsoption behalten. Verworfen zugunsten eines kontrollierten RB-Upgrades.
- **Brooks + 2027 Rookie-3rd:** Als Preis diskutiert, aber Brooks hatte noch langfristiges Upside und lag auf IR; der aktive Rosterplatz wäre nicht gelöst gewesen.
- **Waddle für Swift:** Zu großer opportunistischer Sell-low einer längerfristigen WR-Wette.
- **Swift nur für Draftkapital (z. B. Rookie-2nd):** Ohne aktiven Spielerausgang bei vollem Roster unpraktisch; Rookie-2nd wertvoll.
- **Tucker + Rookie-3rd:** Als denkbare Konzession besprochen, **nicht erforderlich**. Dennis akzeptierte Tucker + einen Rookie-4th.
- **Alternativer RB, etwa Javonte Williams:** In der Analyse betrachtet, aber kein gleichwertiger vereinbarter Deal.

**Bewusst geschützt:** Nabers (explizites klares Nein auf Dennis' Gegenfrage), Brooks (IR/Upside), Waddle (längerfristiges Potenzial), Fannin (TE-Upside) und Mighty Giants' eigener 2027 Rookie-First.

**Price Ceiling:** Kein vom Nutzer ausdrücklich festgelegtes hartes Maximum dokumentiert. Der ausgeführte Preis entspricht dem unveränderten **Eröffnungsangebot**. Ob dies unter einem später akzeptablen Maximalpreis lag, bleibt `unknown`.

## 6. Bekannte Risiken

| Risiko-ID | Ursprüngliche Sorge |
|---|---|
| **R1** | **Tucker explodiert später** und Robert wiederholt sein befürchtetes Watson-/Warren-Muster: ein junger Spieler wird vor dem Ausbruch abgegeben. |
| **R2** | Swift verletzt sich oder baut mit Ende 20 ab; Monangai ist nur eine mögliche Absicherung. |
| **R3** | Swift und Monangai teilen sich gesund zu viel Workload und steigern die Startaufstellung weniger als erhofft. |
| **R4** | Der abgegebene Rookie-4th hat als möglicher Gesamtpick #19–24 mehr Wert als in generischen Seiten dargestellt. |
| **R5** | Marktwerte und Projektionswerte bilden unsere Sechserliga nicht hinreichend ab. |
| **R6** | Mögliche zukünftige Cap-/Salary-Kosten der Swift-Haltung werden erst in der Offseason relevant. |

## 7. Persönlicher Entscheidungszustand am 04.11.2026

| Messgröße | Rekonstruktionsstatus |
|---|---|
| **Decision Confidence** | **offen / `null`** (Robert hat nicht selbst 1–5 bewertet) |
| **Outcome Uncertainty** | **offen / `null`** (keine eigene 1–5-Bewertung) |
| **Gut Feeling** | **`mixed` – vorläufig**: Interesse/Abschlussfreude plus ausdrücklich benannte Verlustangst |
| **Decision Margin** | **`unknown`** bis zur Kalibrierung |
| **Provenienz** | `reconstructed_contemporary_evidence` |

**Primärer Confidence-Treiber:** Günstiger, unverändert angenommener WR→RB-Preis und Monangai als persönlicher Swift-Hedge.

**Primärer Zweifel:** Tucker könnte mit 25 ein wertvollerer WR werden, während Swift alters- und rollenseitig zurückgeht.

**Mögliche Bias-Risiken:** frühere schmerzhafte Erfahrung mit verkauften Talenten; Giants-Sympathie bei Nabers; Wettbewerbsdruck wegen Flos CMC-Trade; mögliches Überschätzen der Monangai-Absicherung. Diese werden als **Risiken**, nicht als diagnostizierte Fehler behandelt.

## 8. Asset-Kette

`sleeper-1400904559005532160` → `sleeper-1424008779854282752`  
**2026 FA 4.04 → Marcels 2027 Rookie-4th → Teil des Swift-Kaufpreises.**

Diese Verbindung beschreibt die **echte Pick-Herkunft**, keine vorab geplante langfristige Trade-Kette. Die frühere Entscheidung wird durch spätere Ereignisse nicht neu benotet.

## 9. Geplanter Review – strikt getrennt vom Record

1. **Early Signal:** Nach ungefähr 4–6 aussagekräftigen Spielen nach dem Trade (Snap Share, Carries/Targets, Monangai-Rolle, tatsächliche FLEX-Differenz).
2. **Season End 2026:** Hat Swift zum Playoff-Run beigetragen? Prozessqualität getrennt vom Ergebnis beurteilen.
3. **Asset Resolution 2027:** Tatsächliche Picknummer, Draft-Shelf bzw. spätere Weitergabe von `2027_Rookie_R4_OO2` auflösen.
4. **Year 1 / Ende 2027:** Tuckers langfristige Entwicklung, Swifts Rollenstabilität und eventuelle Cap-Kosten prüfen.

**Keine automatischen Läufe oder neuen Reviews eingerichtet.** Die Planpunkte sind nur dokumentierte Trigger.

## 10. Rekonstruktionsgrenzen und Seal

- Originales WhatsApp-Material ist **verdichtete zeitgenössische Evidenz**; es wird kein vollständiger privater Chat exportiert.
- Numerische Confidence/Uncertainty und formaler Margin-Wert konnten nicht unmittelbar aus Roberts Nachrichten übernommen werden.
- Nach erfolgter Kalibrierung durch Robert und seiner ausdrücklichen Bestätigung kann die **ex-ante-Fassung versiegelt** werden.
- **Seal-Status:** `draft`; `sealed_at: null`; `sealed_with_user_confirmation: false`.
- **Corrections:** Keine.

Der vollständige maschinenlesbare Datensatz mit Evidenz-/Risiko-/Thesis-IDs und Falsifikationsbedingungen steht in [decision-record.json](decision-record.json).
