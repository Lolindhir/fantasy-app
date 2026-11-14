# So funktionieren unsere Prognosen

Unsere App berechnet für Spieler und Fantasy-Matchups **eigene Vorhersagen**. Sie helfen bei Entscheidungen, können den tatsächlichen Spielverlauf aber nicht vorhersagen.

## 🏈 Woher kommen die erwarteten Spielerpunkte?

Wir betrachten die bisherigen **Fantasy-Punkte**, die Leistungen der laufenden Saison und die Entwicklung der Rolle eines Spielers: Wie viel Einsatzzeit (Snaps) erhält er? Wie viele Gelegenheiten für Punkte bekommt er? Grundlage ist immer **unser Liga-Scoring**.

Zunächst ergibt sich eine Erwartung aus vergangenen Auftritten. Veränderungen bei Einsatzzeit und Gelegenheiten können sie erhöhen oder senken. Dabei zählt eine Entwicklung im Vergleich zur bisherigen Rolle, nicht bloß ein einzelner guter oder schlechter Spielzug.

**Beispiel:** Ein Receiver spielt zuletzt deutlich häufiger und bekommt mehr Targets. Das kann seine Punkteprognose erhöhen.

## 📏 Was bedeutet die Punktespanne?

Eine Prognose von **16,8 Punkten** ist eine erwartete Punktzahl, kein festes Ergebnis. Eine beispielhafte Spanne von **8,4 bis 29,7 Punkten** zeigt, wie stark die tatsächliche Leistung davon abweichen könnte.

- Standardmäßig zeigen wir eine **90-%-Spanne**. Vereinfacht soll sie bei vergleichbaren Prognosen über viele Spiele ungefähr neun von zehn Ergebnisse abdecken.
- Die Grenzen entstehen aus **historischen Prognosefehlern**, abhängig unter anderem von Position, erwarteten Punkten und den bisherigen Schwankungen des Spielers.
- Die Spanne kann auf einer Seite breiter sein als auf der anderen.
- Sie ist **weder eine garantierte Untergrenze noch eine Obergrenze**.

Je breiter sie ist, desto unsicherer ist die Prognose.

## 👥 Wie entsteht die Teamprognose?

Sie basiert auf den **aufgestellten Startern**:

- Vor dem Spiel werden ihre erwarteten Punkte zusammengezählt.
- Starter mit einer Bye-Week und ausdrücklich als OUT eingeordnete noch nicht gestartete Spieler zählen für die aktuelle Teamprognose mit null.
- Sobald das NFL-Spiel eines Starters **abgeschlossen** ist, zählen seine echten Fantasy-Punkte.
- Für noch ausstehende und laufende Spiele nutzen wir weiter die Vorhersage; eine eigene Live-Restpunkte-Prognose gibt es nicht.
- Wenn wesentliche Daten fehlen, zeigen wir keine scheinbar vollständige Zahl.

Die Teamspanne wird aus den Unsicherheiten der Starter berechnet. Wir addieren **nicht einfach** alle unteren oder oberen Spielergrenzen.

## 🏆 Woher kommt die Siegchance?

Unsere App vergleicht die **erwarteten Endpunkte beider Teams** und die Unsicherheit ihrer Ergebnisse.

**Beispiel:** **64 % zu 36 %** bedeutet, dass unser Modell das erste Team häufiger vorne sieht. Ein Sieg ist damit nicht sicher. Die beiden angezeigten Chancen ergeben 100 %.

Nach jedem abgeschlossenen NFL-Spiel eines Starters kann sich die Siegchance ändern, weil dessen echte Punkte in den Vergleich einfließen. Eine fehlende Prognose wird nicht automatisch als 50:50 ausgegeben.

## ⚠️ Was unsere Vorhersagen nicht berücksichtigen

- **Verletzungs- und Ausfallrisiko:** Eine individuelle Spielerprognose gilt grundsätzlich **unter der Annahme, dass der Spieler teilnimmt**. Das Modell schätzt nicht automatisch die Wahrscheinlichkeit, dass er ausfällt. Die Teamprognose kann einen bekannten OUT-Status berücksichtigen.
- **Wenig Historie:** Bei neuen oder selten eingesetzten Spielern fehlt manchmal eine Prognose oder die Spanne ist weniger individuell.
- **Noch unfertige Aufstellungen:** Offene Plätze, Bye- oder OUT-Starter können ein Team vorübergehend schwächer aussehen lassen, als es nach einer Aufstellungsänderung wäre.
- **Spielverlauf:** Touchdowns, kurzfristige Rollenwechsel und andere Überraschungen bleiben unsicher.

**Merksatz:** Die Punktzahl ist unsere beste Schätzung, die Spanne zeigt die Unsicherheit und die Siegchance vergleicht beide Teams. Keiner dieser Werte ist ein Versprechen.
