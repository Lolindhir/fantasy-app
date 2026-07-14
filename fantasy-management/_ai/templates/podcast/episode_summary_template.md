# {{source_name}} {{episode_number}} – {{title}}

> Dieses Template ist ein Baukasten, keine starre Gliederung. Verwende nur passende Abschnitte, ergänze notwendige eigene Überschriften und passe Reihenfolge sowie Tiefe an die tatsächliche Folge an.

## Worum geht es in der Folge?

Ordne Thema, Anlass, Format und zentrale Fragestellung der Folge ausführlich ein. Beschreibe ausschließlich den Podcast-Inhalt und seine Fantasy-Relevanz, nicht den Extraktionsprozess.

Die Einleitung soll Leserinnen und Leser in die Folge hineinholen. Sie darf Formatbegriffe wie Dynasty, Redraft, Rookie Draft, Bestball, PPR oder Return-Yards erklären, wenn diese für das Verständnis der Aussagen wichtig sind.

## Zentrale Aussagen und Bewertungslogik der Hosts

Erkläre nicht nur die Ergebnisse, sondern auch, wie die Hosts argumentieren. Relevante Kriterien können beispielsweise sein:

- Talent und Prospect-Profil
- Landing Spot und Teamumfeld
- Rolle, Snaps, Targets oder Touches
- Draft Capital
- Coaching und Scheme
- Konkurrenz und Depth Chart
- Verletzungen
- Redraft im Vergleich zu Dynasty
- Rookie Draft, Bestball oder andere Formate
- Scoring-Besonderheiten
- Marktpreis oder ADP

Halte unterschiedliche Host-Meinungen, Abwägungen und Unsicherheiten ausdrücklich fest. Eine reine Ergebnisliste reicht nicht aus.

## {{episode_specific_section}}

Nutze für die tatsächlichen Inhalte passende Abschnitte, zum Beispiel News-Blöcke, Teams, Positionsgruppen, Interviews, Strategiethemen, Mock-Draft-Runden oder Debatten.

News und Nebenthemen sollen nicht nur aufgezählt werden. Erkläre die Argumentation, den positiven Case und die Risiken, sofern die Folge dazu substanziellen Inhalt liefert.

## Vollständiges Ranking / Board / Tierstruktur

Diesen Abschnitt nur verwenden, wenn die Folge eine Rangfolge, Tiers, Kategorien, einen Mock Draft oder eine vergleichbare Ordnung enthält.

Rekonstruiere die vollständige Quellstruktur so sicher wie möglich. Markiere unklare Reihenfolgen statt sie zu erfinden.

| Rang / Tier | Entity | Podcast-Einschätzung | Zentrale Begründung | Risiko / Unsicherheit |
|---|---|---|---|---|
| {{rank_or_tier}} | {{entity}} | {{source_view}} | {{reason}} | {{risk}} |

## Ausführliche Profile und Themenblöcke

Erstelle für jeden wichtigen oder gerankten Gegenstand ausreichend ausführliche Abschnitte. Spieler sind ein häufiger Fall, aber Teams, Coaches, Positionsgruppen oder strategische Fragen können ebenso die passende Haupteinheit sein.

Ein Profil soll möglichst die vollständige Argumentationskette der Quelle bewahren und nicht nur einen komprimierten Ein-Satz-Take wiederholen.

### {{entity_name}}

**Einordnung der Quelle:** {{sentiment_tier_or_role}}

**Rolle im Podcast-Board:** {{ranking_tier_sleeper_fade_news_or_other}}

#### Begründung aus dem Podcast

- {{reason_1}}
- {{reason_2}}
- {{reason_3}}

#### Positiver Case

- {{positive_1}}
- {{positive_2}}
- {{positive_3}}

#### Risiken, Gegenargumente und offene Punkte

- {{risk_1}}
- {{risk_2}}
- {{risk_3}}

#### Host-Differenzen oder Formatabhängigkeit

Beschreibe Unterschiede zwischen Hosts, kurzfristiger und langfristiger Sicht oder verschiedenen Fantasy-Formaten, sofern vorhanden. Lasse diesen Unterabschnitt weg, wenn die Quelle keine entsprechende Differenz erkennen lässt.

## Team-, Depth-Chart- und Scheme-Kontext

Fasse fantasy-relevante Teamumfelder, Konkurrenten, Coaches und Nutzungsideen in lesbarer Form zusammen, wenn sie mehrere Takes verbinden oder für das Verständnis des Boards wichtig sind.

Dieser Abschnitt ist inhaltlicher Podcast-Kontext. Er ist kein Entity-Register und enthält keine Alias-, Coverage- oder Extraktionsdaten.

## Fantasy-Strategie der Quelle

Bereite Aussagen zu Rookie Drafts, Redraft, Dynasty, Bestball, Waivers, Trades, Marktwert, ADP oder Scoring ausführlich und source-nah auf.

Erkläre insbesondere, wie die Tiefe einer Klasse, Positionsknappheit, frühe Rollen, Return-Scoring oder Marktpreise die von den Hosts vorgeschlagene Strategie verändern.

## Source-abgeleitete Schlusslisten nach Kriterien

Diesen Abschnitt flexibel verwenden, wenn die Folge genug Material dafür liefert. Mögliche, aber nicht verpflichtende Perspektiven sind:

- höchste Host-Conviction
- beste Opportunity
- bestes Talent oder Upside
- stärkste Sofortrolle
- stärkste langfristige Profile
- beste Redraft- oder Dynasty-Signale
- Sleeper und Dart Throws
- formatabhängige Spezialfälle
- größte Risiken, Fades oder Unsicherheiten
- wichtigste Host-Unstimmigkeiten

Nur Listen erstellen, die durch Aussagen der Folge gestützt werden. Keine eigenen Rankings erfinden.

## Fazit der Podcast-Folge

Fasse ausführlich zusammen, welche Gesamtbotschaft und welche wichtigsten source-nahen Aussagen die Folge vermittelt. Das Fazit darf die zentralen Namen und strategischen Schlussfolgerungen der Hosts bündeln, bleibt aber innerhalb der Quellenperspektive.

## Klare Trennung der Lesefassung

`episode.md` ist ausschließlich die ausführliche menschenlesbare Aufbereitung des Podcast-Inhalts.

Nicht aufnehmen:

- Rohformen oder Transkript-Aliase als Register
- Entity-Resolution-Status
- vollständige Mention- oder Coverage-Tabellen
- Take- oder Mention-IDs
- Timestamps als technische Nachweisstruktur
- Dateilisten und Package-Pfade
- Extraktions-, Review- oder Validatorstatus
- Referenzen auf maschinenlesbare Begleitdateien
- Knowledge-Ableitungen
- Mighty-Giants-Empfehlungen
- eigene Ligaempfehlungen, die nicht aus dem Podcast stammen

Diese technischen Informationen gehören ausschließlich in `takes.json`, `mentions.json` und `index.json`. Namen von Spielern, Teams, Coaches und anderen Entitäten erscheinen in `episode.md` nur dort, wo sie für den verständlichen Inhalt der Folge relevant sind.