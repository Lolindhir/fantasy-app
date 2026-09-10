---
type: draft_analysis
scope: fantasy-management
created: 2026-09-10
status: active
draft_key: 2026_Free_Agent
analysis_kind: post_draft_contextual
context_completeness: partial
team_context: League-wide
supersedes: null
validity_note: "Historische Post-Draft-Baseline. Draftresultate sind fix; Manager-Tendenzen vor zukünftigen Drafts mit neuer Evidenz und aktueller Kaderlage abgleichen."
---

# Free-Agent-Draft-Analyse 2026

## 1. Zweck und Korrekturhinweis

Diese Datei friert den abgeschlossenen 2026 Free-Agent Draft als historische Analysebasis ein und verbindet die tatsächlichen Picks mit dem dokumentierten Pre-Draft-Kontext, dem Rookie-Draft 2026 und den vorhandenen Owner-Profilen.

**Wichtiger Korrekturhinweis:** Eine unmittelbar vor der Persistierung im Chat erstellte Zusammenfassung enthielt eine falsche Pickliste und daraus abgeleitete falsche Positionssummen. Diese Fassung speichert diese Fehler **nicht**, sondern wurde gegen das kanonische `public/data/Drafts.json` neu aufgebaut.

Die maschinenlesbare Begleitdatei liegt unter:

`fantasy-management/analyses/2026/drafts/2026-09-10_2026-fa-draft-postmortem.json`

## 2. Datengrundlage und Kontextqualität

| Quelle | Blob-SHA | Verwendung |
|---|---|---|
| `public/data/Drafts.json` | `5529991a8cebb33486e165f9687ba3fc53a2dbf2` | Kanonische vollständige FA-Draftreihenfolge, Spieler, Pickbesitz und Trades |
| historischer `public/data/League.json`-Blob | `00957a261eea27db831ca400e84b1fc3e1e098f5` | Liga-/Roster-Snapshot des FA-Preboards |
| `analyses/2026/free-agents/2026-08-19-fa-draft-preboard.md` | `e2049d3d8a3537edcf5960f061aa9eaac27c318b` | Vollständige dokumentierte Mighty-Giants-Pre-Draft-Strategie |
| `analyses/2026/drafts/2026-07-13_2026-rookie-draft-postmortem.md` | `f8765b843938c61ff3628e2844279265b5eaa09e` | Rookie-Draft, Teamkontexte und erste Managerbeobachtungen |
| `league-context/owner-registry.json` | `84bb22c293bfae60ec9449a7d34b160be81bd25e` | Owner-/TeamID-Auflösung |
| `league-context/owner-profiles.md` | `7d2b0e9b5db2260d7a5979b0b49ec41ae511073e` | Mehrjährige Draft-Tendenzen und direkte Target-Evidenz |

### Kontextgrenze

Für **Robert** existiert mit dem FA-Preboard eine dedizierte, datierte Need- und Board-Baseline. Für die fünf Gegner existiert kein gleichwertiger vollständiger FA-Day-Need-Snapshot. Dort werden deshalb nur dokumentierte Juli-Teamkontexte und bereits belegte Owner-Tendenzen verwendet. Ein Pick darf nicht rückwärts als Beweis für ein vorheriges Need ausgegeben werden.

Es wurde außerdem kein vollständiger externer FA-Day-Markt-Snapshot für alle 30 Picks archiviert. Deshalb enthält diese Postmortem-Fassung bewusst keine nachträglich erfundenen Pick-Grades oder Market-Delta-Werte.

## 3. Liga- und Draft-Rahmen

Der historische Pre-Draft-Snapshot zeigt sechs Teams mit 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K und 16 Bench-Slots. Der FA-Draft hatte fünf lineare Runden.

In einer so flachen Liga ist die zentrale Bewertungsfrage nicht abstrakte Superflex-Knappheit, sondern der **ligaeigene Replacement Level und der tatsächliche Draftmarkt**. Diese Unterscheidung ist für die QB-Erkenntnis 2026 entscheidend.

