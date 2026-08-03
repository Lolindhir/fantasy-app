# FantasyPros ADP Rankings

Dieser Bereich speichert die öffentlichen FantasyPros-ADP-Composites als eigenständigen Provider innerhalb der Ranking-Art `adp`.

FantasyPros ADP fasst veröffentlichte Draftpositionen mehrerer Plattformen zusammen. Das Signal ist weder FantasyPros-ECR noch eine Projektion oder ein Trade-Marktwert. Die einzelnen Plattformwerte, ihre Abdeckung und ihre sichtbaren Datenstände bleiben erhalten, damit Veränderungen der Quellenkomposition nicht als gewöhnliche Spielerbewegung fehlinterpretiert werden.

## Verwendete Formate

| Ranking-ID | Öffentliche Seite | Primäre Rolle |
|---|---|---|
| `redraft-ppr-overall` | PPR Overall ADP | primärer FantasyPros-ADP-Kontext für RB, WR und TE |
| `redraft-half-ppr-superflex` | Half-PPR Superflex/OP ADP | primärer FantasyPros-ADP-Kontext für QB und Superflex-Knappheit |

Die reale Liga hat sechs Teams, Full PPR, zwei feste QB- und zwei feste TE-Startplätze. Kein FantasyPros-ADP-Feed bildet dieses Format vollständig ab:

- PPR Overall bildet das Scoring für RB/WR/TE besser ab, aber keinen Superflex-Markt.
- Half-PPR Superflex bildet die QB-Nachfrage besser ab, verwendet aber Half PPR und dokumentiert keine passende Sechs-Team-Population.
- Die zwei festen TE-Plätze werden erst in der ligaindividuellen Analyse berücksichtigt.

Die beiden Formate werden nicht gemittelt.

## Ablagestruktur

```text
fantasypros/
├── README.md
├── analysis-metadata.json
├── redraft-ppr-overall/
│   ├── raw-latest.json
│   ├── latest.json
│   └── snapshots/YYYY-MM-DD/
│       ├── ranking.csv
│       └── metadata.json
└── redraft-half-ppr-superflex/
    ├── raw-latest.json
    ├── latest.json
    └── snapshots/YYYY-MM-DD/
        ├── ranking.csv
        └── metadata.json
```

## Speichervertrag

Pro Format gilt:

- `raw-latest.json` enthält die vollständig geparste aktuelle öffentliche Ranking-Tabelle oder offizielle Exportansicht einschließlich aller sichtbaren dynamischen Plattformspalten sowie die Quellen-/Datumsübersicht der kanonischen Seite.
- Die vollständige volatile HTML-Seite wird nicht historisiert.
- Normalisiert werden ausschließlich offensive Spieler der Positionen QB, RB, WR und TE.
- Historisiert werden `ranking.csv` und `metadata.json` für die vier neuesten inhaltlich veränderten Stände.
- Ein unveränderter normalisierter Stand erzeugt keinen neuen Snapshot; der aktuelle Raw-Stand und dessen Freshness werden trotzdem ersetzt.
- Mehrere Änderungen am selben Kalendertag ersetzen den Snapshot dieses Tages.
- Beim fünften unterschiedlichen Snapshot wird der älteste normalisierte Snapshot entfernt.

Vier Stände ermöglichen letzten Delta-Vergleich, kurzfristigen Trend und Erkennung einer einmaligen Gegenbewegung, ohne eine unbegrenzte Quellhistorie aufzubauen.

## Normalisiertes CSV-Schema

```text
name,Rank,source_format_rank,source_overall_rank,position,position_rank,team,bye,source_player_id,player_slug,adp_average,realtime_value,source_ranks_json,contributing_source_count,source_rank_min,source_rank_max,source_rank_range,source_rank_std,source_format,actual_league_team_count
```

Wichtige Felder:

- `Rank`: eindeutiger eigener Rang nach veröffentlichtem ADP-Durchschnitt, Format-Rang und stabiler Quellidentität.
- `source_format_rank`: veröffentlichter `Rank` beziehungsweise `OP`-Rang.
- `source_overall_rank`: zusätzliche `Overall`-Spalte des Superflex-Feeds; bleibt als Quellfeld erhalten, ohne unbestätigte Methodik zu unterstellen.
- `source_ranks_json`: alle sichtbaren Plattformwerte einschließlich `null` für fehlende Werte.
- `adp_average`: veröffentlichter FantasyPros-Durchschnitt; wird gegen die vorhandenen Plattformwerte mit Rundungstoleranz validiert.
- `realtime_value`: sichtbare Real-Time-Spalte, wenn das Format sie veröffentlicht; ihre genaue Methodik bleibt unbestätigt.
- `source_rank_std`: von uns berechnete Populations-Standardabweichung der vorhandenen Plattformwerte; keine Samplegröße und keine Erfolgswahrscheinlichkeit.
- `source_player_id` und `player_slug`: werden aus der HTML-Tabelle übernommen. Liefert die offizielle Exportansicht nur Klartext, bleiben diese Felder leer und der Join fällt auf Name, Position und Team zurück.

