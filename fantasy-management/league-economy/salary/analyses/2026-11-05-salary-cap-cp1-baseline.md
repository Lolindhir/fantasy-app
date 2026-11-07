# CP1 – Reproduzierbare Baseline der Salary-/League-Economy-Forschung

> **Stand:** 05.11.2026. **Zentrales Work Package:** [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344).  
> **Status:** Empirische Basis und methodischer Handoff; keine neue Liga-/Salary-Regel, kein A/B/C-Wirkungstest und keine neue Konzeptentscheidung.  
> **Freeze:** Aktuelle 2026er Quellen aus Commit **799be2a25203f18face8185303f32b31be3d40a7** (05.11.2026, 19:40:24 UTC, finale Scoring-Woche 8). Ältere 2026er Kaderstände jeweils durch eigene Commit-Refs fixiert.

## 1. Designfrage und CP1-Umfang

Ziel ist, zu prüfen, ob das Salary Cap einen einmal aufgebauten Talentvorsprung daran hindert, **ohne relevante wirtschaftliche Cap-/Asset-Abwägungen** dauerhaft konserviert und weiter ausgebaut zu werden. Gutes Management, Draft-/Trade-Entscheidungen und wiederholter sportlicher Erfolg sollen ausdrücklich möglich bleiben. Auch „das bestehende System genügt weitgehend“ ist eine zulässige Hypothese.

**CP1 leistet:** As-of- und Modellmatrix, reproduzierbare Roster- und Cap-Vergleichswerte, historisches Transaktions-/Draft-Inventar, Kaderkontinuität und klar benannte Datenlücken. **CP1 leistet nicht:** neue Ligaentscheidungen, fiktive Managerreaktionen, sichere vergangene Tradegebote oder hypothetische A/B/C-Ergebnisse.

Zwei getrennte Inputs: [Flo-Fallstudie 2026](2026-11-05-flo-cap-impact-case-study.md) enthält historische Evidenz; [Handoff zu Designzielen](2026-11-05-salary-cap-design-goals-handoff.md) enthält Ziele und Hypothesen, **keine** neue Fachregel.

## 2. Modell- und Statusmatrix

| Thema | Bestätigter / aktiver Stand | Grenze dieser Baseline |
|---|---|---|
| Heute aktives Salary | Drei abgeschlossene NFL-Saisons, aktuelle Salary-Preise aus produktivem Modell | Salary und SalaryProjected unterscheiden; keine wöchentliche Vertragsneuberechnung unterstellen |
| Heutiges Salary Cap | Endogen aus den ligaweit 120 höchsten Salaries (6 × 20), durchschnittliche Top-20-Team-Basis × 0,9; 20 teuerste gehaltene Spieler je Team | Geltende jährliche Cap-Deadline, kein durchgängig verbindliches In-Season-Cap |
| A – Istzustand | Aktuelle Salary-Preise + Deadline | Beobachtungsbaseline |
| B – nur permanenter Vollzug | **Identische Salary-Preise wie A**, aber Cap bei relevanten Transaktionen ganzjährig verbindlich | Unbeschlossene Testregel, Wirkung erst in CP2 |
| C – zwei Hebel | Führende rank-/positionsbasierte Criticality (Centered-25, Top-10%-Referenz, k=1,5) + permanentes Cap | Unbeschlossene Testregel; Cap aus neuen Salaries **erneut endogen** |
| D – optionale Kontrolle | Criticality-Salary + bisherige Deadline | Für isolierte Formelwirkung bei Bedarf |
| Rookie Y1–Y3 | **Konzeptentscheidung, nicht aktive Regel:** 65 % Fantasy-/35 % NFL-Draft in Y1, Y2 125 %, Y3 150 % der festen Y1-Dollarbasis, Y4 normales Salary | Nicht stillschweigend in A/B/C aktivieren |
| Gleitendes Minimum | **Konzeptentscheidung, nicht aktiv:** ab Y4 Salary = max(P, M + 0,50 × P), beschlossen als Konzept am 11.10.2026 | Das früher **voll additive** Minimum aus dem Bericht vom 05.10. ist überholt |
| Dead Cap | **Konzeptentscheidung, nicht aktiv:** Cut als Retained Salary; Tenure 0/1/2/3+ = 50/30/15/5 %; Reset beim nächsten Salary Check | Keine mehrjährige Schuld, kein stillschweigender zusätzlicher Transaktionsblocker |
| Top 25/30, Bankkosten, Rookie-Y4-Option, Trade-Salary-Retention, Rollover | Neue, **offene** Hypothesen | Erst prüfen, falls die schlanke A/B/C-Reihe relevante Zielkonflikte nicht löst |

