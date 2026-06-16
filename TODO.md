# TODO

Menschenlesbare Projekt-Todo-Liste für `Lolindhir/fantasy-app`.

Diese Datei ist bewusst von `.ai-context` getrennt.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- `TODO.md` sammelt offene Umsetzungs-, Aufräum- und Dokumentationsaufgaben.
- Todos werden hier auf Deutsch gepflegt, damit sie einfach per Hand angepasst werden können.
- Erledigte Einträge können entfernt oder unten im Archiv abgelegt werden.

## Offen

### Data Generation / Drafts

- [ ] Draft-Live-Enrichment für `public/data/Drafts.json` ergänzen.
  - Kontext: Die abgeschlossene Draft-Historie wird separat gespeichert, aber im wöchentlichen/manuellen `RequestDrafts.ps1`-Flow zusammen mit den aktuellen Drafts aktualisiert. Für laufende Drafts im aktuellen `Drafts.json` fehlt das Ergebnis-Enrichment aber noch.
  - Ziel: Wenn ein aktueller Sleeper-Draft läuft, sollen echte Pick-Ergebnisse über `Get-SleeperDraftPicks` geladen und auf die bestehenden Draft-Picks gemappt werden.
  - Ziel: Pro Pick `PlayerID`, `PlayerName`, `SleeperPickNo`, `SleeperPickedBy` und `Status = Picked` ergänzen, ohne den stabilen `PickKey` zu verändern.
  - Möglicher Ansatz: Die Logik aus `Get-AppliedDraftPickResults` wiederverwendbar machen oder in `DraftUtils.psm1` übernehmen.

### Frontend

- [ ] `Transactions.json` im Frontend modellieren und für League Activity Moves anbinden.
  - Kontext: `src/app/league-activity/league-activity.ts` hat im MVP einen Moves-Platzhalter, weil `Transactions.json` noch nicht im `DataService` geladen wird.
  - Ziel: Transaction-Interfaces ergänzen und `DataService` so erweitern, dass Trades, Adds, Drops und weitere Roster Moves als expliziter Frontend-Vertrag verfügbar sind.
  - Ziel: Moves später in League Activity als chronologische Activity-Timeline darstellen.
  - Hinweis: Keine Pending-Transaction-Datei erzeugen, solange keine zuverlässige Pending-Quelle existiert.

- [ ] Draft-Pick-Anzeige als wiederverwendbare UI-Komponente prüfen und ggf. auslagern.
  - Kontext: Draft Picks werden inzwischen in `src/app/features/overview/overview.ts` und `src/app/features/league-activity/league-activity.ts` angezeigt.
  - Ziel: Gemeinsame Darstellung für Pick-Token, Current Owner und `from Original Owner` vermeiden doppelte Template-/ViewModel-Logik.
  - Mögliche Zielstruktur: `src/app/shared/components/draft-pick-chip` oder ein ähnlicher Shared-UI-Baustein.

- [ ] Draft-Round-Chip-Farblogik aus Overview und League Activity in eine gemeinsame Frontend-Utility, Pipe oder einen Service auslagern.
  - Kontext: Overview und League Activity berechnen die Farben aktuell lokal mit derselben warm-zu-kalt HSL-Skala.
  - Ziel: Alle Komponenten, die Draft Picks anzeigen, verwenden dieselbe Rundenskala.

- [ ] Alternative Sortierung für kompakte Upcoming-Drafts in League Activity prüfen.
  - Kontext: Upcoming-Drafts werden aktuell nach Pick Strength sortiert: zuerst Anzahl Picks in Runde 1, dann Runde 2, dann Runde 3 usw. bis zur flexiblen Draft-Rundenzahl.
  - Alternative: Optional eine Sortierung nach den Draft-Order-Regeln anbieten, z. B. Free-Agent-Drafts nach All-Time-Standings und Rookie-Drafts nach Saison-/Vorjahresplatzierung.
  - Ziel: Falls die Pick-Strength-Sortierung nicht intuitiv genug ist, später einen klar beschrifteten Sortiermodus oder Toggle prüfen.

- [ ] `DataService` strukturell aufteilen und Angular-Struktur prüfen.
  - Kontext: `src/app/services/data-service.ts` enthält aktuell Models, HTTP-Laden, Mapping, Draft-Enrichment, Free-Agent-Marktlogik, Salary-Helfer und Trade-Helfer in einer Datei.
  - Kontext: Die Zielstruktur `src/app/core`, `src/app/shared` und `src/app/features` ist vorbereitet; einige geroutete Feature-Einstiegspunkte re-exportieren aktuell noch alte physische Implementierungen.
  - Ziel: Modelle und app-weite Services perspektivisch in klarere Bereiche auslagern.
  - Ziel: Große Feature-Komponenten physisch aus den alten Ordnern nach `src/app/features/**` verschieben, sobald der Move zuverlässig lokal oder per PR-Patch möglich ist.
  - Zielstruktur prüfen:
    - `src/app/core/models` für League-, Player-, Draft-, Transaction-, Standings- und weitere Domain-Modelle.
    - `src/app/core/services` für app-weite Daten-, Mapping-, Draft-, Player-, Market-, Transaction- und Trade-Services.
    - `src/app/core/mappers` für fachliche Mapper, falls diese von den Services getrennt werden sollen.
    - `src/app/features` für geroutete Seiten und größere fachliche Funktionsbereiche.
    - `src/app/shared/components`, `src/app/shared/pipes` und `src/app/shared/utils` für wiederverwendbare UI-/Material-/Frontend-Helfer.
  - Mögliche Services prüfen: `data.service.ts`, `data-api.service.ts`, `league-mapper.service.ts`, `player-mapper.service.ts`, `draft-mapper.service.ts`, `transaction-mapper.service.ts`, `free-agent-market.service.ts`, `trade-calculator.service.ts`.
  - Optional: Import-Aliases wie `@core/*`, `@shared/*` und `@app/*` prüfen.

