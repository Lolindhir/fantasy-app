# CP6o – 100/50/25-Prozent-Garantien: tatsächliche synthetische Cut-/Ersatzspieler- und Dead-Cap-Recovery

> **22.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Forschung, keine neue aktive oder ligaweit ratifizierte Regel.** Der Nutzer bestätigte für die Vertrags-Hypothese: Cap bleibt **jährlich aus aktuellen Marktwerten** und darf auch sinken; Vertragssalär der Rookies bleibt **100/125/150 %**, Veteranenstaffeln werden variiert; in Vertragsjahr 1/2/3 sind **100/50/25 % des jeweiligen Jahresgehalts** garantiert. **Keine wöchentliche Auszahlung** in diesem Checkpoint. Auftrag: unter denselben CP6n-Zukunftsszenarien echte modellinterne hypothetische Cuts + bezahlte FA-Ersatzverpflichtungen und Jahrgangs-Dead-Cap rechnen; gegen 100-%-Vollgarantie prüfen.

## 1. Strikte Daten-/Regelwelt und Reproduktion

- Reproduzierbare **[CP6o-Engine](../simulation/cp6o_guaranteed_cut_recovery.mjs)**. Die Engine enthält einen unveränderten, explizit eingefrorenen CP6k-Modellkern aus Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`. Das historische 2026er Player-CSV aus Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489` enthält 1.268 Ausgangsdatensätze; seit 2027 kommen synthetische Rookies hinzu.
- Drei Seeds **11, 29, 47**: jeweils sechs **disjunkte, vollständige Full-Salary**-Kader, zunächst alle **2027 caplegal** nach 30 Rookie-Draft-Signings und CP6k-Salary-Reparatur. 2027er Cap und sämtliche sechs Team-Salary-Summen in allen Seeds gegen die ursprünglichen [CP6n-2027-Kohorten](2026-11-22-cp6n-contract-cohort-inputs.json) exakt geprüft.
- Erstmals tatsächliche **2028er und 2029er jeweils 30 neue Rookie-Draft-Verträge** (= fünf Picks pro Team pro Jahr), fixierte 100/125/150%-Rookie-Staffel, anschließend Vor-Cap-Deadline-Korrektur der sechs Owner. Der Simulator bewahrt ID-Exklusivität aller Eigentümer, verlangt mindestens 20 besetzte Research-Plätze (CP6k), maximal 40 Research-Plätze, zwölf QB/RB/WR/TE-Pflichtstarter? **Nein:** weiter die ursprünglichen **13 Starter: QB2, RB2, WR2, TE2, FLEX4, K1**, plus CP6k Positionsdeckungs-Minima. Im produktiven Sleeper sind derzeit **30 normale Slots**, 5 IR/Reserve, 2 Taxi, ohne diese hier modellierte Rechtslage; die 40er-Variante ist noch hypothetisch.
- Das ausgeführte ursprüngliche `world.price` bleibt das **CP6k-Preis-/Cap-Referenzmodell**. **Kein vollständig von Rookie-Kontraktpreisen entkoppelter neuer MarketValue-Index**; 2027 ca. 11 %, 2029 ca. 14–15 % des Top120-Dollarvolumens stammen im CP6k-Modell aus Rookie-Vertragspreisen. Die künftig separate Marktwert-Datenprodukt-Fassung ist **ein zwingendes Forschungs-Gate**, keine hier schon validierte Implementierung. Jeder zusätzliche −10 %/−20 %-Schock wird auf das jeweilige CP6k-Top120-Cap von **2028 und 2029** gleichmäßig angewendet, **nicht** multipliziert zwischen den Jahren. Die 2027er Caps bleiben unverändert. Keine reale 2027–29-NFL-Prognose.
- **Erstvertragsannahme:** alle 2027 vorhandenen Spieler außerhalb des neu 2027 gedrafteten Rookie-Kohorts sind synthetische **neu 2027 signierte Veteranen-/Altverträge**. Echte vor 2027 vorhandene Contract-Vintages wurden mangels unterschriebener Historie **nicht erfunden**. Bei 2028/2029 unter Vertrag genommenen unowned Free Agents startet ein neuer dreijähriger Vertrag zum dann im Modell gültigen Markt-/Salary-Ausgangswert.
- **Veteranen-Vertragsstaffeln:** Year1/2/3 `100/100/100`, `100/105/110`, `100/110/120` % auf die ursprüngliche Year1-Dollarbasis, nicht kumulativ. Garantien unter der Hauptvariante Year1/2/3 `100/50/25` % des jeweiligen Jahres-Schedules; Referenz `100/100/100` Vollgarantie.
- **Cut-Zeitpunkt:** ausschließlich vor jährlichem 2028er/2029er Salary-Cap-Settlement, vor Spieltag 1, **ohne wöchentliche Proratisierung**. Cut gibt das *nicht garantierte* aktuelle Jahr frei, das garantierte aktuelle Jahr zählt als Dead Cap; bereits verpflichtete zukünftige Jahre werden mit ihrer jeweiligen **Jahr-2-/Jahr-3-Garantie** in den Dead-Cap-Ledger gebucht und nur in dem entsprechenden Kalenderjahr cap-wirksam. Auch ein gerade signierter Rookie wäre im aktuellen Year1 zu 100 % garantiert, sodass ein sofortiger Cut in dieser Saison **kein** Budget freimacht. Keine beliebige beschleunigte Gesamtforderung in einem einzelnen Jahr.
- **14-Tage-Claim-Fenster**: im getesteten Stressfall ausdrücklich **kein realisierbarer Käufer/Claim**; die Frist ist als abgelaufen angenommen, der ursprüngliche Owner behält den garantierten Teil, der Cut-Spieler kann nicht sofort wieder zum neu errechneten günstigeren Preis unterschrieben werden. Kein Trade, kein gültiges Käuferangebot und keine Spielerechte für zukünftige Saison erfunden; die Free Agents stammen ausschließlich aus wirklich unowned, aktiven CP6k-Spielern, die noch nicht unter verbotener erneuter Cut-Aufnahme stehen.
- **Management-Aktion:** ein deterministischer, budget- und lineup-bewusster **Greedy-Algorithmus**, der echte modellinterne Cut-IDs auswählt und bei Positions-/20er-Grenzen verfügbare, preisgünstige reale Simulationspool-Spieler auf bezahlten neuen Dreijahresverträgen verpflichtet. Jede Aktion wird mit vorherigem vollem `AnnualSalary`, zeitgleicher Garantie, künftigen Garantien, Netto-Cap-Relief, neuer FA-Salary und Roster/Lineup danach im Audit-JSON geloggt. **Kein Beweis eines optimalen oder von allen Managern freiwillig gewählten realen Managements**; Reihenfolge / FA-Pool / ohne Waiver-Konkurrenz können die Qualität und Sanierung stark verändern. Teams, die nicht legal werden, bleiben als **fehlgeschlagen** ausgewiesen, nicht automatisch geheilt.
- **Vergleichsbasis:** exakt drei Seeds × drei Veteranen-Staffeln × drei Cap-Schocks × zwei Garantievarianten = **54** gepaarte hypothetische Pfade, jeweils bis maximal 2029; kein H2/H3-Kredit, keine unerklärte Zahlung aus Folgejahren.

