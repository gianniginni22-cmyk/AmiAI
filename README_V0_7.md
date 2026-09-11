# Amigurumi AI v0.7.2 — Amigurumi Design Model

## Obiettivo
Inserire una rappresentazione intermedia tra visione e geometria: identità del soggetto → concept amigurumi → template multi-view strutturato → Shape Graph → Geometry Engine → pattern.

## Componenti
- `app/crochet_engine/design_model.py`: schema strict, prompt, fallback e generazione concept image.
- `/api/design`: crea il Design Model e, con API key, una concept image amigurumi.
- UI: `🎨 CREA CONCEPT + TEMPLATE`, visualizzazione concept e tab `Design Model`.
- `/api/analyze`: accetta `design_json` e lo usa come rappresentazione intermedia autorevole per identità, parti, posa e relazioni.

## Regola architetturale
La concept image è una visualizzazione di progetto, non la ground truth. Il modello strutturato resta la rappresentazione tecnica.

## Test
- Design Model: 3/3
- Suite esistente eseguita: 8/8
- Endpoint `/api/design` fallback verificato: HTTP 200

## Nota
La generazione reale della concept image richiede una API key e un modello image configurato (`OPENAI_IMAGE_MODEL`, default `gpt-image-2`).