## 4. Vollständiger Free-Agent Draft

| Pick | Owner | Spieler | Pos. | Pick-Kontext |
|---:|---|---|---|---|
| 1.01 | Robert | Tetairoa McMillan | WR | Pick von Dennis → Robert |
| 1.02 | Tim | Javonte Williams | RB | — |
| 1.03 | Jan | Brock Purdy | QB | — |
| 1.04 | Dennis | Travis Etienne | RB | Pick von Robert → Dennis |
| 1.05 | Marcel | J.K. Dobbins | RB | — |
| 1.06 | Flo | Parker Washington | WR | — |
| 2.01 | Dennis | Terry McLaurin | WR | — |
| 2.02 | Tim | Juwan Johnson | TE | — |
| 2.03 | Jan | George Kittle | TE | — |
| 2.04 | Robert | Jonathon Brooks | RB | Pick zwischenzeitlich gehandelt, am Drafttag wieder beim Originalteam |
| 2.05 | Tim | Romeo Doubs | WR | Pick von Marcel → Tim |
| 2.06 | Flo | Chuba Hubbard | RB | — |
| 3.01 | Dennis | Jalen Coker | WR | — |
| 3.02 | Tim | Isaac TeSlaa | WR | — |
| 3.03 | Jan | Jordan Mason | RB | — |
| 3.04 | Jan | Tyler Allgeier | RB | Pick von Robert → Jan |
| 3.05 | Marcel | Dalton Schultz | TE | — |
| 3.06 | Flo | MarShawn Lloyd | RB | — |
| 4.01 | Dennis | Stefon Diggs | WR | — |
| 4.02 | Tim | Jared Goff | QB | — |
| 4.03 | Jan | Chris Rodriguez | RB | — |
| 4.04 | Marcel | AJ Barner | TE | Pick von Robert → Marcel |
| 4.05 | Marcel | Deebo Samuel | WR | — |
| 4.06 | Flo | Tre Tucker | WR | — |
| 5.01 | Dennis | Cam Ward | QB | — |
| 5.02 | Tim | Jalen McMillan | WR | — |
| 5.03 | Jan | C.J. Stroud | QB | — |
| 5.04 | Robert | Ricky Pearsall | WR | — |
| 5.05 | Marcel | Sam Darnold | QB | — |
| 5.06 | Flo | Malik Willis | QB | — |

## 5. Positionsverteilung

### Free-Agent Draft 2026

| Position | Picks | Anteil |
|---|---:|---:|
| WR | 11 | 36,7 % |
| RB | 9 | 30,0 % |
| QB | 6 | 20,0 % |
| TE | 4 | 13,3 % |

### Gesamte Draft-Season 2026

Der Rookie-Draft enthielt 15 WR, 8 RB, 4 TE und 3 QB. Zusammen mit dem FA-Draft ergibt sich:

| Position | Rookie | FA | Gesamt | Anteil gesamt |
|---|---:|---:|---:|---:|
| WR | 15 | 11 | 26 | 43,3 % |
| RB | 8 | 9 | 17 | 28,3 % |
| QB | 3 | 6 | 9 | 15,0 % |
| TE | 4 | 4 | 8 | 13,3 % |

WR und RB stellen gemeinsam **43 von 60 Picks = 71,7 %**. Das ist ein klares Skill-Position-Schwergewicht, aber deutlich weniger extrem als eine reine WR/RB-Liga. Besonders TE wird durch das Start-2-TE-Format sichtbar mitgedraftet.

## 6. Die wichtigste Liga-Erkenntnis: QB ist ein Tier- und Cliff-Markt

Der konkrete FA-Verlauf:

- Brock Purdy: 1.03
- danach **16 Picks ohne Quarterback**
- Jared Goff: 4.02
- Cam Ward: 5.01
- C.J. Stroud: 5.03
- Sam Darnold: 5.05
- Malik Willis: 5.06

Damit gingen fünf der sechs FA-QBs erst in Runde 4 oder 5; vier der sechs sogar in Runde 5. Gleichzeitig zeigt Purdy 1.03, dass ein gewünschtes Premium-/Sicherheitsprofil sehr früh verschwinden kann.

