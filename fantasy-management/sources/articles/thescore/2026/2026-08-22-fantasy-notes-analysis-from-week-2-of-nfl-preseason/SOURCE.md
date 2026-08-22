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

## Quellenidentität

Titel und Autor wurden vom Nutzer ergänzt und gegen die öffentlich auffindbare theScore-Originalseite verifiziert. Der im Chat bereitgestellte Volltext wird als Raw-Fidelity-Artefakt gespeichert. Falls theScore denselben Artikel später um weitere Preseason-Spiele ergänzt oder materiell ändert, ist die neue Fassung als zusätzlicher immutable Snapshot dieses Living Articles zu behandeln und nicht als unabhängige zweite Quelle.

## Materialität

Das Paket überschreitet die Persistenzschwelle klar:

- **Tre Tucker:** neues dauerhaftes `player-role-watch` aufgrund des indirekten `held_out_with_starters`-Hierarchiesignals und der im Artikel vertretenen WR1-These.
- **Jonathon Brooks:** bestehendes Watch-Target wird auf aktuelle Backfield-Konkurrenz, Goal-Line-/Passing-Down-Usage und Pass Protection geschärft; der Start bei Chuba Hubbards Abwesenheit bleibt als `injury_opened_opportunity` zu interpretieren.
- **De'Zhaun Stribling:** wiederholte Preseason-Produktion plus drei Receptions von Brock Purdy liefern zusätzliche Starter-Drive-/Opportunity-Evidenz für einen bereits gehaltenen Mighty-Giants-Prospect.
- **Kaelon Black:** der Artikel liefert ein relevantes `backup_hierarchy_change`-Signal für einen bereits gehaltenen Mighty-Giants-Prospect.
- **Jaylen Waddle:** positiver Broncos-Debüt-Claim bestätigt kurzfristige Win-Now-Relevanz, erzeugt aber keine neue dauerhafte Konfiguration.

## Bekannte dauerhafte Ableitungen

- `fantasy-management/automation/target-sets/player-role-watch.json`
  - neu: `tre-tucker-2026`
  - geschärft: `jonathon-brooks-2026`

Keine Observation-State-Baseline wurde durch die reine Artikelpersistierung automatisch fortgeschrieben. Qualitative Baselines bleiben nach der aktuellen Fantasy-Operations-Architektur ein separater, ausdrücklich kontrollierter Persistierungsschritt.

## Quellenstatus

Dieses Paket ist historische Source-Evidenz. Rollen, Verletzungen, Depth Charts, ADP, Marktwerte, Fantasy-Ownership und NFL-Teamkontext müssen bei späterer Verwendung erneut gegen aktuelle Repo-Daten und frische externe Quellen geprüft werden.
