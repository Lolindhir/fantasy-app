# TODO

Menschenlesbare Projekt-Todo-Liste für `Lolindhir/fantasy-app`.

Diese Datei ist bewusst von `.ai-context` getrennt.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- `TODO.md` sammelt offene Umsetzungs-, Aufräum- und Dokumentationsaufgaben.
- Todos werden hier auf Deutsch gepflegt, damit sie einfach per Hand angepasst werden können.
- Erledigte Einträge können entfernt oder unten im Archiv abgelegt werden.

## Offen

### Data Generation / Infrastruktur

- [ ] Zugangsdaten-Konfiguration aus `ConfigUtils.psm1` in Umgebungsvariablen bzw. Workflow-Konfiguration auslagern.
  - Kontext: `ConfigUtils.psm1` enthält aktuell technische Pfade und Request-Konfiguration, aber auch sensible Zugangswerte.
  - Ziel: Sensible Werte nicht im Repository versionieren; `Get-Config` soll sie bevorzugt aus der Laufzeitumgebung lesen und nur noch nicht-sensitive technische Defaults enthalten.

- [ ] `PastSeasonsIndex.json`-Aktualisierung nur auf relevante Pfad-/Existenzänderungen prüfen.
  - Kontext: Der Index aktualisiert aktuell auch bei geänderten `ContentHash`-Werten historischer Ressourcen, obwohl sich die sichtbaren Pfade nicht ändern.
  - Ziel: Prüfen, ob für die Angular-Navigation ein Vergleich auf relevante Pfade und `Exists` ausreicht, während Hash-/UpdatedAt-Metadaten optional bleiben oder anders behandelt werden.
  - Hinweis: Nur ändern, wenn dadurch keine nützliche Freshness-/Debug-Information verloren geht.

### Data Generation / Drafts

- [ ] Draft-Live-Enrichment für `public/data/Drafts.json` ergänzen.
  - Kontext: Die abgeschlossene Draft-Historie wird separat gespeichert, aber im wöchentlichen/manuellen `RequestDrafts.ps1`-Flow zusammen mit den aktuellen Drafts aktualisiert. Für laufende Drafts im aktuellen `Drafts.json` fehlt das Ergebnis-Enrichment aber noch.
  - Ziel: Wenn ein aktueller Sleeper-Draft läuft, sollen echte Pick-Ergebnisse über `Get-SleeperDraftPicks` geladen und auf die bestehenden Draft-Picks gemappt werden.
  - Ziel: Pro Pick `PlayerID`, `PlayerName`, `SleeperPickNo`, `SleeperPickedBy` und `Status = Picked` ergänzen, ohne den stabilen `PickKey` zu verändern.
  - Möglicher Ansatz: Die Logik aus `Get-AppliedDraftPickResults` wiederverwendbar machen oder in `DraftUtils.psm1` übernehmen.

### Frontend

- [ ] `Transactions.json` im Frontend modellieren und für Moves anbinden.
  - Kontext: `src/app/features/league-activity/league-activity.ts` ist aktuell die technische Moves-Komponente und bleibt Platzhalter, weil `Transactions.json` noch nicht im `DataService` geladen wird.
  - Ziel: Transaction-Interfaces ergänzen und `DataService` so erweitern, dass Trades, Adds, Drops und weitere Roster Moves als expliziter Frontend-Vertrag verfügbar sind.
  - Ziel: Moves später als chronologische Activity-Timeline darstellen.
  - Hinweis: Keine Pending-Transaction-Datei erzeugen, solange keine zuverlässige Pending-Quelle existiert.

- [ ] Draft-Pick-Anzeige als wiederverwendbare UI-Komponente prüfen und ggf. auslagern.
  - Kontext: Draft Picks werden inzwischen in `src/app/features/overview/overview.ts` und im Drafts-Feature unter `src/app/features/drafts/**` angezeigt.
  - Ziel: Gemeinsame Darstellung für Pick-Token, Current Owner und `from Original Owner` vermeiden doppelte Template-/ViewModel-Logik.
  - Mögliche Zielstruktur: `src/app/shared/components/draft-pick-chip` oder ein ähnlicher Shared-UI-Baustein.

