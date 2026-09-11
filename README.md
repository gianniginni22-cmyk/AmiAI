# Amigurumi AI Designer — MVP 0.3

Pipeline reale:

**foto/testo → analisi multimodale → Shape Graph → Crochet Geometry Engine → pattern + assemblaggio + controlli**

## Cosa cambia

L'MVP non usa più l'output vision direttamente come testo di pattern. Il modello multimodale produce un `shape_graph` strutturato con:

- nodi/parti;
- primitive e profili geometrici;
- coordinate 3D semantiche;
- punti di connessione;
- simmetrie;
- confidence e metadata.

Il server converte poi il JSON in `ShapeGraph`, lo valida e lo passa al Geometry Engine. Il pattern finale viene quindi compilato deterministicamente dai conteggi del grafo.

## Avvio

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env       # Windows: copy .env.example .env
# inserire OPENAI_API_KEY nel proprio ambiente/.env
uvicorn app.main:app --reload
```

Aprire `http://127.0.0.1:8000`.

Senza `OPENAI_API_KEY` viene usato il dinosauro di fallback, ma attraversa comunque **Shape Graph → Geometry Engine**, così la pipeline è testabile end-to-end.

## API

`POST /api/analyze` multipart:

- `image` — opzionale, immagine del soggetto;
- `description`;
- `height_cm`;
- `hook_mm`;
- `level`;
- `style`.

La risposta contiene:

- `result.shape_graph` — modello strutturale;
- `result.pattern` — pattern compilato;
- `result.assembly` — assemblaggio derivato dagli edge;
- `result.checks` — validazioni;
- `result._graph_validation` — metriche tecniche del grafo.

`GET /api/health` verifica che il servizio sia attivo.

## Architettura

```text
                    FOTO / TESTO
                         │
                         ▼
                 OPENAI MULTIMODALE
                         │
                         ▼
                    shape_graph
                         │
                         ▼
                   ShapeGraph.from_dict
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          validate()          assembly()
              │
              ▼
       Crochet Geometry Engine
              │
              ▼
       pattern per ogni parte
              │
              ▼
           output MVP
```

## Nota tecnica

Il profilo è ancora una rappresentazione geometrica semplificata, non una mesh/CAD ricostruita da pixel. Il passo successivo per aumentare la fedeltà è aggiungere stima di silhouette/proporzioni e un `Profile Fitter` che ottimizzi i profili del grafo rispetto alla maschera/sagoma osservata.


## v0.6.2 quality-first
- Vision Parts separati dal motore deterministico.
- JSON Schema strict con proprietà completamente richieste e connessioni serializzate come array.
- Profile Fit + Depth/Pose con confidence e limiti espliciti.
- Quality Gates per grafo, conteggi, giunzioni, confidence e scala.
- Gauge da campione opzionale.
- Assemblaggio più esplicito e UX di stato/qualità.
- Test automatici per conteggi e qualità.

## v0.6.2.2 — Punteggio percentuale qualità
- Il Quality Gate ora espone un punteggio complessivo 0–100% e sei percentuali separate: Visione, Struttura, Geometria, Conteggi maglie, Giunzioni, Scala target.
- Le percentuali sono pesate nel punteggio complessivo (20/20/15/20/15/10) e gli errori bloccanti impediscono di mascherare un problema con una media alta.
- La UI mostra le sei percentuali come barre e il punteggio complessivo.
- Test suite: 18 passed.


## v0.6.2.2 — Bootstrap auto-update + Punteggio Percentuale
- Bootstrap Windows con updater separato `AmigurumiAI-Updater.exe`.
- Check automatico di un manifest JSON HTTPS all'avvio tramite `AMIGURUMI_UPDATE_MANIFEST`.
- Download installer, verifica SHA-256, attesa chiusura app e avvio installer.
- Installazione per-utente (`%LOCALAPPDATA%\Programs\Amigurumi AI`), senza privilegi amministrativi richiesti.
- Punteggio qualità 0–100% con 6 componenti ponderate 20/20/15/20/15/10.
- Il manifest di produzione va pubblicato su HTTPS; esempio in `update-manifest.example.json`.
