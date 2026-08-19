# Taxi Pre-Lock Clarification – 2026-08-19

Status: Korrektur/Ergänzung zur datierten Roster-Baseline `2026-08-19-roster-role-security-baseline.md`.

Diese Datei ändert keine historischen League-Daten. Sie korrigiert die Interpretation der aktuellen Taxi-Belegung auf Basis der vom Nutzer bestätigten Liga-Mechanik.

## Bestätigte Taxi-Mechanik

- Bis zum ersten Ligaspiel können die zwei Taxi-Slots noch frei zwischen allen aktuellen Rookies neu vergeben werden.
- Ein Rookie kann in dieser Phase zwischen regulärem Roster/Bank und Taxi verschoben werden.
- Vor dem ersten Ligaspiel muss die finale Taxi-Belegung festgelegt werden.
- Mit Beginn des ersten Ligaspiels werden die beiden Taxi-Slots gelockt und sind danach nicht mehr frei austauschbar.

## Konsequenz für die aktuelle Baseline

Die in der Baseline dokumentierte aktuelle Sleeper-Belegung mit Kaelon Black und De'Zhaun Stribling ist **nur der aktuelle technische Zustand**, keine strategische Festlegung.

Bis zum Taxi-Lock gilt deshalb:

1. Alle aktuellen Taxi-eligible Rookies werden als ein gemeinsamer Prospect-Pool bewertet, unabhängig davon, ob sie momentan auf Taxi oder auf der Bank stehen.
2. Die aktuelle Taxi-Platzierung darf weder als Schutz noch als Argument gegen einen Cut noch als Qualitätssignal verwendet werden.
3. Für Pre-Draft-/Cut-/Roster-Analysen werden die zwei Taxi-Slots nach der Keep/Cut-Bewertung virtuell den zwei sinnvollsten Entwicklungs-Stashes zugewiesen.
4. Erst danach wird bestimmt, welche verbleibenden Spieler tatsächlich aktive Plätze und welche Spieler die allgemeine Churn-/Conditional-Boundary belegen.
5. Die zwei Taxi-Slots zählen weiterhin nicht als allgemeine Churn-/Streamer-Kapazität.

## Korrektur der bisherigen Churn-Boundary-Interpretation

Die Aussage der Ausgangs-Baseline, dass Dylan Sampson und Chris Bell die zwei ersten aktiven Churn-Boundary-Kandidaten darstellen, ist **vor dem Taxi-Lock nicht als feste Paarung zu lesen**.

Chris Bell ist als aktueller Rookie Teil des gemeinsam zu optimierenden Taxi-Pools. Wenn Bell bei einer aktuellen Neubewertung einen der zwei virtuellen Taxi-Slots erhalten sollte, kann er definitionsgemäß nicht gleichzeitig einen der zwei allgemeinen **aktiven** Churn-Slots repräsentieren. In diesem Fall muss der nächste aktive Boundary-Spieler neu bestimmt werden.

Dasselbe Prinzip gilt für jeden anderen Taxi-eligible Rookie: Die operative Boundary wird erst **nach** der optimalen virtuellen Taxi-Zuweisung bestimmt.

## Harte Roster-Mathematik bleibt unverändert

Die Pre-Lock-Flexibilität schafft keinen zusätzlichen dritten Taxi-Slot. Bei 33 gehaltenen Spielern, 30 regulär aktiven Plätzen und zwei Taxi-Slots bleibt insgesamt ein weiterer Roster-Abgang erforderlich, solange kein Spieler einen nutzbaren Reserve-Platz belegt.

Die Taxi-Flexibilität verändert also **welche** Rookies aktiv bzw. auf Taxi stehen, nicht die Gesamtzahl der haltbaren Spieler.

## Nächster Taxi-Entscheidungspunkt

Vor dem ersten Ligaspiel soll eine eigene finale Taxi-Analyse durchgeführt werden. Sie muss alle dann aktuellen Rookies gemeinsam vergleichen und mindestens berücksichtigen:

- NFL-Draftkapital;
- aktuelle NFL-Rolle und Depth-Chart-Pfad;
- Verletzungsstatus;
- erwartete frühe Weekly Utility;
- Dynasty-/Marktwert und Trend;
- Entwicklungspotenzial;
- Opportunity Cost eines aktiven Rosterplatzes;
- welche zwei Spieler am meisten davon profitieren, als Entwicklungs-Stash gelockt zu werden.

Kanonische Mechanik: `fantasy-management/_ai/ROSTER_ARCHITECTURE.md` und `fantasy-management/league-context/league-format-notes.md`.