- [ ] Current-Draft-Pick-Popover und Player-Mini-Card als gemeinsame UI-Komponente prüfen.
  - Kontext: `CurrentDraftPickChipComponent` und `CurrentDraftOverviewViewComponent` enthalten sehr ähnliche Popover-Inhalte für Pick, Overall, Player, Owner, Original Owner und Traded Pick.
  - Ziel: Popover-Content und Player-Mini-Card wiederverwenden, ohne die unterschiedlichen Trigger (`PickChip` vs. Overview-Kachel) zu koppeln.

- [ ] Draft-Card-Header und Metrikzeile zwischen Current und Future vereinheitlichen.
  - Kontext: Current Drafts nutzen `DraftShellComponent`, Future Drafts rendern `mat-card` inklusive Header und Metrikzeile direkt in `future-drafts-tab.html`.
  - Kontext: Beide zeigen inzwischen `Rounds · Typ · Traded Picks` auf Basis von `draftVm.draft.Settings.Type`.
  - Ziel: Header-/Metrik-Logik entweder vollständig über `DraftShellComponent` oder über ein gemeinsames Draft-Card-Metrics-ViewModel abbilden.

- [ ] Current-Draft-Team- und Listen-Gruppierungen ins zentrale Drafts-ViewModel ziehen.
  - Kontext: Die Current-Draft-Teams- und Listen-Sichten leiten ihre Pick-Gruppierungen und Sortierungen im ersten Wurf komponentennah aus `draftVm.rounds` ab.
  - Ziel: `orderedPicks` und eine Current-spezifische Owner-Pick-Gruppierung in `drafts-view.models.ts` und `drafts-view-model.mapper.ts` zentralisieren.
  - Hinweis: Die Source of Truth bleibt `public/data/Drafts.json`; es geht nur um ein stabileres Angular-ViewModel für die Darstellung.

- [ ] Draft-Round-Chip-Farblogik aus Overview und Drafts in eine gemeinsame Frontend-Utility, Pipe oder einen Service auslagern.
  - Kontext: Overview und Drafts berechnen die Farben aktuell lokal mit derselben warm-zu-kalt HSL-Skala.
  - Ziel: Alle Komponenten, die Draft Picks anzeigen, verwenden dieselbe Rundenskala.

- [ ] Alternative Sortierung für kompakte Future-Drafts in Drafts prüfen.
  - Kontext: Future-Drafts werden aktuell nach Pick Strength sortiert: zuerst Anzahl Picks in Runde 1, dann Runde 2, dann Runde 3 usw. bis zur flexiblen Draft-Rundenzahl.
  - Alternative: Optional eine Sortierung nach den Draft-Order-Regeln anbieten, z. B. Free-Agent-Drafts nach All-Time-Standings und Rookie-Drafts nach Saison-/Vorjahresplatzierung, sobald eine verlässliche Reihenfolge verfügbar ist.
  - Ziel: Falls die Pick-Strength-Sortierung nicht intuitiv genug ist, später einen klar beschrifteten Sortiermodus oder Toggle prüfen.

