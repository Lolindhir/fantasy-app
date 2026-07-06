---
type: podcast_episode_note
scope: fantasy-management
source_id: {{source_id}}
episode_id: {{episode_id}}
episode_number: {{episode_number}}
title: "{{title}}"
published_date: {{published_date}}
processed_date: {{processed_date}}
language: de
status: {{status}}
validity_note: "Quellenextraktion; keine finale Mighty-Giants-Empfehlung. Vor Entscheidungen aktuelle Liga-, Markt- und Depth-Chart-Daten prüfen."
companion_files:
  - {{episode_id}}.json
  - {{episode_id}}_player_data.json
  - {{episode_id}}_take_index.md
---

# {{source_name}} {{episode_number}} – {{title}}

**Aufbereitete Datengrundlage für Fantasy-/Dynasty-Analyse**

## 1. Quellenhinweis und Bereinigung

**Quelle:** {{source_description}}  
**Thema:** {{episode_topic}}  
**Aufbereitung:** Das Rohmaterial wurde inhaltlich ausgewertet, Namens-/Transkriptfehler wurden markiert und die Folge wurde in menschenlesbare Analyse plus maschinenlesbare Begleitdaten überführt.

> Hinweis: Diese Datei ist die Quellenperspektive von {{source_name}}, keine finale Mighty-Giants-Empfehlung.

Raw-Quelle:

`{{raw_path_or_manifest}}`

Bei gesplittetem Raw-Transkript: Die Manifest-Datei listet die Parts in der richtigen Reihenfolge. Die geordnete Verkettung der Parts ist die Raw-Quelle.

## 2. Interpretation der Folge

Beschreibe hier, was für eine Folge es ist:

- Ranking-Folge
- Draft-/Landing-Spot-Review
- News-/ADP-Folge
- Redraft-/Bestball-/Dynasty-Preview
- Strategie-/Meta-Folge
- Mixed Topics

Erkläre, wie die Aussagen für Fantasy und speziell Dynasty zu lesen sind.

## 3. Zentrale Quellenlogik / Bewertungsphilosophie

Extrahiere die wichtigsten Bewertungsprinzipien der Quelle.

Beispiele:

1. Opportunity vs. Talent
2. Draft Capital
3. Redraft vs. Dynasty
4. Rollenpfad / Depth Chart
5. Formatabhängigkeit
6. Injury-/News-Kontext
7. Markt-/ADP-Kontext

## 4. Bereinigte Rankings, Tiers oder Board-Logik

Nutze diesen Abschnitt nur, wenn die Folge Rankings, Tiers, Boards oder klare Gruppierungen enthält.

| Rang / Tier | Spieler / Entity | Pos | Team | Quellen-Einschätzung |
|---:|---|---:|---:|---|
| 1 | {{player}} | {{pos}} | {{team}} | {{summary}} |

## 5. Quellen-Favoriten nach Kategorie

Nutze Kategorien, die aus der Folge wirklich ableitbar sind. Nicht künstlich füllen.

### Höchste Conviction

1. {{entity}}

### Beste Opportunity Plays

1. {{entity}}

### Beste Redraft-/Sofortsignale

1. {{entity}}

### Beste Dynasty-/Langfrist-Signale

1. {{entity}}

### Caution / Fade / Avoid Buckets

1. {{entity_or_bucket}}

## 6. Spieler- oder Entity-Profile

Für alle High-Signal-Spieler/-Entities ein ausführliches Profil erstellen.

## {{player_or_entity_name}}

**Tier:** {{tier}}  
**Podcast-Rolle:** {{source_role}}  
**Sentiment:** {{sentiment}}

### Begründung aus Podcast-Kontext

- {{source_argument_1}}
- {{source_argument_2}}

### Positiv

- {{positive_1}}
- {{positive_2}}

### Negativ / Risiko

- {{risk_1}}
- {{risk_2}}

### Analyse-Tags

`{{tag_1}}`, `{{tag_2}}`, `{{tag_3}}`

---

## 7. Strategie- und Formatnotizen

Extrahiere wiederverwendbare Strategie- und Format-Takes.

- Dynasty
- Rookie Draft
- Redraft
- Bestball
- 2QB / Superflex
- 2TE
- 4Flex
- Return-Scoring
- 6-Team-Liga / hoher Replacement-Level

## 8. Unklare Namen / Entity-Fragen

| Originalform im Transkript | Vermutete Entity | Team | Pos | Vertrauen | Notiz |
|---|---|---:|---:|---:|---|
| {{raw_form}} | {{canonical_guess}} | {{team}} | {{pos}} | {{confidence}} | {{note}} |

## 9. Reuse für Mighty Giants

Beschreibe knapp, wie die Folge später verwendet werden kann:

- Rookie Board
- Trade-Kontext
- Waiver-/Free-Agent-Kontext
- Roster Audit
- Player Watchlist
- Source Comparison

Nicht als finale Empfehlung verwenden. Vor Entscheidungen immer mit aktuellem Roster, Pick Ownership, Ligaformat, Salary-/Cap-Kontext, aktuellen Rankings/Marktwerten und News kombinieren.

## 10. Kurzfazit der Quelle

Fasse die wichtigsten Source-Takes in wenigen Bullets zusammen.

- {{key_take_1}}
- {{key_take_2}}
- {{key_take_3}}

## 11. Verknüpfte maschinenlesbare Daten

- Episode JSON: `{{episode_json_path}}`
- Player/Entity Data: `{{player_data_path}}`
- Take Index: `{{take_index_path}}`
- Atomic Takes: `{{take_path_pattern}}`
- Optional Current Source View: `{{current_source_view_path}}`
