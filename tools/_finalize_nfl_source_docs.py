from pathlib import Path
from textwrap import dedent


def replace_section(text: str, start: str, next_start: str, replacement: str) -> str:
    start_at = text.index(start)
    end_at = text.index(next_start, start_at)
    return text[:start_at] + dedent(replacement).strip() + "\n\n" + text[end_at:]


todo_path = Path("TODO.md")
todo = todo_path.read_text(encoding="utf-8")

todo = replace_section(
    todo,
    "- [ ] Provideradapter für nflverse mit Raw-Persistierung und Content-Hash-Vergleich entwickeln.",
    "- [ ] Kanonische NFL-Player-Identity-Bridge aufbauen.",
    """
    - [x] Provideradapter für nflverse mit Raw-Persistierung und Content-Hash-Vergleich entwickeln.
      - Erledigt: Die registrierten nflverse-Datasets werden zentral geladen, vor Veröffentlichung auf Schema und Mindestumfang validiert und unter `source-data/providers/nflverse/` provider-nah persistiert.
      - Content-Hash: Unveränderte Downloads erzeugen keinen neuen Raw-Inhalt; der letzte validierte lokale Stand bleibt als reproduzierbare Fallback-Basis erhalten.
      - Publication: Der produktive Workflow veröffentlicht Raw-Daten zuerst und materialisiert Canonical erst aus dem bereits persistierten Raw-Stand; Fehler zerstören den letzten guten Providerstand nicht.
      - Abgrenzung: nflverse-Feldnamen bleiben in Adapter-/Normalisierungslogik und sickern nicht als neuer App-Vertrag in `public/data/**` durch.
    """,
)

todo = replace_section(
    todo,
    "- [ ] Kanonische NFL-Player-Identity-Bridge aufbauen.",
    "- [ ] NFL Draft Capital und Combine als erste persistente kanonische Source-Datasets materialisieren.",
    """
    - [x] Kanonische NFL-Player-Identity-Bridge aufbauen.
      - Erledigt: `NFLPlayerID` ist die dauerhafte providerunabhängige Personenidentität unter `source-data/nfl/identities/`; GSIS, Sleeper, Tank01, ESPN, PFR, PFF und weitere Provider-IDs sind Zuordnungen und nicht der Master-Key.
      - App-Vertrag: `public/data/Players.json[].ID` bleibt unverändert die Sleeper-ID für den aktuellen App-/Liga-Kontext.
      - Historie: Provider-Mappings werden saisonbezogen erhalten; spätere ID-Wiederverwendung kann auf eine andere `NFLPlayerID` zeigen, ohne historische Personen umzudeuten.
      - Konflikte: Widersprüchliche oder mehrdeutige Mappings werden explizit quarantänisiert; keine stillen Dedupes, Name-Matches oder heuristischen Gewinner.
      - Validierung: Real-nflverse-Bootstrap, 27 Source-Tests, zweiter semantischer No-op-Pass und Audit mit `duplicateLinkProviderIDCount = 0` sind erfolgreich; Sleeper `133` bleibt als expliziter Zwei-Personen-Konflikt quarantänisiert.
    """,
)