- [ ] `DataService` als schmale App-Datenfassade überprüfen und bei Bedarf weiter stabilisieren.
  - Kontext: `src/app/core/services/data.service.ts` ist aktuell vor allem öffentliche App-Datenfassade und Orchestrator.
  - Kontext: Die alte Location `src/app/services/data-service.ts` wurde entfernt; Consumer importieren `DataService` aus `src/app/core/services/data.service.ts`.
  - Kontext: Die Zielstruktur `src/app/core`, `src/app/shared` und `src/app/features` ist umgesetzt; geroutete Feature-Seiten liegen unter `src/app/features/**`, wiederverwendbare UI-Komponenten unter `src/app/shared/components/**`.
  - Kontext: `src/app/core/models/fantasy.models.ts` ist der zentrale Model-Importpfad. Feature- und Shared-Komponenten importieren ihre reinen Model-/Type-Abhängigkeiten von dort statt direkt aus `data.service.ts`.
  - Kontext: Draft-Modelle liegen in `src/app/core/models/draft.models.ts`, League-/Standing-/FantasyTeam-Modelle in `src/app/core/models/league.models.ts`, Player-/NFLTeam-/Stats-/FreeAgentMarket-Modelle in `src/app/core/models/player.models.ts`.
  - Kontext: `src/app/core/services/data-api.service.ts` enthält das HTTP-Laden der generierten JSON-Dateien und Timestamps.
  - Kontext: `src/app/core/mappers/league.mapper.ts` enthält die reine `RawLeague`-/`RawFantasyTeam`-/DraftPick-zu-`League`/`FantasyTeam`-Transformation inklusive Team-Roster-Zuweisung.
  - Kontext: `src/app/core/mappers/player.mapper.ts` enthält die reine `RawPlayer`-zu-`Player`-Transformation inklusive Stats-, Injury-, SalaryDisplay- und GameHistory-Mapping.
  - Kontext: `src/app/core/services/free-agent-market.service.ts` enthält die FreeAgentMarket-/RuleBasedAutoCut-Logik für Current- und Projected-Salary-Modi.
  - Kontext: `src/app/shared/utils/player-sort.util.ts` enthält die wiederverwendbare Player-Sortierung.
  - Kontext: `src/app/shared/utils/trade-calculator.util.ts` enthält wiederverwendbare Salary- und Trade-Roster-Berechnungen.
  - Ziel: Prüfen, ob Consumer künftig direkt die Shared Utils nutzen sollen, damit die Kompatibilitäts-Delegates in `DataService` entfallen können.
  - Ziel: Prüfen, ob `DataService` dauerhaft als App-Datenfassade benannt bleibt oder später klarer als `FantasyDataService`/`DataFacade` bezeichnet werden soll.
  - Optional: Import-Aliases wie `@core/*`, `@shared/*` und `@app/*` prüfen.

- [ ] Unbenutzte Hilfslogik im Drafts-Feature bereinigen.
  - Kontext: `CurrentDraftPickChipComponent.statusLabel` wird aktuell nicht im Template verwendet.
  - Ziel: Unbenutzte Getter/Hilfslogik entfernen oder bei Bedarf in eine gemeinsame Draft-Pick-Status-Utility verschieben.

- [ ] Prüfen, ob die Inline-Styles der Draft-Pick-Chips aus dem Overview-Template nach `overview.scss` verschoben werden sollen.
  - Kontext: Die Darstellung funktioniert, aber ein Teil des Stylings liegt aktuell inline im Template.
  - Ziel: Template sauberer halten und Styling zentralisieren.

### Dokumentation / AI-Kontext

- [ ] Fehlenden generierten AI-Kontext klären.
  - Kontext: `.ai-context/ai-context.yaml` verweist in der Lesereihenfolge auf `.ai-context/generated/file-docs.json` und `.ai-context/generated/generated-json-contracts.json`.
  - Kontext: Diese generierten Kontextdateien sind aktuell nicht im Repository abrufbar.
  - Ziel: Entweder die generierten Dateien über den vorgesehenen Generator erzeugen und committen oder die Lesereihenfolge/Guidance so anpassen, dass fehlende Generated-Kontextdateien ausdrücklich optional sind.
  - Hinweis: Dateien unter `.ai-context/generated` dürfen nicht manuell gepflegt werden.

- [ ] Leichten Validierungscheck oder CI-Check ergänzen, der parallele AI-Kontext-Doku unter `docs/ai-context/**` verhindert.
  - Kontext: AI-Kontext-Dokumentation soll ausschließlich unter `.ai-context` liegen.
  - Ziel: Doppelte oder auseinanderlaufende Dokumentation vermeiden.

