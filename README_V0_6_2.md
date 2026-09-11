# Amigurumi AI v0.6.2 — Intelligent Part Decomposition

Adds a dedicated semantic decomposition stage before geometry.

- `POST /api/decompose` with strict JSON schema.
- Stable part IDs, category, role, parent relation, symmetry groups, confidence and optional image anchors.
- Local heuristic fallback when no API key is configured or the AI call fails.
- UI button **SCOMPONI SOGGETTO** and **Parti** tab.
- Full generation preserves `vision_parts` as the semantic decomposition feeding the geometry stage.


## v0.6.2.1 — Complexity API error handling
- `/api/complexity` restituisce sempre JSON anche in caso di errore.
- Il frontend verifica HTTP status e payload prima del parsing dei risultati.
- Gli errori interni vengono stampati nel log backend e mostrati con un messaggio diagnostico.