Die belastbare 2026-Regel lautet deshalb **nicht** „QBs sind billig“ und auch nicht „QBs müssen früh genommen werden“. Sie lautet:

> Der Markt kann einen klar gewünschten Premium-QB früh bezahlen und die nächste funktionale oder entwicklungsorientierte QB-Schicht danach sehr lange liegen lassen.

Für künftige Drafts muss deshalb mit **QB-Tiers und Tier-Cliffs** gearbeitet werden, nicht mit einer pauschalen Superflex-Priorität.

Der Rookie-Draft stützt die Trennung der Draftarten zusätzlich: Dort gingen nur drei QBs (Fernando Mendoza 2.02, Ty Simpson 3.04, Drew Allar 5.06). Rookie- und FA-QB-Markt dürfen daher nicht zu einer gemeinsamen ADP-Erwartung verschmolzen werden.

## 7. Tight End: keine pauschale Unterbewertung

Die korrigierten Daten widerlegen die zuvor im Chat formulierte These, TE werde nahezu ignoriert.

Rookie-Draft:
- Kenyon Sadiq 1.06
- Eli Stowers 2.03
- Eli Raridon 3.01
- Oscar Delp 4.04

FA-Draft:
- Juwan Johnson 2.02
- George Kittle 2.03
- Dalton Schultz 3.05
- AJ Barner 4.04

Das sind **8 von 60 Picks = 13,3 %**. Für eine Liga mit zwei festen TE-Startern ist damit klar: TE-Premium/-Scarcity beeinflusst den Markt bereits. Ein einzelner TE darf weiterhin Value sein, aber wir dürfen für 2027 keine automatische „Liga ignoriert TE“-Arbitrage unterstellen.

## 8. Owner-Analysen

### Robert

**Dokumentierter Pre-Draft-Kontext:** Tetairoa McMillan war an 1.01 als Locked Decision festgelegt. Zusätzlicher QB-Erwerb war ausdrücklich aus der aktuellen Strategie ausgeschlossen. Jonathon Brooks gehörte zum starken 2.04-Kandidaten-Tier.

**FA-Picks:** McMillan 1.01, Brooks 2.04, Pearsall 5.04.

Die tatsächlichen Entscheidungen lagen damit sehr nah an der dokumentierten Planung. Besonders wichtig für die Prozessbewertung: Der fehlende QB ist **kein verpasstes Need**, weil QB vor dem Draft bewusst ausgeschlossen worden war. Eine spätere Analyse darf nicht aus dem Ergebnis ein Need konstruieren, das im damaligen Plan nicht existierte.

Über beide 2026-Drafts nahm Robert neun Spieler: **5 WR und 4 RB**. Das ist ein starker 2026-Skill-Position-Fokus, passt aber zum bereits bestätigten Muster, die Positionsstrategie an den eigenen Kader anzupassen, und darf nicht als permanente WR/RB-Regel interpretiert werden.

**2027-Watch:** Vor dem Draft nicht nur Needs festhalten, sondern pro Need/Value-Tier einen konkreten Trigger definieren. Wenn eine Position bewusst ausgeschlossen ist, bleibt sie auch in der späteren Prozessbewertung ausgeschlossen.

### Marcel

**Dokumentierter Kontext:** Der Rookie-Postmortem sah Altersabsicherung auf RB/TE als sinnvoll. Das Owner-Profil bestätigt über mehrere Jahre eine aggressive Bewertung von RB-/TE-Rollen sowie unmittelbarer Produktion.

**FA-Picks:** Dobbins, Schultz, AJ Barner, Deebo Samuel, Darnold.

Mit den Rookie-Picks zusammen investierte Marcel 2026 **3 RB- und 3 TE-Picks bei insgesamt 8 Picks**. Besonders stark ist die direkte Evidenz aus dem laufenden Draft: Marcel tradete gezielt auf 4.04 hoch, um AJ Barner zu nehmen. Das bestätigt Target Conviction und TE-Wertschätzung wesentlich stärker als eine bloße Positionszählung.

