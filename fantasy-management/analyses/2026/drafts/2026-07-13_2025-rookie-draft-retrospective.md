---
type: draft_analysis
scope: fantasy-management
created: 2026-07-13
status: active
draft_key: 2025_D1_Rookie
analysis_kind: retrospective_outcome
context_completeness: partial
team_context: League-wide without reliable draft-day roster snapshots
supersedes: null
validity_note: "Retrospektive Year-1-Outcome-Auswertung. Mangels historischem Drafttag-Markt- und Teamkontext dürfen die Outcome-Grades nicht als vollständige Process-Grades interpretiert werden."
---

# Rookie-Draft-Retrospektive 2025 – Year 1

## 1. Zweck und Abgrenzung

Diese Auswertung betrachtet den Rookie-Draft 2025 nach Abschluss der Rookie-Saison. Sie soll eine erste historische Vergleichsbasis für spätere Draftanalysen schaffen.

Die Analyse beantwortet vor allem:

- Welche Spieler produzierten bereits im ersten NFL-Jahr?
- Welche Picks lieferten gemessen am Pickslot besonders starke oder schwache Outcomes?
- Welche Teamklassen erzielten nach einem Jahr die beste Gesamtausbeute?
- Welche ersten Manager-Muster könnten sich aus dem Draft ergeben?

Die maschinenlesbare Begleitdatei liegt unter:

`fantasy-management/analyses/2026/drafts/2026-07-13_2025-rookie-draft-retrospective.json`

## 2. Wichtige Grenzen

Für 2025 fehlen zwei entscheidende historische Ebenen:

1. Ein verlässlicher Snapshot der Teamkader direkt zum Draftzeitpunkt.
2. Ein versionierter Drafttag-Snapshot von Rookie-ADP oder Dynasty-Marktwerten.

Deshalb werden **keine rückwirkend erfundenen Process-, Market-Value- oder Team-Fit-Grades** vergeben. Die Noten in dieser Datei sind reine **Year-1-Outcome-Grades**.

Das bedeutet:

- Ein guter Rookie-Year-Outcome beweist nicht automatisch, dass der Pick am Drafttag optimal war.
- Ein schwacher Rookie-Year-Outcome beweist nicht automatisch, dass der Prozess schlecht war.
- Verletzungen und entwicklungsabhängige Positionen, insbesondere Tight End und Quarterback, benötigen weitere Reviews.

## 3. Datengrundlage

| Quelle | Blob-SHA / Stand | Verwendung |
|---|---|---|
| `public/data/past_seasons/Drafts/Drafts_2025.json` | `1414c1c08c770eeb55357ba3a49e9746b7409fb3` | Vollständige Pickreihenfolge, Pickbesitz und Trade-Historie |
| `fantasy-management/league-context/owner-registry.json` | `a3607f3645b27bdfe6228a7180fee7014d8744b4` | TeamID- und Managerzuordnung |
| `public/data/chat/players-relevant/players_0017.json` bis `players_0025.json` | Stand 13.07.2026 | PPR-Punkte, Spiele und Rookie-Year-Produktion |

## 4. Bewertungsmethode

Die Player-Outcomes werden positionsabhängig eingeordnet, da Quarterback-Punkte nicht direkt mit Wide Receiver-, Running Back- oder Tight-End-Punkten vergleichbar sind.

### Heuristische Rookie-Year-Buckets

| Position | Strong | Productive | Role / Promising |
|---|---:|---:|---:|
| QB | ab 180 | – | ab 80 |
| RB | ab 150 | ab 100 | ab 40 |
| WR | ab 170 | ab 100 | ab 50 |
| TE | ab 130 | ab 70 | ab 30 |

Diese Schwellen sind eine liga- und formatbezogene Auswertungshilfe, keine permanente Spielerbewertung.

Die Teamnote berücksichtigt:

- rohe Rookie-Year-Produktion;
- Produktion pro Pick;
- Anzahl klarer Hits;
- Pickslot-Effizienz;
- Positionswert in 2QB und 2TE;
- Vermeidung vollständig wertloser Picks.

## 5. Vollständige Draftübersicht nach Year-1-Outcome