### Später / Ideen

- [ ] Rollenbasierte AI-Arbeitsmodi für fokussierte Chats prüfen.
  - Kontext: Aktuell soll ohne expliziten Rollenmodus weiterhin die vollständige Projekt-Guidance gelten, damit keine globalen Regeln versehentlich weggefiltert werden.
  - Idee: Später optionale Arbeitsmodi wie Architektur, Frontend, Data Generation oder AI-Kontext-Maintenance definieren, um relevante Kontextdateien und Checks gezielter zu priorisieren.
  - Leitplanke: Arbeitsmodi dürfen globale Source-of-Truth-, Write-Strategy-, Dokumentations-, TODO- und Post-Commit-Regeln nicht deaktivieren.

- [ ] Aussagekräftigere Summary-Kacheln für Moves prüfen.
  - Kontext: Die aktuelle Moves-Seite ist nur ein Platzhalter, weil `Transactions.json` noch nicht im Frontend modelliert ist.
  - Ziel: Summary-Kacheln sollen später stärker auf echte Aktivität, Relevanz und nächste Entscheidungen fokussieren.
  - Potenzielle Kacheln: `Traded Picks`, `Next Draft`, `Most Active Team`, `Round 1 Moves`, `Upcoming`, `Moves`.
  - Hinweis: Sinnvoll vor allem, sobald `Transactions.json` im Frontend modelliert ist und Moves/Trades als explizite Daten verfügbar sind.

- [ ] Moves optisch mit Sleeper-Screenshots und eigener Zielvorstellung weiter verfeinern.
  - Kontext: Die Moves-Seite ist aktuell ein Platzhalter.
  - Ziel: Nach Abgleich mit Sleeper-Drafts/Trades und der gewünschten eigenen Darstellung UI/UX gezielt verbessern.

- [ ] Trade Simulator später in Moves integrieren.
  - Kontext: `src/app/features/trade/trade-simulator/trade-simulator.ts` bleibt vorerst eine eigene Route unter `/trade`.
  - Ziel: Später prüfen, ob und wie der Trade Simulator als Tool oder Subbereich unter Moves aufgeht.

## Erledigt / Archiv

- [x] Past Drafts im Frontend auf Basis von `PastSeasonsIndex.json` ergänzen.
  - Kontext: `PastSeasonsIndex.json` macht verfügbare historische Season-Ressourcen auffindbar.
  - Ergebnis: `/drafts` hat einen dritten Reiter `Past`, lädt verfügbare Draft-Seasons aus `PastSeasonsIndex.json`, bietet eine Season-Auswahl und rendert historische Draft-Cards analog zu Current Drafts mit Overview, Teams und List.
  - Hinweis: Historische Draft-Dateien bleiben getrennt von `Drafts.json` und werden nicht als aktuelle Team-Assets interpretiert.

- [x] Drafts und Moves als getrennte Routen vorbereiten.
  - Kontext: Der gemeinsame Bereich `/league-activity` wurde durch getrennte sichtbare Feature-Routen ersetzt.
  - Ergebnis: Drafts liegen als eigene Route `/drafts` unter `src/app/features/drafts`; Moves nutzt weiterhin `LeagueActivityComponent` als technische Platzhalter-Komponente unter `/moves`; `/league-activity` leitet auf `/moves` weiter.
  - Validierung: Tests nach Merge erfolgreich.

- [x] `Players_Relevant.json`- und Chat-Export-Pfade nach `ConfigUtils.psm1` verlagern.
  - Kontext: `RequestLeague.ps1` baute den relevanten Spielerpfad und den Chat-Chunk-Zielordner ursprünglich lokal über `$config.DataDir`.
  - Ergebnis: `Get-Config` stellt `PlayersRelevantFile` und `PlayersRelevantChatDir` bereit; `RequestLeague.ps1` nutzt diese Config-Werte für `Players_Relevant.json` und den Chat-Export unter `public/data/chat/players-relevant`.

