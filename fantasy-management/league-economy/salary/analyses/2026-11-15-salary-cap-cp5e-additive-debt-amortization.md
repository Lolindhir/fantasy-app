# CP5e – Additive Dead-Cap-Härte, verpflichtende Tilgung und Cut-Grenzfälle

> **Forschung 15.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344). Kein Ligaentscheid, keine aktive Regel.** Nutzerpräferenz: Voll additive Cut-Dead-Cap-Anrechnung (**C-add**) ist die bevorzugte harte *Forschungshypothese*; C-virt bleibt Vergleich. Der [geschützte Sechs-Ziele-Nordstern](../../../league-context/league-philosophy.md) bleibt unverändert. Quellen: [CP5d](2026-11-15-salary-cap-cp5d-debt-backtest.md) / [CP5d-Originalmetriken](2026-11-15-salary-cap-cp5d-metrics.json), Juni-2026-Roster-Commit `85e22feb064fdaf2257d6c3149c8d1655ada0908`, Zeitgenossen-Spieler-BLOB `21001d6c0819dbbcb3deff084d63fe377714541c`.

**Reproduzierbare Einzelprüfung:** [CP5e-JSON-Metriken](2026-11-15-salary-cap-cp5e-metrics.json) mit 14 Cut-Schritten, sechs Teams, Tilgungsfällen und 60 Quell-/Rechenprüfungen.

## 1. Ergebnis

**C-add macht historisch beobachtete Cap-Cuts wirklich teuer:** Die 14 seit dem 07.06.2026 mittags archivierten Cut-only-Ereignisse ergeben nominal **54.996.380 $** Retention. Gegenüber einer reinen Top-20-Rechnung reduzieren 13 der 14 Cuts die Cap-Belegung noch positiv, **einer erhöht sie**. Insgesamt verringern die Cuts den ursprünglichen Top-20-Payroll um **187.743.938 $**, durch additive Retention bleibt eine Nettoentlastung von **132.747.558 $**.

Am 29.06.2026 stünden dennoch **35.094.437 $** neue aggregierte C-add-Schuld auf zwei Teams: Packers **4.068.909 $**, Just Bill **31.025.528 $**. Der C-virt-Vergleich hätte nur **4.941.734 $** auf einem Team. Dies sind **hypothetische** Gegenfaktik-Kosten: Weder Retention noch Debt galten 2026 als tatsächlich aktive Regel.

Eine reine Kreditobergrenze garantiert keine Tilgung: Selbst bei `Top20 = Cap` überdauert vorhandene Schuld ohne Pflichtzahlung unbegrenzt. Deshalb werden **zwei** oder **drei folgende Jahreschecks zur Tilgung** (H2/H3) getrennt vom Kreditlimit geprüft. **Kein individueller mehrjähriger Veteranenvertrag**, keine zusätzlichen In-Season-Freigaben.

## 2. Juni-Cuts: Wirkung nach Salary-Rang und Aufrücken der nächsten Spieler

Für jedes Team wurden die 14 historischen Cut-IDs auf den Kader vom 29.06. zurückgelegt und unter den **damals archivierten Preisen** in Event-Reihenfolge entfernt. Damit berücksichtigt jede Rechnung automatisch, welcher Spieler anschließend in die Top 20 aufrückt. Reverse-Rekonstruktion: sechs von sechs Endkadern und Top-20-Summen exakt wie CP5d; Flos rekonstruierter Top20-vor-Cuts **547.568.190 $** stimmt mit CP4/CP5d überein. Die Rekonstruktion ist *mechanisch*, nicht eine kausale Neusimulation von Manageraktionen.

Beträge Mio. $ (gerundet), alle 14 Cut-Einzelmetriken stehen zusätzlich im CP5e-JSON.

| Team | Cuts | Top20 vor Cuts | Top20 nach Cuts | Retention additiv | Nettoentlastung | Neue C-add-Schuld |
|---|---:|---:|---:|---:|---:|---:|
| Mighty Giants | 0 | 428,34 | 428,34 | 0,00 | 0,00 | 0,00 |
| Ruhr Valley Packers | 4 | 458,47 | 428,07 | 10,26 | 20,15 | 4,07 |
| Just Bill | 8 | 547,57 | 427,73 | 37,55 | **82,29** | **31,03** |
| Mammoth Marauders | 2 | 454,91 | 417,41 | 7,19 | 30,31 | 0,00 |
| Team DennisLACards | 0 | 410,70 | 410,70 | 0,00 | 0,00 | 0,00 |
| Team TimpaBay | 0 | 430,41 | 430,41 | 0,00 | 0,00 | 0,00 |