**2027-Watch:** Bei RB-/TE-Tiers Marcel als erhöhte Konkurrenz modellieren. Bei Trade-ups zuerst prüfen, ob ein konkreter Target bekannt ist; sein Move-up-Verhalten ist target-spezifisch, nicht automatisch generisch.

### Flo

**Dokumentierter Kontext:** Als Champion bestand im Juli kein akutes Einzel-Need. Sein mehrjähriges Profil zeigt formatbewusste Diversifikation.

**FA-Picks:** Parker Washington, Chuba Hubbard, MarShawn Lloyd, Tre Tucker, Malik Willis.

Das ist WR2/RB2/QB1. Über beide Drafts ergibt sich WR4/RB3/QB2/TE1. Flo bestätigt damit stärker als jeder einfache Positions-Tell ein Muster der **breiten Portfolio-Streuung**.

**2027-Watch:** Flo nicht anhand einer einzigen Position forecasten. Attraktive spätere RB-/Upside-Pfade und formatrelevante QB/TE-Stashes bleiben wichtiger als ein fixer Positionsbias.

### Jan

**Dokumentierter Kontext:** Im Juli besaß Jan einen Elite-QB-/Elite-WR-Kern und hohen Roster-Druck. Historisch arbeitet er mit einem eigenen Board, ist bei TE aggressiv und wartet häufig auf QB-Value.

**FA-Picks:** Purdy, Kittle, Jordan Mason, Allgeier, Chris Rodriguez, Stroud.

Das ist ein besonders wertvolles Update für unser Modell: Jan nahm **keinen einzigen WR**, obwohl WR seine historische Kernstärke ist. Gleichzeitig nahm er Purdy bereits 1.03 und Stroud 5.03. Die alte Formulierung „Jan wartet auf QB“ ist damit zu starr. Besser:

> Jan ist bereit, auf QB-Value zu warten, aber ein Premiumprofil auf seinem eigenen Board kann den Positionskontext überstimmen.

Über beide 2026-Drafts ist Jan sehr breit verteilt: RB4, WR3, QB3, TE2.

**2027-Watch:** Jan ist vor allem ein Independent-Board-/Tier-Risiko. Wenn wir einen QB oder TE am Ende eines Tiers bewusst durchlassen wollen, darf seine Position im Draft nicht ignoriert werden.

### Dennis

**Dokumentierter Kontext:** Der Rookie-Postmortem nannte langfristige QB- und WR-Anker als zentrale Aufbauziele. Sein Owner-Profil zeigt wiederholt gute Bereitschaft, fallende QBs zu nehmen.

**FA-Picks:** Etienne, McLaurin, Coker, Diggs, Cam Ward.

Auffällig: Dennis hatte sowohl im Rookie- als auch im FA-Draft exakt **WR3/RB1/QB1**. Über die Saison sind das WR6/RB2/QB2 und kein TE. Das ist ein starkes saisoninternes Wiederholungssignal, aber noch kein mehrjähriger permanenter Positionsplan.

Ward erst 5.01 passt dabei gut zum bekannten QB-Verhalten: Dennis erzwingt die Position nicht allein wegen 2QB, sondern nimmt sie, wenn Preis und eigener Wert zusammenpassen.

**2027-Watch:** Aktuelle Need-Lage zuerst bestimmen; anschließend Dennis besonders bei fallenden QB- und WR-Tiers als Gefahr modellieren.

### Tim

**Dokumentierter Kontext:** Der Rookie-Postmortem identifizierte zusätzliches junges WR-Ceiling als Need. Das mehrjährige Profil bestätigt starke junge-WR-Präferenz und tiefe QB-/TE-Portfolios.

**FA-Picks:** Javonte Williams, Juwan Johnson, Romeo Doubs, Isaac TeSlaa, Jared Goff, Jalen McMillan.

