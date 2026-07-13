---
type: draft_analysis
scope: fantasy-management
created: 2026-07-13
status: active
draft_key: 2026_Rookie
analysis_kind: post_draft_contextual
context_completeness: full
team_context: League-wide
supersedes: null
validity_note: "Historische Post-Draft-Einschätzung mit Teamkontext zum 13.07.2026. Dynamische Rollen, Verletzungen und Marktwerte vor Wiederverwendung neu prüfen."
---

# Rookie-Draft-Analyse 2026

## 1. Zweck und Einordnung

Diese Datei friert den Draftprozess direkt nach Abschluss des Rookie-Drafts 2026 ein. Sie soll später drei voneinander getrennte Fragen beantworten helfen:

1. Welche Entscheidungen waren am Drafttag mit den verfügbaren Informationen sinnvoll?
2. Welche Manager wichen systematisch vom Markt oder von Sleeper ADP ab?
3. Welche Picks und Draftklassen entwickelten sich nach einem, zwei und drei Jahren tatsächlich gut?

Die maschinenlesbare Begleitdatei liegt unter:

`fantasy-management/analyses/2026/drafts/2026-07-13_2026-rookie-draft-postmortem.json`

## 2. Datengrundlage

| Quelle | Blob-SHA / Stand | Verwendung |
|---|---|---|
| `public/data/Drafts.json` | `4b49cbe9696a0a24765b87091e7c87567f7df299` | Draftreihenfolge, Ergebnisse, Pickbesitz und Trades |
| `public/data/League.json` | `600447dc3f4407132e946b1cbf6c47bdd4a66818` | Kader, Ligaformat, Teamfenster und Vorjahresleistung |
| `public/data/chat/players-relevant/index.json` | `46688b1e861259040b70043cb4398bd9c9788e2e` | Player-ID-, Positions- und Chunk-Zuordnung |
| Stoned Lack 570 | `d451bb4562f9e8c51282d316d3f556fc20b6ec59` | Qualitativer WR-, Rollen- und Opportunity-Kontext |
| Stoned Lack 571 | `d0b6ad7d8346e16b21911e3f164046a8a4d188b0` | Qualitativer RB-, Rollen- und Handcuff-Kontext |
| KeepTradeCut Rookie Rankings | abgerufen 13.07.2026 | Datierter Crowd-Marktvergleich |

Der KTC-Snapshot war Superflex, 0,5 PPR und standardmäßig ohne Tight-End-Premium. Er ist deshalb kein direktes Abbild dieser Liga, sondern nur ein Marktanker.

## 3. Liga- und Bewertungsrahmen

Die Liga besteht aus sechs Teams und startet 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K sowie 16 Bench-Spieler. Der hohe Replacement Level bedeutet:

- Premium-Ceiling ist wichtiger als bloße NFL-Rosterfähigkeit.
- Quarterbacks und Tight Ends erhalten durch feste Doppelstarterplätze einen echten Formatbonus.
- Running-Back- und Wide-Receiver-Tiefe bleibt wegen vier Flexplätzen relevant.
- Späte Picks sollten entweder ein klares Ceiling, knappe Positionsliquidität oder einen starken Rollenhebel besitzen.

### Grading-Modell

| Komponente | Gewicht | Bedeutung |
|---|---:|---|
| Process | 40 % | Qualität der Entscheidung mit den damals verfügbaren Informationen |
| Market Value | 25 % | Value relativ zum datierten Markt- und Consensus-Stand |
| Team Fit | 20 % | Passung zu Kader, Teamfenster und Positionsportfolio |
| Class Construction | 15 % | Komplementarität, Risikoverteilung und Liquidität der gesamten Klasse |

Spätere Outcomes werden separat bewertet. Ein guter Prozess bleibt ein guter Prozess, auch wenn ein Spieler später bustet. Ein schlechter Prozess wird nicht rückwirkend gut, nur weil ein Spieler unerwartet ausbricht.

