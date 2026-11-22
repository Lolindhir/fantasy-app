# CP6q – Rookie-Draftrundengarantien und 40/45/50 Plätze ohne Taxi

> **22.11.2026 – Forschung zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) und [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576).** Keine aktive Regeländerung; die sechs geschützten Liga-Ziele bleiben unverändert, ihre Liga-Ratifizierung steht weiterhin aus. Nachfolger von [CP6p](2026-11-22-cp6p-mature-vintages-rookie-guarantee-and-125-150.md).

## 1. Untersuchte Regelidee

**Kader:** Optional bis zu 40, 45 oder 50 reguläre Spieler, keine Taxi- oder IR-Sonderplätze in dieser **Research-Modellwelt**, 13 Starter, 20 verpflichtende Mindest-Researchbelegungen, vollständige Cap-Anrechnung jedes Spielervertrags. Die heutige reale Sleeper-Liga hat dagegen 30 reguläre +5 IR +2 Taxi. Die IR-Frage ist deshalb ausdrücklich nicht beschlossen und erfordert spätere Abgrenzung.

**Rookie-Salary:** unverändert 100/125/150 % vom bei Auswahl festgesetzten Year-1-Dollarbetrag. Year1 = Vorjahres-Cap × [65 % × Fantasy-Draftkurve + 35 % × bereinigte NFL-Draftkurve]. Gegenüber CP6p entscheidende Korrektur: Der tatsächlich in unserer Fantasy-Liga **ausgeübte Pick** bestimmt das Salary, nicht ein bei Spielererzeugung vorgetäuschter Rang. Die im Simulator gewählte Draftklasse hat fünf Runden.

| Klasse | Year1-Garantie | Year2-Garantie | Year3-Garantie |
|---|---:|---:|---:|
| Runde 1–2 | 100 % | 100 % | 100 % |
| Runde 3–4 | 100 % | 100 % | 50 % |
| Runde 5 | 100 % | 50 % | 25 % |
| Undrafted / historischer Fantasy-Rang unbekannt | 100 % | 50 % | 25 % |

Die Vergleichswelten behalten für **alle** gedrafteten Rookies entweder 100/50/25 (Teil) oder 100/100/100 (Voll). Die Garantiequote ist die bei einem vorzeitigen Cut in jedem Vertragsjahr fällige Bindung, nicht die Salary-Höhe. Beispiel Year1-Basis 10 Mio. $ und Year2/3-Salary 12,5/15 Mio.: Cut vor Jahr 2 bindet insgesamt 27,5 Mio. (R1–2), 20 Mio. (R3–4) oder 10 Mio. $ (R5/UDFA), jeweils auf die Fälligkeitsjahre verteilt.

**Veteranen:** 100/110/120 gegen 100/125/150 % Gehaltsstaffel; immer 100/50/25 % Garantien, nach natürlichem 3Y-Ablauf kostenlose Nichtverlängerung oder Neubewertung zu Marktpreisen. Cap 2028–31 jeweils Schocks 0/−10/−20 %, auch sinkendes Cap, kein künstlicher Floor. Ältere synthetische Vertragsvintages beginnen versetzt 2025/26/27.

## 2. Reproduktion und Validierung

