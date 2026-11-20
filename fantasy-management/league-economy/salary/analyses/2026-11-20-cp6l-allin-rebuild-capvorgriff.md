# CP6l – All-in, Cap-Vorgriff und Rebuild als mehrjährige Finanzierungsstrategien

> **20. November 2026 · Forschung, kein Ligabeschluss und keine aktive Regel.** [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344), Fortsetzung von [CP6k](2026-11-19-cp6k-six-team-paired-5y.md) unter dem unveränderten [geschützten Sechs-Ziele-Nordstern](../../../league-context/league-philosophy.md). Der Nutzer möchte Cap-Vorgriff/All-in und Rebuild ausdrücklich in den Langzeitvergleich aufnehmen.
>
> **Grenze:** Dieser Checkpoint führt einen **real berechneten, vollständig replizierbaren FINANZIERUNGS-Stresstest** aus, aber **noch keinen** sportlichen All-in-gegen-Rebuild-Simulator mit echten beidseitig legalen Trades, Draftpick-Transfers, Verletzungen und C-add-Retention. Aus reiner theoretischer finanzieller Kreditfähigkeit darf keine zusätzliche Starterqualität oder realisierbarer Trade behauptet werden.

## 1. Das erweiterte Forschungsproblem: Stärke über die Zeit verschieben

CP6k verglich `passiv halten` mit `aktiv reloaden`. Dabei waren alle sechs Teams jährlich cap-konform, aber es gab **kein** mehrjähriges Kredit-/Tilgungsledger, keine echte Veteranenveräußerung gegen Picks und keine inter-team Trades. Ein höheres Fünfjahres-*Minimum* `H5 = min(I_2027,...,I_2031)` belohnt vor allem gleichmäßige Qualität. Es **bestraft konstruktionsbedingt** eine absichtliche Rebuild-Saison und kann einen völlig rationalen **All-in-Titelversuch** schlecht bewerten.

Deshalb künftig **zusätzlich zum H5** explizit messen:

- **All-in:** kurzfristige, rechtlich und finanziell **echte** Qualitäts- und Titelchancensteigerung aus künftig fälligen Cap-Schulden, inklusive verlorener Assets und des späteren Gehalts-/Tilgungsdrucks;
- **Reload:** jährliche aktive Kadererneuerung ohne übermäßige Schuld, nachhaltige Ausgangsstärke und Option, später zu kaufen/verkaufen;
- **Rebuild:** absichtlich günstigerer aktueller Kader mit wirtschaftlich **wirklichen** Zukunftsassets: günstig erworbene junge Spieler und reguläre bzw. durch echte Trades erhaltene Draftpicks; niedrigere aktuelle Cap-Summe ist **kein** von selbst in 2028 übertragbares Guthaben;
- **Hybrid/Timing-Option:** wann lohnt sich der Wechsel vom Reload zum All-in oder zum Rebuild? Offene Trades und 4/6 Playoff-Plätze verleihen Abwarten einen Optionswert.

Primärer **Strategievergleich** sollte deshalb jährliche Starter-/Playoff-/Titelwahrscheinlichkeiten, erfolgsgewichtete Mehrjahreswerte, maximale Titelfenster, Rückzahlungs-/Insolvenzrisiko, Rebuild-Turnaround, Assets und Fairness enthalten. `H5` bleibt ein **separater Robustheits-/Dominanzwert**, ist aber nicht alleiniger Strategie-Siegerindikator. Kein künstlicher Zwang, dass Rebuild oder dauernder Championwechsel stattfinden muss.

## 2. Bindende Forschungspräzedenz und offen gebliebene Mechaniken

[CP5d](2026-11-15-salary-cap-cp5d-debt-backtest.md) zeigte, dass ein reiner Kreditdeckel ohne verbindliche Amortisation prinzipiell ewig bestehen bleiben kann. [CP5e](2026-11-15-salary-cap-cp5e-additive-debt-amortization.md) testete getrennt:

- **Gesamtkreditgrenzen:** 5/10/15/25 % des jeweiligen Team-Caps, **nicht ratifiziert**;
- **H2:** jede Schuldenvintage benötigt zwei **folgende** Jahreschecks; 2027er Neuaufnahme frühestens 2028 zu tilgen, vollständig spätestens am Check 2029;
- **H3:** drei folgende Checks, letzte Rate 2030;
- **verbindliche Mindestjahresrate** `ceil(Restschuld / verbleibende Checks)`, älteste Vintage zuerst, vollständige vorzeitige Tilgung erlaubt;
- **No-refinance-Gate:** fällige Tilgung **nur** aus tatsächlichem `Cap − gehaltene volle Salaries − aktuelle additive Retention`, **nicht** aus neuer Schuld, weder stiller Erlass noch automatisch fremde Spieler entlassen;
- **C-add Cut-Retention:** getrennt von aggregierter Schuld; konzeptionelle Staffel 50/30/15/5 % nach ununterbrochener Team-Tenure, Reset beim nächsten regulären Salary-Check. Cut und Trade deshalb niemals wirtschaftlich gleich behandeln.

Für unsere **andere** Full-Salary-Forschungswelt gilt dabei `vollständige Summe aller gehaltenen Spieler` statt Top-20. Die individuelle additive Retention muss künftig **zusätzlich** getragen und getrennt von echten Darlehensvintages gebucht werden; sie ist im vorliegenden CP6l-Pilot bewusst noch nicht enthalten.

## 3. CP6l – ausgeführter Finanzierungs-Stresstest

**Reproduzierbarer Code:** [`cp6l_cap_deferral_overlay.mjs`](../simulation/cp6l_cap_deferral_overlay.mjs) · [komplette maschinenlesbare Ergebnisse](2026-11-20-cp6l-financing-metrics.json).

**Eingaben:** exakt die drei in CP6k archivierten Seed-JSONs [11](2026-11-19-cp6k-seed-11-results.json), [29](2026-11-19-cp6k-seed-29-results.json), [47](2026-11-19-cp6k-seed-47-results.json), jeweils 30 gedraftete plus **0/30/50 zusätzlich undrafted Rookies** und dieselben **passiven/aktiven** Sechs-Team-Pfade. In jedem davon bleibt das aus der **vollständigen Salary-Anrechnung** endogen entstandene Team-Cap identisch zu CP6k.

**Finanzierungsalternativen je 2027er Team-0-Pfad:**

1. Einmalig **5 %** des 2027er Caps leihen, Gesamtlimit 10 %;
2. einmalig **10 %**, Limit 10 %;
3. einmalig **15 %**, Limit 25 %.

Jeweils **H2 oder H3**, sowie **nur fällige Mindestraten** vs. **sofortige freiwillige Maximaltilgung aus sämtlichem sonst ungenutztem jährlichem Cap**. Null hypothetische Zinsen; diese Annahme ist eine Sensitivität, **keine festgelegte Kreditkondition**. Bei sinkendem künftigem Cap wird auch der Kreditdeckel jährlich neu geprüft.

**Wichtigste günstige Annahme:** Das „finanzierte zusätzliche All-in-Salary“ ist nur ein **2027er Einjahres-Finanzrahmen** von `damals ohnehin ungenutztes Cap + neuer Kredit`. Dieser zusätzliche Vertrag **verschwindet im Modell nach genau einer Saison**, ohne neuen Dead Cap, ohne Verlust an Picks und ohne Gegenpartei. CP6k-Kader und Spielerpunktzahlen bleiben 2028–2031 exakt identisch. Das ist also ein **optimistischer, nicht automatisch realisierbarer Schuldendienst-Test**, **keine** akquirierte Star-Verstärkung und **kein** direkter quantitativer All-in/H5-Vergleich. Reale Starverträge/Trade-Assets würden die Tilgung in der Regel erschweren.

**2027er Referenzwelt – Supply 30, aktives Regime, in Mio. $:**

| Seed | Jahres-Cap | tatsächlich gehaltenes Full Salary | bereits freier Cap-Raum | 10-%-Vorgriff |
|---:|---:|---:|---:|---:|
| 11 | 491,895 | 441,472 | 50,423 | 49,190 |
| 29 | 491,811 | 438,730 | 53,081 | 49,181 |
| 47 | 491,904 | 429,454 | 62,450 | 49,190 |

