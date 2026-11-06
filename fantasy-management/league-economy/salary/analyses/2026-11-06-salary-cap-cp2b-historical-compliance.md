# CP2b – Historisch echte Salaries, Cap-Compliance und sportliche Opportunitätskosten

> **Stand: 06.11.2026 · zentrales [Research-Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344).** Anschluss an [CP1](2026-11-05-salary-cap-cp1-baseline.md) und [CP2a](2026-11-05-salary-cap-cp2-abc-stress-test.md). **Empirischer/kontrafaktischer Stresstest, kein Liga-Regelbeschluss.** Keine Änderung aktiver Salaries, Contracts, Drafts, Dead Cap, Generatoren, Workflows oder App.

## 1. Kernergebnis mit evidenzgetrenntem Status

1. **Historisch exakt nachgewiesen:** Für sechs 2026er Git-Snapshots sind sämtliche individuellen Spieler-Salaries direkt aus dem **damals committeten** \`public/data/Players.json\` zugänglich. Alle in \`League.json\` gehaltenen IDs sind enthalten; in **6/6 Snapshots** entspricht der aus marktweiten Top 120 berechnete Cap dem jeweils publizierten \`SalaryCap\` **dollargenau**.
2. **Beobachteter Effekt:** Die Offseason-Deadline brachte die Liga am 29.06. und 25.08. auf **0/6** Over-Cap-Teams, am 09.09. nach FA-Draft und Änderungen wieder auf **4/6** und am 05.11. auf **5/6**. Das ist kein geltender In-Season-Regelverstoß.
3. **Kontrafaktischer Cut-only-Befund:** In den **gespeicherten** September- und November-Lineups aller sechs Teams reichen – unter bewusst vereinfachten Annahmen – ausschließlich Abgänge von **momentanen Nichtstartern**, um das jeweils getestete Cap zu erreichen. Das bedeutet aber **nicht**, dass nur austauschbare Spieler betroffen wären: teure Backups/Verletzte wie Lamar Jackson, Jalen Hurts, De'Von Achane und Jordan Love haben hohen tatsächlichen und zukünftigen Wert.
4. **Trade-Gegenprobe:** Am 29.06. gab es für Brock Purdy aus Flos acht Juni-Cuts bei den anderen fünf damaligen Teams **keinen** direkt ohne Gegenabgang cap-finanzierbaren Käufer. Ein theoretischer Trade gegen Picks ist daher **nicht** mit einem belegten realisierbaren Angebot gleichzusetzen.
5. **Offen:** Das Verhalten der sechs Manager unter seit der Deadline tatsächlich geltendem permanentem Cap, sportlich zulässige Ersatzverpflichtungen, ex-ante-Pickbewertungen und echte Tradegebote bleiben kontrafaktisch. CP3 untersucht den Markt und langfristigen Rookie-Wert; dieses Dokument beschließt keine Antworten darauf.

## 2. Historische Pricing- und Quellenprovenienz – G1

### 2.1 2026: voll archivierte Spieler-Salaries statt Oktober-Backcast

Für jeden Zeitpunkt wurden **beide** Dateiversionen vom **identischen Git-Commit** abgerufen: \`public/data/League.json\` (alle sechs Rosters, Cap) und \`public/data/Players.json\` (je Spieler \`ID\`, \`Salary\`; Spielerpopulation und Preise können sich zwischen Versionen unterscheiden). Bei jedem Kader werden alle eindeutig gehaltenen Spieler-IDs nach \`Players[].Salary\` bewertet, absteigend sortiert, **Top 20** summiert. Das endogene Cap wird aus den marktweiten **Top 120** berechnet (\`0,9 × Summe Top120 / 6\`, auf ganze Dollar gerundet).

| Zeitpunkt | Git-Commit für beide Dateiversionen | Blob \`Players.json\` | Publiziertes Cap | Aus Players neu errechnet | fehlende gehaltene IDs |
|---|---|---|---:|---:|---:|
| 07.06. vor Cuts | [5b4ed63172deae79759e7150f8511bd2ea3edb4e](https://github.com/Lolindhir/fantasy-app/blob/5b4ed63172deae79759e7150f8511bd2ea3edb4e/public/data/Players.json) | \`1bd0afccc6909e3dbfe11518af11f1a7fd4fe093\` | 434.255.984 $ | 434.255.984 $ | 0 |
| 09.06. nach Cuts | [7ece134fec39741aba8e82bda554f8f13e8bead4](https://github.com/Lolindhir/fantasy-app/blob/7ece134fec39741aba8e82bda554f8f13e8bead4/public/data/Players.json) | \`f0174366022365d53f6cd7b252a5dcc8b90caab3\` | 434.255.984 $ | 434.255.984 $ | 0 |
| 29.06. vor Deadline | [85e22feb064fdaf2257d6c3149c8d1655ada0908](https://github.com/Lolindhir/fantasy-app/blob/85e22feb064fdaf2257d6c3149c8d1655ada0908/public/data/Players.json) | \`21001d6c0819dbbcb3deff084d63fe377714541c\` | 434.255.984 $ | 434.255.984 $ | 0 |
| 25.08. vor FA-Draft | [539aae40da3de444000805cea3170a116fae129d](https://github.com/Lolindhir/fantasy-app/blob/539aae40da3de444000805cea3170a116fae129d/public/data/Players.json) | \`72c021c0fdc6bc7b19c4e32221b3b47e43973513\` | 434.255.984 $ | 434.255.984 $ | 0 |
| 09.09. nach FA-Draft | [b40956172a704ff616008d7835f527b86f128063](https://github.com/Lolindhir/fantasy-app/blob/b40956172a704ff616008d7835f527b86f128063/public/data/Players.json) | \`f8cc9a97cbe19eed6907a7630da053052a35e577\` | 434.255.984 $ | 434.255.984 $ | 0 |
| 05.11. Woche 8 final | [799be2a25203f18face8185303f32b31be3d40a7](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/Players.json) | \`6459aef56b661eb9f3f83ac6c2516577d328cf93\` | 427.653.631 $ | 427.653.631 $ | 0 |

**Kontrollrechnung:** Flo 07.06. **547.568.190 $** → 09.06. **427.729.579 $** = **119.838.611 $** tatsächlich historisch dokumentierte Top-20-Entlastung. Der frühere, offen als Oktoberpreis-Proxy ausgewiesene CP1-Betrag **109.086.072 $** wird **nicht** als exakter Juni-Wert weiterverwendet. Beide Zahlen beziehen sich auf unterschiedliche Datengrundlagen; die historische Fallstudie wird nicht stillschweigend überschrieben.

Die November-Player-Valuation-Dateien \`data-derived/player-valuation/nfl-reise/2026/week-00.json\` und \`week-08.json\` konnten ebenfalls vollständig über die GitHub-Blob-/Contents-Schnittstelle geladen werden; sie besitzen bei **956/956** gemeinsamen Spielern identisches **Salary** (unterschiedliche laufende \`SalaryProjected\` sind erwartbar). Die **historischen** \`Players.json\`-Stände vom September und November unterscheiden sich hingegen bei **385 von 933** gemeinsamen IDs im Salary, was die Bedeutung des **As-of-Preisstichtags** unterstreicht. Eine konkrete Ursache (Modell-/Datenmigration, Population, Änderung der Salary-Basis) ist damit **nicht bewiesen**. Insbesondere ist **permanente Cap-Kontrolle nicht dasselbe wie dauerndes Salary-Repricing**.

### 2.2 Exakte Cap-Zeitreihe (Mio. $)

| Team | 07.06. | 09.06. | 29.06. | 25.08. | 09.09. | 05.11. |
|---|---:|---:|---:|---:|---:|---:|
| Mighty Giants | 428,25 | 428,25 | 428,34 | 416,76 | 418,01 | 440,46 |
| Ruhr Valley Packers | 458,47 | 458,47 | 428,07 | 428,07 | 461,74 | 460,08 |
| Just Bill (Flo) | 547,57 | 427,73 | 427,73 | 427,73 | 441,66 | 510,87 |
| Mammoth Marauders | 454,91 | 454,91 | 417,41 | 417,41 | 476,02 | 484,31 |
| DennisLACards | 410,70 | 410,70 | 410,70 | 410,70 | 412,68 | 348,17 |
| TimpaBay | 432,72 | 432,72 | 430,41 | 430,41 | 480,17 | 460,50 |
| **Jeweiliges Cap** | **434,26** | **434,26** | **434,26** | **434,26** | **434,26** | **427,65** |
| **Teams oberhalb Cap** | **3/6** | **2/6** | **0/6** | **0/6** | **4/6** | **5/6** |

**Alle Werte aus den damals gemeinsam committeten League-/Players-Dateien.** Der Schritt vom August zum September ist besonders sauber: Bei **1.242 gemeinsamen PlayerIDs** ist das \`Salary\` in beiden Marktdateien **unverändert**; die Marktpopulation tauscht je 20 Einträge, das Cap bleibt gleich. Die Veränderung der sechs Team-Cap-Belegungen ist hier eine tatsächliche Rosterbewegung, nicht Preisrevaluation. Im November liegt jedoch ein **anderer** Preis-/Populationsstand vor. Keine der Tabellen beweist hypothetische Titelwahrscheinlichkeiten.

## 3. Transparentes Testregelwerk für B und C – **nur Annahmen, kein Ligaentscheid** (G4)

| Gegenstand | Kontrollierte Testannahme | Offene Liga-Fachentscheidung |
|---|---|---|
| **Salary-Stichtag** | Für einen In-Season-Vollzug zunächst einmal bewerteten Salary-Vektor und endogenes Cap **fixieren**; keine automatische wöchentliche Preisanpassung | Welcher genaue Salary-Check/Zyklus setzt das Pricing neu? Was geschieht bei technischen Datenkorrekturen? |
| **Beginn** | Test startet bei einem nach der Deadline tatsächlich **legalen** Kader: 29.06. und 25.08. A/B **6/6** unter Cap | Zeitpunkt und Umgang mit Rookie-/FA-Draft, Wechsel von Offseason zu Regular Season |
| **Transaktionspakete** | Alle Spieler-**Adds und Drops gemeinsam** ausführen; **beide Seiten eines Trades** nach gesamtem Paket bewerten; Spieler mit niedriger Salary zählen nur, wenn sie nach Top-20-Neurechnung hineingelangen | Sollen Entlastungscuts unmittelbar zum Trade gehören dürfen? Grace-Window/Atomicity für unterschiedliche Systeme |
| **Gültigkeit für Kader** | \`Teams[].Roster\` enthält Spieler auf Taxi und Reserve bereits; Top 20 daraus bilden, ohne Duplikate. Startende 13 Spieler sind keine eigene Salary-Ausnahme | Künftige Ausnahme-/Lock-Regeln für Taxi/IR, konkrete Kader- und Eligibility-Restriktionen |
| **Drafts** | Jeder Draft-Pick ist ein Spielerzugang. Wenn bei A/B das Cap durch ihn überschritten würde, sind **kompensierende Entscheidungen** erforderlich; den Pick nicht rückwirkend für ungültig erklären | Picks sofort cap-pflichtig, oder Draft-/Cut-Window mit anschließender Compliance? |
| **Waiver/FA** | Vollständiger Add/Drop-Claim als Bundle statt Preis des Zugangs isoliert; Transfer darf ohne bereinigte Vorbilanz nicht als „legal“ klassifiziert werden | Reihenfolge konkurrierender Waiver, Bündelung mehrerer Claims, Settle-/Rollback-Mechanik |
| **Over-Cap-Roster** | Als **Diagnose** zwei Semantiken vergleichen: strikter Post-Event-Check und „No Worsening“ (nur Verbesserung/Neutralität). Beides **nicht beschlossen** | Fairer Übergang von einem heute erlaubten Over-Cap-Zustand zu permanenten Regeln; Cuts zur Bereinigung nicht blockieren |
| **Rookie / Dead Cap** | Für A/B/C nur heutiges Salary und isoliertes Criticality-Salary **ohne** diese noch nicht produktiven Vertragsbausteine | Bereits festgehaltene Rookie- und Dead-Cap-Konzeptentscheidungen später gesondert, mit Vertragszyklus, prüfen |

**Wichtig:** Eine „legale“ Cut-only-Kaderliste unten ist eine **mathematische Existenzprobe** für den Salary-Mechanismus, nicht ein vom Manager akzeptierter Deal, keine vorgeschriebene Spielerabgabe und keine Gewähr, dass jeder kurzfristige Roster-/Positionsbedarf erhalten bleibt.

## 4. Von legalem August-Kader über den FA-Draft zum Over-Cap-Kader

**A/B = tatsächliches Salary vom 25.08., Cap 434.255.984 $; C = isolierter Criticality-k1,5-Preisvektor aus der alten, ausdrücklich abgegrenzten [05.10.-CSV](2026-10-05-salary-simulation-players.csv) und daraus endogenes Cap 437.083.780 $.** Die C-Preise sind eine Modellalternative, **nicht** die damals geltenden Salaries. Das ist ein kontrollierter Szenarioblick auf identische Kader, **kein kausaler Vergleich eines vollständig gleichdatigen Modell-Deployments**.

- 25.08., **vor** FA-Draft: A/B **0/6** Teams über Cap, C **2/6**.
- 2026 Free-Agent-Draft: **30/30** Picks mit PlayerID, alle in der 25.08.-Rosterbasis noch **nicht gehalten**. Naiv **nur** diese Picks in \`OverallPick\`-Reihenfolge hinzufügen, **ohne** zwischenzeitliche Cuts/Trades: **5** Picks überschreiten bei A/B erstmals die Grenze aus einem vorher legalen Zustand; bei C **3** (andere Teams waren schon beim Start über dem modellierten C-Cap). **13** A/B- bzw. **15** C-Picks erhöhen die Cap-Belegung eines danach über Cap liegenden Teams.
- 09.09., tatsächlicher fertig aktualisierter Kader nach weiteren Bewegungen: A/B **4/6**, C **5/6** über Cap. Die naive Draft-only-Zwischenstufe weicht erwartbar von den dokumentierten Endkadern ab, weil es nach oder um den Draft weitere Cuts/Transfers gab.
- Die genannten **5 bzw. 3** sind **keine verbotenen Draftpicks**; bei permanentem Cap müssten Zeitpunkt und Möglichkeit eines gleichzeitigen/finalen Ausgleichs geklärt werden. **30** erfolgreiche FA-Picks werden nicht als 30 Transaktionen mit vollständigem Bundle- und Cut-Kontext ausgegeben.

Als zusätzliche Robustheit: Bei der tatsächlichen \`Players.json\`-Preispopulation sind die Salaries aller **1.242** zwischen 25.08. und 09.09. gemeinsam vorhandenen Spieler identisch. Die beschriebene erneute Grenzüberschreitung entsteht im untersuchten Zeitraum damit nicht aus einer verdeckten Neubewertung gemeinsamer Spieler.

## 5. Kann man unter Cap kommen und alle derzeitigen Starter halten?

**Cut-only-Existenzprobe:** Für den dokumentierten 09.09.- und 05.11.-Kader pro Team die derzeitige **\`Teams[].Starter\`**-Menge einfrieren. Alle Nichtstarter aus \`Roster \ Starter\` nach Salary absteigend sortieren und jeweils den teuersten Nichtstarter entfernen. Nach jedem Schritt **Top 20 erneut bestimmen**. Stoppen, sobald die Cap-Belastung unter dem Preis-/Cap-Modell liegt. Keine neuen Adds, keine Trades, **kein** Dead Cap; Taxi/Reserve dürfen nur bei nach aktuellem Regelwerk erlaubtem Cut verlassen werden. Diese deterministische Strategie minimiert die **Anzahl** der Nichtstarter-Cuts für dieses Cut-only-Ziel, aber **nicht** den sportlichen Schaden und unterstellt keine Managerpräferenz.

| Team | 09.09. A/B echte Preise | 09.09. C Criticality | 05.11. A/B echte Preise | 05.11. C Criticality |
|---|---:|---:|---:|---:|
| Mighty Giants | 0 | 1 | 1 | 1 |
| Ruhr Valley Packers | 2 | 5 | 2 | 2 |
| Just Bill (Flo) | 1 | 3 | 3 | 6 |
| Mammoth Marauders | 2 | 2 | 2 | 1 |
| DennisLACards | 0 | 0 | 0 | 0 |
| TimpaBay | 2 | 2 | 2 | 2 |
| **Summe, nur jetztige Nichtstarter** | **7** | **13** | **10** | **12** |
| **Kader mit Starterzwang im Cut-only-Modell** | **0/6** | **0/6** | **0/6** | **0/6** |

Die Zahl **0/6** ist ein **wichtiger Gegenbefund**: Unsere bisher gewünschte Wirkung „etablierte Starter abgeben müssen“ ist **nicht nachgewiesen**. Auch das Criticality-Modell kann die **auf dem Snapshot eingetragenen** 13 Starter stehenlassen, wenn ein Manager dafür mehr teure Alternativen/Absicherungen aufgibt.

**Nicht gleichzusetzen:** „Starter behalten“ bedeutet **nicht**, dass alle wichtigen Franchise-Spieler bleiben. Verletzte und spielstarke Nichtstarter können erheblichen Titel-/Zukunftswert besitzen. Dies ist auch **kein** vollständiger Positions-/Kaderkapazitäts- oder Playoff-Forecast. Nach der hypothetischen Bereinigung müssten Ersatzbank, Taxi-Lock, IR-/Kaderregeln und weitere Transaktionen gesondert neu geplant werden.

### Beispiel Flo – 05.11. (nur illustrative Starter-erhalten-Cutfolge)

- **B, aktuelles November-Salary, Cap 427,65 Mio.:** Lamar Jackson, Kyler Murray, DJ Moore (3 Nichtstarter) → Top-20-Belastung 510,87 → **425,30 Mio. $**.
- **C, Criticality, Cap 437,08 Mio.:** Lamar Jackson, DJ Moore, Kyler Murray, Brandon Aubrey, Jordan Addison, Kirk Cousins (6 Nichtstarter) → Top-20-Belastung 549,13 → **432,90 Mio. $**.
- Lamar Jackson ist im 05.11.-Kader nicht als Starter eingetragen, aber in \`Players.json\` mit **16,02 Fantasy-Punkten je NFL-Spiel 2026** und **16,70** in 2025 geführt; zugleich aktuelle Verletzungs-/Out-Information. Kirk Cousins (ebenfalls Nichtstarter) besitzt **20,58 Fantasy-Punkte je NFL-Spiel 2026** in diesem Wochenstand. Diese Spieler pauschal „belanglose Bank“ zu nennen wäre sachlich falsch.
- Jan könnte unter B rein rechnerisch Jalen Hurts (IR, **2025 19,07 PPG**) und Trevor Lawrence (2026 **19,66 PPG**) verlieren, ohne die eingefrorene Starterliste anzurühren. Packers könnten De'Von Achane (2025 **20,18 PPG**) und A.J. Brown abgeben; TimpaBay Jordan Love (2026 **19,36 PPG**) und Matthew Stafford.

**Sportlicher Proxy und Grenzen:** Die Fantasy-Punkte sind **tatsächlich veröffentlichte NFL-Spielerdaten** bis zur finalen Woche 8 (bzw. 2025 im \`PointHistory.SeasonMinus1\`), **keine** projizierten künftigen Starts oder echten Punkteverluste der Fantasy-Teams. Ein verletzter QB kann aktuell nicht sofort ersetzt werden, hat aber Franchise-/Absicherungswert; ein sportlich starker Ersatzspieler verliert nicht zwingend automatisch den Markt. Ein echter Replacement-Test muss Wochen-/Positionsanforderungen und Verfügbarkeit während desselben Fensters berücksichtigen.

### Stichtagsgetreuer grober Free-Agent-Replacement-Check

Aus dem **05.11.-Roster-ungebundenen** Spielerpool, nur NFL-Spieler mit **mindestens vier gezählten Spielen 2026**, gibt es beispielsweise **Geno Smith (15,76 PPG; Salary 25,3 Mio.)**, **Malik Willis (15,17 PPG; 4,3 Mio.)**, **Adonai Mitchell (WR, 12,12 PPG; 2,0 Mio.)** und **Michael Mayer (TE, 9,64 PPG; 2,0 Mio.)**. Diese Zahlen belegen, dass tatsächlich preisgünstigere, teils sofort nutzbare Alternativen im **beobachteten** Markt existieren; sie belegen **nicht**, dass dieselben Spieler in einer kontrafaktischen B-/C-Welt frei geblieben wären, eine vollständige 13-Starter-Lineup abdecken, zuverlässig fit sind oder langfristig gleichwertig wären.

## 6. Trade-/Käufer-Liquidität: Vorhandene Picks sind nicht dasselbe wie zahlungsfähige Nachfrage

**Reiner historischer Cap-Fähigkeitscheck:** Flos acht Spieler vom 07.→09.06.-Cut nehmen; hypothetisch am **29.06.** (alle sechs Kader tatsächlich unter Cap) **jedem anderen Team einzeln** einen der Spieler **ohne Gegenabgang** hinzufügen, dessen Top-20-Belastung neu berechnen. Bei 20er Cap kann die marginale Kostenwirkung geringer als das nominelle Spieler-Salary sein. **Kein** fiktives Angebot, keine historische Verhandlung und keine Aussage, ob diese Spieler damals noch frei oder gefragt gewesen wären.

| Von Flo gecutteter Spieler | Salary am 29.06. | Andere Teams, die ihn *ohne* Gegenabgang aufnehmen könnten |
|---|---:|---:|
| Alvin Kamara | 24,4 Mio. $ | 1 |
| George Kittle | 23,0 Mio. $ | 2 |
| Sam Darnold | 24,2 Mio. $ | 1 |
| Terry McLaurin | 19,0 Mio. $ | 2 |
| Travis Etienne | 22,8 Mio. $ | 2 |
| Javonte Williams | 17,0 Mio. $ | 2 |
| Romeo Doubs | 12,9 Mio. $ | 3 |
| Brock Purdy | 41,5 Mio. $ | **0** |

**Interpretation:** Flo **hätte** die Spieler womöglich mit zusätzlichen Salary-Abgängen, Salary-Offsets oder vorgezogenem Trade-Clearing verkaufen können. Diese Optionen dürfen geprüft werden, aber direkte Trade-Nachfrage ist gerade bei einem weitgehend ausgeschöpften Markt **nicht garantiert**. Der anschließende FA-Draft unter **ohne In-Season-Vollzug** geltenden Regeln ist kein Nachweis, dass diese Käufer **unter permanentem Cap** dieselbe Zahlungsbereitschaft gehabt hätten.

Der 05.11.-Status bestätigt das Liquiditätsproblem: Unter beiden aktuellen Vergleichspreisen liegt **nur Dennis** in den tatsächlich aufgebauten Kadern unter Cap. Da das hypothetische permanente Cap schon **vor** dem Draft auf andere Kaderentscheidungen gewirkt hätte, ist dies **keine** belastbare Käuferprognose für B/C. Daher in CP3 Markt-Clearance und mögliche verhandelbare Trade-Salary-Offsets **als separate Hypothesen** prüfen.

## 7. Unterschied A/B und Criticality C: abgewogene Zwischenbewertung

- **B – permanenter Vollzug allein** adressiert unmittelbar das empirisch gesicherte Problem, dass nach der erfolgreich erzwungenen Juni-Bereinigung neue teure FA- und Trade-Zugänge ohne laufende Cap-Compliance möglich sind. Für 2026 wären viele dokumentierte Transaktionen bei legalem Cap-Start neu zu planen gewesen.
- **C – Criticality zusätzlich** verschiebt Salary teils **stärker auf Elite-Kernspieler** und reduziert an anderen Stellen mittelteure Tiefe; beim September-/November-Stand wären nach dem gewählten Cut-only-Modell teils **mehr Nichtstarter** betroffen. Das ist **kein** Beweis, dass künftig mehr echte Starter verkauft würden, dass weniger Favoriten entstehen oder dass die Marktliquidität besser würde. Es kann den Käufermarkt sogar verengen.
- **Gegenprobe:** Der hypothetische B-/C-Erfüllungsweg durch Cut von Nichtstartern ist in allen aktuellen Roster-Snapshots rechnerisch vorhanden. Dies spricht gegen die vorschnelle Annahme, dass der Elitekern zwangsläufig gesprengt wird; allerdings verlieren die Teams unter C durchaus substanzielle Alternative-/Verletzungs-/Entwicklungswerte.
- **Rookies:** Die derzeitigen A/B- und isolierten C-Salaries der 30 Draft-Rookies 2026 sind **0 $**; ein echter 3-Jahres-Contract-/Entwicklungs-Surplus wird durch die A/B/C-Reihe **nicht** getestet. Dazu bleiben die bereits festgehaltenen, **nicht aktiven** Rookie-/Minimum-/Dead-Cap-Konzeptbausteine separat zu untersuchen.
- **Rebuild/Reload:** Zwei Win-now-Saisons von Flo/Marcel, ein einzelner November-Trade oder die Zahl erzwungener Cuts belegen für sich **nicht**, wie 2027/2028 aussehen würde. Eine faire Systementscheidung braucht Markt-/Rookie- und Mehrjahres-Evidenz.

## 8. Reproduktionsvorgaben (ohne produktiven Code)

Ein vollständiger Git-Checkout mit den obigen sechs Git-Commits genügt. Der Prozess braucht **keine** neue Salary-Implementierung:

~~~python
import json, subprocess

SNAPSHOTS = {
    "07Jun": "5b4ed63172deae79759e7150f8511bd2ea3edb4e",
    "09Jun": "7ece134fec39741aba8e82bda554f8f13e8bead4",
    "29Jun": "85e22feb064fdaf2257d6c3149c8d1655ada0908",
    "25Aug": "539aae40da3de444000805cea3170a116fae129d",
    "09Sep": "b40956172a704ff616008d7835f527b86f128063",
    "05Nov": "799be2a25203f18face8185303f32b31be3d40a7",
}

def at(commit, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{commit}:{path}"], text=True))

def usage(ids, salary, n=20):
    return sum(sorted((salary[id] for id in set(ids)), reverse=True)[:n])

for label, commit in SNAPSHOTS.items():
    league = at(commit, "public/data/League.json")
    players = at(commit, "public/data/Players.json")
    salary = {p["ID"]: p["Salary"] for p in players}
    cap = round(0.9 * sum(sorted(salary.values(), reverse=True)[:120]) / 6)
    assert cap == league["SalaryCap"], (label, cap, league["SalaryCap"])
    for team in league["Teams"]:
        assert set(team["Roster"]) <= salary.keys()
        print(label, team["TeamID"], usage(team["Roster"], salary), cap)
~~~

Für Criticality C/D zusätzlich den **datierten** Preisvektor \`salary_B_k15_ohne_vertraege\` aus der 05.10.-Simulation laden und dessen Cap aus der **dazugehörigen Gesamtmarktpopulation** endogen neu bilden (nicht historische A-Preise mit C-Cap vermischen). Die Nonstarter-Cut-Existenzprobe folgt dem deterministischen Schritt „höchstes Salary außerhalb \`Starter\` entfernen, Top 20 neu bilden“, bis unter dem jeweiligen Cap. Das ist kein Policy-Vorschlag.

**QA der tatsächlichen Auswertung:** 6/6 historische Cap-Neuberechnungen stimmen dollar-genau, **0** fehlende Roster-IDs, 1.242 identisch bepreiste gemeinsame PlayerIDs August→September, archivierter Flo-Cut-Differenzwert neu exakt berechnet; September-/November-Cut-only-Stressprobe für alle 6 Teams unter B/C, 8 Juni-Cuts gegen fünf hypothetische direkte Käufer getestet; Week-8-PPG der betroffenen Nichtstarter aus demselben eingefrorenen November-Players-Stand.

## 9. CP2b-Abschlussgrenze und Handoff

**CP2b als historische Price-/Mechanik-/Cut-only-Testaufgabe abgeschlossen.** Empirisch präzisiert ist nun die tatsächliche Deadline-Wirkung und die tatsächliche Nachrüstung nach FA-Draft. Unter der ausdrücklichen Cut-only-Annahme können alle **momentan eingetragenen** Starter gehalten werden, aber nur um den Preis teils wertvoller Tiefe; ein permanentes Cap verbessert möglicherweise strukturell die Wirtschaftlichkeit, garantiert keine Transfers oder mehrjährige Rookie-Entwicklung.

**Keine Entscheidung darüber, welche Mechanik eingeführt wird.** Offene Folgefragen werden für [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) in CP3 (Trade-Liquidität, Cut-vs-Trade, Rookie-Retention-/Reacquisition und echte zeitliche Entwicklung) und CP4 (nur bei Evidenzbedarf: vorhandene bestätigte Vertragsbausteine als gesonderte Zusatzmodelle) bearbeitet. Die G4-Fachdetails über Draft-Siedlung, Preis-Freeze/Refresh, Taxi-/IR-Ausnahmen und Grace-Period sind **testbare Annahmen**, **nicht** verabschiedete Ligaregeln.

Die Rolle **2024/2025 als mehrjährige Outcome-Evidenz** bleibt Folgearbeit; deren historische Price- und Roster-Fenster wurden durch den hier konkret auf 2026 fixierten CP2b-Test **nicht** erschöpfend geprüft.
