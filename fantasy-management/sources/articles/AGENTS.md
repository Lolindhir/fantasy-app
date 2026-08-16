# Article Source Agent Instructions

Diese Regeln gelten für alle Arbeiten unter `fantasy-management/sources/articles/` und für jede Aufgabe, bei der ein einzelner Artikel, News-Text, Camp-/Preseason-Überblick oder vergleichbarer nutzerbereitgestellter Text als Fantasy-Management-Quelle ausgewertet oder persistiert werden soll.

## Pflichtlektüre

Vor Artikelarbeit lesen:

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. `fantasy-management/_ai/ARTICLE_SOURCE_MODEL.md`
6. `fantasy-management/sources/README.md`
7. `fantasy-management/sources/articles/README.md`
8. das konkrete `SOURCE.md`, `raw.txt`, `article.md` und `extraction.json`, wenn ein bestehendes Paket bearbeitet wird
9. aktuelle Repo-/Liga-Daten und frische externe Quellen, sobald aus der Quelle eine aktuelle Fantasy-Aussage oder Entscheidung abgeleitet werden soll

Bei Preseason-/Camp-Artikeln ist zusätzlich `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md` verpflichtend.

## Fidelity-Regel

- Direkt vom Nutzer bereitgestellter Rohtext darf als `raw.txt` exakt persistiert werden.
- `raw.txt` darf nicht sprachlich verbessert, zusammengefasst oder aus Erinnerungen rekonstruiert werden.
- Ist der exakte Raw-Input nicht mehr verfügbar, muss das Paket diesen Mangel ausdrücklich ausweisen; niemals eine Rekonstruktion als Original ausgeben.
- `article.md` darf denselben vollständigen Nutzertext lesefreundlich strukturieren, wenn Raw vorhanden ist.
- Ohne Raw muss `article.md` sichtbar als Rekonstruktion/Source Digest gekennzeichnet sein.

## Trennungsregel

Immer getrennt halten:

1. **Source Claim** – was der Artikel sagt;
2. **Verification** – was aktuelle Repo-Daten oder weitere Quellen bestätigen/widerlegen;
3. **Interpretation** – was der Claim für das tatsächliche Ligaformat und Mighty Giants bedeutet;
4. **Decision/Write** – welche dauerhafte Handlung oder Regeländerung daraus folgt.

Ein Artikel darf richtige Beobachtungen und falsche oder zu aggressive Fantasy-Schlüsse gleichzeitig enthalten. Persistenz der Quelle bedeutet nicht Übernahme ihrer Meinung.

## Write-Regel

- `Artikel auswerten` / `nur auswerten` ist read-only.
- `nur Quelle sichern` erlaubt nur das Source Package.
- `Artikel auswerten und persistieren` erlaubt Source Package plus die im gleichen Arbeitsgang klar ausgewiesenen fachlichen Ableitungen innerhalb des normalen Write-Scope.
- Eine anschließende `Freigabe` gilt nur für den unmittelbar zuvor beschriebenen Scope.
- GitHub-Actions- oder sonstige separat genehmigungspflichtige technische Aktivierungen bleiben separat freigabepflichtig.

## Copyright-/URL-Regel

Ein vollständiges Raw-Webseitenarchiv wird nicht automatisch aus einer URL erzeugt. Vollständiges `raw.txt` ist für direkt nutzerbereitgestellten oder anderweitig rechtmäßig vollständig vorliegenden Inhalt vorgesehen. Bei URL-only-Quellen Provenienz, zulässige kurze Belege, strukturierte Claims und eigene Zusammenfassung speichern.

## Materialität

Persistenz vorschlagen, wenn der Artikel mindestens eine materielle Roster-/Draft-/Trade-/FA-Bewertung verändert, einen dauerhaften Watch-Kandidaten erzeugt, eine wichtige These bestätigt/widerlegt, schwer rekonstruierbare Usage-/Camp-/Injury-Evidenz enthält oder eine neue wiederverwendbare Regel auslöst.

## Dynamische Wahrheit

Article Packages sind historische Evidenz. Rollen, Verletzungen, Rankings, Marktwerte, ADP, Ownership und NFL-Teamkontext bei späterer Verwendung immer neu prüfen, wenn sie entscheidungsrelevant sind.

## Registry

Nicht jeden Einzelartikel in `source-registry.json` eintragen. Erst bei wiederholter Nutzung desselben Publishers/Autors, dauerhafter Qualitätsgewichtung oder geplanter Automatisierung einen Registry-Eintrag erwägen und gegebenenfalls vorschlagen.

## Sprache

Menschenlesbare Paketdokumentation und Interpretationshinweise werden auf Deutsch geführt, sofern der Nutzer nichts anderes verlangt. Der originale Raw-Text bleibt selbstverständlich in seiner Originalsprache.
