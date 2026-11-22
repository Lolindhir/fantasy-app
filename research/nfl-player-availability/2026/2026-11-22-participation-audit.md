# nflverse Participation als Played-Evidenz: Quellen-, Rechte- und Vergleichsaudit (Issue #1612, CP0 bis CP2)

Stand: 2026-11-22. Status: `partially_supported` (positive Evidenz belegt, Integration nicht freigegeben). Rein lesend: kein Writer, keine Daten, keine Consumer geändert.
Reproduktion: `participation_audit.py` (gleicher Ordner), Ergebnisse je Saison 2016 bis 2025 in `2026-11-22-participation-audit-results.json` (Repo-Stand `64fd5048`).

## 1. Quelle (belegt)

- Release `pbp_participation` in `nflverse/nflverse-data`, Dateien `pbp_participation_<season>.csv`, Saisons 2016 bis 2025 vorhanden, **2026 liefert 404** (nicht annehmen, dass es existiert).
- 2016 bis 2022 NGS, ab 2023 FTN; FTN liefert erst nach der gesamten Saison inkl. Postseason, nie in-season (nflreadr-Dokumentation).
- Beobachtete Größe: 21 bis 22 MB (2016 bis 2022), rund 49 bis 50 MB (2023 bis 2025) je Saison. SHA-256 der Pilot-Dateien stehen im Ergebnis-JSON (`participation_sha256`, 2022/2024/2025 und die übrigen Saisons). Die GitHub-API und die Release-Seite waren aus der Umgebung nicht lesbar, daher **kein offizieller Asset-Digest geprüft** (Annahme: wie bei anderen nflverse-Quellen verfügbar, vor Aufnahme nachzuprüfen).
- **Formatwechsel (wichtige Entdeckung):** `players_on_play` ist bis 2022 eine Liste numerischer `gsis_it_id`, ab 2023 GSIS. `offense_players` und `defense_players` enthalten in **allen** Saisons echte GSIS-IDs (`00-…`). Die Vereinigung beider Listen ist die einzig saisonübergreifend brauchbare positive Evidenz; kein zusätzlicher Crosswalk nötig.

## 2. Rechte (belegt, keine Rechtsberatung)

- Das Repo-Level-LICENSE der nflverse-Daten ist CC BY 4.0, aber `load_participation` sagt ausdrücklich **CC BY-SA 4.0**, Attribution an „FTN Data via nflverse“ (ab 2023) bzw. „NFL NextGenStats via nflverse“ (bis 2022).
- ShareAlike greift bei Weitergabe von Original oder Bearbeitung. Unser Repo und GitHub Pages (`public/data`) sind öffentlich; Roh-Kopien im Repo oder ein Release-Asset wären Weitergabe. Offene Rechtsfrage (nicht entschieden): ob ein reines Teilnahme-Faktum je Spieler/Spiel eine Bearbeitung im Sinne von BY-SA ist.
- Nicht lesbar waren: Release-Seite, nflverse-data Issue 51, nflverse-pbp Issue 80.

## 3. Ergebnisse je Saison (belegt, Absolutwerte)

Population = Datensätze des bestehenden Produkts `nfl-player-availability-v2`. „Positiv“ = Spieler hat in dem Spiel mindestens einen Eintrag in offense/defense_players, aufgelöst über bestehende GSIS-Zuordnung (kein Namensabgleich).

| Saison | Spiele Part./Plan | Spieler-Spiele positiv | PFR/Stats-played | davon auch Part. | nur PFR/Stats | unknown im Produkt | davon durch Part. belegt | Widersprüche zu not-played | davon mit echtem Spielzug |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | 267/267 | 23.674 | 23.888 | 23.663 | 225 | 8 | 3 | 6 | 5 |
| 2017 | 267/267 | 23.865 | 23.863 | 23.863 | 0 | 0 | 0 | 0 | 0 |
| 2018 | 267/267 | 23.939 | 23.877 | 23.877 | 0 | 0 | 0 | 2 | 0 |
| 2019 | 267/267 | 23.888 | 23.848 | 23.844 | 4 | 7 | 7 | 3 | 1 |
| 2020 | 269/269 | 25.000 | 24.987 | 24.987 | 0 | 6 | 6 | 1 | 0 |
| 2021 | 285/285 | 26.470 | 26.450 | 26.449 | 1 | 1 | 1 | 4 | 1 |
| 2022 | 284/284 | 26.381 | 26.375 | 26.375 | 0 | 1 | 0 | 0 | 0 |
| 2023 | 285/285 | 26.542 | 26.530 | 26.530 | 0 | 22 | 8 | 3 | 1 |
| 2024 | 285/285 | 26.617 | 26.588 | 26.581 | 7 | 12 | 12 | 2 | 1 |
| 2025 | 285/285 | 26.620 | 26.589 | 26.577 | 12 | 7 | 5 | 3 | 1 |

