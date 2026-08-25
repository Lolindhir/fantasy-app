# Source Metadata — Fantasy notes, analysis from Week 2 of NFL preseason

- **Package ID:** `thescore-2026-08-22-fantasy-notes-analysis-from-week-2-of-nfl-preseason`
- **Source kind:** `article`
- **Origin:** `thescore`
- **Title:** `Fantasy notes, analysis from Week 2 of NFL preseason`
- **Publisher:** `theScore`
- **Author:** `Eric Patterson`
- **Publication date:** `2026-08-22` (same-day publication inferred from theScore's relative timestamp observed on 2026-08-22)
- **Original URL:** `https://video.thescore.com/nfl/news/3572142/fantasy-notes-analysis-from-week-2-of-nfl-preseason`
- **Input method:** `user_provided_chat`
- **First captured for repository:** `2026-08-22`
- **Capture timezone:** `Europe/London`
- **Raw capture status:** `complete_user_provided_text`
- **Source mode:** `living_article`
- **Latest immutable snapshot:** `2026-08-25T12-51-00Z`
- **Registry source ID:** `thescore`

## Quellenidentität

Titel und Autor wurden vom Nutzer ergänzt und gegen die öffentlich auffindbare theScore-Originalseite verifiziert. Der im Chat bereitgestellte Volltext wird als Raw-Fidelity-Artefakt gespeichert. Falls theScore denselben Artikel später um weitere Preseason-Spiele ergänzt oder materiell ändert, ist die neue Fassung als zusätzlicher immutable Snapshot dieses Living Articles zu behandeln und nicht als unabhängige zweite Quelle.

Für die wiederkehrende Publisher-Kalibrierung gilt `fantasy-management/_ai/source-registry.json -> thescore` beziehungsweise `fantasy-management/sources/articles/thescore/SOURCE_NOTES.md`. Direkt beobachtbare Usage-/Snap-/Sequencing-Claims werden höher gewichtet als daraus abgeleitete Hierarchie- oder Draft-Empfehlungen.

## Capture-Historie

- `legacy_root_capture_2026-08-22`: vollständiger, vom Nutzer bereitgestellter Erst-Capture in den Root-Artefakten `raw.txt`, `article.md` und `extraction.json`.
- `2026-08-25T12-51-00Z`: vom Nutzer bereitgestellte spätere Fassung unter `snapshots/2026-08-25T12-51-00Z/`; enthält neue Ashton-Jeanty- und Jacory-Croskey-Merritt-Claims sowie einen materiell geänderten Mike-Washington-Claim. Fehlende ältere Claims dieser kürzeren Fassung werden nicht als Retraktion interpretiert, solange die Quelle sie nicht ausdrücklich zurücknimmt oder widerspricht.

## Materialität

Das Paket überschreitet die Persistenzschwelle klar:

- **Tre Tucker:** neues dauerhaftes `player-role-watch` aufgrund des indirekten `held_out_with_starters`-Hierarchiesignals und der im Artikel vertretenen WR1-These.
- **Jonathon Brooks:** bestehendes Watch-Target wird auf aktuelle Backfield-Konkurrenz, Goal-Line-/Passing-Down-Usage und Pass Protection geschärft; der Start bei Chuba Hubbards Abwesenheit bleibt als `injury_opened_opportunity` zu interpretieren.
- **De'Zhaun Stribling:** wiederholte Preseason-Produktion plus drei Receptions von Brock Purdy liefern zusätzliche Starter-Drive-/Opportunity-Evidenz für einen bereits gehaltenen Mighty-Giants-Prospect.
- **Kaelon Black:** der Artikel liefert ein relevantes `backup_hierarchy_change`-Signal für einen bereits gehaltenen Mighty-Giants-Prospect.
- **Jaylen Waddle:** positiver Broncos-Debüt-Claim bestätigt kurzfristige Win-Now-Relevanz, erzeugt aber keine neue dauerhafte Konfiguration.
- **Ashton Jeanty (Snapshot 2026-08-25):** neuer Injury-Claim; die Knöchelverstauchung und unbekannte Schwere sind Source-Evidenz, während die im Artikel angenommene mögliche Abwesenheit zum Saisonstart nicht als unabhängig bestätigte Availability-Wahrheit behandelt wird.
- **Mike Washington (Snapshot 2026-08-25):** der frühere reine Explosivitäts-/Contingent-Claim wird materiell zur Handcuff-These aufgewertet. Aktuelle Repo-Daten führen ihn jedoch als `opponent_rostered`; deshalb entsteht kein neuer manueller `player-role-watch`-Target.
- **Jacory Croskey-Merritt (Snapshot 2026-08-25):** neuer Source-Claim zu möglichem Washington-RB1- und Goal-Line-Aufstieg. Er ist ebenfalls `opponent_rostered` und bleibt ohne konkreten Trade-/Strategiegrund im breiten Gegner-Monitoring statt in der manuellen Role-Watch.

## Bekannte dauerhafte Ableitungen

- `fantasy-management/automation/target-sets/player-role-watch.json`
  - neu aus dem Erst-Capture: `tre-tucker-2026`
  - geschärft aus dem Erst-Capture: `jonathon-brooks-2026`
  - keine neue Target-Aufnahme aus dem Snapshot `2026-08-25T12-51-00Z`, da die beiden potenziellen Role-Watch-Kandidaten Mike Washington und Jacory Croskey-Merritt aktuell gegnerisch gerostert sind.
- `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`
  - aus dem Snapshot `2026-08-25T12-51-00Z`: Opponent-Roster-Eskalation in gezieltes manuelles Monitoring präzisiert.

Keine Observation-State-Baseline wurde durch die reine Artikelpersistierung automatisch fortgeschrieben. Qualitative Baselines bleiben nach der aktuellen Fantasy-Operations-Architektur ein separater, ausdrücklich kontrollierter Persistierungsschritt.

## Quellenstatus

Dieses Paket ist historische Source-Evidenz. Rollen, Verletzungen, Depth Charts, ADP, Marktwerte, Fantasy-Ownership und NFL-Teamkontext müssen bei späterer Verwendung erneut gegen aktuelle Repo-Daten und frische externe Quellen geprüft werden.
