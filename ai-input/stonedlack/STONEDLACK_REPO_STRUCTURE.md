# Recommended Repository Structure for StonedLack Source Notes

Dieses Repo speichert extrahierte StonedLack-Podcastdaten für spätere Fantasy-/Dynasty-Analysen.

## Empfohlene Struktur

```text
stonedlack-source-notes/
  README.md
  STONEDLACK_EXTRACTION_GUIDE.md

  schemas/
    stonedlack_take_schema.json

  raw_transcripts/
    2026/
      2026-05-04_sl_0570_rookie_wr_ranking.raw.md
      2026-05-11_sl_0571_rookie_rb_ranking.raw.md

  episodes/
    2026/
      2026-05-04_sl_0570_rookie_wr_ranking.md
      2026-05-04_sl_0570_rookie_wr_ranking.json
      2026-05-11_sl_0571_rookie_rb_ranking.md
      2026-05-11_sl_0571_rookie_rb_ranking.json

  entities/
    player_aliases.json
    team_aliases.json
    coach_aliases.json

  indexes/
    player_take_index.json
    episode_index.json
    source_favorites.json
```

## Dateiarten pro Folge

Pro Folge entstehen künftig drei Dateien:

| Datei | Zweck | Pfad |
|---|---|---|
| Raw-Transkript | unveränderte Primärquelle | `raw_transcripts/YYYY/*.raw.md` |
| Markdown-Notiz | lesbare Auswertung | `episodes/YYYY/*.md` |
| JSON-Datenfile | maschinenlesbare Takes | `episodes/YYYY/*.json` |

## Warum Raw-Transkripte separat?

Raw-Transkripte sind wichtig, weil sie:

- spätere Audits ermöglichen,
- Fehler in der Aufbereitung nachvollziehbar machen,
- alternative Extraktionen erlauben,
- anderen AIs als Primärquelle dienen,
- Namenskorrekturen überprüfbar machen.

## Raw-Transkriptformat

Raw-Dateien verwenden `.raw.md` und enthalten nur Frontmatter plus Originaltranskript.

Beispiel:

```markdown
---
episode_id: sl_0571
episode_number: 571
source_name: StonedLack
source_type: youtube_transcript
published_date: 2026-05-11
processed_date: 2026-06-21
language: de
raw_transcript_status: verbatim_user_paste
---

Kapitel 1: Cold Turkey
0:00...
```

## Pfadreferenzen in JSON

Jede JSON-Datei soll auf ihre Artefakte verweisen:

```json
{
  "artifacts": {
    "raw_transcript_path": "raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md",
    "markdown_note_path": "episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.md",
    "json_data_path": "episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.json",
    "raw_transcript_version": "v1",
    "raw_transcript_sha256": "..."
  }
}
```

## Pfadreferenzen in Markdown

Jede Markdown-Notiz soll am Ende auf Raw und JSON verweisen:

```markdown
## Artefakt-Referenzen

- Raw-Transkript: `../../raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md`
- JSON-Datenfile: `2026-05-11_sl_0571_rookie_rb_ranking.json`
```

## Dateibenennung

```text
YYYY-MM-DD_sl_EPISODE_THEMENSCHWERPUNKT.raw.md
YYYY-MM-DD_sl_EPISODE_THEMENSCHWERPUNKT.md
YYYY-MM-DD_sl_EPISODE_THEMENSCHWERPUNKT.json
```

Beispiele:

```text
2026-05-04_sl_0570_rookie_wr_ranking.raw.md
2026-05-04_sl_0570_rookie_wr_ranking.md
2026-05-04_sl_0570_rookie_wr_ranking.json
```

## Entity-Aliase

Die Alias-Dateien sollten über Zeit wachsen.

Beispiel `player_aliases.json`:

```json
{
  "player_kaelon_black": {
    "canonical_name": "Kaelon Black",
    "aliases": ["Ken Black", "Kill Black", "Kellen Black"],
    "position": "RB",
    "team": "San Francisco 49ers",
    "last_verified": "2026-06-21"
  }
}
```

## Arbeitsablauf pro neuer Folge

1. Transkript in Chat geben.
2. AI mit `STONEDLACK_EXTRACTION_GUIDE.md` und `schemas/stonedlack_take_schema.json` instruieren.
3. AI erzeugt direkt:
   - `raw_transcripts/YYYY/*.raw.md`
   - `episodes/YYYY/*.md`
   - `episodes/YYYY/*.json`
4. Dateien ins Repo committen.
5. Bei späteren Folgen vorhandene Alias-Dateien wieder mitgeben.
6. Periodisch Index-Dateien aktualisieren.

## Spätere Meta-Auswertung

Mit den JSON-Dateien lassen sich später Fragen beantworten wie:

- Welche Spieler sind wiederkehrende StonedLack-Favoriten?
- Welche Spieler werden über mehrere Folgen negativer/positiver?
- Wo widersprechen StonedLack-Takes anderen Outlets?
- Welche Takes sind nur für Return-Yards relevant?
- Welche Spieler haben hohes Sentiment, aber niedrige Conviction?
- Welche Spieler werden als Buy/Sell/Fade genannt?
- Wo liegt die unveränderte Primärquelle?