| Pick | Team | Spieler | Pos. | Punkte | Spiele | Bucket | Outcome |
|---:|---|---|---|---:|---:|---|---:|
| 1.01 | Dennis | Ashton Jeanty | RB | 233,70 | 16 | Strong | A |
| 1.02 | Jan | Omarion Hampton | RB | 110,80 | 8 | Productive | B+ |
| 1.03 | Tim | TreVeyon Henderson | RB | 147,30 | 11 | Productive | A- |
| 1.04 | Robert | Colston Loveland | TE | 140,00 | 15 | Strong | A |
| 1.05 | Marcel | Travis Hunter | WR | 63,80 | 7 | Role / Injury Caveat | C+ |
| 1.06 | Flo | Cam Ward | QB | 191,48 | 16 | Strong | A |
| 2.01 | Dennis | Tetairoa McMillan | WR | 200,90 | 16 | Strong | A+ |
| 2.02 | Jan | RJ Harvey | RB | 117,80 | 8 | Productive | A- |
| 2.03 | Tim | Emeka Egbuka | WR | 193,90 | 16 | Strong | A+ |
| 2.04 | Robert | Tyler Warren | TE | 180,90 | 16 | Strong | A+ |
| 2.05 | Marcel | Kaleb Johnson | RB | 8,90 | 8 | Limited | D |
| 2.06 | Flo | Matthew Golden | WR | 68,20 | 13 | Role | B- |
| 3.01 | Dennis | Quinshon Judkins | RB | 169,80 | 14 | Strong | A+ |
| 3.02 | Jan | Bhayshul Tuten | RB | 30,60 | 5 | Limited | C- |
| 3.03 | Tim | Jayden Higgins | WR | 119,20 | 16 | Productive | A- |
| 3.04 | Flo | Tre' Harris | WR | 64,60 | 16 | Role | B- |
| 3.05 | Marcel | Mason Taylor | TE | 88,90 | 13 | Productive | B+ |
| 3.06 | Flo | Cam Skattebo | RB | 128,70 | 8 | Productive | A+ |
| 4.01 | Dennis | Shedeur Sanders | QB | 89,86 | 7 | Promising | B+ |
| 4.02 | Jan | Luther Burden | WR | 96,80 | 10 | Role | B |
| 4.03 | Tim | Jaxson Dart | QB | 228,18 | 13 | Strong | A+ |
| 4.04 | Robert | Kyle Williams | WR | 23,00 | 12 | Limited | C- |
| 4.05 | Marcel | Jack Bech | WR | 42,40 | 14 | Limited | C+ |
| 4.06 | Flo | Dylan Sampson | RB | 48,20 | 8 | Role | B |
| 5.01 | Dennis | Elijah Arroyo | TE | 37,90 | 13 | Role | B- |
| 5.02 | Jan | Terrance Ferguson | TE | 52,10 | 13 | Role | B |
| 5.03 | Tim | Jaydon Blue | RB | 7,30 | 2 | Limited | D |
| 5.04 | Robert | Pat Bryant | WR | 67,70 | 14 | Role | B+ |
| 5.05 | Marcel | Jalen Milroe | QB | -0,60 | 3 | Limited | D |
| 5.06 | Flo | Jacory Croskey-Merritt | RB | 139,40 | 16 | Productive | A+ |

## 6. Teamranking nach Year 1

| Rang | Team | Note | Score | Gesamtpunkte | Punkte pro Pick |
|---:|---|---:|---:|---:|---:|
| 1 | Dennis | A+ | 98 | 732,16 | 146,43 |
| 2 | Tim | A+ | 97 | 695,88 | 139,18 |
| 3 | Flo | A | 94 | 640,58 | 106,76 |
| 4 | Robert | A- | 90 | 411,60 | 102,90 |
| 5 | Jan | B | 82 | 408,10 | 81,62 |
| 6 | Marcel | C+ | 68 | 203,40 | 40,68 |

## 7. Teamanalysen

### 7.1 Dennis – Team DennisLACards

**Klasse:** Ashton Jeanty, Tetairoa McMillan, Quinshon Judkins, Shedeur Sanders, Elijah Arroyo.

Dennis erzielte die höchste rohe und pickbereinigte Rookie-Year-Ausbeute. Entscheidend war nicht nur Jeanty an 1.01, sondern die Tiefe der Treffer:

- McMillan produzierte an 2.01 bereits 200,9 Punkte.
- Judkins war mit 169,8 Punkten an 3.01 ein herausragender Pickslot-Outcome.
- Sanders lieferte an 4.01 bereits verwertbare 2QB-Produktion.
- Arroyo war der einzige Pick ohne klaren Unterschiedsspieler-Outcome, erreichte aber zumindest einen frühen TE-Rollenbereich.

**Year-1-Urteil:** Beste Gesamtklasse. Drei klare starke Hits plus ein vielversprechender später Quarterback.

### 7.2 Tim – Team TimpaBay

**Klasse:** TreVeyon Henderson, Emeka Egbuka, Jayden Higgins, Jaxson Dart, Jaydon Blue.

Tim lag nur knapp hinter Dennis, obwohl ein Pick praktisch keine Produktion lieferte. Dafür waren die übrigen vier außergewöhnlich stark:

- Egbuka erzielte 193,9 Punkte an 2.03.
- Higgins lieferte 119,2 Punkte an 3.03.
- Dart war mit 228,18 Punkten an 4.03 der beste reine Pickslot-Outcome des gesamten Drafts.
- Henderson produzierte trotz elf Spielen 147,3 Punkte.

**Year-1-Urteil:** Herausragende Klasse. Der Dart-Pick hebt sie auf A+-Niveau.

### 7.3 Flo – Just Bill

**Klasse:** Cam Ward, Matthew Golden, Tre' Harris, Cam Skattebo, Dylan Sampson, Jacory Croskey-Merritt.

Flo hatte mit sechs Picks das größte Volumen und verwandelte insbesondere späte Running Backs in enorme Produktion:

- Ward war ein sofortiger starker 2QB-Starter.
- Skattebo erzielte 128,7 Punkte in nur acht Spielen.
- Croskey-Merritt lieferte als letzter Pick des Drafts 139,4 Punkte.
- Golden, Harris und Sampson blieben zunächst in Rollenbereichen, waren aber keine vollständigen Nuller.

**Year-1-Urteil:** Sehr starke, breite Klasse. Die späten RB-Treffer sind das zentrale historische Signal.

### 7.4 Robert

**Klasse:** Colston Loveland, Tyler Warren, Kyle Williams, Pat Bryant.

Die Klasse ist ein gutes Beispiel dafür, weshalb das Ligaformat berücksichtigt werden muss:

- Loveland erzielte 140,0 Punkte.
- Warren erzielte 180,9 Punkte.
- Beide waren sofort starke Start-2-TE-Bausteine.
- Pat Bryant war an 5.04 mit 67,7 Punkten ein solider später WR-Outcome.
- Kyle Williams blieb mit 23,0 Punkten klar zurück.

Ohne historischen Team-Snapshot lässt sich nicht sicher beurteilen, wie stark der doppelte frühe TE-Fokus zum damaligen Kader passte. Rein im Outcome war er jedoch erfolgreich.

**Year-1-Urteil:** Zwei klare TE-Hits bei nur vier Picks ergeben eine starke Klasse.

### 7.5 Jan – Mammoth Marauders

**Klasse:** Omarion Hampton, RJ Harvey, Bhayshul Tuten, Luther Burden, Terrance Ferguson.

Jan investierte in den ersten drei Runden ausschließlich in Running Backs:

- Hampton und Harvey waren produktiv, allerdings in jeweils nur acht Spielen.
- Tuten blieb deutlich zurück.
- Burden zeigte eine brauchbare frühe WR-Rolle.
- Ferguson lieferte an 5.02 solide TE-Tiefe.

Die Klasse hatte keine vollständige Katastrophe, aber auch keinen starken positionsabhängigen Outcome-Bucket.

**Year-1-Urteil:** Solide und noch entwicklungsfähig, aber nach einem Jahr klar hinter den Topklassen.

### 7.6 Marcel – Ruhr Valley Packers

**Klasse:** Travis Hunter, Kaleb Johnson, Mason Taylor, Jack Bech, Jalen Milroe.

Mason Taylor war der klare positive Pick mit 88,9 Punkten an 3.05. Hunter zeigte in sieben Spielen brauchbare Produktion, ist wegen Verletzung und Sonderrolle aber noch nicht abschließend bewertbar.

Die restliche Klasse blieb schwach:

- Kaleb Johnson erzielte nur 8,9 Punkte.
- Bech blieb bei 42,4 Punkten.
- Milroe hatte keinen stabilen Starterpfad und kam auf -0,6 Punkte.

**Year-1-Urteil:** Niedrigste rohe und pickbereinigte Produktion der Liga. Die Klasse benötigt in Year 2 deutliche Entwicklung.

## 8. Die wichtigsten Pickslot-Values

### 1. Jaxson Dart an 4.03

228,18 Punkte in 13 Spielen auf der wertvollsten Ligaposition. Kein anderer Pick kombinierte einen so späten Slot mit vergleichbarer sofortiger Produktion.

### 2. Jacory Croskey-Merritt an 5.06

139,4 Punkte als letzter Pick des Drafts. Ein extremes Beispiel für die asymmetrische Upside später Running Backs.

### 3. Tetairoa McMillan an 2.01

200,9 Punkte über eine komplette Saison. Ein Premium-WR-Outcome außerhalb der ersten Runde.

### 4. Tyler Warren an 2.04

180,9 Punkte in einem Start-2-TE-Format. Der Ligaformatbonus machte diesen Pick besonders wertvoll.

### 5. Quinshon Judkins an 3.01