Vollständige Einzelereignisse, Teamzustände, Dead-Cap-Jahrgänge und deren Weitertrag: **[Seed 11](2026-11-22-cp6o-seed11-guarantee-recovery.json)**, **[Seed 29](2026-11-22-cp6o-seed29-guarantee-recovery.json)**, **[Seed 47](2026-11-22-cp6o-seed47-guarantee-recovery.json)**. `--json` gibt alle Jahre/Teams und Aktionen aus.

## 2. Hauptergebnis: Vergleich 100/50/25 gegen Vollgarantie

| Gemessener Zustand | Garantie **100/50/25** | Garantie **100/100/100** |
|---|---:|---:|
| Gleiche gepaarte 3-Seed/3-Slope/3-Cap-Stress-Welten | 27 | 27 |
| Bis zum **2029er** jährlichen Settlement **alle sechs Teams** mit Full-Salary-Cap und 13 Starter-/20er-Positionsdeckungs-Minima legal | **27/27** | **0/27** |
| Durch algorithmische Cuts und FA-Käufe tatsächlich erreicht | ja, in den begrenzten Welten | ohne Buyer/Claim, 2028er Pfad gescheitert |
| Gesamte Cut-Ereignisse über **27 alternative** 2027–29-Pfade | **1.330** | nicht sinnvoll vergleichbar als Management-Cuts; keine sofortigen finanziellen Entlastungen |
| Neu signierte FA-Replacement-Verträge über 27 Pfade | **328** | keine |
| Neue Rookie-Draft-Verträge **je vollständig simuliertem Pfad** nach der 2027er Basis | **60** | erste 2028er Draftklasse: **30**; 2029 wegen 2028er Fehler nicht fortgesetzt |

