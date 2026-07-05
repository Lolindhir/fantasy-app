# TODO

Menschenlesbare Projekt-Todo-Liste für `Lolindhir/fantasy-app`.

Diese Datei ist bewusst von `.ai-context` getrennt.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- `TODO.md` sammelt offene Umsetzungs-, Aufräum- und Dokumentationsaufgaben.
- Todos werden hier auf Deutsch gepflegt, damit sie einfach per Hand angepasst werden können.
- Erledigte Einträge können entfernt oder unten im Archiv abgelegt werden.

## Offen

### Data Generation / Infrastruktur

- [ ] Laufzeit-Konfiguration aus `ConfigUtils.psm1` in Umgebungsvariablen bzw. Workflow-Konfiguration auslagern.
  - Kontext: `ConfigUtils.psm1` enthält aktuell technische Pfade und Request-Konfiguration sowie laufzeitabhängige Werte.
  - Ziel: Laufzeitabhängige Werte nicht direkt im Repository pflegen; `Get-Config` soll sie bevorzugt aus der Laufzeitumgebung lesen und nur noch technische Defaults enthalten.

- [ ] `CapDeadlineBufferDays` sauber über `ConfigUtils.psm1` bereitstellen.
  - Kontext: `CapDeadlineBufferDays` liegt als liga-spezifische Regel in `Metadata.json`, wird aber aktuell in `RequestLeague.ps1` direkt aus `Metadata.json` gelesen.
  - Grund: `ConfigUtils.psm1` enthält derzeit noch laufzeitabhängige Werte und konnte deshalb nicht gefahrlos vollständig ersetzt werden.
  - Ziel: Nach Auslagerung der Laufzeitwerte soll `Get-Config` den Wert aus `Metadata.json` laden und als Teil der Generator-Konfiguration bereitstellen.

- [ ] `PastSeasonsIndex.json`-Aktualisierung nur auf relevante Pfad-/Existenzänderungen prüfen.
  - Kontext: Der Index aktualisiert aktuell auch bei geänderten `ContentHash`-Werten historischer Ressourcen, obwohl sich die sichtbaren Pfade nicht ändern.
  - Ziel: Prüfen, ob für die Angular-Navigation ein Vergleich auf relevante Pfade und `Exists` ausreicht, während Hash-/UpdatedAt-Metadaten optional bleiben oder anders behandelt werden.
  - Hinweis: Nur ändern, wenn dadurch keine nützliche Freshness-/Debug-Information verloren geht.

- [ ] Backup-Daten aus `public/data/backup` herausziehen und versioniert im Repo behalten.
  - Kontext: `public` soll nur Dateien enthalten, die die Angular-App zur Laufzeit ausliefert oder lädt.
  - Kontext: Backups werden aktuell über `ConfigUtils.psm1` unter `public/data/backup` erzeugt und vom Cleanup-Workflow `.github/workflows/clean-backups.yml` bereinigt.
  - Ziel: Backups in einen sichtbaren Repo-Root-Ordner wie `data-backup/` verschieben, weiterhin versionieren und für manuelle Nutzung verfügbar halten.
  - Mit anpassen: `ConfigUtils.psm1`, `.github/workflows/clean-backups.yml`, betroffene Update-Workflows mit `git add public/data/** data-backup/**` und ggf. Deploy-Absicherung.

### Data Generation / Drafts

- [ ] Draft-Live-Enrichment für `public/data/Drafts.json` bei nächstem laufenden Sleeper-Draft validieren.
  - Kontext: Die technische Live-Enrichment-Logik für aktuelle Drafts ist implementiert; ein echter laufender Sleeper-Draft wurde damit aber noch nicht praktisch geprüft.
  - Ziel: Bei einem laufenden Sleeper-Draft kontrollieren, ob `Drafts.json` echte Pick-Ergebnisse korrekt setzt.
  - Zu prüfen: `Status = Picked`, `PlayerID`, `PlayerName`, `SleeperPickNo`, `SleeperPickedBy`, stabile `PickKey` und korrekte Frontend-Darstellung.

### Data Generation / League Status

