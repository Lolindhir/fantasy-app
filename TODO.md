# TODO

Menschenlesbare Projekt-Todo-Liste für `Lolindhir/fantasy-app`.

Diese Datei ist bewusst von `.ai-context` getrennt.

- `.ai-context` dokumentiert dauerhafte Architektur-, Domain- und Source-of-Truth-Entscheidungen.
- `TODO.md` sammelt offene Umsetzungs-, Aufräum- und Dokumentationsaufgaben.
- Todos werden hier auf Deutsch gepflegt, damit sie einfach per Hand angepasst werden können.
- Erledigte Einträge können entfernt oder unten im Archiv abgelegt werden.

## Offen

### Data Generation / Drafts

- [ ] Draft-Live- und Completed-Enrichment ergänzen.
  - Kontext: Wenn ein Sleeper-Draft läuft oder abgeschlossen ist, sollen die echten Pick-Ergebnisse über `Get-SleeperDraftPicks` geladen und auf die bestehenden Draft-Picks gemappt werden.
  - Ziel: Pro Pick `PlayerID`, `PlayerName`, `SleeperPickNo`, `SleeperPickedBy` und `Status = Picked` ergänzen, ohne den stabilen `PickKey` zu verändern.
  - Möglicher Ansatz: Funktion `Apply-SleeperDraftPickResults` ergänzen.

### Frontend

- [ ] `DataService` strukturell aufteilen und Angular-Struktur prüfen.
  - Kontext: `src/app/services/data-service.ts` enthält aktuell Models, HTTP-Laden, Mapping, Draft-Enrichment, Free-Agent-Marktlogik, Salary-Helfer und Trade-Helfer in einer Datei.
  - Ziel: Modelle und app-weite Services perspektivisch in klarere Bereiche auslagern, z. B. `src/core/models`, `src/core/services` und `src/shared`.
  - Optional: Import-Aliases wie `@core/*`, `@shared/*` und `@app/*` prüfen.

- [ ] Draft-Round-Chip-Farblogik aus `src/app/overview/overview.ts` in eine gemeinsame Frontend-Utility, Pipe oder einen Service auslagern.
  - Kontext: Die Overview berechnet die Farben aktuell lokal.
  - Ziel: Alle Komponenten, die Draft Picks anzeigen, verwenden dieselbe Rundenskala.

- [ ] Prüfen, ob die Inline-Styles der Draft-Pick-Chips aus dem Overview-Template nach `overview.scss` verschoben werden sollen.
  - Kontext: Die Darstellung funktioniert, aber ein Teil des Stylings liegt aktuell inline im Template.
  - Ziel: Template sauberer halten und Styling zentralisieren.

### Dokumentation / AI-Kontext

- [ ] Leichten Validierungscheck oder CI-Check ergänzen, der parallele AI-Kontext-Doku unter `docs/ai-context/**` verhindert.
  - Kontext: AI-Kontext-Dokumentation soll ausschließlich unter `.ai-context` liegen.
  - Ziel: Doppelte oder auseinanderlaufende Dokumentation vermeiden.

### Später / Ideen

- [ ] Prüfen, ob Draft-Pick-Anzeigen als wiederverwendbare UI-Komponente umgesetzt werden sollen.
  - Kontext: Draft Picks werden vermutlich später auch außerhalb der Overview angezeigt.
  - Ziel: Doppelte Anzeige- und Formatierungslogik vermeiden.

## Erledigt / Archiv

- [x] `CHAT_START.md` als Projektquelle und im Repository-Root hinterlegen.
  - Kontext: Die Datei liegt sowohl hier im ChatGPT-Projekt als Quelle als auch im Repository-Root.
  - Ziel: Neue Chats sollen zuerst auf `AGENTS.md` und danach auf die `.ai-context`-Lesereihenfolge verweisen.

Erledigte Einträge hier nur ablegen, wenn die Historie nützlich ist. Ansonsten können erledigte Einträge aus der offenen Liste entfernt werden.
