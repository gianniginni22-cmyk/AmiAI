"""Deterministic quality gates for generated amigurumi patterns."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import math
from .shape_graph import ShapeGraph

@dataclass
class QualityReport:
    score: float
    status: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    gates: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self):
        return {"score": round(self.score, 1), "status": self.status,
                "errors": self.errors, "warnings": self.warnings,
                "metrics": {k: (round(float(v), 3) if isinstance(v, (int, float)) else {sk: round(float(sv), 3) for sk, sv in v.items()}) for k,v in self.metrics.items()},
                "gates": self.gates}

def assess_graph(graph: ShapeGraph, project=None, target_height_cm: float = 15.0) -> QualityReport:
    errors, warnings = [], []
    v = graph.validate()
    errors.extend(v.errors); warnings.extend(v.warnings)
    geometric = [n for n in graph.nodes.values() if n.has_pattern_geometry]
    if not geometric: errors.append("Nessun pezzo lavorabile nel grafo.")
    counts_ok = True; max_delta = 0; invalid_rounds = 0
    if project:
        for part in project.parts.values():
            prev = None
            for r in part.shape.rounds:
                max_delta = max(max_delta, abs(r.after-r.before))
                if not r.stitch_count_ok or r.after != r.before+r.increases-r.decreases:
                    counts_ok=False; invalid_rounds += 1
                if prev is not None and abs(r.after-prev) > 6:
                    warnings.append(f"{part.name}: salto di conteggio oltre 6 maglie tra giri.")
                prev=r.after
    joins_ok = True
    for e in graph.edges.values():
        p=graph.nodes.get(e.parent); c=graph.nodes.get(e.child)
        if not p or not c or e.parent_point not in p.connections or e.child_point not in c.connections:
            joins_ok=False
    if not counts_ok: errors.append("Uno o più giri hanno conteggi incoerenti.")
    if not joins_ok: errors.append("Una o più giunzioni non sono risolvibili.")
    confs=[]
    for n in graph.nodes.values():
        c=n.metadata.get("confidence")
        if isinstance(c,(int,float)): confs.append(float(c))
    confidence=sum(confs)/len(confs) if confs else float(graph.metadata.get("confidence", .5) or .5)
    if confidence < .55: warnings.append("Confidenza visiva bassa: la geometria richiede verifica manuale.")
    scale_error=0.0
    if geometric:
        z0=min(n.position.z+min(p.z_cm for p in n.profile) for n in geometric)
        z1=max(n.position.z+max(p.z_cm for p in n.profile) for n in geometric)
        span=max(0.0,z1-z0); scale_error=abs(span-target_height_cm)/max(target_height_cm,1e-6)
        if scale_error>.35: warnings.append("L'altezza geometrica complessiva differisce molto dal target; il campione reale può richiedere una scala.")
    gates={"graph_valid":v.ok,"stitch_counts":counts_ok,"joints_resolvable":joins_ok,
           "has_geometry":bool(geometric),"confidence_acceptable":confidence>=.4}

    # Punteggi percentuali separati: permettono di capire *perché* un modello
    # non raggiunge 100%, invece di mostrare solo un voto globale.
    graph_pct = 100.0 if v.ok else max(0.0, 100.0 - min(100.0, len(v.errors)*35.0))
    counts_pct = 100.0 if counts_ok else max(0.0, 100.0 - min(100.0, invalid_rounds*5.0))
    joints_pct = 100.0 if joins_ok else 0.0
    geometry_pct = 100.0 if geometric else 0.0
    vision_pct = max(0.0, min(100.0, confidence*100.0))
    scale_pct = max(0.0, min(100.0, 100.0 - scale_error*100.0))
    components = {
        "visione": vision_pct,
        "struttura_grafo": graph_pct,
        "geometria": geometry_pct,
        "conteggi_maglie": counts_pct,
        "giunzioni": joints_pct,
        "scala_target": scale_pct,
    }
    weights = {"visione":.20,"struttura_grafo":.20,"geometria":.15,
               "conteggi_maglie":.20,"giunzioni":.15,"scala_target":.10}
    score = sum(components[k]*weights[k] for k in components)
    # Un errore bloccante non può essere mascherato dalla media.
    if errors: score = min(score, 59.0)
    status="PASS" if score>=80 and all(gates.values()) else ("REVIEW" if score>=55 else "FAIL")
    return QualityReport(max(0,min(100,score)),status,errors,warnings,
        {"vision_confidence":confidence,"max_round_delta":max_delta,"invalid_rounds":invalid_rounds,
         "height_relative_error":scale_error,"component_scores":components,
         "component_weights":weights},gates)

def construction_notes(graph: ShapeGraph) -> List[str]:
    roots=graph.roots(); lines=[]
    lines.append("Costruzione consigliata: lavora i pezzi principali separatamente, imbottisci progressivamente e cuci dopo aver verificato gli assi di posa.")
    if roots: lines.append("Base del montaggio: " + ", ".join(graph.nodes[r].name for r in roots) + ".")
    for e in graph.edges.values():
        p=graph.nodes[e.parent]; c=graph.nodes[e.child]
        lines.append(f"{c.name}: allinea il punto {e.child_point} con {p.name}/{e.parent_point}; controlla simmetria e orientamento prima della cucitura.")
    return lines