- [ ] Sleeper-Feld für `CutsAllowed` bzw. Move-/Cut-Sperre prüfen.
  - Kontext: `CutsAllowed` wird aktuell wie bisher grundsätzlich auf `true` gesetzt und nur bei `Completed` geschlossen.
  - Ziel: Herausfinden, ob Sleeper ein verlässliches Feld für Cut-/Roster-Move-Sperren liefert und dieses datengetrieben anbinden.
  - Hinweis: `CutsAllowed` darf nicht aus `League.Phase` abgeleitet werden; insbesondere `Cap Check` ist nur ein Prozessstatus, keine eigenständige Cut-Source-of-Truth.

### Data Generation / League History

- [ ] Hall-of-Fame-/Legacy-Auswertungen generatorseitig modellieren.
  - Kontext: Die Standings-Route erzeugt Hall-of-Fame-Highlights, Award-Legende, All-Time-Regular-Season und Season-Archive aktuell bewusst als Frontend-Prototyp in `league-standings-view.util.ts`.
  - Entscheidung: Season-Awards bleiben dauerhaft Teil von `Standings.json`; es soll kein eigenständiges `Awards.json` für diesen Contract entstehen.
  - Ziel: Nach Stabilisierung der UI und Datenform prüfen, welche Legacy-/History-Readmodels generatorseitig aus `Standings.json` abgeleitet und ggf. als eigener Legacy-/History-Contract bereitgestellt werden sollen.
  - Kandidaten: Legacy-Highlights (`Champ of Champs`, `Regular Season King`, `Podium Machine`, `Award Collector`), Award-Legende, Season-History-Readmodel, All-Time-Regular-Season-Readmodel.
  - Hinweis: Angular darf diese Werte vorläufig als Frontend-ViewModel ableiten; langfristige source-of-truth-nahe Historienauswertungen sollten aber generatorseitig entstehen.

- [ ] `WinPercentageDisplay` für All-Time Regular Season generatorseitig erzeugen.
  - Kontext: All-Time-Regular-Season-Daten enthalten aktuell `WinPercentage`, aber kein `WinPercentageDisplay`.
  - Kontext: Die Frontend-Anzeige nutzt vorläufig `WinPercentageDisplay`, falls vorhanden, und formatiert sonst das vorhandene numerische `WinPercentage` als Fallback.
  - Ziel: Der Generator soll für `Placements.AllTime.Regular` dasselbe Display-Feld erzeugen wie bei anderen Regular-Season-Platzierungen, damit Angular kein Display-Fallback mehr benötigt.

### Frontend

- [ ] `Transactions.json` im Frontend modellieren und für Moves anbinden.
  - Kontext: `src/app/features/league-activity/league-activity.ts` ist aktuell die technische Moves-Komponente und bleibt Platzhalter, weil `Transactions.json` noch nicht im `DataService` geladen wird.
  - Ziel: Transaction-Interfaces ergänzen und `DataService` so erweitern, dass Trades, Adds, Drops und weitere Roster Moves als expliziter Frontend-Vertrag verfügbar sind.
  - Ziel: Moves später als chronologische Activity-Timeline darstellen.
  - Hinweis: Keine Pending-Transaction-Datei erzeugen, solange keine zuverlässige Pending-Quelle existiert.

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
  - Kontext: `src/app/shared/utils/league-standings-view.util.ts` enthält wiederverwendbare ViewModel-Logik für Current Standings, Season Results, Previous-Season-Awards und All-Time Standings.
  - Ziel: Prüfen, ob Consumer künftig direkt die Shared Utils nutzen sollen, damit die Kompatibilitäts-Delegates in `DataService` entfallen können.
  - Ziel: Prüfen, ob `DataService` dauerhaft als App-Datenfassade benannt bleibt oder später klarer als `FantasyDataService`/`DataFacade` bezeichnet werden soll.
  - Optional: Import-Aliases wie `@core/*`, `@shared/*` und `@app/*` prüfen.

- [ ] Dynamische Farbbindung der Overview-Draft-Pick-Chips prüfen.
  - Kontext: Die statischen Draft-Pick-Chip-Styles liegen inzwischen in `overview.scss`; im Template bleibt nur die dynamische Hintergrundfarbe per `[style.background-color]="pick.backgroundColor"`.
  - Ziel: Prüfen, ob diese Binding-Lösung bewusst beibehalten wird oder ob die Farbe später über CSS-Klassen bzw. CSS Custom Properties modelliert werden soll.