Formel je Cut: `Top20_vorher − Top20_nachher − round_half_up(Salary_at_cut × DeadCapQuote)`.

**Devin Neal ist der konkrete Grenzfall:** Bei Mammoth hatte er vor seinem Cut Salary-Rang **28** (1.824.050 $ Salary) und damit keinerlei Top-20-Belastung. Sein Cut erzeugt dennoch **547.215 $** additive Retention (30 %); die Cap-Belegung **steigt**, statt zu sinken. Das ist unter C-add kein Rechenfehler, sondern eine bewusst **über die Top-20-Spielerbewertung hinausgehende Cut-Strafe**. Der Nutzer favorisiert genau dieses harte Prinzip; es bleibt zu prüfen, ob es als Liga-Norm auch bei günstigen Bankspielern gewünscht ist. Für alle anderen 13 beobachteten Cuts ist die Nettoentlastung positiv.

**Just Bills acht Cuts im Detail:** 119.838.611 $ Top-20-Entlastung minus 37.551.933 $ Retention = **82.286.678 $** wirkliche C-add-Entlastung; trotz tatsächlichem Unter-Cap-Kader ohne Retention bleiben hypothetisch 31.025.528 $ Schulden. Es wäre methodisch falsch, aus dieser Gegenrechnung echte 2026er Spielerabgabe-Absichten zu folgern.

## 3. Harte Laufzeiten H2 und H3

**Unbeschlossene Test-Abfolge:** Am jährlichen Check wird im **alten Salary-Zyklus zuerst** `Top20(gehaltene Spieler) + alle zum Check noch aktiven Cut-Retentions + alte aggregierte Team-Schuld` gegen das Cap geprüft. Erst **nach** dem Check endet die individuelle Retention beim ohnehin vorgesehenen Salary-Reset. Der positive Jahresüberhang wird einmalig als *eigenständige Team-Schuld* registriert, **nicht** als ein zweites oder jährlich neu fälliges Spielergehalt. Der nächste Salary-Zyklus bepreist Spieler wieder vollständig eigenständig.

- **H2:** Schuld aus Juni 2026 hat die erste verbindliche Rate Juni 2027 und muss beim Check Juni **2028** vollständig getilgt sein.
- **H3:** Dieselbe Schuld hat drei Folgechecks (2027, 2028, spätestens Juni **2029**).
- **Mindestfälligkeit je Jahrgang:** `ceil(Restschuld / verbleibende Jahreschecks)`. Freier Cap-Puffer dient zur Tilgung; älteste Jahrgänge zuerst, frühere vollständige Tilgung erlaubt. Das alte Jahres-Salary bzw. die individuellen Cuts werden nicht einfach weitergeschrieben.
- **No-refinance-Gate:** Eine **fällige Rate** muss aus `Cap − aktueller Top20 − aktuelle Retention` gedeckt sein. Eine zusätzliche Verschuldung zur Zahlung dieser Pflicht-Rate, ein stiller Schuldenschnitt oder eine automatisch erzwungene Spielerentlassung sind ausgeschlossen. Ein nicht gedeckter Check ist **nicht compliant**; klare freiwillige Settlement-/Konfliktfolgen müssen *später ligaweit beschlossen werden*.

**Mechanischer Stresstest**: Juni-2026-Salaries, Cap und Endkader sind für die gesamte Zukunft künstlich eingefroren, keine weiteren Transaktionen, kein neues Dead Cap. Das sind **keine realen 2027–2029-Prognosen**. Beträge Mio. $:

| Team | Schuld 2026 | Rate 2027 H2 | Rate 2027 H3 | Unveränderter Jahres-Puffer | Extra-Entlastung H2 / H3 |
|---|---:|---:|---:|---:|---:|
| Ruhr Valley Packers | 4,07 | 2,03 | 1,36 | 6,19 | 0 / 0 |
| Just Bill | **31,03** | **15,51** | **10,34** | **6,53** | **8,99 / 3,82** |