## 4. Vollständige Draftübersicht

| Pick | Team | Spieler | Pos. | Markt-Rang | Delta | Grade |
|---:|---|---|---|---:|---:|---:|
| 1.01 | Tim | Carnell Tate | WR | 2 | -1 | A- |
| 1.02 | Robert | Jeremiyah Love | RB | 1 | +1 | A+ |
| 1.03 | Dennis | Jordyn Tyson | WR | 4 | -1 | A |
| 1.04 | Jan | Makai Lemon | WR | 5 | -1 | A |
| 1.05 | Marcel | Jadarian Price | RB | 6 | -1 | A- |
| 1.06 | Flo | Kenyon Sadiq | TE | 8 | -2 | A- |
| 2.01 | Tim | KC Concepcion | WR | 7 | 0 | A |
| 2.02 | Dennis | Fernando Mendoza | QB | 3 | +5 | A+ |
| 2.03 | Marcel | Eli Stowers | TE | 10 | -1 | A- |
| 2.04 | Jan | Jonah Coleman | RB | 13 | -3 | A- |
| 2.05 | Tim | Denzel Boston | WR | 12 | -1 | A- |
| 2.06 | Flo | Omar Cooper | WR | 9 | +3 | A |
| 3.01 | Tim | Eli Raridon | TE | 36 | -23 | C+ |
| 3.02 | Dennis | Nicholas Singleton | RB | 17 | -3 | B+ |
| 3.03 | Robert | Chris Bell | WR | 14 | +1 | A |
| 3.04 | Jan | Ty Simpson | QB | 11 | +5 | A |
| 3.05 | Jan | Antonio Williams | WR | 15 | +2 | A- |
| 3.06 | Flo | Germie Bernard | WR | 16 | +2 | B+ |
| 4.01 | Robert | Malachi Fields | WR | 21 | -2 | B+ |
| 4.02 | Dennis | Elijah Sarratt | WR | 19 | +1 | B |
| 4.03 | Robert | Kaytron Allen | RB | 24 | -3 | B+ |
| 4.04 | Jan | Oscar Delp | TE | 35 | -13 | C+ |
| 4.05 | Marcel | Mike Washington | RB | 30 | -7 | C+ |
| 4.06 | Flo | Emmett Johnson | RB | 23 | +1 | B+ |
| 5.01 | Tim | Ja'Kobi Lane | WR | 27 | -2 | B+ |
| 5.02 | Dennis | Chris Brazzell | WR | 25 | +1 | B+ |
| 5.03 | Robert | De'Zhaun Stribling | WR | 18 | +9 | A+ |
| 5.04 | Jan | Ted Hurst | WR | 22 | +6 | A- |
| 5.05 | Robert | Kaelon Black | RB | 34 | -5 | B |
| 5.06 | Flo | Drew Allar | QB | 33 | -3 | B- |

**Delta:** positiver Wert bedeutet, dass der Spieler später als sein Markt-Rang ausgewählt wurde. Ein negatives Delta zeigt einen Pick vor dem neutralen Marktbereich.

## 5. Gesamtgrading

| Rang | Team | Note | Score | Kernaussage |
|---:|---|---:|---:|---|
| 1 | Dennis | A | 95 | Zwei Premiumassets und der beste QB-Value des Drafts |
| 2 | Mighty Giants | A- | 92 | Klassen-RB1 plus mehrere passende Upside-Wetten |
| 3 | Jan | A- | 90 | Tiefste und ausgewogenste Klasse, aber ein klarer TE-Reach |
| 4 | Tim | B+ | 87 | Sehr starke WR-Spitze, Raridon mit hohem Opportunity Cost |
| 5 | Flo | B+ | 86 | Formatgerecht, ausgewogen und ohne gravierenden Fehler |
| 6 | Marcel | B | 82 | Zwei starke Kernpicks, aber nur drei Picks und ein Handcuff-Reach |