- [ ] Overview-Cap-/Awards-Blöcke als nächste UI-Slices prüfen.
  - Kontext: Standings, Season Results und All-Time Standings wurden aus der Overview in gemeinsame ViewModels bzw. Shared-Komponenten ausgelagert.
  - Kontext: `overview.scss` enthält weiterhin Cap-Space-, Deadline- und Regular-Season-Awards-Styles direkt in der Overview.
  - Ziel: Bei weiterem Overview-Refactor prüfen, ob Cap Space, Deadline und Awards eigene Komponenten/ViewModels bekommen sollen.

- [ ] Deadline-Anzeige im Overview allgemein statt Cap-Deadline-spezifisch modellieren.
  - Kontext: Die Overview-Header-Deadline nutzt aktuell `League.CapDeadline` und den festen Text `until Cap Deadline`.
  - Ziel: Deadline-Datum und Anzeige-Label allgemein modellieren, z. B. als `DeadlineDate`/`DeadlineLabel` oder als Liste von Deadlines, damit später auch andere League-Deadlines angezeigt werden können.
  - Hinweis: Die aktuelle Restzeitanzeige mit Tagen bzw. unter 24 Stunden mit Stunden/Minuten beibehalten.

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

- [ ] Draft-Kapital-Score und Pick-Werte für Draft-Assets prüfen.
  - Kontext: Drafts zeigen bereits Pick-Besitz und Trade-History; für Dynasty-Planung wäre zusätzlich interessant, wie wertvoll die aktuellen und zukünftigen Picks eines Teams sind.
  - Kontext: Overview Draft Capital und Drafts nutzen vorläufig eine frontendseitige Pick-Strength-Sortierung aus `src/app/shared/utils/draft-capital.util.ts`.
  - Idee: Einzelne Picks mit einem Wert versehen, z. B. abhängig von Runde, konkretem `OverallPick` bei Exact-Drafts und reduzierter Rundenschätzung bei RoundOnly-Future-Drafts.
  - Idee: Eine generierte Statistikdatei für historische Pick-Werte aufbauen, z. B. `public/data/stats/DraftPickValueStats.json`.
  - Idee: Historische Draft-Picks mit den gepickten Spielern und deren Fantasy-Punkten nach Rookie-Year, 2-Year-Window und 3-Year-Window verbinden.
  - Ziel: Daraus pro Team und Draft/Season einen Draft-Capital-Score ableiten, ohne Draft-Ownership als Source-of-Truth ins Frontend zu verlagern.
  - Ziel: Durchschnittliche Punkte pro konkretem Pick, Pick-Bucket, Runde und DraftType berechnen, damit Pick-Werte liga-spezifisch statt nur manuell geschätzt werden.
  - Ziel: Sobald generatorseitig Draft-Capital-Werte vorliegen, Overview Draft Capital und Drafts-Sortierungen auf diese Datenwerte umstellen und die frontendseitige Pick-Strength nur noch als Fallback verwenden.
  - Hinweis: Gewichtung später bewusst diskutieren, weil `1.01`, frühe Runde 1 und spätere Runden sehr unterschiedlich bewertet werden sollten.
  - Hinweis: Kleine Sample Sizes über Fallbacks abfangen, z. B. exakter Pick → Pick-Bucket → Runde → DraftType-Durchschnitt.

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

- [x] Draft-Startzeit aus Sleeper prüfen und in `Drafts.json` übernehmen.
  - Ergebnis: `Drafts.json` bekommt für aktuelle Sleeper-Drafts `SleeperStartTime` aus `start_time` und `DraftStartTimeUtc` als UTC-ISO-Wert. `League.Phase = "Pre Draft"` nutzt diese generierte Startzeit jetzt datengetrieben.