**Wichtig:** Wer zunächst die vorhandenen rund 50–62 Mio. $ ausgibt, betreibt **noch keine kreditfinanzierte** Überinvestition. Erst die Verbindlichkeit über dem ursprünglichen Cap schafft echten All-in-Vorgriff. Das zusätzliche Budget ist **nicht** notwendigerweise ein real ausführbarer Spielertransfer.

### 3.1 Ergebnis: Finanzierung eines zusätzlichen Einjahres-Investments

Für die **drei aktiven Seeds und 30 zusätzliche undrafted Rookies**:

| 2027er Kredit | Frist | Nur Pflicht-Mindestraten gedeckt | Mit frühestmöglicher höherer Tilgung gedeckt |
|---|---|---:|---:|
| **5 %** (~24,6 Mio. $) | H2 | **3/3** | **3/3** |
| 5 % | H3 | **3/3** | **3/3** |
| **10 %** (~49,2 Mio. $) | H2 | **2/3** | **3/3** |
| 10 % | H3 | **2/3** | **3/3** |
| **15 %** (~73,8 Mio. $) | H2 | **0/3** | **1/3** |
| 15 % | H3 | **2/3** | **2/3** |

Dies sind **durchgerechnete Finanzierungsfeasibility-Proben**, nicht der Anteil realer Manager, der erfolgreich leihen könnte. Wenn eine Mindestrate ungedeckt bleibt, ist der Weg nach dem harten Forschungsgate **nicht compliant**, selbst wenn die Restschuld rechnerisch erst nach dem Endtermin irgendwann bezahlt werden könnte. Fehlende Cap-Entlastung darf nicht durch automatische Cuts oder neue Kredite erfunden werden.

**Konkreter Seed-47-Stress, 2027er 10-%-Kredit/H2:**

- Ursprünglicher Kredit **49.190.414 $**, 2028er Mindestrate **24.595.207 $**, 2028er echter Cap-Puffer **37,922 Mio. $**.
- Werden 2028 **nur** die 24,595 Mio. $ Pflicht gezahlt, bleiben 2029 weitere **24,595 Mio. $** fällig. Der 2029er freie Cap-Raum beträgt jedoch nur **15,693 Mio. $**; die zusätzliche freiwillig aufzubringende Nettoentlastung beträgt deshalb exakt **8.901.710 $**.
- Wird der verfügbare 2028er Puffer von ca. **37,922 Mio. $ frühzeitig** zur Tilgung verwendet, bleibt bis 2029 genügend Restliquidität für die Frist. Dieser Weg ist rechnerisch compliant, **opfert aber Zukunftsflexibilität**; seine echten sportlichen Opportunitätskosten sind noch nicht eingerechnet.

Die vollständige CP6l-Matrix umfasst **18** CP6k-Sechs-Team-Pfade × **3** Kreditgrößen × **2** Laufzeiten × **2** Tilgungsweisen = **216** Finanzierungsfälle. Davon scheitern **88** unter den expliziten Bedingungen. Auch die erfolgreichen **128** Fälle sind **keine** nachgewiesenen ausführbaren All-in-Moves.

### 3.2 Rebuild: Cap-Spielraum ist noch kein Zukunftsasset

In denselben sechs-Team-Jahreswelten wurde berechnet, wie viel **zusätzliche** Salary-Entlastung nötig wäre, um 2027 **5/10/15 % des Caps absichtlich frei zu halten**.

Für die drei aktiven Supply-30-Seeds sind Zielwerte von **5 und 10 % schon ohne zusätzliche Abgaben** erreicht. Für ein bewusst höheres **15-%-Headroom-Ziel** (rund 73,8 Mio. $) müsste die eigene gehaltene Salary-Belastung zusätzlich sinken um:

| Seed | bereits freier Cap | zusätzliche Entlastung für 15 % Headroom |
|---:|---:|---:|
| 11 | 50,423 Mio. $ | **23,361 Mio. $** |
| 29 | 53,081 Mio. $ | **20,691 Mio. $** |
| 47 | 62,450 Mio. $ | **11,336 Mio. $** |

