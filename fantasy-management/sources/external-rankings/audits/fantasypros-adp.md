# Quellen-Audit: FantasyPros ADP

## Status

- Auditdatum: 4. August 2026
- Ranking-Art: `adp`
- Anbieter: FantasyPros
- Nutzungsstatus: `rejected_for_automation`
- Vollständige anonyme Quelle: nein
- Zusatzkosten oder authentifizierter Zugang vorgesehen: nein

## Zweck des Audits

Geprüft wurde, ob FantasyPros neben dem bereits genutzten Expertenkonsens eine vollständige, kostenlose und automatisierbare ADP-Quelle für Fantasy Management bereitstellt.

FantasyPros ADP wäre nur dann eine eigenständige Quelle, wenn tatsächlich beobachtete Draftpositionen vollständig zugänglich sind. FantasyPros-ECR-Felder dürfen nicht als Ersatz für ADP behandelt werden, weil Expertenkonsens und Draftverhalten unterschiedliche Signale messen.

## Geprüfte Zugriffswege

Die Live-Prüfung umfasste:

- die kanonischen anonym erreichbaren FantasyPros-ADP-Seiten
- den in der gerenderten Seite eingebetteten Report-Payload
- die sichtbare Tabellenstruktur und mögliche Pagination
- öffentlich erkennbare XHR- oder Datensätze mit einem vollständigen Report
- die frühere `export=xls`-Ansicht im GitHub-Runner

## Befunde

### Unvollständiger anonymer Report

Die anonym erreichbaren ADP-Seiten lieferten nur fünf Spielerzeilen. Der eingebettete Report-Payload enthielt denselben fünf Spieler umfassenden Ausschnitt und keinen vollständigen, lediglich in der Oberfläche ausgeblendeten Datenbestand.

Nach diesen fünf Zeilen erschien eine Account-Sperre. Der sichtbare Ausschnitt ist deshalb ausdrücklich kein vollständiges Ranking.

### Kein alternativer öffentlicher Vollbestand

Im anonymen Browserzustand wurden nicht gefunden:

- eine Pagination zu weiteren Spielerzeilen
- ein versteckter vollständiger Tabellenbestand
- ein öffentlicher XHR-Datensatz mit dem vollständigen Report
- ein vollständiger anonymer CSV-, JSON- oder anderer strukturierter Export

### Frühere Export-Route nicht nutzbar

Die frühere `export=xls`-Ansicht stellte dem GitHub-Runner keinen vollständigen Export bereit. Sie bildet daher keinen belastbaren Produktionsvertrag für einen automatisierten Fetcher.

## Qualitäts- und Interpretationsregeln

- Der sichtbare Top-5-Ausschnitt darf nicht gespeichert oder als vollständiges ADP-Ranking interpretiert werden.
- FantasyPros ECR ist Expertenkonsens und darf nicht in ADP umbenannt oder als ADP-Ersatz verwendet werden.
- Ein unvollständiger Report darf nicht mit Werten anderer Anbieter künstlich vervollständigt werden.
- Ein Fetcher muss bei einem Account-Gate, unerwartet kleiner Zeilenzahl oder fehlendem Vollbestand geschlossen fehlschlagen.

## Entscheidung

Unter den Vorgaben ohne Zusatzkosten und ohne authentifizierten Zugang wird FantasyPros ADP nicht integriert.

Daraus folgen verbindlich:

- kein FantasyPros-ADP-Fetcher
- kein FantasyPros-ADP-Providerverzeichnis mit Snapshots oder Raw-Daten
- kein Workflow für diese Quelle
- keine Login-, Cookie- oder API-Secrets
- keine Verwendung des anonymen Top-5-Ausschnitts
- Fantasy Football Calculator bleibt die aktive automatisierte ADP-Quelle

## Abgrenzung zum aktiven FantasyPros-ECR

Diese Ablehnung betrifft ausschließlich FantasyPros ADP. Die vorhandenen FantasyPros-Rankings unter `expert-consensus` bleiben davon unberührt, weil sie über einen anderen vollständigen Quellzugang verfügen und ein anderes Signal messen.

## Neubewertung

Eine erneute Prüfung ist nur sinnvoll, wenn FantasyPros einen vollständigen anonymen offiziellen ADP-Report, Export oder dokumentierten öffentlichen Feed bereitstellt.

Bis dahin ist der Status nicht `manual_reference_only`, sondern `rejected_for_automation`, weil selbst die anonyme manuelle Tabelle nur einen unvollständigen Ausschnitt zeigt.

## Maschinenlesbare Kurzfassung

```yaml
provider: fantasypros
ranking_kind: adp
audit_date: 2026-08-04
access:
  anonymous_report_complete: false
  visible_rows: 5
  embedded_payload_complete: false
  public_pagination_found: false
  public_full_xhr_found: false
  anonymous_export_complete: false
usage:
  automated_fetching: rejected
  snapshot_storage: rejected
  top_five_as_ranking: prohibited
  authenticated_access: not_planned
active_alternative: fantasy-football-calculator
reconsider_when:
  - complete_anonymous_official_report_available
  - documented_public_complete_feed_available
```