- [Simulator](../simulation/cp6q_round_guarantees_capacity.mjs), abgeleitet von CP6p-Blob `337277081723708c7e634ea00d17295dace090f5` und archiviertem Oktober-2026-CSV-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489` (1.268 Spieler). Vollständiger Lauf: `node fantasy-management/league-economy/salary/simulation/cp6q_round_guarantees_capacity.mjs --json`.
- Sechs persistierte Batch-Ergebnisse: [seed11-vet110](2026-11-22-cp6q-seed11-vet110-results.json), [seed11-vet125](2026-11-22-cp6q-seed11-vet125-results.json), [seed29-vet110](2026-11-22-cp6q-seed29-vet110-results.json), [seed29-vet125](2026-11-22-cp6q-seed29-vet125-results.json), [seed47-vet110](2026-11-22-cp6q-seed47-vet110-results.json), [seed47-vet125](2026-11-22-cp6q-seed47-vet125-results.json). [Zusammenfassung als JSON](2026-11-22-cp6q-round-guarantees-capacity-overview.json).
- 3 Seeds × 3 Max-Slots × 3 Rookie-Garantien × 2 Veteranenstaffeln × 3 Markt-Cap-Verläufe = **162 alternative fünfjährige Pfade** (2027–31) mit sechs disjunkten Team-Ownerships. Kein 162-facher realer Markt, keine historisch beobachteten Menschenentscheidungen.
- **162/162 Pfade legal**, **810 komplette Sechs-Team-Jahreszustände** und **4860 Teamjahre** (Roster 20–Max und Vertrags-Salary inkl. modelliertem Dead Cap), für jeden Pfad 120 Rookie-Draft-Signings in 2028–31. Sechs Garantie-Unitchecks vor der Einspielung des Simulators bestanden. Jede Batch-JSON enthält Quellenblob, 27 geprüfte Pfade und 5-jährige Team-Kennzahlen.
- Quelle der Rechenergebnisse ist die **V8-Ausführung des aktuellen Simulators mit ausschließlich `node:fs`-/`import.meta`-Adapter**. Das ist kein unabhängig ausgeführter Node-CLI-Test, kein GitHub-CI-Status und kein mathematischer globaler Optimumsnachweis. Die Größe des Full Runs erforderte sechs getrennte, nachvollziehbare Ausführungen.

## 3. Ergebnis – Kadergröße

| Maximalzahl | Erzwungene Draft-Kapazitätscuts* | Höchste tatsächlich belegte Spielerzahl | Pfade mit mehr als 40 belegten Spielern |
|---:|---:|---:|---:|
| 40 | 46 | 39 | 0 |
| 45 | 0 | 42 | 4 |
| 50 | 0 | 42 | 4 |

\* Summiert über **54 alternative Pfade je Maximalgröße**, keine historische Saison. Ein Draft-Zwangscut kann auftreten, obwohl die endgültige Nach-Settlement-Belegung unter der Grenze liegt.

**Paarkontrolle:** Für jede der 54 Kombinationen aus Seed, Veteranenstaffel, Garantie und Marktschock gibt es identische 40/45/50-Vergleichswelten. 40→45 eliminiert 46 erzwungene Draft-Cuts. In **54/54** Paaren bleibt der 2031er Team-0-Starterindex dennoch unverändert. 45→50 verändert in **54/54** Paaren sogar den kompletten gespeicherten Fünfjahres-Teamwertpfad, die FA-Aktionen, Cuts und Nichtverlängerungen **überhaupt nicht**. Das ist ein **Negativbefund gegen 50** in der aktuellen Greedy-Simulation, kein Beweis, dass 50 unter anderen Strategien nie nützlich sein kann.

## 4. Garantie-Effekt und sportliche Stärke

Für jede Zeile werden **neun alternative Fünfjahrespfade** (3 Seeds ×3 Cap-Schocks) bei **45 Plätzen** zusammengefasst. Cuts und Nichtverlängerungen sind verschiedene ökonomische Exits. Rookie-Holds 2031 und verfügbare Quality≥3 Free Agents sind **ligaweite Mediane je simulierte Welt**. Starterindex ist der **Median Team 0 im Jahr 2031** (kein Champion-Wahrscheinlichkeitsmodell).

### Veteranen 100/110/120

| Rookie-Garantie | Draft-Zwangscuts bei 40 | bei 45 | Belastete Cuts bei 45 | Nichtverlängerungen bei 45 | Median Starterindex 2031 | Median Rookie-Holds ligaweit | Median freie Quality≥3-Spieler |
|---|---:|---:|---:|---:|---:|---:|---:|
| Teilgarantie 100/50/25 | 10 | 0 | 423 | 394 | 179.40 | 87 | 414 |
| Rundenstaffel | 10 | 0 | 269 | 535 | 180.64 | 93 | 419 |
| Vollgarantie | 10 | 0 | 231 | 554 | 180.70 | 93 | 414 |

### Veteranen 100/125/150

| Rookie-Garantie | Draft-Zwangscuts bei 40 | bei 45 | Belastete Cuts bei 45 | Nichtverlängerungen bei 45 | Median Starterindex 2031 | Median Rookie-Holds ligaweit | Median freie Quality≥3-Spieler |
|---|---:|---:|---:|---:|---:|---:|---:|
| Teilgarantie 100/50/25 | 6 | 0 | 599 | 413 | 173.30 | 84 | 433 |
| Rundenstaffel | 5 | 0 | 388 | 543 | 174.22 | 93 | 427 |
| Vollgarantie | 5 | 0 | 354 | 571 | 174.22 | 95 | 426 |

**Interpretation:** Die Rundenstaffel führt im aktuellen Greedy-Agenten zu weniger unmittelbaren belasteten Cuts, aber mehr bewussten kostenlosen Nichtverlängerungen als die durchgehende Teilgarantie. Eine Vollgarantie reduziert die Cuts noch stärker, ohne eine eindeutige sportliche Dominanz zu belegen. Das ist *kein* Qualitätsmerkmal an sich: Eine hohe Garantie kann den ökonomisch sinnvollen Ausstieg gerade verhindern, bis der Vertrag ausläuft. Ein bewusstes Draft-Commitment entsteht finanzmechanisch; der Manager-Agent **optimiert die Rookie-Draft-Entscheidung bisher nur anhand des am Pick bekannten Salaries, nicht der künftig garantierten Kosten**. Diese Endogenität muss ein Folgeexperiment nachholen.

Die 100/125/150-Veteranenstaffel belastet die Kader langfristig stärker und erlaubt niedrigere 2031er Team-0-Starterindizes; aus einem Einbruch folgt nicht automatisch ein Fairness-Fehler, wenn der Manager bewusst zuvor All-in gewählt hätte. Ein solcher bewusster All-in wurde hier *nicht* modelliert.

## 5. Finanzierungsprüfung (alle fünf Pflichtachsen)

1. **Seller Relief:** Keine realen Trade-Seller. Bei simulierten Cuts berechnet der Full-JSON-Lauf vollständiges ausstehendes Salary, aktuell garantierten Anteil, verbleibende garantierte zukünftige Year-Vintages, den aktuellen Netto-Cap-Effekt und notwendige volle FA-Ersatzkosten. Ein ausgelaufener Vertrag kann vor neuer Bindung für **0 Dead Cap** nicht verlängert werden. **Cuts ≠ Trades.**
2. **Buyer Burden:** Nur Free Agents aus dem wirklich nicht besessenen synthetischen Pool, mit vollständigem dreijährigem neuem Vertrag und Cap-/Kaderplatzkosten. **Keine bilateralen Trades, Käuferzustimmung, Claim-Effekte oder Pick-Komponenten gemessen.** Keine fiktiven Käufer oder angenommenen Buyer-Preise.
3. **Roster Capacity:** Forschungsvergleich 40/45/50 reguläre Plätze ohne Taxi/IR, maximal 13 vorgeschriebene Starter, gültige Positionsdeckung und simultane Draft-Cuts als Events. **Die tatsächlich vorhandenen 30+5+2 Sleeper-Slots und tatsächliche IR-Eligibility-/Aktivierungslogik wurden nicht umgestellt oder ausführbar simuliert.**
4. **League-wide debt/guarantees:** Dead-Cap-Vintages pro vertraglichem Signjahr und fälligem Jahr beim alten Team, niemals automatischer Erlass oder Schulden-Kredit. Keine neue Debt-/H2-/H3-Anleihe und kein durch Trade ausgelagerter Betrag (kein Trade).
5. **Future settlement:** 2027–31 jährliche Gesamt-Cap-Prüfung, Cap darf sinken; Folgejahres-Gehälter und garantiert fälliger Dead Cap im ausführbaren Full-Ledger. **2032–34 Cap/Owner/Playoff-/Insolvenz- und echte historische 2025–26 Vertragsentscheidungen fehlen**; keine Refinanzierung durch fiktiven neuen Kredit.

## 6. Abgleich mit allen sechs Nordstern-Zielen

1. **Langfristige Aufholbarkeit:** Veränderte Index-/Cap-Wege messbar, Titelwahrscheinlichkeiten und Verfolger-Trade-Strategien **nicht belegt**. 45 erleichtert Entwicklungsflexibilität, garantiert kein sportliches Catch-up.
2. **Gutes Management belohnen:** Salary nach tatsächlichem Pick plus Garantierisikoklasse belohnt frühe und günstige späte Scoutingentscheidungen unterschiedlich; ohne agentische Vertragsrisikoentscheidung bleibt die Stärke unbestimmt.
3. **Keine zementierten Vorteile:** 3Y-Verträge, Cap und Ablauf schaffen wiederkehrende wirtschaftliche Entscheidungen; dominantes Management darf weiter stark bleiben.
4. **Wirtschaftliche Konsequenzen:** Höhere garantierte Rookie-Verpflichtungen und steigende Veteranen-Salaries sind sichtbar in den Full-Salary-/Dead-Cap-Pfaden. Weniger Cuts sind keine Bewertung der Härte.
5. **Strategische Freiheit:** 45 eröffnet zusätzliche bezahlte Rookie-Holds ohne 40er Forced-Draft-Cuts; 50 bleibt in diesen Modellpfaden ungenutzt. Unterschiedliche All-in-/Reload-/Rebuild-/Flex-Agenten und verfügbare Käufer nicht modelliert.
6. **Operative Durchsetzbarkeit:** Draft-Round → Garantieklasse und jährliche Salary/Dead-Cap-Abrechnung sind grundsätzlich gut prüfbar. Neue Sleeper-Rosterlimits, Midseason-FA-Abschluss, IR-Ausnahmen, Vertragstransfer, Claimpflichten und Failure/Appeals müssen vor einer Umsetzung operationalisiert werden.

## 7. Vorläufiger Befund und nächster Checkpoint

**45 reguläre Plätze ohne Taxi sind nun der führende *Forschungs*-Kandidat**: gegen 40 vermeidet er insgesamt 46 erzwungene Draft-Platz-Cuts, ohne in diesen Vergleichspfaden den Starterindex künstlich zu erhöhen; gegen 50 ist die gesamte beobachtete Output-Ökonomie bei identischen Greedy-Managern gleich. **Die nach Fantasy-Draftrunde gestaffelte Rookie-Garantie bleibt ernsthafter Kandidat, kein bewiesener Gewinner über Teil-/Vollgarantie.** Die unabhängige Salary-Staffel 100/125/150 für Veteranen ist weiterhin strategisch relevant, noch nicht als praktikabler vollständiger Trade-Markt belegt.

**Nächste Hard Gates vor Liga-Ratifizierung:** realistisch komplett kontraktsensitives 2025–27-Burn-in; Agenten mit absichtlich verschiedenen All-in-/Reload-/Rebuild-/Flex-Zielen; beidseitig bezahlbarer Trade-/Pick-/Claim-Markt; Kapazitäts-/FA-Liquiditätssensitivität; IR-Konzept ohne Taxi einschließlich Eligibility und Roster-Settlement; unabhängiger Node-CLI-/CI-Lauf, jährliche Operator-Minuten, Appeal-/Hard-Failure-Prüfung. 2027+ NFL-Ergebnisse sind synthetisch und keine Prognosen. Der Nordstern und alle produktiven Liga-/Salary-/Sleeper-Einstellungen wurden **nicht** geändert.
