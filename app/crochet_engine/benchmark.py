"""CORE-008 deterministic end-to-end regression benchmark.

The benchmark deliberately separates semantic/reference correspondence from
mathematical/technical pattern validity. It exercises the complete local core
from Design Model through graph, pose metadata, geometry, techniques, joints
and final pattern.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import re

from .pipeline import compile_design
from .shape_graph import ShapeGraph
from .quality import assess_graph
from .engine import Gauge


@dataclass
class BenchmarkCase:
    name: str
    design: Dict[str, Any]
    expected_roles: Dict[str, int]
    required_features: List[str] = field(default_factory=list)
    expected_subject_tokens: List[str] = field(default_factory=list)
    min_reference_match: float = 80.0
    min_pattern_validity: float = 80.0


def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-zàèéìòù]+", str(s).lower()))


def _role_counts(design: Dict[str, Any]) -> Dict[str, int]:
    roles: Dict[str, int] = {}
    for p in design.get("parts", []):
        role = str(p.get("role", "other"))
        roles[role] = roles.get(role, 0) + int(p.get("count") or 1)
    return roles


def score_case(case: BenchmarkCase, target_height_cm: float = 15.0, hook_mm: float = 2.5) -> Dict[str, Any]:
    out = compile_design(case.design, target_height_cm, hook_mm)
    graph = ShapeGraph.from_dict(out["shape_graph"])
    project = graph.compile(Gauge(28, 32), include_details=True)
    quality = assess_graph(graph, project, target_height_cm)

    roles = _role_counts(case.design)
    role_hits = sum(min(roles.get(k, 0), v) for k, v in case.expected_roles.items())
    role_total = sum(case.expected_roles.values()) or 1
    role_score = 100 * role_hits / role_total

    text = _norm(case.design.get("subject", "") + " " + case.design.get("semantic_summary", ""))
    expected = set(case.expected_subject_tokens)
    subject_hits = sum(1 for tok in expected if any(tok in t or t in tok for t in text))
    subject_score = 100 if not expected else 100 * subject_hits / len(expected)

    feats = " ".join(str(x).lower() for x in case.design.get("distinctive_features", []))
    feature_score = 100 if not case.required_features else 100 * sum(1 for f in case.required_features if f.lower() in feats) / len(case.required_features)

    reference_match = 0.45 * subject_score + 0.35 * role_score + 0.20 * feature_score

    # Independent structural checks beyond the generic quality score.
    technique_ok = all(bool(n.metadata.get("technique")) for n in graph.nodes.values() if n.has_pattern_geometry)
    topology_ok = all(e.parent in graph.nodes and e.child in graph.nodes for e in graph.edges.values())
    assembly_ok = bool(out.get("assembly")) and len(graph.edges) >= max(0, len(graph.nodes) - 1)
    pattern_ok = bool(out.get("pattern")) and len(out.get("pattern", "")) > 500
    construction_ok = all(bool(n.metadata.get("construction")) for n in graph.nodes.values() if n.has_pattern_geometry)

    independent_gates = {
        "quality": quality.status != "FAIL",
        "technique": technique_ok,
        "topology": topology_ok,
        "assembly": assembly_ok,
        "pattern": pattern_ok,
        "construction_metadata": construction_ok,
    }
    pattern_validity = quality.score
    pass_case = (
        reference_match >= case.min_reference_match
        and pattern_validity >= case.min_pattern_validity
        and all(independent_gates.values())
    )

    return {
        "name": case.name,
        "reference_match": round(reference_match, 1),
        "pattern_validity": round(pattern_validity, 1),
        "pass": pass_case,
        "quality": quality.to_dict(),
        "role_score": round(role_score, 1),
        "feature_score": round(feature_score, 1),
        "subject_score": round(subject_score, 1),
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "techniques": sorted({str(n.metadata.get("technique")) for n in graph.nodes.values()}),
        "independent_gates": independent_gates,
        "pattern_present": pattern_ok,
        "assembly_present": assembly_ok,
    }


def run_benchmark(cases: List[BenchmarkCase]) -> Dict[str, Any]:
    results = [score_case(c) for c in cases]
    ref_avg = sum(r["reference_match"] for r in results) / len(results) if results else 0
    pat_avg = sum(r["pattern_validity"] for r in results) / len(results) if results else 0
    passed = sum(1 for r in results if r["pass"])
    return {
        "cases": results,
        "case_count": len(results),
        "passed_cases": passed,
        "failed_cases": len(results) - passed,
        "reference_match_avg": round(ref_avg, 1),
        "pattern_validity_avg": round(pat_avg, 1),
        "pass": bool(results) and passed == len(results),
    }


def _part(i, label, role, count=1, parent=None, sym=None, construction="forma principale", feature="", x=.5, y=.5, sx=.5, sy=.5, h=5, w=3, d=2):
    return {
        "id": i, "label": label, "role": role, "count": count, "parent_id": parent,
        "symmetry_group": sym, "estimated_height_cm": h, "estimated_width_cm": w,
        "estimated_depth_cm": d, "center_front": {"x": x, "y": y},
        "center_side": {"x": sx, "y": sy}, "depth_hint": "front",
        "confidence": .9, "construction": construction, "notes": feature,
    }


def standard_cases() -> List[BenchmarkCase]:
    """Representative arbitrary-subject regression set for CORE-008."""
    return [
        BenchmarkCase("teddy", {
            "subject": "Mr Bean Teddy Bear", "semantic_summary": "orsetto con muso e orecchie tonde",
            "overall_confidence": .95, "distinctive_features": ["orecchie tonde", "muso nero"],
            "parts": [_part("body", "corpo", "body"), _part("head", "testa", "head", parent="body", feature="muso", w=4),
                      _part("arm", "braccio", "arm", 2, "body", "arms", "tubo"), _part("leg", "gamba", "leg", 2, "body", "legs", "tubo"),
                      _part("ear", "orecchio", "ear", 2, "head", "ears", "disco", w=2.2, d=1.0)]},
            {"body":1,"head":1,"arm":2,"leg":2,"ear":2}, ["orecchie tonde"], ["orsetto","orecchio"]),
        BenchmarkCase("dinosaur", {
            "subject": "Dinosaur", "semantic_summary": "dinosauro quadrupede con coda lunga e corna",
            "overall_confidence": .95, "distinctive_features": ["coda lunga", "corna"],
            "parts": [_part("body","corpo","body",w=5,d=3.5,h=7), _part("head","testa","head",parent="body",w=4,d=3,h=4.5),
                      _part("tail","coda","tail",parent="body",construction="tubo affusolato",feature="lunga affusolata",h=8,w=1.8,d=1.4),
                      _part("leg","zampa","leg",4,"body","legs","tubo",h=4,w=1.7,d=1.7), _part("horn","corno","horn",2,"head","horns","cono",h=2,w=1,d=1)]},
            {"body":1,"head":1,"tail":1,"leg":4,"horn":2}, ["coda lunga"], ["dinosaur"]),
        BenchmarkCase("beaver", {
            "subject": "Anthropomorphic Beaver", "semantic_summary": "castoro antropomorfo con coda piatta e grandi denti",
            "overall_confidence": .95, "distinctive_features": ["coda piatta", "denti grandi"],
            "parts": [_part("body","corpo","body",w=5,d=3.2,h=6), _part("head","testa","head",parent="body",w=4,d=3,h=4),
                      _part("arm","braccio","arm",2,"body","arms","tubo"), _part("leg","gamba","leg",2,"body","legs","tubo"),
                      _part("tail","coda piatta","tail",parent="body",construction="piatto",feature="piatta",h=4,w=4,d=.8),
                      _part("teeth","denti","detail",2,"head","teeth","applicazione",feature="grandi",h=1.2,w=.8,d=.4)]},
            {"body":1,"head":1,"arm":2,"leg":2,"tail":1,"detail":2}, ["coda piatta"], ["beaver","castoro"]),
        BenchmarkCase("mushroom", {
            "subject": "Red Mushroom", "semantic_summary": "fungo con cappello largo e gambo stretto",
            "overall_confidence": .92, "distinctive_features": ["cappello largo", "gambo stretto"],
            "parts": [_part("stem","gambo","body",h=7,w=2.4,d=2.4), _part("cap","cappello","plate",parent="stem",construction="piatto",feature="largo",h=3,w=7,d=6),
                      _part("spot","macchia","detail",5,"cap","spots","applicazione",h=.6,w=.8,d=.3)]},
            {"body":1,"plate":1,"detail":5}, ["cappello largo"], ["mushroom","fungo"]),
        BenchmarkCase("robot", {
            "subject": "Small Robot", "semantic_summary": "robot antropomorfo con corpo rettangolare, testa e antenne",
            "overall_confidence": .9, "distinctive_features": ["corpo rettangolare", "antenne"],
            "parts": [_part("body","corpo","body",h=6,w=5,d=3.5,construction="rettangolare"), _part("head","testa","head",parent="body",h=4,w=4,d=3,construction="rettangolare"),
                      _part("arm","braccio","arm",2,"body","arms","tubo"), _part("leg","gamba","leg",2,"body","legs","tubo"),
                      _part("antenna","antenna","horn",2,"head","antennas","cono",h=2,w=.7,d=.7)]},
            {"body":1,"head":1,"arm":2,"leg":2,"horn":2}, ["antenne"], ["robot"]),
        BenchmarkCase("bird", {
            "subject": "Asymmetric Bird", "semantic_summary": "uccello con un'ala più aperta e coda laterale",
            "overall_confidence": .9, "distinctive_features": ["ala aperta", "coda laterale"],
            "parts": [_part("body","corpo","body",h=5,w=4,d=3), _part("head","testa","head",parent="body",h=3.2,w=3,d=2.5),
                      _part("wing_l","ala sinistra","wing",parent="body",construction="lamina",feature="aperta",x=.35,y=.45,sx=.4,sy=.45,h=3,w=4,d=.8),
                      _part("wing_r","ala destra","wing",parent="body",construction="lamina",feature="chiusa",x=.72,y=.55,sx=.6,sy=.5,h=2,w=2.5,d=.7),
                      _part("tail","coda laterale","tail",parent="body",construction="tubo",feature="laterale",x=.85,y=.62,sx=.75,sy=.55,h=3,w=1.2,d=1)]},
            {"body":1,"head":1,"wing":2,"tail":1}, ["ala aperta","coda laterale"], ["bird","uccello"]),
    ]


def run_standard_benchmark() -> Dict[str, Any]:
    report = run_benchmark(standard_cases())
    report["benchmark"] = "CORE-008"
    report["criterion"] = "Tutti i casi devono superare reference_match, pattern_validity e i gate strutturali indipendenti."
    return report