Die exakten Werte für Just Bill: H2-Mindestrate **15.512.764 $** minus freier Cap-Puffer **6.526.405 $** = **8.986.359 $** zusätzliche Entlastung beim ersten Folgecheck. H3-Mindestrate **10.341.843 $**, zusätzliche Entlastung **3.815.438 $**. Eine sofortige **Volltilgung** 2027 würde **24.499.123 $** zusätzlich erfordern; das ist **nicht** mit H2 zu verwechseln.

**Kritischer Einwand:** Bei der echten jährlichen Salary-Neubewertung können Spieler, Cap, Mindestgehälter, Rosters und Retentions abweichen. Die künstlich fixierte 2026er Spielermenge ist gerade keine Prognose, welche Spieler 2027 verfügbar oder verkäuflich wären. Auch ein Pflichttermin darf nicht allein deshalb als realisierbar gelten, weil die Gleichung lösbar ist.

## 4. Harter Ein-Cut-Stress (bewusst **nicht** beobachtete Gegenfaktik)

Für den echten Juni-2026-Endkader von Just Bill mit seinen damals 23 gehaltenen Spielern wurde hypothetisch **ein weiterer Cut** unter identischem Salary-Vektor untersucht. Weil die individuellen Tenures dieser *nicht tatsächlich gecutteten* Spieler in dieser Probe nicht vollständig historisch verifiziert sind, verwenden wir **einheitliche** 5/15/30/50-%-Quoten als reine Sensitivität (nicht als echte Spieler-Einordnung).

Zur vollständigen Vermeidung der 31.025.528-$-C-add-Schuld mit **nur einem** solchen zusätzlichen Cut:

| Einheitliche hypothetische Cut-Quote | Anzahl ausreichender Einzel-Cuts | Kandidaten nach alter Salary-Preiswelt |
|---|---:|---|
| 5 % | 5 | Lamar Jackson, Amon-Ra St. Brown, Bijan Robinson, Dak Prescott, James Cook |
| 15 % | 4 | Lamar Jackson, Amon-Ra St. Brown, Bijan Robinson, Dak Prescott |
| 30 % | **1** | **Lamar Jackson** |
| 50 % | **0** | keiner |

Dies sind **weder konkrete Cut-Empfehlungen noch erzwungene Starter-Abgaben**. Mehrere Cuts, passende Trades, frühere Abgaben oder andere neue Salaries können einen völlig anderen Ausgleich erlauben. Aber der Test zeigt: Ein **zusätzlicher günstiger Bench-Cut** kann den Additiv-Cap sogar verschlechtern. Eine neue harte Regel benötigt deshalb einen **sicheren Settlement-Pfad** samt klarer Behandlung einer unerfüllbaren Pflicht – sonst entsteht eine Insolvenzfalle ohne bewiesene Käuferliquidität.

## 5. Kreditlimit unabhängig von der Tilgungsfrist

Für den Juni-2026-C-add-Stand mit null Altschuld gelten folgende hypothetische Gesamtschulden-Grenzen aus `floor(Prozent × 434.255.984 $)`:

| Kreditlimit | Maximaler Betrag | Wer überschreitet am 29.06.2026? |
|---|---:|---|
| **5 %** | **21.712.799 $** | Just Bill um **9.312.729 $** |
| **10 %** | **43.425.598 $** | niemand |
| **15 %** | **65.138.397 $** | niemand |
| **25 %** | **108.563.996 $** | niemand |

**Weitere sieben voneinander unabhängige 2025/26-as-of-Snapshots**, ohne C-add-Retention und mit `D_prior=0`, ergeben die folgende Zahl von Teams oberhalb der Kreditgrenze (**keine sieben Jahresdeadlines**, und die Stände dürfen nicht zu einer Verlaufsrechnung addiert werden):

| Datum | 5 % | 10 % | 15 % | 25 % |
|---|---:|---:|---:|---:|
| 05.11.2025 | 2 | 0 | 0 | 0 |
| 05.12.2025 | 1 | 0 | 0 | 0 |
| 21.12.2025 | 1 | 0 | 0 | 0 |
| 29.06.2026 | 0 | 0 | 0 | 0 |
| 25.08.2026 | 0 | 0 | 0 | 0 |
| 09.09.2026 | 3 | 1 | 0 | 0 |
| 05.11.2026 | 4 | 2 | 1 | 0 |

2025 verwendet ausschließlich historische `SalaryDollars`/Top120÷6, 2026 `Salary`/0,9×Top120÷6. **25 %** wirkt in dieser Beobachtungsauswahl nicht limitierend. **5 %** hat bereits spürbar schärfere Wirkung und birgt entsprechend größeren Settlement-Druck.