**Verwechslungsgefahr:** Das historische „Szenario C“ der Salary-Gesamtsimulation vom 05.10. mit voll additivem Minimum (Cap 478,9 Mio.) ist **nicht** das neue Szenario C des Salary-Cap-Vollzugs. Die Criticality-Referenz 8,4417 stammt aus der neuen Liga-Scoring-Simulation; die frühere 8,6425 bezog sich auf eine andere Scoring-Basis. Beide sind datierte Modellstände, keine neuen aktiven Regeln.

## 3. Quellen-Freeze und Datenzeitpunkte

### 3.1 Sechs historische Kaderstände 2026

| Kontrollpunkt | Eingefrorene League.json-Commit-Referenz | Damals veröffentlichtes Cap |
|---|---|---:|
| 07.06. vor Juni-Cuts | [5b4ed63172deae79759e7150f8511bd2ea3edb4e](https://github.com/Lolindhir/fantasy-app/blob/5b4ed63172deae79759e7150f8511bd2ea3edb4e/public/data/League.json) | 434.255.984 $ |
| 09.06. nach Juni-Cuts | [7ece134fec39741aba8e82bda554f8f13e8bead4](https://github.com/Lolindhir/fantasy-app/blob/7ece134fec39741aba8e82bda554f8f13e8bead4/public/data/League.json) | 434.255.984 $ |
| 29.06. vor Cap-Deadline | [85e22feb064fdaf2257d6c3149c8d1655ada0908](https://github.com/Lolindhir/fantasy-app/blob/85e22feb064fdaf2257d6c3149c8d1655ada0908/public/data/League.json) | 434.255.984 $ |
| 25.08. nach Rookie-, vor FA-Draft | [539aae40da3de444000805cea3170a116fae129d](https://github.com/Lolindhir/fantasy-app/blob/539aae40da3de444000805cea3170a116fae129d/public/data/League.json) | 434.255.984 $ |
| 09.09. nach FA-Draft | [b40956172a704ff616008d7835f527b86f128063](https://github.com/Lolindhir/fantasy-app/blob/b40956172a704ff616008d7835f527b86f128063/public/data/League.json) | 434.255.984 $ |
| 05.11. W8 final | [799be2a25203f18face8185303f32b31be3d40a7](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/League.json) | 427.653.631 $ |

**Einheitliche rückblickende Spielerpreise:** [Salary-Spielertabelle 05.10.2026](2026-10-05-salary-simulation-players.csv), **Blob 96ef8deac5930ffc3dc84dbf12cbbf4719c58489**, 1.268 Spieler; verwendet wird ausschließlich **salary_published** (alte produktive Formel), keine Criticality-/Rookie-/Minimum-Versuchsspalte. Diese nachträglichen Preise sind **kein** individueller Salary-Snapshot vom Juni.

### 3.2 Fixierte Archive und aktuelles Readmodel

Alle folgenden Dateien werden für den Freeze am **Commit 799be2a25203f18face8185303f32b31be3d40a7** gelesen, nicht unbegrenzt über den künftigen main-Stand.

- [TeamCapOutlook.json](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/TeamCapOutlook.json), Blob **584ffadf7ab1a6c7c4dc156dc9956c6c165fcff3**; FinalScoredWeek 8, Current SalaryCap 427.653.631 $, SalaryCapProjected 451.769.671 $.
- [Transactions 2026](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/Transactions.json), Blob **0aa85766a962a9d499fe5610a269771dd3b02ce1**.
- [Transactions 2025](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/past_seasons/Transactions/Transactions_2025.json), Blob **dcbde96543113ebaf2276359af8b5a5ff1b13d79**; [Transactions 2024](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/past_seasons/Transactions/Transactions_2024.json), Blob **840140d0d4f5823a39d1478fc98710c39ae0953e**.
- [Drafts 2026 und Zukunft](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/Drafts.json), Blob **b5d45766520f0a1f1b6b80a38c618962fc417a19**; [Drafts 2025](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/past_seasons/Drafts/Drafts_2025.json), Blob **86f6f19a1fff07c3656930b6d03ac8f3293617ae**; [Drafts 2024](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/past_seasons/Drafts/Drafts_2024.json), Blob **861c7325eaec346da731501dbd901e8fe2cdef4c**.
- [Rosters 2025](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/data-source/leagues/nfl-reise/seasons/2025/rosters.json), Blob **76e7d2f77566e73b56cad44421ef4bd868af6c9d**; [Rosters 2024](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/data-source/leagues/nfl-reise/seasons/2024/rosters.json), Blob **2e4ce37d908de4781ff2b1bf1ae4b1d7d9e2a19a**.

## 4. Konstante Top-20-Belegung auf den sechs 2026er Kaderständen

Pro Team: eindeutige PlayerIDs aus **Teams[].Roster** (die enthaltenen Taxi-/Reserve-Spieler werden **nicht** nochmals hinzugefügt); je ID **salary_published** aus demselben Oktober-Datensatz; absteigend sortieren und die ersten 20 addieren. Nach jedem Cut Top 20 neu bilden. An allen sechs Zeitpunkten **0 fehlende PlayerIDs** im Salary-Datensatz.

| Team | 07.06. | 09.06. | 29.06. | 25.08. | 09.09. | 05.11. |
|---|---:|---:|---:|---:|---:|---:|
| Mighty Giants | 426,93 | 426,93 | 427,16 | 415,37 | 416,83 | 440,46 |
| Ruhr Valley Packers | 462,08 | 462,08 | 427,48 | 427,48 | 464,95 | 460,08 |
| Just Bill (Flo) | 542,99 | 433,90 | 433,90 | 433,90 | 449,25 | 510,87 |
| Mammoth Marauders (Jan) | 459,80 | 459,80 | 425,28 | 425,28 | 481,64 | 484,31 |
| DennisLACards | 409,58 | 409,58 | 409,58 | 409,58 | 411,18 | 348,17 |
| TimpaBay | 429,31 | 429,31 | 429,01 | 429,01 | 475,11 | 460,50 |
| **Cap des jeweiligen Snapshots** | **434,26** | **434,26** | **434,26** | **434,26** | **434,26** | **427,65** |
| **Rechnerisch oberhalb** | **3/6** | **2/6** | **0/6** | **0/6** | **4/6** | **5/6** |

**Einheit:** Mio. $. Die identische spätere Salary-Preisbasis ermöglicht einen internen historischen Vergleich, aber **keine centgenaue historische Legalitätsprüfung**. Die Cap-Werte stammen aus den jeweils archivierten League-Dateien; die individuellen Salaries aus Oktober. Die Folge **3/6 → 0/6 → 4/6** ist ein wichtiger **Prüftrigger** für den Vollzugszeitpunkt, kein bereits bewiesener Effekt des hypothetischen permanenten Caps.

### Gegencheck mit dem aktuellen W8-Cap-Readmodel

Im eingefrorenen TeamCapOutlook stimmt die Top-20-Belegung für **6/6 aktuelle Teams dollar-genau** mit der oben verwendeten salary_published-Tabelle überein.

| Team | Current.Usage | Differenz zu aktuellem Cap | Projected.Usage (nur Outlook) |
|---|---:|---:|---:|
| Mighty Giants | 440,46 Mio. | +12,81 Mio. | 507,86 Mio. |
| Ruhr Valley Packers | 460,08 Mio. | +32,43 Mio. | 474,12 Mio. |
| Just Bill | 510,87 Mio. | **+83,22 Mio.** | 555,24 Mio. |
| Mammoth Marauders | 484,31 Mio. | +56,65 Mio. | 511,54 Mio. |
| DennisLACards | 348,17 Mio. | –79,48 Mio. | 372,32 Mio. |
| TimpaBay | 460,50 Mio. | +32,85 Mio. | 507,51 Mio. |

Flo genau: **510.871.937 $ − 427.653.631 $ = +83.218.306 $**. Das ist ein tatsächlicher Snapshot des Cap-Readmodels, **kein** historischer Regelverstoß. Der frühere Cap-Wert von 428,89 Mio. stammt aus einem anderen Datenstand und wird hier nicht vermischt.

## 5. Transaktionen, Drafts und Kaderkontinuität 2024–2026

**Zählregeln:** Abgeschlossene Trades getrennt; fehlgeschlagene Waiver-Claims zählen nicht als erfolgreiche Adds. **Reiner Cut** = Status complete, kein Trade, mindestens ein Drops-Eintrag, **kein** Adds-Eintrag. 2026-Stichtag 01.07.2026, 00:00 UTC. 2026 ist im Freeze noch **nicht abgeschlossen**.

| Saison | Transaktionseinträge | Abgeschlossen | Trades abgeschlossen | Reine Cuts |
|---|---:|---:|---:|---:|
| 2024 | 179 | 132 | 7 | 7 |
| 2025 | 204 | 127 | 2 | 21 |
| 2026 bis 05.11. | 143 | 121 | 11 | 66 |

Von den 2026er reinen Cuts: **31 vor** und **35 nach** dem Stichtag; von den Trades **5 vor** und **6 danach**.

| Team | Reine Cuts vor 01.07. | Danach | Trade-Beteiligungen 2026 |
|---|---:|---:|---:|
| Mighty Giants | 0 | 7 | 9 |
| Ruhr Valley Packers | 9 | 5 | 3 |
| Just Bill | 10 | 3 | 2 |
| Mammoth Marauders | 4 | 9 | 2 |
| DennisLACards | 4 | 7 | 4 |
| TimpaBay | 4 | 4 | 2 |

Ein Trade wird ligaweit **einmal**, aber pro teilnehmendem Team bei beiden gezählt.

**Draft-Kohorten:** 2024 archiviert ein **initialer Free-Agent-/Ligadraft mit 162 Picks**, **kein** vergleichbarer separater Rookie-Draft. 2025: **30** Rookie-Picks, am 05.11. noch **20** Spieler ligaweit gehalten, **14** noch vom ursprünglichen Draft-Team. 2026: **30** Rookie- und **30** Free-Agent-Picks; von den Rookies noch **27** ligaweit gehalten, **23** beim ursprünglichen Draft-Team. Diese Kennzahl misst **Bestand**, nicht durchgehendes Halten, Starts, Cut/Re-Adds oder den Wert langfristiger Verträge. Das ist Gegenstand von CP3.

**Roster-Identität:** Archivierte 2024/25-Kader aus Source-Daten, Stand 2026 aus dem fixierten League-Snapshot; verglichen über die Sleeper-PlayerID in ProviderMappings.

| Team | Aus archiviertem 2024er Roster im 2025er Roster | Aus 2025er Roster am 05.11.2026 noch gehalten |
|---|---:|---:|
| Mighty Giants | 16/27 | 20/33 |
| Ruhr Valley Packers | 19/27 | 19/33 |
| Just Bill | 20/27 | 19/33 |
| Mammoth Marauders | 19/27 | 23/33 |
| DennisLACards | 21/27 | 16/30 |
| TimpaBay | 18/27 | 21/30 |

Das misst weder Starter-Leistung noch den historischen Cap-Verbrauch dieser Spieler; Archive und laufende Saison sind verschiedene Stichtage.

## 6. Flo als Cross-Check, nicht als alleiniger Maßstab

- Juni-Cuts (07.→09.06.): **542.987.565 → 433.901.493 $**, also **109.086.072 $** Top-20-Entlastung bei **identischer rückblickender** Salary-Basis. Flo behielt **8/10** der retrospektiv teuersten zehn Spieler seines 07.06.-Kaders und **13/20** seiner vorherigen Top 20.
- Nach dem FA-Draft 09.09.: **449,25 Mio. $** in derselben Rückrechnung. Flo stand nach Week 8 **7–1**. Die **CMC- und Goff-Trades vom 03.11.** kamen erst **nach** dieser Bilanz.
- Am fixierten 05.11.-Stand: **+83.218.306 $** gegenüber dem **Current Cap**. Das dokumentiert sowohl **reale erzwungene Umverteilung** als auch **spätere erneute Aufrüstung**.
- Die früh vergebenen FA-Picks für gecuttete Spieler beweisen **Interesse nach dem Cut**, **keine** historisch sicheren Tradegebote vor der Deadline. Die gesonderte Flo-Fallstudie wird wegen neuer 05.11.-Transaktionen nicht rückwirkend umgeschrieben.
- Der fixierte 05.11.-Stand enthält auch einen weiteren Trade **Mighty Giants ↔ Dennis**, der **nicht** Teil der frühen Flo-Fallstudie ist.

## 7. Datenlücken und CP2-Gates

| ID | Grenze | Erforderliche Behandlung |
|---|---|---|
| G1 | **Exakte historische Player-Salaries** für die damaligen Kader sind mit einem 05.10.-Backcast nicht nachgewiesen. Große Derived-Player-Valuation-Dateien (2024–2026, oft >1 MB) waren über den GitHub-Connector nicht vollständig lesbar; **nicht leer**. | In CP2 lokal mit Repository-Historie aus Data-Derived/Player-Valuation materialisieren und mit historischen Caps/Salaries vergleichen; sonst Backcast als Proxy markieren. |
| G2 | 05.10.-Simulation mit voll additivem Minimum ist überholt; Criticality-Referenz hängt vom Scoring ab. | A/B strikt gleiche Preise, C neue Salary-/Cap-Basis, bestätigte Rookie-/Dead-Cap-Konzepte nur nach expliziter Trennung ergänzen. |
| G3 | Aktuelles Current, Projected, historisches Cap und Rückrechnung haben verschiedene Datenstände. | Je Resultat Modell, Season, As-of, Final Week, Roster-Ref, Salary-Ref, Cap-Ref fixieren. |
| G4 | Permanente Cap-Regel für gleichzeitige Trade-Bundles, Waiver, FA-/Rookie-Draft, Taxi/IR und bereits Over-Cap-Teams fachlich ungeklärt. | In CP2 **explizite Testannahmen**, keine versteckte Ligaentscheidung und keine rückwirkende Verurteilung historischer Moves. |
| G5 | Dead-Cap-Reset beim nächsten Salary-Check bereits Konzeptentscheidung; genaue Prüfreihenfolge bei permanentem Cap offen. | Nicht unbemerkt Dead Cap verlängern oder zusätzlich zählen, sondern bei späterer Sensitivität prüfen. |
| G6 | Historische Tradeangebote, Käufer-Cap-Liquidität und hypothetische Entscheidungen fehlen. | Niemals konkrete mögliche Picks als sicher erzielbare Werte behaupten; CP3 untersucht Marktliquidität. |
| G7 | 2024 initialer Ligadraft ≠ spätere Rookie-Drafts; 2026 noch laufend; archivierter Kader ≠ alle wöchentlichen Lineups. | Nur vergleichbare Zeitfenster und Rollen verwenden. |
| G8 | 2027er Pick-Besitz nach 03.11.-Trade war zeitweise App-/Derived-inkonsistent (separates #1319). | Künftige Pick-Transfers für historischen As-of durch abgeschlossene Transaktionen und passende Draft-Versionen abgleichen. |

## 8. Reproduktionsrezept – Python und vollständiger Git-Checkout

Voraussetzung: Lokale Repository-Historie enthält **alle** genannten Commit- und Blob-SHAs. Ein Shallow Clone kann unvollständig sein. Das Beispiel reproduziert die Tabelle aus Abschnitt 4 ohne neue Salary-Implementierung.

~~~python
import csv, io, json, subprocess

SALARY_BLOB = "96ef8deac5930ffc3dc84dbf12cbbf4719c58489"
SNAPSHOTS = {
    "07jun_pre": "5b4ed63172deae79759e7150f8511bd2ea3edb4e",
    "09jun_post": "7ece134fec39741aba8e82bda554f8f13e8bead4",
    "29jun_deadline": "85e22feb064fdaf2257d6c3149c8d1655ada0908",
    "25aug_pre_fa": "539aae40da3de444000805cea3170a116fae129d",
    "09sep_post_fa": "b40956172a704ff616008d7835f527b86f128063",
    "05nov_w8": "799be2a25203f18face8185303f32b31be3d40a7",
}

def show(spec):
    return subprocess.check_output(["git", "show", spec], text=True)

prices = {
    row["id"]: int(row["salary_published"])
    for row in csv.DictReader(io.StringIO(show(SALARY_BLOB)), delimiter=";")
}
for label, ref in SNAPSHOTS.items():
    league = json.loads(show(ref + ":public/data/League.json"))
    for team in league["Teams"]:
        ids = set(team["Roster"])  # Taxi/IR schon enthalten
        missing = ids - prices.keys()
        assert not missing, (label, team["TeamID"], missing)
        used = sum(sorted((prices[pid] for pid in ids), reverse=True)[:20])
        print(label, team["TeamID"], used, league["SalaryCap"])
~~~

**Gegenchecks bereits ausgeführt:** 1.268 Spieler in der Vergleichs-CSV, 0 nicht zugeordnete PlayerIDs in den sechs Snapshot-Sätzen; aktuelle November-Werte bei 6/6 Teams identisch zum Cap-Readmodel; Flos Juni-Differenz entspricht der früher archivierten Fallstudie.

## 9. Handoff an CP2

**CP1 ist als reproduzierbare Ist- und Quellen-Baseline abgeschlossen, nicht als vollständiger historischer Preis-Audit oder A/B/C-Backtest.** Zuerst in CP2: stichtagsgenaue Salary-Versionierung (G1), transparente Transaktions-Testannahmen (G4) und identische Source-/As-of-Fixpunkte für alle Modelle. Dann **A: heute + Deadline**, **B: identische Preise + permanentes Cap**, **C: Criticality-Preise + permanentes Cap**; D bei Bedarf zur Isolation der Formel.

Beibehalten wird die Ergebnisoffenheit: Auch das heutige System kann ausreichend sein. Weitere Instrumente erst untersuchen, wenn die schlanken Tests diese Frage nicht beantworten. Keine Produktänderung oder Liga-Regelentscheidung aus diesem Bericht.