Dies ist **nur die Budget-Arithmetik**; es wurde weder jemand automatisch gecuttet noch eine Gegenpartei gefunden, die einen Veteranen für einen Pick kaufen möchte. Ohne explizit ratifizierten **Cap-Carryover** gilt: in Jahr 2027 nicht ausgegebenes Cap erzeugt **keine übertragene 2028er Kasse**. Ein Rebuild erhält Mehrjahreswert vor allem durch **legitim getauschte Rookie-Picks und günstige Nachwuchs-Verträge**, nicht durch ungenutztes Papierbudget allein.

### 3.3 Scheinbar gute Kreditinstrumente ohne sportlichen Nutzen

Die Schuldendienstprobe ist absichtlich günstig. Für die **vollständige All-in-/Rebuild-Integration** fehlen drei hochkritische Mechanismen:

- **All-in-Kaufkraft:** Welche tatsächlich **freien** oder von einem zustimmenden anderen Team verkauften Spieler sind mit zusätzlichem Budget erreichbar? Was sind Saldo aus Delta-Starterqualität, 2027er Zusatzsalary, 2028+ fortbestehender Salary und abgegebenen Picks?
- **Rebuild-Veräußerung:** Welche Teams brauchen die teuren Veteranen überhaupt? Wie hoch ist ihr **gesamter** Buyer-Cap-Aufwand, welche regulären Slots müssen sie freimachen und welche echten Picks/jungen Spieler treten sie dafür ab? Was geschieht bei fehlender Käuferliquidität?
- **Risiko und Zeit:** Ein All-in kann die Titelchance stark erhöhen und gleichzeitig H5 verschlechtern; ein Rebuild kann H5 absichtlich einbrechen lassen, aber 2029/2030 stärker sein. Deshalb **Jahresfenster, Wahrscheinlichkeitsverteilungen und Asset-Endwerte** statt eines H5-Siegerindikators.

## 4. Verpflichtender Fünfachsen-Nachweis (CP6l Phase 1)

| Achse | Unter dieser datierten Preis- und Kaderwelt |
|---|---|
| **1. Seller-Entlastung** | **Nicht modelliert:** kein tatsächlich ausgeführter Cut oder Verkauf. Das Rebuild-Ziel ist nur eine notwendige zusätzliche Payroll-Reduktion; Retained C-add 50/30/15/5 % muss bei konkreten Cuts als gesonderter **Nettoabzug** abgebildet werden, nicht kostenlose Entlastung. |
| **2. Buyer-Kosten** | **Nicht beobachtet/anwendbar:** es gibt keinen tatsächlichen Käufer/Trade, nur ein hypothetisches einjähriges zusätzliches Salary-Budget. Käuferbedürfnis, sämtliche Marginalkosten, Assetpreis und Counterparty-Akzeptanz unbekannt. |
| **3. Roster/IR/Taxi-Slots** | CP6k-Basisteams sind jährlich mit 20–40 regulären Spielern und 13 Startern legal; **ein tatsächlich zusätzlicher All-in-Spieler wurde nicht eingebucht**. Simultaner Drop, verfügbares Slotbudget, Taxi- und Reserve-Berechtigungen fehlen. |
| **4. Ligaweite Schulden nach Team/Vintage** | **Nur Team 0** bekommt hypothetisch ein 2027er Kredit-Vintage. Fünf Gegner bleiben in dieser **isolierten** Rechnung schuldenfrei, haben aber reale Schuld-/Trade-Daten hier nicht geliefert. Daher kein vollständig endogener Liga-Schuldenmarkt, keine geschobenen Buyer-Schulden. |
| **5. Künftige echte Tilgung** | H2/H3-Zahlungen in Dollar **berechnet**, Sollraten, Jahressummen, Limit und Ausfälle vorgelegt; **kein** Refinanzieren fälliger Raten, kein automatischer Schuldschnitt oder Auto-Cut. Aber die künftigen Salaries folgen der unveränderten CP6k-Gegenfaktik und sind **keine belastbare Prognose** nach realem All-in oder Rebuild. |

## 5. Bewertung anhand der sechs geschützten Ziele