Das bereits in CP5d geprüfte **rein hypothetische Dezember-2025-Schuldseed** produziert verbunden mit Juni-Cadd **84,34 Mio. $**, gegenüber **48,10 Mio. $** bei C-virt. Die historischen Dezemberstände sind **keine bewiesene Debt-Deadline**; daraus darf insbesondere keine echte fällige 2026er H2-/H3-Rate abgeleitet werden.

## 6. Sechs Nordstern-Ziele und Vergleich mit F2/F3/permanent

| Ziel | C-add + H2/H3 potenziell positiv | Ungeprüfte Gegenwirkung |
|---|---|---|
| **1 Langfristige Chancengleichheit** | Vorheriger Überschuss wird zur zukünftigen Last | Hohe Debt kann schwächere Teams ebenfalls länger zurückwerfen; keine gemessenen Titel-/Aufholchancen |
| **2 Management belohnen** | Cap-Planung, Cut-Timing und Veräußerung statt bloßer Gratis-Cuts werden relevanter | Buyer-Liquidität und echte Managerpräferenz fehlen |
| **3 Kein garantiert perpetuierter Vorteil** | Kredit läuft nicht ohne neue Entscheidung/Kosten unbegrenzt weiter | Weiterhin freies In-Season-Akkumulieren bis zum Jahrescheck |
| **4 Preis sportlicher Dominanz** | Reale Ein-Zyklus-Haftung auch bei Nicht-Top20-Cuts; mehrjährige aggregierte Debt | Star-/Bench-Cuts können hart wirken, auch bei legitimem Rebuild |
| **5 Strategievielfalt** | Win-now mit späterer Belastung gegen Reload abwägbar | Zu kurze Laufzeit/enger Deckel kann einseitig wirtschaftlich zwingen |
| **6 Operativer Vollzug** | Wenige feste Checks, ein aggregierter Schuldjahrgang/Team, vorhandene Cut-Ereignisse statt individueller Verträge | Hard-Failure-Fall und tatsächliche Commissioner-Minuten offen |

**F2 bleibt eine ernsthafte Konkurrenz:** Ein zusätzlicher verbindlicher Check **nach dem FA-Draft** hätte beim isolierten 09.09.2026-Preisstand **vier Teams und 122.567.015 $** positiven Überhang betroffen. C-add/H2/H3 hält die Juni-Cuts teurer und macht erst **künftige jährliche Deadlines** für Nachfinanzierung bindend; es ersetzt diese unmittelbare Post-Draft-Wirkung **nicht**. F3 und permanenter Cap stehen weiterhin als Vergleich, nicht als schon entschiedene Umsetzung.

## 7. Handoff / noch offene Gates

1. **Nutzerpräferenz C-add** bewusst als wichtiges Forschungssignal erfassen; keine Liga-Ratifizierung daraus ableiten.
2. **Jahrgangslaufzeit** H2 vs. H3 getrennt von **Kreditgrenze** 5 vs. 10/15 % testen; kein „einfache Lösung = 10 %/2 Jahre“ beschließen.
3. **Schuld nicht refinanzierbar**, Altjahrgang vor neuer Aufnahme bedienen, keine Schuld abschneiden und keine automatisch ungewollten Cuts. Hard-Settlement-Failure und überprüfbare Nachfrist ausdrücklich als offene Ligaentscheidung führen.
4. **Käufer-, Trade- und Cap-Liquidität** unter C-add prüfen: Rechenbare Einzel-Cuts sind keine tatsächlich realisierbaren Managerentscheidungen.
5. **Operative Kosten** eines Jahresabschlusses einschließlich Cut-Ledger, Jahrgang, Review und Eskalationsfall in einem Pilot messen. Es liegen noch keine realen Minuten vor.

Die Baselines A jährlich, F2/F3 feste zusätzliche Termine, B permanenter Cap und C-virt Kontrollrechnung bleiben vergleichbar, ohne die Preis-/Zeitachsen zu mischen. CP5-Rest (mehrjährige Wettbewerbseffekte, echte Manager-/Käuferreaktionen, gemessener Betreiberaufwand) und CP6-Ligaentscheidung sind **offen**; keine aktive Liga-/Salary-/App-/Workflow-/Data-Source-Regel wurde geändert.