**Leseregel:** 1.330 Cuts und 328 FAs sind **summierte Ereignisse aus alternativen Stresswelten**, **keine** tatsächlichen 1.330 Ligaaktionen. Nicht in Wahrscheinlichkeiten umdeuten. 27/27 beschreibt erfolgreiche **einzelne heuristische Beispiele**, nicht eine mathematisch globale Garantie, dass alle künftigen Caps/Kaderzustände legalisierbar wären.

**Wichtigster Gegenbeleg gegen die verkürzte Aussage „Vollgarantie = immer systemisch unmöglich“:** Schon bei **keinem zusätzlichen Cap-Einbruch** und **100/100/100 %-Veteranengehalt** scheitert im Vollgarantie-Modell 2028 je nach Seed nur **ein einzelnes Team** (rund **1,21 Mio. $**, **14,07 Mio. $** oder **5,12 Mio. $** über Cap), obwohl die **ligaweite Gesamtsumme klar unter sechs Team-Caps** liegt. Das ist eine **fehlende liquiditäts-/übernahmewirksame Gegenmaßnahme** unter dem untersuchten no-Claim/no-Trade-Mechanismus; ein realer Käufer könnte den konkreten Fall beheben. Bei dramatischem Cap-Einbruch können darüber hinaus echte **aggregierte, selbst durch Trades nicht heilbare Vollgarantie-Lücken** entstehen (wie im CP6n-Stress dokumentiert). **Diese zwei Ausfallgründe sind nicht identisch.**

## 3. Wie viele Cuts braucht die Teilgarantie?

Nachstehend die **Spanne über die drei Seed-Welten pro vollständigem 2027–29-Pfad**, inklusive 2028 und 2029, zusammen für die sechs Teams. Die unterschiedlichen Seeds besitzen nicht dieselben Player-Owner-Startverteilungen; kein probabilistisches Confidence-Intervall.

| Veteranen-Year1/2/3 | Kein Zusatzschock | Markt-Cap −10 % | Markt-Cap −20 % |
|---|---:|---:|---:|
| **100/100/100** | **8–12 Cuts** | **31–37 Cuts** | **55–65 Cuts** |
| **100/105/110** | **21–32 Cuts** | **52–58 Cuts** | **68–75 Cuts** |
| **100/110/120** | **40–44 Cuts** | **59–68 Cuts** | **79–83 Cuts** |

Hier zeigt sich der Preis der Entscheidung: Die Garantie-Staffel **macht Sanierung möglich**, aber **eine stärkere automatische Gehaltseskalation in schwachen Marktjahren** verstärkt den personellen Aderlass teils massiv.

### Harte Kombination: 100/110/120 Veteranengehalt, −20 % Cap