## Quellenkomposition

Jeder Snapshot speichert:

- sichtbare Plattformspalten,
- aktive Plattformen mit mindestens einem Wert,
- Feldabdeckung je Plattform,
- sichtbare Plattform-Datenstände,
- einen deterministischen `source_composition_fingerprint`.

Ändert sich die Quellenkomposition oder der sichtbare Datenstand, entsteht ein neuer Snapshot auch dann, wenn die normalisierte Reihenfolge zufällig gleich bleibt. Eine spätere Auswertung muss solche Veränderungen als Source-Context-Change kennzeichnen und darf sie nicht allein als Marktbewegung interpretieren.

## Abrufstrategie

Für die aktive Saison wird zuerst die kanonische öffentliche Seite ohne `year`-Parameter mit einem normalen Browser-User-Agent geladen. Historische Saisons verwenden weiterhin den expliziten `year`-Parameter.

Enthält die kanonische Antwort eine vollständige Rankingtabelle, wird sie direkt geparst. Liefert FantasyPros dagegen nur die dynamische Seitenschale ohne Rankingtabelle, gilt ein eng begrenzter Fallback:

1. Die kanonische Seite bleibt verbindlich für Titel, Saison, Formatidentität und sichtbare Quellenstände.
2. Mit derselben Cookie-Session und der kanonischen Seite als Referer wird die offizielle `export=xls`-Ansicht geladen.
3. Der Export darf eine HTML-Tabelle oder ein tabulator-/kommagetrenntes Textdokument sein.
4. Nur der exakt erkannte Fehler „Rankingtabelle fehlt“ aktiviert den Fallback. Andere Identitäts-, Quellen-, Spieler-, Mindestgrößen- oder AVG-Fehler bleiben sofort fail-closed.
5. `raw-latest.json`, `metadata.json` und `latest.json` dokumentieren die tatsächlich verwendete Extraktionsmethode und beide Abruf-URLs.

Zwischen sämtlichen Live-Requests, einschließlich eines Fallback-Abrufs, liegen standardmäßig fünf Sekunden. Schlägt auch der offizielle Export fehl, enthält die Fehlermeldung beide versuchten URLs und die konkrete Parserursache, aber kein vollständiges HTML-Dokument.

## Direkter Abruf

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_adp.py --skip-unchanged
```

Prüfmodi:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_adp.py --dry-run
python fantasy-management/_ai/scripts/fetch_fantasypros_adp.py \
  --input ppr-overall=/path/ppr.html \
  --input half-ppr-superflex=/path/superflex.html \
  --dry-run
```

Der Fetcher lädt und validiert beide Formate vollständig, bevor eines geschrieben wird. Netzwerk-, Seitenidentitäts-, Tabellen-/Export-, Spieler-, Quellen-, Durchschnitts-, Mindestgrößen- oder Schemafehler beenden den Lauf ohne Veröffentlichung eines einseitigen Vergleichs.

## Automatische Aktualisierung

Der bestehende Workflow `Update FantasyPros Rankings` testet die FantasyPros-Fetcher, aktualisiert ECR und anschließend beide ADP-Formate im selben Job und staged beide FantasyPros-Ranking-Arten einschließlich Snapshot-Löschungen. Ein fehlgeschlagener Abruf verhindert den Commit-Schritt.

## Quellenübergreifende Auswertung

- FantasyPros ADP nicht mit Fantasy Football Calculator mitteln.
- FantasyPros und Fantasy Football Calculator über listenlängenbereinigte Perzentile vergleichen.
- Plattformüberschneidungen anhand der aktuellen FantasyPros-Quellenkomposition dynamisch ausweisen.
- Für QB den Half-PPR-Superflex-Feed verwenden; für RB/WR/TE den PPR-Overall-Feed.
- Die endgültige Bewertung ergänzt sechs-Team-Replacement-Level sowie zwei feste QB- und TE-Plätze.

FantasyPros ist bei jeder Anzeige oder Auswertung der Quelldaten sichtbar zu attribuieren.