## 6. Teamanalysen

### 6.1 Dennis – Team DennisLACards

**Kontext:** Vorjahresletzter mit 4-9 und 170,8 Punkten pro Spiel. Der Kader besaß junge Premiumbausteine, brauchte aber zusätzliche langfristige QB- und WR-Anker.

**Picks:** Jordyn Tyson, Fernando Mendoza, Nicholas Singleton, Elijah Sarratt, Chris Brazzell.

**Stärken:**

- Tyson ist ein echter junger WR-Kernbaustein.
- Mendoza an 2.02 war der beste positions- und marktbezogene Value des Drafts.
- Der Pick löst langfristig die Altersfrage hinter Herbert und Nix deutlich besser als ein weiterer mittlerer Skill-Position-Spieler.
- Singleton bringt einen zusätzlichen jungen RB-Ausgang in einen ansonsten alters- und rollenabhängigen Backfield-Mix.
- Sarratt und Brazzell diversifizieren die WR-Wetten, ohne teures Kapital zu verbrennen.

**Risiken:**

- Die letzten drei Picks sind eher Portfolio-Ergänzungen als sichere Difference Maker.
- Der Draft verbessert Dennis langfristig stärker als kurzfristig.

**Urteil:** Beste Klasse des Drafts, weil Tyson und Mendoza die wertvollsten strukturellen Probleme des Kaders lösen.

### 6.2 Robert – Mighty Giants

**Kontext:** Vorjahres-Regular-Season-Sieger mit 10-3 und 190,17 Punkten pro Spiel. Elite auf QB, WR und TE; der größte Portfoliobedarf lag bei jungen Running Backs und zusätzlichen liquiden Upside-Assets.

**Picks:** Jeremiyah Love, Chris Bell, Malachi Fields, Kaytron Allen, De'Zhaun Stribling, Kaelon Black.

**Stärken:**

- Love ist der perfekte Premium-Pick für einen Contender mit außergewöhnlicher WR-Tiefe.
- Bell war preisgerecht und besitzt echtes Outside-WR-Ceiling.
- Stribling an 5.03 war der beste Late-Round-Value des Drafts.
- Love, Allen und Black bilden drei unterschiedliche RB-Auszahlungspfade: Premiumtalent, Goal-Line-Rolle und Contingent-Upside.
- Die Klasse verbindet unmittelbares Contender-Ceiling mit langfristiger Jugend.

**Risiken:**

- Fields, Allen und Black lagen leicht vor dem neutralen Marktbereich.
- Black über Zachariah Branch tauschte Marktliquidität gegen besseren teambezogenen RB-Fit.
- Die WR-Tiefe bleibt so groß, dass selbst erfolgreiche Bell-, Fields- oder Stribling-Outcomes zunächst eher Trade-Liquidität als Startzwang erzeugen.

**Urteil:** Bester Contender-Draft. Keine Bestnote, weil der letzte Pick bewusst vom stärkeren neutralen Marktasset wegführte.

### 6.3 Jan – Mammoth Marauders

**Kontext:** Elite-QB- und Elite-WR-Kern mit sehr tiefem Kader und hohem Roster-Druck. Die Klasse sollte Ceiling über mehrere Positionen verteilen.

**Picks:** Makai Lemon, Jonah Coleman, Ty Simpson, Antonio Williams, Oscar Delp, Ted Hurst.

**Stärken:**

- Lemon, Coleman, Simpson und Antonio bilden eine sehr tiefe Spitzengruppe.
- Simpson an 3.04 war starker 2QB-Marktvalue.
- Antonio war ein klarer eigener Target-Pick mit plausiblem frühen Slot-/WR2-Pfad.
- Hurst war spät ein guter Marktvalue.
- Die Klasse verteilt Upside auf WR, RB, QB und TE.

**Risiken:**