169,8 Punkte in 14 Spielen. Ein starker Running-Back-Hit deutlich außerhalb der ersten Runde.

### 6. Cam Skattebo an 3.06

128,7 Punkte in acht Spielen und ein sehr hoher Punkteschnitt. Verletzungen verhindern eine noch höhere Bewertung.

## 9. Die auffälligsten schwachen Outcomes

### Kaleb Johnson an 2.05

8,9 Punkte in acht Spielen waren der schwächste frühe Skill-Position-Outcome.

### Jalen Milroe an 5.05

Der niedrige Preis begrenzt den Schaden. Die Wahl zeigt aber, dass ein Quarterback in 2QB nicht allein wegen der Position wertvoll wird: Ohne realistischen Starterpfad entsteht keine Liquidität.

### Jaydon Blue an 5.03

Nur 7,3 Punkte in zwei Spielen. Als später RB-Dart war der Prozess möglicherweise vertretbar, der Year-1-Outcome war jedoch schwach.

### Kyle Williams an 4.04

23,0 Punkte trotz zwölf Einsätzen. Der Pick blieb klar hinter den später verfügbaren starken Outcomes zurück.

### Travis Hunter an 1.05

Die 63,8 Punkte wirken für einen frühen Pick schwach, werden aber durch nur sieben Spiele und die ungewöhnliche Zwei-Wege-Rolle relativiert. Er ist deshalb kein sauberer Bust-Call, sondern ein offener Review-Fall.

## 10. Ligaweite Erkenntnisse

### Quarterbacks

Der Draft zeigt die extreme Spannweite später Quarterbacks:

- Dart an 4.03 wurde ein Volltreffer.
- Sanders an 4.01 zeigte einen positiven frühen Pfad.
- Milroe an 5.05 erzeugte kaum Wert.

Die Position allein reicht nicht. Der unmittelbare oder zumindest realistisch entstehende Starterpfad bleibt entscheidend.

### Tight Ends

Das Start-2-TE-Format wurde 2025 deutlich belohnt:

- Loveland und Warren waren starke Hits.
- Mason Taylor war produktiv.
- Ferguson und Arroyo lieferten frühe Rollenproduktion.

Das spricht nicht dafür, jeden Tight End aggressiv zu ziehen. Es zeigt aber, dass echte Target-Earner- und Starterprofile in dieser Liga früher wertvoll werden können als in Standardformaten.

### Running Backs

Späte Running Backs lieferten enorme asymmetrische Outcomes:

- Skattebo an 3.06.
- Croskey-Merritt an 5.06.
- Judkins an 3.01.

Gleichzeitig scheiterten Tuten, Kaleb Johnson und Blue früh. Die Position besitzt hohe Varianz, weshalb mehrere günstige Pfeile oft besser sind als ein einzelner teurer rollenbasierter Reach.

### Wide Receiver

McMillan und Egbuka waren sofortige starke Hits. Higgins lieferte ebenfalls produktiv. Mehrere spätere WRs blieben dagegen nur in Rollenbereichen. Für eine 6-Team-Liga ist die Schwelle zur echten Startrelevanz besonders hoch.

## 11. Erste Managerbeobachtungen

Die folgenden Aussagen bleiben `candidate` beziehungsweise `low confidence`, weil nur ein Draft und kein vollständiger damaliger Teamkontext vorliegen:

- **Robert:** Frühe TE-Investitionen wurden im 2TE-Format unmittelbar belohnt.
- **Marcel:** Die breite Positionsverteilung führte nur bei Mason Taylor zu einem klar positiven Pickslot-Outcome.
- **Flo:** Zusätzliche Pickmenge und späte RB-Wetten erzeugten außergewöhnliche Upside.
- **Jan:** Der frühe RB-Fokus lieferte zwei produktive, aber keinen starken Rookie-Year-Outcome.
- **Dennis:** Premiumtalent und fallende Werte wurden über mehrere Runden erfolgreich kombiniert.
- **Tim:** Sowohl frühe Skill-Position-Spieler als auch der späte QB-Dart trafen außergewöhnlich gut.

Erst die Verbindung mit 2026 und späteren Drafts darf daraus stabilere Owner-Profile machen.

## 12. Nächste Reviews

| Review | Zieltermin | Schwerpunkt |
|---|---:|---|
| Year 2 | 13.07.2027 | Rollenstabilität, Wertentwicklung, Starterstatus und zweite Saison |
| Year 3 | 13.07.2028 | Langfristige Hits, Busts, Peak Value und Team-Ertrag |

Die ursprüngliche Retrospektive wird nicht überschrieben. Spätere Reviews werden als neue Dateien gespeichert und verweisen über `review_of` auf diese Analyse.