- [ ] Prüfen, ob die Inline-Styles der Draft-Pick-Chips aus dem Overview-Template nach `overview.scss` verschoben werden sollen.
  - Kontext: Die Darstellung funktioniert, aber ein Teil des Stylings liegt aktuell inline im Template.
  - Ziel: Template sauberer halten und Styling zentralisieren.

### Dokumentation / AI-Kontext

- [ ] Leichten Validierungscheck oder CI-Check ergänzen, der parallele AI-Kontext-Doku unter `docs/ai-context/**` verhindert.
  - Kontext: AI-Kontext-Dokumentation soll ausschließlich unter `.ai-context` liegen.
  - Ziel: Doppelte oder auseinanderlaufende Dokumentation vermeiden.

### Später / Ideen

- [ ] Rollenbasierte AI-Arbeitsmodi für fokussierte Chats prüfen.
  - Kontext: Aktuell soll ohne expliziten Rollenmodus weiterhin die vollständige Projekt-Guidance gelten, damit keine globalen Regeln versehentlich weggefiltert werden.
  - Idee: Später optionale Arbeitsmodi wie Architektur, Frontend, Data Generation oder AI-Kontext-Maintenance definieren, um relevante Kontextdateien und Checks gezielter zu priorisieren.
  - Leitplanke: Arbeitsmodi dürfen globale Source-of-Truth-, Write-Strategy-, Dokumentations-, TODO- und Post-Commit-Regeln nicht deaktivieren.

- [ ] Aussagekräftigere Summary-Kacheln für League Activity prüfen.
  - Kontext: Die aktuellen Kacheln für Drafts und Picks sind nur bedingt aussagekräftig, weil weit entfernte Future-Drafts und generische Pick-Anzahlen wenig Mehrwert liefern.
  - Ziel: Summary-Kacheln sollen später stärker auf echte Aktivität, Relevanz und nächste Entscheidungen fokussieren.
  - Potenzielle Kacheln: `Traded Picks`, `Next Draft`, `Most Active Team`, `Round 1 Moves`, `Upcoming`, `Moves`.
  - Hinweis: Sinnvoll vor allem, sobald `Transactions.json` im Frontend modelliert ist und Moves/Trades als explizite Daten verfügbar sind.

- [ ] League Activity optisch mit Sleeper-Screenshots und eigener Zielvorstellung weiter verfeinern.
  - Kontext: Der MVP zeigt Draft-Cards, Round Panels, Picks und einen Moves-Platzhalter.
  - Ziel: Nach Abgleich mit Sleeper-Drafts/Trades und der gewünschten eigenen Darstellung UI/UX gezielt verbessern.

## Erledigt / Archiv

- [x] League Activity MVP für Drafts & Moves im Frontend anlegen.
  - Kontext: Der bisher deaktivierte Navigationseintrag `Drafts & Moves` sollte aktiviert werden, aber die technische Struktur sollte einen stabileren Namen bekommen.
  - Ergebnis: Route `/league-activity`, `LeagueActivityComponent` und Navigationseintrag wurden angelegt. Der MVP zeigt current/upcoming/live Drafts aus `Drafts.json` als Draft-Cards mit Runden und Pick-Zeilen; Moves bleibt Platzhalter bis `Transactions.json` im Frontend modelliert ist.

- [x] Completed-Draft-Historie separat von `Drafts.json` aufbauen.
  - Kontext: Abgeschlossene Drafts sollen nicht in `public/data/Drafts.json` gemischt werden, damit alte Picks nicht als aktuelle Team-Assets erscheinen.
  - Ergebnis: `DraftHistoryUtils.psm1` erzeugt historische Draft-Dateien unter `public/data/past_seasons/Drafts/Drafts_<season>.json`; der bestehende wöchentliche/manuelle `RequestDrafts.ps1`-Flow aktualisiert Current-Drafts und Completed-History zusammen.

- [x] `CHAT_START.md` als Projektquelle und im Repository-Root hinterlegen.
  - Kontext: Die Datei liegt sowohl hier im ChatGPT-Projekt als Quelle als auch im Repository-Root.
  - Ziel: Neue Chats sollen zuerst auf `AGENTS.md` und danach auf die `.ai-context`-Lesereihenfolge verweisen.

Erledigte Einträge hier nur ablegen, wenn die Historie nützlich ist. Ansonsten können erledigte Einträge aus der offenen Liste entfernt werden.