- [x] Draft-Pick-Trigger-Darstellung weiter vereinheitlichen.
  - Kontext: Current-Pick-Chip und Future-Round-Pill duplizierten Button-, traded-dot- und Popover-Trigger-Logik.
  - Ergebnis: `DraftPickTriggerComponent` kapselt die gemeinsame Trigger-Mechanik und bietet Varianten für `chip` und `round-pill`. `CurrentDraftPickChipComponent` bleibt als Wrapper für bestehende Current/Past-Views erhalten; Future-Round-Pills nutzen den Trigger direkt. Die Overview-Kachel bleibt wegen ihrer eigenständigen Card-Darstellung in `DraftPickCardComponent`.

- [x] Draft-ViewModel-Service für die Drafts-Route ergänzen.
  - Kontext: `DraftsPageComponent` sollte ViewModel-Erzeugung nicht direkt über Mapper-Funktionen orchestrieren.
  - Ergebnis: `DraftsViewModelService` kapselt die Drafts-ViewModel-Erzeugung und delegiert an die reinen Mapper.

- [x] Current-Draft-Team- und Listen-Gruppierungen ins zentrale Drafts-ViewModel ziehen.
  - Kontext: Teams- und Listen-Sichten leiteten Gruppierungen und Sortierungen zunächst komponentennah aus `draftVm.rounds` ab.
  - Ergebnis: `DraftViewModel` enthält `orderedPicks` und `currentOwnerPickGroups`; die Komponenten rendern diese Felder direkt.

- [x] Draft-Pick-Overview-Kachel als wiederverwendbare UI-Komponente extrahieren.
  - Kontext: Die Overview-Kachel enthielt Markup, Position-Farben, Popover-Trigger und ein nachträgliches DOM-Rendering des Kontextlabels direkt in der Overview-View.
  - Ergebnis: `DraftPickCardComponent` kapselt die Overview-Pick-Kachel inklusive Popover-Trigger und Kontextlabel; die Overview-View rendert nur noch das Board-Grid.

- [x] Draft-Round-Chip-Farblogik aus Overview und Drafts in eine gemeinsame Frontend-Utility auslagern.
  - Kontext: Overview und Drafts berechneten Draft-Round-Farben lokal und leicht unterschiedlich.
  - Ergebnis: `getDraftRoundColor` und `getDraftStatusClass` liegen in `src/app/shared/utils/draft-ui.util.ts`; Overview und Drafts verwenden dieselbe Rundenskala.

- [x] Gemeinsames Draft-Pick-Popover neutral benennen und verschieben.
  - Kontext: Das frühere `CurrentDraftPickPopoverComponent` wurde von Current/Past Drafts und Future Drafts genutzt, lag aber technisch unter dem Current-Drafts-Pfad.
  - Ergebnis: `DraftPickPopoverComponent` liegt unter `src/app/features/drafts/components/draft-pick-popover/**` und wird von Current/Past/Future-Draft-Triggern verwendet.

- [x] Draft-Card-Header und Metrikzeile zwischen Current/Past und Future vereinheitlichen.
  - Kontext: Current/Past Drafts nutzten `DraftShellComponent`, Future Drafts renderten `mat-card` inklusive Header und Metrikzeile direkt.
  - Ergebnis: Future Drafts rendern jetzt ebenfalls `DraftShellComponent`; Header und Metrikzeile kommen zentral aus der Shell.

- [x] Current-Draft-Pick-Popover und Player-Mini-Card als gemeinsame UI-Komponente prüfen.
  - Kontext: `CurrentDraftPickChipComponent`, `CurrentDraftOverviewViewComponent` und Future-Draft-Round-Pills nutzten ähnliche Popover-Inhalte für Pick, Overall, Player, Owner, Original Owner und Traded Pick.
  - Ergebnis: Der gemeinsame Popover-Content liegt inzwischen in `DraftPickPopoverComponent` und unterstützt vollständige Current/Past-Picks sowie kompakte Future-Picks. Die kompakte Trigger-Mechanik wurde später zusätzlich in `DraftPickTriggerComponent` zentralisiert.

- [x] Unbenutzte Hilfslogik im Drafts-Feature bereinigen.
  - Kontext: `CurrentDraftPickComponent.statusLabel` wurde nicht im Template verwendet.
  - Ergebnis: Der ungenutzte Getter wurde beim Umstellen auf das gemeinsame Draft-Pick-Popover entfernt.

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