| Messgröße über 2028 und 2029 | Seed 11 | Seed 29 | Seed 47 |
|---|---:|---:|---:|
| Cuts 2028 | 67 | 75 | 70 |
| Cuts 2029 | 12 | 8 | 11 |
| **Cuts gesamt** | **79** | **83** | **81** |
| Entgeltpflichtige Ersatz-FA-Signings gesamt | **26** | **35** | **32** |
| Neu signierte Rookie-Draftverträge gesamt | 60 | 60 | 60 |
| **Dead Cap im Jahr 2028** | 546,66 Mio. $ | 665,25 Mio. $ | 584,67 Mio. $ |
| **Dead Cap im Jahr 2029** | 376,71 Mio. $ | 413,66 Mio. $ | 365,57 Mio. $ |
| **Alle sechs Teams** 2028/2029 legal? | Ja/Ja | Ja/Ja | Ja/Ja |

Die Beträge aus 2028 **werden nicht blind in 2029 übertragen**. 2028 schon gecuttete 2027er Verträge hinterlassen für 2029 die **bereits bei Vertragsabschluss garantierten 25 %-Year3-Anteile** (Seed 11 ca. **302,11 Mio. $**); zusätzliche Cuts **2029** erhöhen dann den fälligen 2029er Dead Cap weiter auf **376,71 Mio. $**. Genau diese Jahrgangsrechnung verhindert sowohl stillen Erlass als auch die Verwechslung mit einem H2/H3-Cap-Kredit.

### Der eigentliche sportliche Preis ist schwerwiegend

Beispiel Seed 11, hartes Szenario vor/nach **2028er** Cuts, am selben modellinternen Spielerwert-/Lineup-Zeitpunkt:

| Betroffenes Team | Starterindex vorher | Starterindex danach | Verlust |
|---|---:|---:|---:|
| Team 0 | 197,115 | 141,068 | **−56,047** |
| Team 1 | 192,850 | 160,828 | **−32,022** |
| Team 2 | 191,858 | 133,983 | **−57,875** |
| Team 3 | 177,936 | 176,129 | −1,807 |
| Team 4 | 171,198 | 171,198 | 0 |
| Team 5 | 163,465 | 163,465 | 0 |

**Das ist ein entscheidendes Gegenargument zur schnellen Empfehlung „27/27 legal = gutes Liga-Design“:** Die vorher stärksten Teams verlieren potenziell dramatisch an Wettbewerbsfähigkeit, während die zuvor günstigeren Teams den Schock weitgehend überstehen. Ein solcher Jahrgangswechsel kann gewünschte Aufholbarkeit schaffen – er kann aber auch übermäßig brutale, spielspaßarme Franchisefallen verursachen. Und mit freiem freiwilligem Trade-/Claim-Markt würde sich dieser Verlauf möglicherweise deutlich unterscheiden. Keine Aussagen über echte 2028er Titelchancen ableiten.

## 4. Mildes Gegenbeispiel: Nicht jeder Cap-Reset erzeugt Cap-Hell

Bei **100/100/100 Veteranengehalt** und **keinem zusätzlichen Markt-Cap-Schock**, Garantie 100/50/25, erforderte das vollständige dreijährige Modell nur **8–12 Cuts** je sechs-Team-Liga, **0–1** neue Ersatz-FA-Signings und jährlichen 2029er Dead Cap von ca. **40,88–65,48 Mio. $**. Es gibt weiterhin teure Folgen; aber kein notwendiges massives Zerbrechen aller bestehenden Teamkerne.

Die Entscheidung über **Veteranen-Eskalation (0/5/10 % jährliche zusätzliche Erstbasis)** ist damit fast genauso systemrelevant wie die Garantie selbst. Die Rookie-Staffel 100/125/150 % wurde dabei in **allen** Varianten unverändert weiter verwendet.

## 5. Die fünf verpflichtenden Finanzierungsachsen