todo = replace_section(
    todo,
    "- [ ] NFL Draft Capital und Combine als erste persistente kanonische Source-Datasets materialisieren.",
    "- [ ] nflverse Player Stats, Schedules, Rosters und Snap Counts gegen die bestehende Tank01-/Sleeper-Datenbasis evaluieren.",
    """
    - [x] Kanonische NFL-Draft-Historie und Draftstatus als persistentes Source-Dataset materialisieren.
      - Erledigt: nflverse Draft Picks werden über die zentrale `NFLPlayerID` normalisiert und saisonweise unter `source-data/nfl/draft/` persistiert; der aktuelle Bootstrap umfasst 47 Draft-Saisons von 1980 bis 2026.
      - Semantik: Draftjahr, Runde, Position innerhalb der Runde, Overall Pick, Draft-Team und Player-Identität bleiben explizit; `drafted`, `undrafted`, `not_yet_drafted` und `unknown` werden nicht vermischt.
      - Historie: Abgeschlossene Draftjahrgänge sind kanonische historische Source-Daten und werden nicht als aktuelle App-Draft-Assets interpretiert.
      - Validierung: Draft-Materialisierung ist Bestandteil des Real-Data-Audits und des verpflichtenden zweiten No-op-Passes.

    - [ ] NFL Combine als nächstes persistentes kanonisches Source-Dataset materialisieren.
      - Ziel: Jahrgangsbezogene Combine-Messungen mit `NFLPlayerID` und Draft-Verknüpfung in `source-data/nfl/` materialisieren.
      - Historie: Abgeschlossene Jahrgänge dauerhaft erhalten und standardmäßig nur fehlende neue Jahrgänge ergänzen; bewusste historische Korrekturen nur über einen expliziten Force-/Repair-Pfad zulassen.
      - Integration: Erst nach Stabilisierung des Combine-Source-Datasets entscheiden, welche Felder in `Players.json` oder weitere generierte App-Readmodels übernommen werden.
      - Validierung: Coverage gegen den aktuellen Playerbestand prüfen, insbesondere Rookies, ältere Spieler und Spieler ohne eindeutige Combine-Zuordnung.
    """,
)

todo_path.write_text(todo, encoding="utf-8", newline="\n")

decisions_path = Path(".ai-context/manual/decisions.yaml")
decisions = decisions_path.read_text(encoding="utf-8")
marker = "  - id: ADR-025\n    title: NFL player identity is provider-independent and provider mappings are historical"
if marker not in decisions:
    decisions = decisions.rstrip() + dedent(
        """

          - id: ADR-025
            title: NFL player identity is provider-independent and provider mappings are historical
            status: accepted
            context: >
              The app intentionally relies on Sleeper for its current player and league
              state, but historical data must remain correct if a provider corrects,
              collides or eventually reuses an identifier. Real nflverse input has shown
              that one provider mapping can contradict otherwise distinct player
              identities, so treating every shared provider ID as an unconditional merge
              edge is not safe.
            decision: >
              Use NFLPlayerID as the durable provider-independent identity of one real NFL
              player in canonical source data. Keep public/data/Players.json[].ID as the
              Sleeper player_id because Sleeper remains the leading provider for the
              current app and fantasy-league state; this Sleeper field is an app contract,
              not the permanent cross-provider person key. Treat Sleeper, Tank01, GSIS,
              ESPN, PFR, PFF and all other external IDs as historical mappings to
              NFLPlayerID. Persist mapping validity with at least season-level resolution.
              A conflicting provider mapping must be quarantined rather than merging two
              otherwise distinguishable people. Historical canonical facts retain the
              NFLPlayerID resolved for the event or season plus source provenance. Names
              remain descriptive rather than authoritative merge keys. Runtime timestamps
              must not make otherwise identical canonical source-data semantically different.
            rationale: >
              This preserves Sleeper as the practical source of truth for the current app
              while decoupling long-lived player history from assumptions about the
              lifetime uniqueness of any external provider identifier. The resolver can
              fail closed on dirty mappings without corrupting canonical people.
            consequences:
              positive:
                - Current Angular and generated Players.json contracts remain unchanged.
                - Historical facts can survive provider ID reuse or corrections.
                - Provider conflicts are isolated to mappings instead of collapsing people.
                - New providers can attach without becoming a new global master ID.
                - Semantic no-op materialization is independent from freshness metadata.
              negative:
                - The identity bridge requires historical mappings and conflict quarantine.
                - Resolution APIs need temporal context when an external ID is not globally unique.
        """
    ).rstrip() + "\n"
    decisions_path.write_text(decisions, encoding="utf-8", newline="\n")
