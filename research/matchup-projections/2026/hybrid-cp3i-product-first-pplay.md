# CP3i – Product-first-Teilnahmemodell, lag-only Walk-forward-Pilot

- **Datum:** 2026-11-22
- **Tracking:** [Issue #1451](https://github.com/Lolindhir/fantasy-app/issues/1451)
- **Status:** Forschung auf einem separaten Branch; **kein** aktives Modell, keine Source-/Derived-/App-/WinProb-/UI-Änderung.
- **Reproduzierbarer Runner:** [`calibrate_product_pplay.cjs`](calibrate_product_pplay.cjs)

## Ziel und Datenherkunft

Die probabilistische Teilnahme `P(Played=true)` soll aus dem **bereits bestehenden** Shared-Derived-Owner `data-derived/nfl-player-availability/<season>.json` gelernt werden, nicht aus eigenen Consumer-Snap-/Injury-/ESPN-Interpretationen. `PlayerWeekFantasy` bleibt später der Besitzer der **Teilnahme-bedingten** Punkteverteilung. Dieses Experiment modelliert weder Workload bei positiver Teilnahme noch Best-Ball-Punkte oder Manager-Chancen.

Live-GitHub-Inhalts-Readback auf `main`: Die vollständigen 2016–2026-Saisondateien geben `ProductVersion=nfl-player-availability-v3`, `SchemaVersion=3` zurück. Die frühere v2-Publikationslücke aus CP3h ist damit geschlossen. 2026 bleibt eine **laufende**, nicht vollständig finale Saison; sie ist hier weder Trainings- noch Holdout-Input. 2016–2025 werden als abgeschlossene Produktjahre verwendet.

**Cohort-As-of-Regel:** Für jede Regular-Season-Woche W ab 2 wird die Kandidatenpopulation ausschließlich aus den Spieler-Records der **Vorwoche W−1** gebildet. Features pro Spieler sind nur deren `Roster.Status`, `Played` und maximal acht vorangegangene bekannte `Played`-Labels. Die nachträglichen Zielwochen-Records werden **ausschließlich** zum Ermitteln von Outcome/Scorability benutzt: `Played=true/false` als Label, `Played=null` als unbekannt; Bye/nicht-REG getrennt, fehlender Datensatz nie als DNP. Der Runner kappt die Laufzeit auf die tatsächlich vorhandene Regular Season (17 Wochen vor 2021, 18 ab 2021), ohne Postseason-Wochen als zusätzliche Vorhersagefälle einzubeziehen. Keine aktuellen `Available`, `Report`, `Roster` oder `Participation.Plays`-Werte aus Woche W gelangen in die Modellfeatures.

**Einschränkung:** Auch Vorwochen-Produkte sind heutige retrospektive Revisionen, **keine** belegten exakten damaligen Veröffentlichungsstände. Die Datenverwendung ist zeitlich verzögert, aber kein offiziell abgenommener Point-in-Time-Replay. Das v3-Record enthält keine explizite individuelle `Position`; es findet deshalb **keine** Positionierung per Rohdaten-Join statt. Die Population mit Vorwochen-Record enthält auch Reserve-/Nicht-aktive Fälle und ist nicht identisch mit den Fantasy-Kadern unserer sechs Manager.

## Fixierter Versuchsaufbau

| Datenteil | NFL-Saisons | Bewertbare Spielerwochen | Verwendung |
|---|---|---:|---|
| Training | 2016–2022 | 128.087 | Globale und Vorwochen-Zustandsquoten |
| Validierung | 2023–2024 | 36.134 | Einmalige Hyperparameterauswahl |
| Unberührter Holdout | 2025 | 18.672 | Nach der Modellauswahl ausgewertet |

**Baselines:** (1) `P(play)=1` (bewusst naive All-Play-Annahme), (2) konstante Trainingsquote `0,436797`, (3) Shrinkage-Quote nach `Vorwochen-Rostergruppe × Vorwochen-Played` mit Pseudostichprobe `k=20`. Gruppen: `ACT`, `INA`, `RESERVE` (RES/PUP), `OTHER` und `NONE`; `Played` ist `T/F/U`.

**Modell:** Gruppenprior aus Training `p_g=(played_g + k × p_global)/(n_g+k)`; je Spieler ein geglätteter Verlauf `p=(played_in_last_n + alpha × p_g)/(n+alpha)` mit maximal 4 oder 8 **bekannten** Vorwochen-Labels. Ein `null`-Label zählt weder als Einsatz noch als Nicht-Einsatz. Grid: `k∈{5,20,100,400}`, `alpha∈{1,2,4,8,16,32}`, Fenster 4 oder 8. Kleinster Validierungs-Brier gewinnt (deterministische Gridreihenfolge bei Rundungsgleichstand). **Gewählt:** `k=400`, `alpha=8`, letzte 4 bekannte Teilnahmen. Globaler Gruppenprior wird **nicht** auf 2023–2025 nachtrainiert; historische Spielerlabels der abgeschlossenen Wochen innerhalb der späteren Perioden dürfen für jeweils künftige Wochen als Lag verwendet werden.

## Ergebnis

| Verfahren | Validierungs-Brier 2023/24 | Holdout-Brier 2025 | Holdout-LogLoss 2025 |
|---|---:|---:|---:|
| Alle spielen (`p=1`) | 0,527287 | 0,544559 | 11,285035 |
| Konstante Trainingsquote | 0,250545 | 0,248362 | 0,689875 |
| Vorwochen-Roster und -Teilnahme (`k=20`) | 0,097516 | 0,097192 | 0,328040 |
| **Plus geglättete eigene Historie** | **0,090910** | **0,090145** | **0,311719** |

Gegen die starke Vorwochenstatus-Baseline verbessert sich der Holdout-Brier um **0,007047 absolut (ca. 7,25 % relativ)**. Mittlerer Prognosewert im Holdout: **45,249 %**; beobachteter Anteil: **45,544 %**; mittlerer Bias `p-y=-0,002954`. Diese Zahlen beschreiben **nur das hier definierte Teilnahmelabel** innerhalb der beobachtbaren Kohorte, **nicht** die Genauigkeit künftiger Fantasy-Scores.

Im 2025-Holdout haben **10.051** der bewertbaren Fälle einen Vorwochen-Kaderstatus `ACT` oder `INA`. Dort beträgt der Brier des ausgewählten Modells **0,122060**, mittleres `p=76,675 %`, tatsächliche Teilnahme **77,107 %**. Die restlichen **8.621** Fälle mit anderem Vorwochenstatus haben einen deutlich niedrigeren Einsatzanteil. Der niedrige Gesamt-Brier profitiert stark von diesen leicht erkennbaren Reserve-/Nicht-aktiv-Kandidaten; **er darf nicht als Prognosegüte für einen ausschließlich startfähigen Fantasy-Kader verkauft werden**.

Holdout-Coverage des Vorwochen-Risikosets: 21.520 Kandidaten, davon **18.672** mit binärem `Played` und regulärem Spiel; **1.796** ohne Folgewoche-Record, **1.051** Bye/nicht-REG, **1** unbekannt. Die Auswertung schließt diese 2.848 Fälle aus dem Loss aus und protokolliert sie getrennt. In den mittleren Wahrscheinlichkeits-Buckets sind Abweichungen vorhanden (z. B. Band 0,6–0,7: vorhergesagt etwa 0,661 versus beobachtet etwa 0,832 bei n=656); **keine vollständige Kalibrierung**.

## Reproduktions- und Abnahmezustand

Auf einem vollständigen Checkout mit v3-Dateien:

```bash
node research/matchup-projections/2026/calibrate_product_pplay.cjs --self-test
node research/matchup-projections/2026/calibrate_product_pplay.cjs > /tmp/cp3i-product-pplay.json
```

Der Runner liest ausschließlich die zehn 2016–2025-JSONs unter `data-derived/nfl-player-availability`, fordert v3 strikt ein, prüft Tri-State und eindeutige `Week+CanonicalPlayerID`, berechnet den unveränderlichen 2025-Holdout und gibt Input-SHA256 für Reproduzierbarkeit aus. Keine Schreiboption, kein generiertes App-/Derived-Produkt, keine neue Testinventar-Familie.

**Tatsächlich validiert (22.11.):** Die synthetische `--self-test`-Logik wurde durch direkte Ausführung des eingecheckten Quelltexts in einer isolierten V8-Harness-Umgebung mit Node-API-Stubs erfolgreich geprüft: Kohortengrenze, Null, Bye, fehlende Records, doppelte IDs, Unterdrückung aktueller Zielwochen-Features, Brier. Anschließend wurde exakt die exportierte `run(documents)`-Funktion aus dem eingecheckten Runner **gegen die zehn tatsächlichen v3-GitHub-JSONs** in dieser Harness ausgeführt; Resultate oben und die Coverage-Jahreszählungen wurden reproduziert. **Nicht** behaupten: ein erfolgreicher eigenständiger `node`-CLI-Lauf auf vollständigem lokalen Git-Checkout oder unabhängiger Produktionslauf. PR-CI ist separat zu bewerten.

## Grenzen, Architektur und nächste Forschung

- **Keine positionsspezifische Kalibrierung:** Das Availability-v3-Record enthält keine `Position`. Vor einer produktiven Wiederverwendung muss die positionsbezogene Evidenz bei dem geeigneten Shared-Derived-Owner korrekt identifiziert werden; keine Raw-Snap-/Rohroster-Consumer-Umleitung.
- **Kein lückenloses Point-in-Time-Feature-Replay:** W−1-Lag ist notwendige, nicht hinreichende As-of-Garantie. Historische Revisions-/Publikationstermine und genaue frühe NFL-Spieler-Locks bleiben unbewiesen.
- **Cohort-Shift und Missingness:** Die retrospektive Vorwochen-NFL-Population umfasst nicht notwendigerweise neu aktivierte Spieler, während unsere sechs Fantasy-Teams Kader aus Sleeper besitzen. Fehlende Zielrecords dürfen nicht als DNP nachkodiert werden.
- **Keine inferenzstatistische Überlegenheitsbehauptung:** Wiederholte Spielerwochen und gemeinsame NFL-Spiele sind korreliert; Validierungs-Grid nicht unabhängig. Die deutliche Verbesserung gegenüber globaler Quote ist größtenteils leichte Status-Segmentierung.
- **Noch keine Integration in Monte Carlo:** CP3g-ESPN ist nur eine historische experimentelle Baseline. Die nächste Forschungsabnahme muss 2026 W5–10 auf den **gleichen damaligen Sleeper-Kadern und PWF/Decision-Windows-Snapshots** ausführen, mit sauberer Fantasy-Relevanz-Abdeckung, Pflichtslot-Fail-Close, Punkt-MAE, Bias, Unsicherheitsabdeckung und differenzierten Verfügbarkeits-Labels. Dann erst Manager-Effizienz und WinChance-Brier getrennt.
- **Keine Workload-Gleichsetzung:** `Played=true` kann wenige Snaps bedeuten. `P(volles Workload | played)` bleibt ein eigener Forschungspfad.

**CI-/Sicherheitsauswirkung:** Nur zwei neue Research-Artefakte im bestehenden `research/matchup-projections/2026/`-Owner; kein produktiver Test oder CI-Test-Router geändert, keine Veröffentlichung, kein neuer Workflow oder Writer, keine Änderung an `data-meta`. Lokaler Vollhistorien-CLI-Lauf steht zur unabhängigen Reproduktion aus; Research-Draft bleibt bis zur Abnahme ungemergt. **Rollback:** Revert dieser zwei Forschungsdateien.