1. **Seller Relief:** Kein Trade-Seller in CP6o. Beim Cut spart Team A im jeweiligen Jahr **(1−Garantiequote)×gesperrtes Jahresgehalt**, solange kein aktueller Ersatz notwendig ist. Beispiel bei 21 Mio. $ Year2-Gehalt: 10,5 Mio. $ aktuelle Pflicht-Dead-Cap-Kosten, 10,5 Mio. $ *brutto* frei; künftiger Year3-Dead Cap zusätzlich nach dessen fixem 25 %-Dollar-Schedule. Bereits bestehende andere Jahrgangsgarantien im Team zählen extra. Die Aktion kann zusätzlich eine **neue vollwertige** 3Y-FA-Verpflichtung erzeugen. Starker Nettoeffekt erst nach vollständigem Bundle.
2. **Buyer Burden:** Für Claims und bilaterale Trades **kein Käufer beobachtet oder erfunden**. Bei jeder tatsächlich im Modell zugewiesenen unowned FA wird die **vollständige aktuelle Salary** sowie die Folgejahre des neuen Vertrages beim aufnehmenden Team gebucht. Cutspieler werden bewusst nicht fiktiv von einem fremden Team übernommen. Der neue Käufer des ursprünglichen Vertrags, seine Zustimmung und sein künftiger Claim-Cap wären ein anderer Simulationsbranch.
3. **Roster / IR / Taxi:** Vollständige Positions-/13er-Startdeckungsprüfung plus **Research-Minimum 20 und Maximum 40**, einzigartige Ownership, all-held full-salary, 30 neue Rookie-Verträge/Jahr. **Aktive Sleeper-Slots sind 30 normale, 5 IR, 2 Taxi**, und diese 2027er zukünftigen Taxistatus-/IR-Rechte **nicht** modelliert. Die Forschung belegt daher **keine** 2027er echte Sleeper-legalen 40er-Roster oder alle tatsächlichen FA-/Cut-Abwicklungen.
4. **Ligaweite Schuld / Jahrgang:** Kein H2/H3-Kreditmechanismus. Jeder nicht übernommene Cut wird **pro ursprünglichem Vertrag + Signierjahr + Fälligkeitsjahr** garantiertem Dead Cap beim damaligen Team zugeschrieben. Keine Schuld wird ersatzlos gelöscht, kein Dead Cap still bei jährlicher Marktwert-Neubewertung resettet. Die im alten Canon beschriebenen C-add-Ein-Zyklus-50/30/15/5-Tenure-Regeln sind **andere unratifizierte Kandidaten**, nicht kumulativ in CP6o eingeschaltet. Full/Partial-Garantie miteinander zu addieren wäre falsch.
5. **Künftige Erfüllbarkeit:** Für jeden Pfad wird 2028 und 2029 **nach** den tatsächlich vorgenommenen Modell-Cuts, bezahlten FA-Bundles, Rookies sowie aktuellem Dead Cap gegen das jeweils geltende, eventuell sinkende MarketCap geprüft; die noch ausstehenden Dead-Cap-Jahrgänge **bis nach 2029/2031** werden ausgewiesen. Erfolgreiche Checks über 2029 sind **kein** Beweis für 2030/31, wenn neue FA-/Rookie-Signings dann weiterlaufen. Fehlgeschlagene Vollgarantie bleibt **unresolved**, nicht per erfundener Refinanzierung, Cap-Anhebung oder Commissioner-Autocut geheilt.

## 6. Nordstern: Was gewinnen wir, was verlieren wir?