- Delp an 4.04 war deutlich vor dem Standardmarkt und hatte hohe Opportunity Costs.
- Sechs neue Rookies verschärfen den bereits bestehenden Konsolidierungs- und Cut-Druck.

**Urteil:** Sehr guter, eigenständiger Draft. Jans Entscheidungen zeigen klar, dass er nicht blind nach Sleeper ADP arbeitet.

### 6.4 Tim – Team TimpaBay

**Kontext:** Starker QB- und RB-Kern, aber schwächere Vorjahresproduktion und ein klarer Bedarf an jungem WR-Ceiling.

**Picks:** Carnell Tate, KC Concepcion, Denzel Boston, Eli Raridon, Ja'Kobi Lane.

**Stärken:**

- Tate, Concepcion und Boston bilden die stärkste reine WR-Spitze einer Klasse.
- Tate über Love war aus dem konkreten Kaderkontext vertretbar.
- Concepcion an 2.01 traf Markt und Need exakt.
- Lane war ein sinnvoller später Outside-WR-Dart.

**Risiken:**

- Raridon an 3.01 war der größte Standardmarkt-Reach des Drafts.
- Der 2TE-Faktor hilft, aber Tim hatte bereits starke Tight-End-Tiefe; mehrere hochwertigere WR-, RB- und QB-Assets waren noch verfügbar.
- Die Klasse ist sehr stark von mehreren WR-Entwicklungen abhängig.

**Urteil:** A-Klasse an der Spitze, aber kein A-Draft insgesamt.

### 6.5 Flo – Just Bill

**Kontext:** Amtierender Champion und punktbestes Team der Vorsaison. Kein akuter Need; formatgerechte Knappheits- und Upside-Picks waren sinnvoll.

**Picks:** Kenyon Sadiq, Omar Cooper, Germie Bernard, Emmett Johnson, Drew Allar.

**Stärken:**

- Sadiq ist in dieser Liga wertvoller als im Standardmarkt.
- Cooper an 2.06 war ein sauberer WR-Value.
- Bernard bietet einen frühen Snap-Pfad.
- Emmett Johnson ergänzt einen interessanten RB-Dart in einer attraktiven Offense.
- Allar ist als letzter Pick ein vertretbarer 2QB-Stash.

**Risiken:**

- Kein Spieler aus dem absoluten Markt-Top-7-Bereich.
- Allar besitzt keinen bestätigten unmittelbaren Starterpfad und ist deshalb nur ein langfristiger Stash.

**Urteil:** Solider Champion-Draft ohne Panik und ohne groben Fehler.

### 6.6 Marcel – Ruhr Valley Packers

**Kontext:** Runner-up mit starkem Veteranenkern, aber nur drei Picks. Altersabsicherung bei RB und TE war sinnvoll.

**Picks:** Jadarian Price, Eli Stowers, Mike Washington.

**Stärken:**

- Price war der klare zweite RB der Klasse und ein guter langfristiger Henry-Nachfolger.
- Stowers war im Start-2-TE-Format mindestens preisgerecht.
- Die Klasse adressierte echte Alters- und Positionsfragen.

**Risiken:**

- Nur drei Picks begrenzen die Gesamtchance auf mehrere Hits.
- Washington an 4.05 war ein deutlich früher Handcuff-/Trade-Chip-Pick.
- Stribling, Branch, Brazzell und Hurst waren zu diesem Zeitpunkt liquidere Alternativen.

**Urteil:** Zwei gute Kernpicks, aber zu wenig Volumen und zu hoher Opportunity Cost beim dritten Pick.

## 7. Ligaweite Muster

### 7.1 Quarterbacks

Mendoza an 2.02 und Simpson an 3.04 waren starke 2QB-Values. Allar an 5.06 war nur deshalb vertretbar, weil der Preis niedrig war. Für spätere Drafts sollte beobachtet werden, ob die Liga regelmäßig unmittelbare Starterrollen unterschätzt und gleichzeitig Entwicklungs-QBs zu optimistisch behandelt.

