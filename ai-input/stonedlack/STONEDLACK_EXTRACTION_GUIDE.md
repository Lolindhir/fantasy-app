# StonedLack Extraction Guide

**Zweck:**  
Diese Datei beschreibt ein stabiles Extraktionsformat für StonedLack-Podcast-Transkripte.  
Ziel ist, aus jeder Folge eine wiederverwendbare Datenbasis für spätere Dynasty-/Fantasy-Football-Analysen, Meta-Rankings und AI-gestützte Auswertungen zu erzeugen.

Stand: 2026-06-21

---

## 1. Grundprinzip

Jede Podcastfolge wird in **drei Ebenen** dokumentiert:

1. **Raw-Transkript**  
   Das unbearbeitete Transkript wird möglichst unverändert gespeichert.  
   Es dient als Primärquelle und Audit-Trail.

2. **Lesbare Markdown-Quellennotiz**  
   Eine sauber strukturierte Zusammenfassung der Folge mit Kapiteln, Themen, Spielern, Takes, Rankings, Sleepern, Strategien und Unsicherheiten.

3. **Maschinenlesbares JSON-Datenfile**  
   Eine JSON-Datei mit atomisierten Takes, Entity-Mappings, Tiers, Rankings und Bewertungsfeldern.

Wichtig:  
Nicht jede Folge hat einen Positionsfokus. Deshalb darf das Format nicht nur auf `WR`, `RB`, `Rookie Rankings` usw. ausgelegt sein.  
Das zentrale Objekt ist immer der **Take**: eine konkrete Fantasy-/Dynasty-Aussage aus der Folge.

---

## 2. Ziel-Dateipfade pro Folge

Eine transkribierende AI soll alle erzeugten Dateien direkt an die passenden Repo-Pfade schreiben.

### 2.1 Standardpfade

```text
raw_transcripts/YYYY/YYYY-MM-DD_sl_EPISODE_slug.raw.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.json
```

### 2.2 Beispiel

```text
raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.json
```

### 2.3 Slug-Regeln

Der `slug` soll kurz und stabil sein:

- Kleinbuchstaben
- Wörter mit `_` trennen
- keine Umlaute
- keine Sonderzeichen
- thematisch beschreibend

Beispiele:

- `rookie_wr_ranking`
- `rookie_rb_ranking`
- `startup_mock`
- `nfl_news_adp`
- `redraft_preview`
- `week_1_reactions`

---

## 3. Raw-Transkript-Regeln

Das Raw-Transkript ist die Primärquelle und darf nicht inhaltlich bereinigt werden.

### 3.1 Was erhalten bleiben muss

- Kapitelüberschriften
- Timestamps
- automatische Transkriptfehler
- Wiederholungen
- Füllwörter
- Off-Topic-Passagen
- erkannte Sprecherwechsel, falls vorhanden

### 3.2 Was ergänzt werden darf

Nur ein YAML-Frontmatter-Block am Anfang:

```yaml
---
episode_id: sl_0571
episode_number: 571
source_name: StonedLack
source_type: youtube_transcript
published_date: 2026-05-11
processed_date: 2026-06-21
language: de
raw_transcript_status: verbatim_user_paste
notes:
  - "Automatisches YouTube-Transkript; Namen können fehlerhaft sein."
---
```

Danach folgt das Transkript unverändert.

### 3.3 Raw-Datei nie überschreiben

Wenn später ein besseres Transkript vorliegt, eine neue Version speichern:

```text
raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.v2.md
```

Im JSON dann `raw_transcript_version` entsprechend setzen.

---

## 4. Aufgaben der transkribierenden AI

Wenn ein neues Transkript geliefert wird, soll die AI eigenständig:

1. Podcast-Metadaten erkennen oder aus dem Kontext ableiten.
2. Raw-Transkript unverändert unter `raw_transcripts/YYYY/` speichern.
3. Kapitel und Themenblöcke identifizieren.
4. Spieler-, Team-, Coach-, Format- und Strategie-Erwähnungen extrahieren.
5. Fehlerhafte Transkript-Namen bereinigen.
6. Namen gegen reale NFL-/College-/Fantasy-Kontexte mappen.
7. Explizite Rankings, Tiers, Sleeper, Buy/Sell/Fade/Watch-Takes extrahieren.
8. Implizite Takes nur markieren, wenn sie klar aus dem Gespräch folgen.
9. Jede relevante Aussage mit Kontext, Argumenten, Risiken und Unsicherheit speichern.
10. Zwischen Host-Aussage und eigener Interpretation unterscheiden.
11. Markdown-Quellennotiz unter `episodes/YYYY/` erzeugen.
12. JSON-Datenfile unter `episodes/YYYY/` erzeugen.
13. Optional Alias-/Index-Dateien aktualisieren.

---

## 5. Wichtige Regel: Nicht halluzinieren

Die AI darf keine fehlenden Details erfinden.

Wenn etwas unklar ist:

- `unknown` verwenden.
- `unresolved` verwenden.
- Extraktionssicherheit als `low` markieren.
- In der Markdown-Datei unter „Offene Punkte / Unsicherheiten“ aufführen.

Beispiel:

```json
{
  "team": "unknown",
  "verification_status": "unverified",
  "extractor_confidence": "low"
}
```

---

## 6. Namensbereinigung und Entity Resolution

Automatische YouTube-Transkripte sind bei Namen oft fehlerhaft.  
Die AI muss alle Namen bereinigen und mappen.

### 6.1 Vorgehen

Für jeden relevanten Namen:

1. Originalform aus dem Transkript speichern.
2. Phonetische Varianten erkennen.
3. Kontext nutzen:
   - Position
   - Team
   - College
   - NFL-Draft-Runde
   - Landing Spot
   - Mitspieler
   - gegnerische oder erwähnte Konkurrenz
4. Gegen aktuelle Quellen prüfen, wenn verfügbar.
5. Canonical Name speichern.
6. Confidence setzen.

### 6.2 Empfohlene Quellen zur Verifikation

Priorität:

1. Offizielle NFL-Teamseiten
2. NFL.com Draft Tracker
3. Offizielle College-/Athletics-Seiten
4. Pro Football Reference / Sports Reference
5. ESPN / Sleeper / FantasyPros / KeepTradeCut nur für Fantasy-Kontext, nicht als primäre Identitätsquelle

### 6.3 Entity-Felder

```json
{
  "entity_id": "player_kaelon_black",
  "canonical_name": "Kaelon Black",
  "entity_type": "player",
  "position": "RB",
  "team": "San Francisco 49ers",
  "college": "Indiana",
  "transcript_mentions": ["Ken Black", "Kill Black", "Kellen Black"],
  "verification_status": "verified",
  "verification_sources": [
    {
      "name": "NFL.com Draft Tracker",
      "url": "https://www.nfl.com/draft/tracker/2026/prospects/rb_all",
      "accessed_at": "YYYY-MM-DD"
    }
  ],
  "entity_confidence": "high",
  "notes": "Transkript phonetisch stark verzerrt."
}
```

---

## 7. Take-Modell

Ein **Take** ist die zentrale Dateneinheit.

Ein Take ist z. B.:

- „Breece Hall verkaufen“
- „Antonio Williams ist ein Sleeper“
- „Jeremiyah Love ist Dynasty-RB1, aber Redraft zu teuer“
- „KC Concepcion könnte schneller Targets sehen als Makai Lemon“
- „Tucker Kraft ist Top-10-TE trotz möglicher verpasster Spiele“
- „Return-Yards machen Barion Brown interessant“
- „In diesem Rookie Draft ist Pick 1.07 besonders unangenehm“

### 7.1 Take-Typen

Erlaubte Werte für `take_type`:

- `player_evaluation`
- `ranking`
- `tier`
- `sleeper`
- `buy`
- `sell`
- `hold`
- `fade`
- `watchlist`
- `trade_strategy`
- `draft_strategy`
- `rookie_draft_value`
- `redraft_value`
- `bestball_value`
- `dynasty_value`
- `injury_reaction`
- `depth_chart_projection`
- `role_projection`
- `coaching_scheme`
- `news_reaction`
- `market_adp`
- `format_note`
- `league_settings_note`
- `meta_strategy`
- `uncertainty`
- `other`

### 7.2 Fantasy-Kontext

Erlaubte Werte für `fantasy_context`:

- `dynasty`
- `rookie_draft`
- `startup`
- `redraft`
- `bestball`
- `waiver`
- `trade`
- `devy`
- `general_fantasy`
- `real_football`
- `unknown`

Mehrere Werte sind möglich.

### 7.3 Format-Kontext

Mögliche Werte für `league_format_context`:

- `PPR`
- `half_PPR`
- `standard`
- `superflex`
- `1QB`
- `TE_premium`
- `return_yards`
- `IDP`
- `bestball`
- `deep_rosters`
- `taxi_squad`
- `unknown`

### 7.4 Bewertungsskalen

#### Sentiment

- `very_positive`
- `positive`
- `mixed`
- `cautious`
- `negative`
- `very_negative`
- `neutral`

#### Conviction

- `very_high`
- `high`
- `medium`
- `low`
- `very_low`

#### Action

- `draft`
- `reach`
- `buy`
- `sell`
- `hold`
- `fade`
- `avoid`
- `watch`
- `stash`
- `handcuff`
- `trade_for`
- `trade_away`
- `do_not_overpay`
- `no_action`
- `unknown`

#### Time Horizon

- `immediate`
- `early_season`
- `full_season`
- `long_term`
- `multi_year`
- `unknown`

---

## 8. Evidence-Regel

Jeder wichtige Take soll Evidence enthalten.

Evidence kann sein:

1. **kurzer Originalausschnitt** aus dem Transkript  
2. **paraphrasierte Aussage** mit Timestamp  
3. **Kapitel-/Zeitbereich**

Keine langen Zitate verwenden. Lieber paraphrasieren.

Beispiel:

```json
{
  "evidence": [
    {
      "timestamp_start": "1:03:03",
      "timestamp_end": "1:04:44",
      "type": "paraphrase",
      "text": "Stony sagt, Jonah Coleman interessiere ihn mehr als Nicholas Singleton, weil er bei Denver durch Dobbins' Verletzungsrisiko und Paytons RB-Rotation früher relevant werden könne."
    }
  ]
}
```

---

## 9. Markdown-Ausgabe

Die Markdown-Quellennotiz soll immer diese Struktur verwenden:

```markdown
# StonedLack Podcast [Episode] – [Titel/Thema]

## 1. Quellenhinweis und Bereinigung
## 2. Verifizierte Namens- und Entity-Mappings
## 3. Episodenüberblick
## 4. Zentrale Source-Philosophie / Bewertungslogik
## 5. Explizite Rankings / Tiers
## 6. Sleeper / Buy / Sell / Fade / Watchlist
## 7. Spielerprofile / Entity-Profile
## 8. Strategie-Takes
## 9. Formatabhängige Hinweise
## 10. Offene Punkte und Unsicherheiten
## 11. Artefakt-Referenzen
## 12. Kurzfazit der Quelle
```

Wenn eine Sektion nicht relevant ist, trotzdem aufführen und kurz schreiben:

```markdown
Keine expliziten Rankings in dieser Folge.
```

### 9.1 Artefakt-Referenzen

Die Markdown-Datei soll die zugehörigen Dateien nennen:

```markdown
## 11. Artefakt-Referenzen

- Raw-Transkript: `../../raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md`
- JSON-Datenfile: `2026-05-11_sl_0571_rookie_rb_ranking.json`
```

---

## 10. Spieler-/Entity-Profile