1. **Langfristige Chancengleichheit:** Cap-Vorgriff kann kurzfristige Dominanz intensivieren; H2/H3 erzwingen spätere Gegenkräfte. Reale Aufholbarkeit von Verkäufern/Verfolgern noch unbewiesen.
2. **Gutes Management belohnen:** Frühzahlung und Kredit-Timing schaffen wirtschaftlich echte Planung; reine Mindesttilgung reicht in mehreren Fällen nicht. Strukturell guter Kreditmanager darf Vorteile erzielen, nicht kostenlos.
3. **Keine zementierten Vorteile:** Verbindliche Schlussraten sind stärker als bloßes 25-%-Limit; der harte Folgecheck kann späte Zahlungstermine blockieren. C-add-/Trade-Effekte fehlen.
4. **Wirtschaftliche Konsequenzen:** 15-%-All-in ist trotz günstiger Einjahreslaufzeit nur selten unter H2 finanzierbar; jeder Ausfall dokumentiert erforderliche **zusätzliche** Cap-Entlastung statt automatischer Straf-Cuts.
5. **Strategische Freiheit:** All-in, Reload und Rebuild können unterschiedliche rationale Fenster schaffen. Bewiesen ist vorerst nur ein Debt-Headroom-Konflikt; Asset-/Rebuild-Wert fehlt.
6. **Operative Umsetzbarkeit:** Pro Kreditjahrgang und Team genügt ein datiertes, versioniertes Debt-Ledger für H2/H3; der **Hard-Failure-Vollzug** (Commissioner/Appeal/Spielerabgabe) und tatsächliche Sleeper-Unterstützung bleiben offen.

## 6. Anschluss: CP6m-Strategiemodell in derselben Ausgangswelt

Ein **vollständiger Vergleich** darf erst als gelöst gelten, wenn folgende Gates gemeinsam erfüllt sind:

1. **Keine Baseline-Vermischung:** CP6k-Seed, sechs Eigentümer, identische Player- und Year1–3-Vintages, idente Performance-/Injury-/Rookie-Futures, dieselben globalen Top120-Caps. **Kein** unsichtbar erfundenes Spielerangebot.
2. **Lückenlose Transaction-/Asset-Engine:** real angebotene Stars/Free Agents; beidseitige Rosterlimits vor/nach Paket, erworbene/übertragene exakte Pick-IDs und Draft-Runden; **Buyer cap + vollständige Seller-Nettoentlastung**; genau ein Eigentümer pro Spieler und Pick, keine gratis Picks.
3. **Vintages und Tilgung:** Cap-Borrow H2/H3, 5/10/15/25-%-Deckel, keine neue Schuld zur Zahlung fälliger Alt-Schuld; C-add-Retention pro Cut gesondert und Reset nur am regulären Salary-Zyklus. Kreditzahlungen bei jedem jährlichen Settlement vor neuem All-in.
4. **Entscheidungsregime gepaart:** `passiv`, `reload`, `all-in-2027 + debt repayment`, `rebuild-2027/28 -> contend`, `hybrid/optional sell` mit vergleichbarer Informationslage/Managementaufwand der Gegner. Innerhalb der Fünfjahresgrenze **alle** H3-Vintages final prüfen oder explizite nicht abgegoltene Tail-Obligations ausweisen.
5. **H5 nur sekundär:** jährliche Starterindizes, realistische Weekly-Availability und projizierte Playoff-/Titelchancen, Top-Gap, Rendite abgegebener Picks, 2029/2031er Asset-/Cap-Wert und Time-to-Catch-up. Mindest-Roster-Depth und Future-Exit-/Rookie-Pool empirisch kalibrieren, CP6f/g auf identischen Inputs vergleichen.
6. **Fail closed:** Kommt kein legaler freiwilliger Schnitt/Trade zustande, ist die Szenariowelt **nicht compliant**; kein automatisch erfundener Commissioner-Cut und keine stillschweigend auf 2032 geschobene Tilgung. Track als Hard-Failure-Zweig und nicht als All-in-Sieg.

**Status:** CP6l ist ein dokumentierter, ausführbarer **Finanzierungs-Checkpoint**, kein vollendeter Strategie-/Sport-/Rebuild-Test. Aktive Salary-, Draft-, Cap- und Sleeper-Ligaregeln bleiben unverändert. Auch die sechs Nordstern-Ziele sind geschützt und noch nicht durch alle sechs Manager ratifiziert.
