# Profile Fitter v0.4

Aggiunge il fitting deterministico della geometria del Shape Graph rispetto alla foto.

Pipeline:

`foto -> segmentazione silhouette -> misure per profilo -> ShapeGraph.profile -> Geometry Engine`

## Limiti

- La segmentazione demo è ottimizzata per il soggetto verde del test.
- Il fit è 2D: profondità e parti nascoste restano stime.
- L'AI deve continuare a fornire la scomposizione semantica; il fitter non sostituisce la vision.
- Le dimensioni vengono stabilizzate con un blend rispetto al profilo precedente, evitando salti irrealistici.

## API

`POST /api/analyze` accetta la stessa foto del MVP. Se una foto è presente, la risposta include `profile_fit` con bbox, scala px/cm, confidence e osservazioni per nodo.
