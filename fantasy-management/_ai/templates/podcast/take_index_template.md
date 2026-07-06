# {{source_name}} {{episode_number}} – Take-Index

Status: deutsch lesbarer Index der normalisierten atomaren Takes. JSON-Takes liegen unter:

`{{take_path_pattern}}`

## Qualitätsstatus

Die Takes `{{episode_id}}_t001` bis `{{episode_id}}_tNNN` sind die kanonische episode-lokale Take-Schicht für diese Folge.

Sie müssen enthalten:

- stabile Dateinamen passend zur `take_id`
- deutsche Summary-, Argument-, Risiko- und Interpretationsfelder
- strukturierte Evidence
- explizites `source_statement`
- explizites `cleaned_entity_mapping`
- explizite `ai_interpretation`
- `episode_local_scope` mit Hinweis, dass globale Indexe deferred sind

Globale Indexdateien werden nicht aktualisiert, außer die Aufgabe ist explizit ein Index-Rebuild.

## Strategie und Meta-Takes

| Take | Thema | Kurzsignal |
|---|---|---|
| `{{take_id}}` | {{topic}} | {{short_signal}} |

## Spieler-/Entity-Takes

| Take | Spieler / Entity | Kurzsignal |
|---|---|---|
| `{{take_id}}` | {{entity}} | {{short_signal}} |

## Team-/Markt-/Rollen-Signale

| Take | Entity | Kurzsignal |
|---|---|---|
| `{{take_id}}` | {{entity}} | {{short_signal}} |

## Caution / Fade / Uncertainty

| Take | Entity / Bucket | Kurzsignal |
|---|---|---|
| `{{take_id}}` | {{entity_or_bucket}} | {{short_signal}} |

## Hinweis

Dieser Index ist absichtlich auf Deutsch. Die JSON-Dateien bleiben maschinenlesbar und enthalten Evidence, Argumente, Risiken, Freshness, Current-Relevance, Quellenstatement, Entity-Mapping und AI-Interpretation.
