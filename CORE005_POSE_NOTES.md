# CORE-005 — Pose & Orientation

CORE-005 collega la posa semantica alla Shape Graph e all'assemblaggio.

## Implementato
- `center_front` e `center_side` contribuiscono a posizione 3D relativa (`x/y/z`).
- Gli anchor semantici producono un orientamento locale bounded (`pitch/yaw/roll`).
- `ShapeNode.world_connection()` applica realmente la rotazione Euler e la scala agli offset locali.
- Le informazioni di posa vengono conservate nei metadata (`pose_source`, `semantic_pose`).
- Se è disponibile una fotografia, `DepthPoseEstimator` viene applicato alla Shape Graph durante `compile_design`; le stime relative sostituiscono/rafforzano la posa semantica.
- L'assemblaggio espone l'orientamento locale dei pezzi quando significativo.

## Limiti deliberati
Una singola immagine non consente ricostruzione metrica completa. La posa resta relativa/uncertainty-aware. Questo livello non pretende di essere un CAD/mesh solver.

## Regressione
34 test passano.