(Pflichtsaisons 2022, 2024, 2025 plus 2016 bis 2021 und 2023 zur Einordnung.)

Kernaussagen:

1. **Zusätzlich sicher belegte Einsätze:** Von 64 `unknown`-Spieler-Spielen (alle Evidenz `snap-counts-identity-gap`, 2016 bis 2025) belegt Participation **42** als gespielt (2022: 0 von 1, 2024: 12 von 12, 2025: 5 von 7). In allen 42 Fällen existiert mindestens ein echter Spielzug (Pass, Run, Kickoff, Punt, FG, PAT). Es sind überwiegend Special-Teams-lastige Spieler (typisch 5 bis 25 Plays, davon der Großteil Special Teams). 22 bleiben unknown (Participation enthält sie nicht, daraus folgt nichts).
2. **Coverage:** Jedes Planspiel (REG und POST) ist enthalten, kein Participation-Spiel fehlt im Kalender, keine Dubletten je Spiel und Play. Ab 2024 gibt es keine verwaisten Plays gegenüber der Original-PBP und alle Kickoff-, Punt-, FG- und PAT-Plays sind abgedeckt (z. B. 2025: 7.439 von 7.439). 2016 bis 2022 enthalten zusätzlich rund 700 bis 780 Plays, die in der Original-PBP nicht vorkommen (praktisch alle mit leeren Spielerlisten), plus rund 4.000 bis 4.400 Plays mit leeren Listen (nur `no_play` oder ohne Typ). Bei echten Plays gibt es keine Lücke.
3. **Participation ist nicht vollständig:** PFR/Stats weisen je Saison 0 bis 12 (2016: 225) Spieler-Spiele aus, die Participation nicht enthält. Daraus folgt: Fehlen in Participation ist **keine** Evidenz für not-played.
4. **Special Teams:** PFR-ST-only-Spieler (Offense und Defense 0, ST > 0) sind in Participation praktisch vollständig enthalten (z. B. 2024: 5.030 von 5.030, 2025: 5.045 von 5.048). Participation kennt ST-Plays, aber kein ST-Snapcount; wir leiten daraus keine Snapzahlen ab.
5. **Oakland 2016 bis 2019:** Alle OAK-Spiele sind im Kalender, Positive und PFR-played stimmen praktisch überein (2017: 1.433 von 1.433, 2018: 1.434 von 1.437, 2019: 1.434 von 1.435, 2016: 1.517 von 1.525).
6. **Identität:** In keiner Saison ein GSIS mit zwei kanonischen Besitzern, 0 unaufgelöste GSIS im Pilot. Keine Namensabgleiche.
7. **Qualität der Listen:** 2023 bis 2025 sind `players_on_play` und die Vereinigung identisch und `n_offense/n_defense` stimmen, mit je 1 bis 2 Dubletten innerhalb einer Liste je Saison. 2019 hat 467 Plays mit Dubletten in `defense_players`. Nach Set-Bildung unkritisch.
8. **Außerhalb der Produktpopulation:** 184 Spieler-Spiele (2016 bis 2025, meist 2018: 60, 2019: 34, 2025: 35) sind positiv, haben aber im Produkt keinen Datensatz (Position nicht in der Fantasy-Auswahl oder Spieler nicht ACT/INA). Sie ändern das Produkt nicht, solange die Population gleich bleibt.

## 4. Widersprüche (belegt, nicht aufgelöst)

24 Spieler-Spiele, in denen das Produkt `not-played` hat, Participation aber positiv ist:

- 14 davon haben ausschließlich `no_play`-Plays (Strafen, annullierte Plays) und meist nur 1 Eintrag. Plausibel: Spieler stand in einer Formation, zählte aber nicht als Snap. Ein No-Play ist kein sicherer Einsatz.
- 10 haben mindestens einen echten Spielzug, davon 4 mit auffällig vielen Plays (78, 72, 26 und 21 Plays). Das spricht für **fehlerhafte PFR-Zeilen oder -Zuordnung**, das heißt für falsche `not-played` im heutigen Produkt (Roster-Status RES bei 21 Plays, d. h. ggf. auch veralteter Roster-Status). Kein stilles Überschreiben, sondern sichtbar machen.

## 5. Unsicherheiten und Annahmen

- Die Participation-Listen sind eine Sicht der Quelle, keine Garantie (Datenquelle NGS ist 2023 eingestellt worden; FTN-Erhebung wird nicht von uns geprüft).
- Annahme (nicht belegt): Eine `no_play`-Teilnahme zählt nicht als Snap. Die Regel „nur echte Spielzugtypen zählen als positive Evidenz“ ist eine Empfehlung.
- Keine Prozentwerte „Übereinstimmung“ als Qualitätsaussage, nur Absolutzahlen.
- Revisionen: Der Pilot nutzt einen Download-Stand vom 2026-11-22; Änderungen der Upstream-Dateien wurden nicht beobachtet.