Über beide Drafts nahm Tim **7 WR bei 11 Picks**, dazu 2 TE, 1 RB und 1 QB. Das ist die stärkste positionsbezogene 2026-Konzentration eines Gegners. Gleichzeitig zeigt Javonte 1.02, dass Tim hohen Value außerhalb des WR-Schwerpunkts nimmt.

Goff 4.02 sollte nicht als „QB-Sniper“-Beweis gelesen werden. Er kam nach 16 QB-losen Picks und passt eher zu Value-Mitnahme.

**2027-Watch:** Bei jungen WR-Tiers Tim deutlich hochgewichten; bei TE ebenfalls über Liga-Baseline. QB erst dann als besondere Gefahr behandeln, wenn aktueller Kader/Target-Kontext das zusätzlich stützt.

## 9. Owner Draft Behavior Matrix – 2026 Baseline

| Owner | Rookie 2026 | FA 2026 | Gesamt | Belastbarstes Signal |
|---|---|---|---|---|
| Robert | WR3 / RB3 | WR2 / RB1 | WR5 / RB4 | roster-adaptive Strategie; 2026 Skill-Position-Fokus |
| Marcel | RB2 / TE1 | RB1 / TE2 / WR1 / QB1 | RB3 / TE3 / WR1 / QB1 | RB/TE + konkrete Target-Conviction |
| Flo | WR2 / RB1 / TE1 / QB1 | WR2 / RB2 / QB1 | WR4 / RB3 / QB2 / TE1 | breite Diversifikation |
| Jan | WR3 / RB1 / QB1 / TE1 | RB3 / QB2 / TE1 | RB4 / WR3 / QB3 / TE2 | eigenes Board; positionsflexibel; Tier-/Target-getrieben |
| Dennis | WR3 / RB1 / QB1 | WR3 / RB1 / QB1 | WR6 / RB2 / QB2 | 2026 WR/QB-Aufbau + QB-Value-Disziplin |
| Tim | WR4 / TE1 | WR3 / RB1 / TE1 / QB1 | WR7 / TE2 / RB1 / QB1 | stärkste junge-WR-Neigung |

Die fortschreibbare Langzeitmatrix liegt separat unter `fantasy-management/league-context/owner-draft-behavior.md`.

## 10. Strategische Änderungen für 2027

Aus der 2026 Draft-Season werden fünf operative Änderungen abgeleitet:

1. **Rookie- und FA-Draft getrennt modellieren.** Positionsverteilungen, ADP-Erwartungen und Owner-Verhalten werden draftartspezifisch geführt.
2. **QB über Tiers statt pauschaler Scarcity steuern.** Premium-QB, funktionaler Starter und Entwicklungs-/Contingency-QB sind getrennte Märkte.
3. **TE-Markt empirisch behandeln.** Das 2TE-Format beeinflusst bereits Picks; keine automatische TE-Unterbewertung annehmen.
4. **Need-vs-Value-Trigger vor dem Draft festlegen.** Für echte Needs werden akzeptable Tiers, Tier-Cliffs und Reaktionspunkte definiert. Bewusst ausgeschlossene Needs werden nicht rückwirkend als Fehler bewertet.
5. **Owner Matrix jährlich fortschreiben.** Die Matrix modifiziert Pick-Wahrscheinlichkeiten, ersetzt aber nie die aktuelle Kader-/Need-Analyse oder direkte Target-Evidenz.

Die dauerhaften Methodenregeln stehen in `fantasy-management/_ai/DRAFT_STRATEGY_RULES.md`.

## 11. Review-Plan

Diese historische Analyse wird nicht mit späteren Outcomes überschrieben.

| Review | Zieltermin |
|---|---:|
| Year 1 | 10.09.2027 |
| Year 2 | 10.09.2028 |
| Year 3 | 10.09.2029 |

Bei den Reviews sollen insbesondere geprüft werden: QB-Tier-Cliff 2026, Persistenz der Owner-Positionsmuster, Erfolg der Trade-up-Targets, tatsächlicher Wert der späten QB-Schicht und ob Rookie-/FA-Märkte auch 2027 strukturell unterschiedlich bleiben.