### 7.2 Tight Ends

Sadiq und Stowers waren formatgerecht. Raridon und Delp zeigen dagegen, dass das Start-2-TE-Format nicht jeden beliebigen Reach rechtfertigt. Der richtige Vergleich ist nicht Standard-KTC allein, sondern:

- realistische Route Participation,
- Target-Earner-Potenzial,
- NFL-Draftkapital,
- Konkurrenz,
- und der konkrete Opportunity Cost.

### 7.3 Running Backs

Nach Love und Price wurde die dünne Klasse sichtbar aggressiv behandelt. Coleman, Singleton, Allen, Washington, Emmett Johnson und Black gingen teilweise vor neutralen WR-Marktwerten. Das ist in einer RB-knappen Liga erklärbar, sollte aber in späteren Reviews auf tatsächliche Rollen- und Wertspikes geprüft werden.

### 7.4 Wide Receiver

Die stärksten späten Values waren:

1. De'Zhaun Stribling an 5.03
2. Ted Hurst an 5.04
3. Chris Brazzell an 5.02
4. Ja'Kobi Lane an 5.01

Zachariah Branch blieb trotz eines Marktbereichs um Rookie 20 ungedraftet und ist damit ein wichtiger Referenzspieler für die spätere Beurteilung von Black, Washington und mehreren TE-Reaches.

## 8. Draft-Auszeichnungen

| Kategorie | Gewinner |
|---|---|
| Beste Gesamtklasse | Dennis |
| Bester Einzelpick | Fernando Mendoza an 2.02 |
| Bestes Premiumasset | Jeremiyah Love |
| Bester Late-Value | De'Zhaun Stribling an 5.03 |
| Tiefste Klasse | Jan |
| Beste formatbezogene Wahl | Kenyon Sadiq an 1.06 |
| Größter Reach | Eli Raridon an 3.01 |
| Zweitgrößter Reach | Oscar Delp an 4.04 |
| Größter ungedrafteter Marktname | Zachariah Branch |

## 9. Managerbeobachtungen

Diese Beobachtungen sind noch keine permanenten Profile. Sie sind in der JSON-Datei als `provisional` hinterlegt und müssen durch weitere Drafts, Trades oder Entscheidungen bestätigt werden.

- **Robert:** Passt die Positionsstrategie sichtbar an den eigenen Kader an, statt dauerhaft eine Position zu bevorzugen.
- **Marcel:** Investiert wiederholt in RB- und TE-Profile und akzeptiert rollenbasierte Handcuff-Wetten.
- **Flo:** Verteilt Kapital breit über knappe Positionen und mehrere Upside-Pfade.
- **Jan:** Arbeitet mit eigenem Board, kombiniert Consensus-Value mit persönlichen Targets und ist bereit, Tight Ends deutlich vor dem Standardmarkt zu nehmen.
- **Dennis:** Sammelt Premiumtalent und nutzt fallende Quarterback-Werte aggressiv.
- **Tim:** Priorisiert wiederholt junge Wide Receiver und ergänzt mit einzelnen QB-, TE- oder RB-Wetten.

## 10. Follow-ups

Die ursprüngliche Analyse bleibt unverändert. Spätere Reviews werden als neue Dateien gespeichert und verweisen über `review_of` auf diese Post-Draft-Analyse.

| Review | Zieltermin |
|---|---:|
| Year 1 | 13.07.2027 |
| Year 2 | 13.07.2028 |
| Year 3 | 13.07.2029 |

Besonders relevante spätere Vergleichsfragen:

- Black gegen Branch
- Raridon gegen die an 3.01 verfügbaren Alternativen
- Delp gegen Stribling, Brazzell und Branch
- Mendoza und Simpson als 2QB-Values
- Allen, Washington, Emmett Johnson und Black als Rollen-RBs
- Stribling als später Markt- und Draftkapital-Value