Für jede relevante Entity soll die Markdown-Datei möglichst dieses Profil verwenden:

```markdown
## [Name]

**Entity-Typ:** Spieler / Team / Coach / Strategie / Format  
**Position:**  
**Team:**  
**College:**  
**Podcast-Rolle:**  
**Sentiment:**  
**Conviction:**  
**Fantasy-Kontext:**  

### Kernaussage

### Begründung aus Podcast-Kontext

### Positiv

### Negativ / Risiko

### Formatabhängigkeit

### Offene Punkte / Unsicherheit

### Analyse-Tags
```

Bei Teams, Coaches oder Strategiekonzepten entsprechend anpassen.

---

## 11. JSON-Ausgabe

Das JSON-Datenfile soll mindestens enthalten:

```json
{
  "metadata": {},
  "artifacts": {},
  "entities": [],
  "takes": [],
  "rankings": [],
  "tiers": [],
  "strategy_notes": [],
  "uncertainties": []
}
```

### 11.1 Pflichtfelder in `artifacts`

```json
{
  "artifacts": {
    "raw_transcript_path": "raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md",
    "markdown_note_path": "episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.md",
    "json_data_path": "episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.json",
    "raw_transcript_version": "v1",
    "raw_transcript_sha256": "optional_checksum"
  }
}
```

### 11.2 Pflichtfelder pro Take

```json
{
  "take_id": "sl_0571_take_001",
  "episode_id": "sl_0571",
  "speaker": "Stony",
  "take_type": "sleeper",
  "entity_refs": ["player_jonah_coleman"],
  "fantasy_context": ["dynasty", "rookie_draft"],
  "league_format_context": ["PPR"],
  "sentiment": "very_positive",
  "conviction": "high",
  "action": "draft",
  "time_horizon": "early_season",
  "summary": "Jonah Coleman ist für Stony interessanter als Nicholas Singleton.",
  "supporting_arguments": [],
  "risks": [],
  "evidence": [],
  "extractor_confidence": "high"
}
```

---

## 12. Speaker-Regeln

Wenn der Sprecher klar erkennbar ist:

- `speaker: "Lack"`
- `speaker: "Stony"`

Wenn beide zustimmen:

- `speaker: "both"`

Wenn unklar:

- `speaker: "unknown"`

Wenn ein Host eine andere Meinung hat, getrennte Takes anlegen.

Nicht zu einer falschen Konsensmeinung verschmelzen.

---

## 13. Explizit vs. implizit

Jeder Take soll ein Feld `take_origin` haben:

- `explicit` = wurde klar gesagt
- `implicit` = folgt stark aus Aussagen, wurde aber nicht exakt so gesagt
- `extractor_inference` = AI-Interpretation auf Basis mehrerer Aussagen

Bei `extractor_inference` besonders vorsichtig sein und Confidence senken.

---

## 14. Rankings und Tiers

Wenn ein Ranking explizit genannt wird, exakt erfassen.

Wenn ein Ranking aus Gespräch und Folien rekonstruiert wird, markieren:

```json
{
  "ranking_origin": "reconstructed_from_transcript"
}
```

Wenn ein Ranking unsicher ist:

```json
{
  "ranking_confidence": "medium"
}
```

### 14.1 Tier-Felder

```json
{
  "tier_id": "sl_0571_tier_001",
  "episode_id": "sl_0571",
  "tier_name": "Klare Rookie-RB Targets",
  "tier_type": "rookie_draft",
  "entities": ["player_jeremiyah_love", "player_jadarian_price"],
  "tier_origin": "reconstructed_from_transcript",
  "confidence": "high"
}
```

---

## 15. Strategische Takes separat erfassen

Nicht nur Spieler extrahieren.

Wichtige Strategie-Takes sind z. B.:

