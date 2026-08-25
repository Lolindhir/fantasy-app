# Source Metadata — Fantasy: 2026 RB rankings

- **Package ID:** `thescore-2026-08-21-fantasy-2026-rb-rankings`
- **Source kind:** `article`
- **Origin:** `thescore`
- **Title:** `Fantasy: 2026 RB rankings`
- **Publisher:** `theScore`
- **Author:** `Eric Patterson`
- **Publication date:** `unknown` (der bestehende Paketpfad trägt `2026-08-21`; dieses Datum wird hier nicht nachträglich als unabhängig verifiziert ausgegeben)
- **Original URL:** `https://www.thescore.com/news/3561786/fantasy-2026-rb-rankings`
- **Input method:** `user_provided_chat`
- **First captured for repository:** `2026-08-25`
- **Capture timezone:** `Europe/London`
- **Raw capture status:** `complete_user_provided_excerpt_not_full_article`
- **Source mode:** `living_article`
- **Registry source ID:** `thescore`

## Capture-Umfang

`raw.txt` enthält den im Chat bereitgestellten Ausschnitt des fortgeschriebenen theScore-RB-Rankings-Artikels, nicht den vollständigen Artikel. Der bereitgestellte Ausschnitt ist als Fidelity-Artefakt vollständig erhalten; fehlende Teile des Gesamtartikels werden nicht rekonstruiert.

Der Snapshot enthält drei konkrete Updates:

- Ashton Jeanty: Knöchelverletzung und daraus abgeleitete Ranking-Abstufung;
- Mike Washington Jr.: Handcuff-/Opportunity-These bei möglicher Jeanty-Abwesenheit;
- Jacory Croskey-Merritt: RB1-/Goal-Line-These für Washington.

## Quellenidentität und Kalibrierung

Titel, Publisher, Autor und Original-URL wurden am 2026-08-25 gegen die öffentlich auffindbare theScore-Seite verifiziert. Die Seite ist als Living Article zu behandeln, weil die Rankings und der Abschnitt `Latest updates` fortgeschrieben werden können.

Für die Quellengewichtung gilt `fantasy-management/sources/articles/thescore/SOURCE_NOTES.md`: direkt beobachtbare Injury-/Usage-/Depth-Chart-Evidenz ist stärker als redaktionelle Schlussfolgerungen wie `must-draft handcuff`, `RB1` oder eine konkrete Goal-Line-Prognose.

## Materialität

Das Paket überschreitet die Persistenzschwelle, weil es mehrere zeitkritische Rollen-/Injury-Signale dokumentiert:

- **Ashton Jeanty:** die Knöchelverletzung ist aktuelle Gegner-/Trade-Kontext-Evidenz; die Quelle geht bei der Ausfallprognose weiter als die derzeit belastbare Bestätigung.
- **Mike Washington Jr.:** die durch Jeantys Verletzung geöffneten First-Team-Reps sind ein echtes `injury_opened_opportunity`-Signal, auch wenn daraus kein sicherer Week-1-Lead-Back folgt.
- **Jacory Croskey-Merritt:** die RB1-These wird durch den aktuellen offiziellen Commanders-Depth-Chart und sein Schonungsmuster mit anderen etablierten Spielern gestützt; die konkrete Aussage über die Mehrheit der Goal-Line-Arbeit bleibt eine Projektion.

## Aktuelle Verifikation vom 2026-08-25

- Raiders HC Klint Kubiak bezeichnete Jeanty als `on the mend`; die Raiders nannten keinen konkreten Rückkehrzeitpunkt. NFL-Berichte ordnen die Verletzung als nicht langfristigen Knöchel-Sprain mit unbekannter Timeline ein.
- Raiders-Teamreporting dokumentiert, dass Mike Washington Jr. am 2026-08-24 erste exklusive First-Team-Reps erhielt, ausdrücklich als Ersatz für den verletzten Jeanty.
- Der aktuelle offizielle Commanders-Depth-Chart führt Jacory Croskey-Merritt an erster Stelle vor Rachaad White; Washington hielt Croskey-Merritt zudem in den ersten beiden Preseason-Spielen zusammen mit weiteren etablierten Spielern heraus.

## Mighty-Giants-/Monitoring-Auswirkung

Die aktuellen Operations-Daten vom 2026-08-25 klassifizieren Ashton Jeanty, Mike Washington und Jacory Croskey-Merritt jeweils als `league_owned`; keiner der drei steht im aktuellen Mighty-Giants-Roster.

Daraus folgt **keine neue dauerhafte `player-role-watch`- oder Todo-Konfiguration**:

- Free-Agent-Eskalation ist nicht anwendbar, weil die Spieler nicht fantasy-free-agent sind;
- gegnerische Roster und relevante Injury-/Role-Veränderungen gehören bereits zur vorgesehenen Daily-Monitoring-Population;
- der Artikel erzeugt daher historische Source-Evidenz und Research-/Trade-Kontext, aber keinen zusätzlichen manuellen Target-Eintrag.

## Bekannte dauerhafte Ableitungen

- Source Package vollständig archivieren.
- Keine neue Watch-/Todo-/Baseline-Konfiguration aus diesem Snapshot.

## Quellenstatus

Dieses Paket ist historische Evidenz. Verletzungstimeline, Rollen, Rankings, Marktwerte, Ownership und NFL-Teamkontext müssen bei späterer Verwendung erneut gegen aktuelle Repo-Daten und frische externe Quellen geprüft werden.
