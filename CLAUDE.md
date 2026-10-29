# CLAUDE.md

@AGENTS.md

## Antwortformat (nur Claude)

- Antworte auf Deutsch.
- Längere, ausführliche Antworten sind in Ordnung, enden aber immer mit einem kompakten Block **„Zusammenfassung"**.
- Der Block ist scanbar (Stichpunkte) und enthält:
  - Empfehlung
  - Entscheidungen, die der User treffen muss
  - Nächste Schritte
- Der User liest den langen Text darüber nur, wenn die Zusammenfassung nicht reicht.
- Bei kurzen Antworten entfällt der Block.

## Verhalten

- Unsicherheit kennzeichnen: Ausdrücklich markieren, was geprüft ist und was nur Annahme ist.
- Abschlussbericht: Am Ende kurz nennen, was geändert wurde, was verifiziert ist und was nicht (inklusive übersprungener Schritte).
- Entscheidungen mit Empfehlung: Wenn der User entscheiden muss, eine klare Empfehlung nennen statt nur Optionen aufzulisten.
- Wartende Threads (Claude-Projekte mit Koordinator und Threads): Wartet ein Thread auf etwas (CI, Merge-Voraussetzung, User), den Wartegrund an den Thread-Titel hängen, z. B. „… · wartet auf CI“, und den Zusatz entfernen, sobald es weitergeht. Grund: Die Statusanzeige zeigt solche Threads sonst als inaktiv.
- Issues nennen: Nie nur die Nummer nennen. Beim ersten Nennen eines Issues immer Titel und eine kurze Beschreibung dazu angeben, damit klar ist, worum es geht. Gilt sinngemäß auch für PRs.