| Ziel | Ergebnis CP6o | Weitere Prüfung |
|---|---|---|
| **1. Langfristige Aufholbarkeit** | Wiederholte Marktschocks können über günstigere Garantien finanzielle und sportliche Vorteile bestehender Topteams tatsächlich abschmelzen | 2028er Ex-ante-Indexverluste bis ca. 58 Punkte einzelner Teams: **zu hart?** Langjährige Title/Rebuild-Kausalität noch offen |
| **2. Gutes Management belohnen** | Contract-Kosten, junge günstige Rookieverträge und vorsorgliche Salaryplanung erzeugen mehrjährige Trade-offs | Greedy hat nicht Managerpräferenzen, Trading, Prepicks, Verhandlungen oder antizipierte 2029er Kosten optimiert |
| **3. Keine unendlichen Vorteile** | Drei-Jahres-Contract-Expiry, dynamische Marktpreise und garantierte Altverpflichtungen bilden tatsächliche Gegenkräfte | 2027er historische Alt-Vertragsjahrgänge fehlen, echte 2030er Renewal- und Claim-Märkte fehlen |
| **4. Wirtschaftliche Konsequenzen** | Direkter Befund: 2028 gecuttete Spieler verursachen noch 2029 echten fälligen Dead Cap; Cap darf trotz laufender Verträge sinken | Nicht jede wirtschaftliche Konsequenz ist gesund; aggregierter Cap-/Garantieausfall vs. lokale Reparaturkosten unterscheiden |
| **5. Strategische Freiheit** | Teilgarantie ermöglicht echte Cap-Rettung statt der starren 100%-Vollgarantien; günstige FA und Rookieoptionen | No-Claim-Marktheuristik kann hochwertigen Spielerhandel massiv **unterschätzen**; Roster-Schließung via Cuts erzwingt einseitiges Team-Verhalten |
| **6. Operative Umsetzbarkeit** | Dollar-Jahrgangsledger, jährliche Checks und Gap-Ausweise algorithmisch klar und nachvollziehbar, **ohne** Weekly-Payroll | Kein in Sleeper automatisch durchsetzbares Cut-Claim-14d-/Trade-Bundle-/Starter-Sperrgate; Jahresschnitt vielleicht organisatorisch einfacher als permanent |

## 7. Schlussfolgerung und nächstes Forschungs-Gate

**Zwingend differenzieren:** Unter den 54 definierten, gepaarten Pfaden **ist 100/50/25 eine wirksame Reparaturmechanik**. Vollgarantie ohne Käufer ist in diesen Pfaden schon bei sehr kleinen individuellen 2028er Defiziten nicht sanierbar. **Doch**: Die Reparatur kann extreme sportliche Einbrüche und viele Cuts erzeugen; **27/27 legal ist keine hinreichende Auszeichnung des Regelwerks**.

**Forschungspriorität:** 100/50/25 als bevorzugte **Garantie-Sensitivität** weiterführen, Veteran-Y2/Y3-Eskalation 0 % / 5 % / 10 % eng vergleichen, keine wöchentlichen Payroll-Ledger starten. Das MarketCap nach echten contract-unabhängigen Rookie-Marktwerten definieren und die 2024–26er Vertragsanfänge beziehungsweise eine **bewusst neu festgelegte 2027er Übergangsregel** rekonstruieren. Danach echte sechsfach begrenzte Käufer-/Verkäufer-/Waiver-Claim- und Draft-Pick-Märkte mit beidseitiger Cap-Abrechnung und leistungsfähigem, nicht nur greedy Managerverhalten simulieren; zusätzlich das per Jahr unattraktive Alt-Contract-Salary analysieren. Dann können A/F2/B Cap-Checkpoint-Frequenzen bei **identischer Markt-/Contract-Welt** bewertet werden. Vor produktivem Einsatz 14-Tage-Claim- und Signing-Grace-Hard-Failure/Starter-/Waiver-Regeln explizit ligaweit abstimmen, keine Auto-Cuts.

**Projektzustand:** nur Forschungsbranch und Draft-PR; active `League.json`, Sleeper, Salary und die sechs geschützten Liga-Ziele unverändert. Die kanonische Rookie-/Ein-Zyklus-C-add-Diskussion wurde nicht überschrieben. 