- „WR-Klasse ist tief, RB-Klasse dünn.“
- „Bei TE darf man nicht overpayen.“
- „Draft Capital ist bei Rookie-Drafts wichtig.“
- „Return-Yards verändern Late-Round-WR/RB.“
- „Pick 1.07 ist dieses Jahr unangenehm.“
- „In 6-Team-Ligen verschiebt sich der Wert der Runden.“

Diese Aussagen in `strategy_notes` und/oder als Take mit `take_type: "draft_strategy"` speichern.

---

## 16. Formatabhängigkeit konsequent erfassen

Wenn ein Take nur in bestimmten Formaten gilt, muss das klar sein.

Beispiele:

- Return-Yards
- Superflex
- TE-Premium
- Bestball
- Redraft vs Dynasty
- 1QB vs Superflex
- tiefe Rosters / Taxi Squad

Nie allgemeingültig formulieren, wenn die Quelle formatabhängig argumentiert.

---

## 17. Unsicherheiten dokumentieren

Jede Datei soll eine Sektion `Offene Punkte und Unsicherheiten` enthalten.

Typische Unsicherheiten:

- Name nicht sicher gemappt
- Team/Roster nicht verifiziert
- Take nur aus Transkript rekonstruiert
- Ironie/Sarkasmus möglich
- Host uneinig
- Aussage nur für bestimmtes Format gültig
- Zeitpunkt/ADP könnte veraltet sein

---

## 18. Empfohlene Dateinamen

```text
raw_transcripts/
  2026/
    2026-05-11_sl_0571_rookie_rb_ranking.raw.md

episodes/
  2026/
    2026-05-11_sl_0571_rookie_rb_ranking.md
    2026-05-11_sl_0571_rookie_rb_ranking.json

entities/
  player_aliases.json
  team_aliases.json

schemas/
  stonedlack_take_schema.json

README.md
STONEDLACK_EXTRACTION_GUIDE.md
```

---

## 19. Qualitätscheck vor Abgabe

Vor dem Speichern prüfen:

- Ist das Raw-Transkript unverändert gespeichert?
- Verweist das JSON auf die Raw-Datei?
- Verweist die Markdown-Datei auf Raw und JSON?
- Sind alle relevanten Namen bereinigt?
- Gibt es eine Mapping-Tabelle?
- Sind nicht verifizierte Namen markiert?
- Sind Host-Takes von AI-Inferenz getrennt?
- Sind Redraft/Dynasty/Bestball sauber getrennt?
- Gibt es Formatabhängigkeiten?
- Gibt es Evidence mit Zeitstempeln?
- Gibt es eine klare Kurzfassung?
- Ist das JSON valide?
- Sind die Dateinamen konsistent?

---

## 20. Minimales Ausgabeziel bei sehr langen Folgen

Wenn eine Folge zu lang ist, Priorität:

1. Raw-Transkript speichern.
2. Alle Spieler-/Team-/Coach-Takes mit Fantasy-Relevanz extrahieren.
3. Alle Buy/Sell/Fade/Draft/Reach/Watch Aussagen extrahieren.
4. Alle Rankings/Tiers erfassen.
5. Alle Formatabhängigkeiten markieren.
6. Alle Unsicherheiten notieren.
7. Off-Topic-Segmente nur kurz zusammenfassen oder auslassen.

Off-Topic-Gespräche nur dokumentieren, wenn sie Kontext für die Folge liefern, nicht aber als strukturierte Fantasy-Takes.

---

## 21. Leitgedanke

Die Ausgabe soll nicht nur „schön zusammenfassen“, sondern später maschinell beantwortbar machen:

- Was denkt StonedLack zu Spieler X?
- Wie hat sich ihre Meinung zu Spieler X über Folgen verändert?
- Welche Spieler sind wiederkehrende Favoriten?
- Welche Takes sind formatabhängig?
- Welche Takes widersprechen anderen Outlets?
- Welche Aussagen waren besonders stark oder vorsichtig formuliert?
- Welche Rankings waren explizit und welche rekonstruiert?
- Wo liegt das unveränderte Raw-Transkript zur Prüfung?