- [x] Legacy-Kompatibilitäts-Re-Exports entfernen.
  - Kontext: Nach dem Angular-Struktur-Refactor lagen die gerouteten Feature-Seiten unter `src/app/features/**`; alte Pfade waren temporär als Re-Export-Wrapper erhalten.
  - Ergebnis: Die alten Wrapper-Dateien `src/app/overview/overview.ts`, `src/app/team-list/team-list.ts`, `src/app/players-page/players-page.ts`, `src/app/trade-simulator/trade-simulator.ts`, `src/app/league-activity/league-activity.ts`, `src/app/about/about.ts`, `src/app/player-list/player-list.ts` und `src/app/player-detail-dialog/player-detail-dialog.ts` wurden nach Build-/Testbestätigung und Repo-Suche ohne produktive Referenzen entfernt.

- [x] Alte Komponenten-Specs aus den früheren Root-Locations entfernen.
  - Kontext: Nach dem Angular-Struktur-Refactor lagen noch alte `.spec.ts`-Dateien in früheren Root-Locations und importierten lokale Wrapper, die nicht mehr produktiv genutzt wurden.
  - Ergebnis: Alte Specs für Team List, About, Overview, Players Page, Trade Simulator, Player List und Player Detail Dialog wurden entfernt.

- [x] Angular-Feature-Struktur vorbereiten und geroutete Seiten verschieben.
  - Kontext: Geroutete Angular-Seiten sollten von wiederverwendbaren UI-Komponenten getrennt werden.
  - Ergebnis: Routen zeigen auf `src/app/features/**`; `PlayerList` und `PlayerDetailDialog` liegen unter `src/app/shared/components/**`; alte Compatibility-Re-Export-Wrapper wurden nach erfolgreicher Stabilisierung entfernt.
  - Validierung: Build-Workflow und manueller UI-Durchklick waren erfolgreich.

- [x] League Activity MVP für Drafts & Moves im Frontend anlegen.
  - Kontext: Der bisher deaktivierte Navigationseintrag `Drafts & Moves` sollte aktiviert werden, aber die technische Struktur sollte einen stabileren Namen bekommen.
  - Ergebnis: Route `/league-activity`, `LeagueActivityComponent` und Navigationseintrag wurden angelegt. Der MVP zeigte current/upcoming/live Drafts aus `Drafts.json` als Draft-Cards mit Runden und Pick-Zeilen; Moves blieb Platzhalter bis `Transactions.json` im Frontend modelliert ist.
  - Hinweis: Diese Architektur wurde später durch getrennte `/drafts`- und `/moves`-Routen abgelöst.

- [x] Completed-Draft-Historie separat von `Drafts.json` aufbauen.
  - Kontext: `Drafts.json` bleibt auf aktuelle/kommende/live Drafts beschränkt, damit alte Picks nicht als aktuelle Team-Assets erscheinen.
  - Ergebnis: `DraftHistoryUtils.psm1` erzeugt historische Draft-Dateien unter `public/data/past_seasons/Drafts/Drafts_<season>.json`; der bestehende wöchentliche/manuelle `RequestDrafts.ps1`-Flow aktualisiert Current-Drafts und Completed-History zusammen.

- [x] `CHAT_START.md` als Projektquelle und im Repository-Root hinterlegen.
  - Kontext: Die Datei liegt sowohl hier im ChatGPT-Projekt als Quelle als auch im Repository-Root.
  - Ziel: Neue Chats sollen zuerst auf `AGENTS.md` und danach auf die `.ai-context`-Lesereihenfolge verweisen.

Erledigte Einträge hier nur ablegen, wenn die Historie nützlich ist. Ansonsten können erledigte Einträge aus der offenen Liste entfernt werden.
