# Amigurumi AI 0.6.1 — quality-first multimodal compiler

Questa versione consolida la pipeline in 10 aree: schema strict, separazione visione/motore, Shape Graph, fit silhouette, depth/pose uncertainty-aware, controlli di costruibilità, assemblaggio, UX/errori, gauge da campione e suite di test.

## Pipeline
Foto/testo → Vision Parts → Shape Graph → Profile Fit → Depth/Pose → Gauge → Geometry Engine → Quality Gates → Pattern/Assembly.

L'AI non è incaricata di inventare direttamente le righe del pattern: restituisce una rappresentazione strutturata; il motore deterministico calcola i conteggi e valida ogni giro.

## Test
`Set-ExecutionPolicy -Scope Process Bypass`
`.\packaging\build_windows.ps1`

## v0.6.2 — Analisi automatica della complessità
Prima della generazione è disponibile `POST /api/complexity`, che stima la complessità costruttiva da immagine e/o descrizione. Produce score 0–100, livello, confidence, motivazioni e raccomandazioni. Con immagine usa una segmentazione grossolana della silhouette, bordi, componenti, fori, complessità del contorno e simmetria; non pretende di ricostruire la geometria nascosta.
