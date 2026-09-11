"""Profile fitting from a reference image into Shape Graph profiles.

This module intentionally stays deterministic. It does not try to infer semantic
parts from pixels; the multimodal model supplies the Shape Graph, and this fitter
uses the reference image to correct the radial profiles of those parts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

import cv2
import numpy as np

from .engine import ProfilePoint
from .shape_graph import ShapeGraph, ShapeNode


@dataclass
class MaskResult:
    mask: np.ndarray
    bbox: Tuple[int, int, int, int]
    area: int
    confidence: float


@dataclass
class ProfileObservation:
    z_cm: float
    diameter_cm: float
    width_px: float
    confidence: float


@dataclass
class NodeFit:
    node_id: str
    changed: bool
    confidence: float
    observations: List[ProfileObservation] = field(default_factory=list)
    original_diameters_cm: List[float] = field(default_factory=list)
    fitted_diameters_cm: List[float] = field(default_factory=list)
    reason: str = ""


@dataclass
class ProfileFitReport:
    image_width: int
    image_height: int
    foreground_bbox: Tuple[int, int, int, int]
    foreground_area: int
    foreground_confidence: float
    px_per_cm: float
    nodes: Dict[str, NodeFit]
    warnings: List[str] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        vals = [n.confidence for n in self.nodes.values() if n.confidence > 0]
        return float(sum(vals) / len(vals)) if vals else 0.0

    def to_dict(self) -> dict:
        return {
            "image": {"width": self.image_width, "height": self.image_height},
            "foreground": {
                "bbox": list(self.foreground_bbox),
                "area_px": self.foreground_area,
                "confidence": round(self.foreground_confidence, 3),
            },
            "px_per_cm": round(self.px_per_cm, 3),
            "mean_confidence": round(self.mean_confidence, 3),
            "warnings": self.warnings,
            "nodes": {
                k: {
                    "changed": v.changed,
                    "confidence": round(v.confidence, 3),
                    "reason": v.reason,
                    "observations": [
                        {"z_cm": o.z_cm, "diameter_cm": round(o.diameter_cm, 3),
                         "width_px": round(o.width_px, 1), "confidence": round(o.confidence, 3)}
                        for o in v.observations
                    ],
                    "original_diameters_cm": [round(x, 3) for x in v.original_diameters_cm],
                    "fitted_diameters_cm": [round(x, 3) for x in v.fitted_diameters_cm],
                }
                for k, v in self.nodes.items()
            },
        }


class ProfileFitter:
    """Fit Shape Graph radial profiles against a segmented reference image."""

    def __init__(self, min_area_ratio: float = 0.015, smooth: float = 0.35):
        self.min_area_ratio = min_area_ratio
        self.smooth = smooth

    def segment(self, image: np.ndarray) -> MaskResult:
        if image is None or image.size == 0:
            raise ValueError("Immagine vuota.")
        if image.ndim == 2:
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        else:
            bgr = image.copy()
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        # Green yarn is the dominant semantic cue in the current demo. The lower
        # saturation branch also keeps dark green plates and shadows connected.
        green = cv2.inRange(hsv, np.array([25, 38, 15], np.uint8), np.array([95, 255, 245], np.uint8))
        green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
        green = cv2.morphologyEx(green, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(green, 8)
        if n <= 1:
            raise ValueError("Impossibile isolare il soggetto dall'immagine.")
        areas = stats[1:, cv2.CC_STAT_AREA]
        idx = 1 + int(np.argmax(areas))
        area = int(stats[idx, cv2.CC_STAT_AREA])
        h, w = green.shape
        if area < self.min_area_ratio * h * w:
            raise ValueError("La maschera del soggetto è troppo piccola.")
        mask = np.where(labels == idx, 255, 0).astype(np.uint8)
        # Fill tiny holes and smooth the silhouette without expanding it heavily.
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        ys, xs = np.where(mask > 0)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))
        # Confidence rewards a large central component and penalizes excessive fragmentation.
        component_ratio = area / float(h * w)
        confidence = min(1.0, 0.55 + component_ratio * 2.2)
        return MaskResult(mask, bbox, area, confidence)

    @staticmethod
    def _global_z_range(graph: ShapeGraph) -> Tuple[float, float]:
        vals = []
        for node in graph.nodes.values():
            if not node.profile or node.kind == "detail":
                continue
            vals.append(node.position.z + min(p.z_cm for p in node.profile))
            vals.append(node.position.z + max(p.z_cm for p in node.profile))
        if not vals:
            return 0.0, 1.0
        lo, hi = min(vals), max(vals)
        return lo, hi if hi > lo else lo + 1.0

    @staticmethod
    def _global_x_range(graph: ShapeGraph) -> Tuple[float, float]:
        vals = [n.position.x for n in graph.nodes.values() if n.profile and n.kind != "detail"]
        if not vals:
            return -1.0, 1.0
        lo, hi = min(vals), max(vals)
        return (lo, hi if hi > lo else lo + 1.0)

    def _project(self, node: ShapeNode, local_z: float, graph: ShapeGraph,
                 bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x0, y0, x1, y1 = bbox
        z0, z1 = self._global_z_range(graph)
        gx0, gx1 = self._global_x_range(graph)
        wz = node.position.z + local_z
        # Use explicit image anchors if a vision model has supplied them.
        anchor = node.metadata.get("image_anchor_px")
        if isinstance(anchor, dict):
            ax = float(anchor.get("x", 0.5))
            ay = float(anchor.get("y", 0.5))
            span = node.metadata.get("image_span_px")
            if isinstance(span, dict):
                sy = float(span.get("y", max(20.0, y1 - y0)))
                local_min = min(p.z_cm for p in node.profile) if node.profile else 0.0
                local_max = max(p.z_cm for p in node.profile) if node.profile else 1.0
                t = (local_z - local_min) / max(local_max - local_min, 1e-6)
                return ax * (x1 - x0) + x0, ay * (y1 - y0) + y0 + (t - 0.5) * sy
            return ax * (x1 - x0) + x0, ay * (y1 - y0) + y0
        # Default semantic projection: x left/right, z vertical.
        tx = (node.position.x - gx0) / max(gx1 - gx0, 1e-6)
        ty = 1.0 - (wz - z0) / max(z1 - z0, 1e-6)
        return x0 + tx * (x1 - x0), y0 + ty * (y1 - y0)

    @staticmethod
    def _row_segment(mask: np.ndarray, y: int, expected_x: float, half_window: int) -> Optional[Tuple[int, int]]:
        h, w = mask.shape
        y = max(0, min(h - 1, int(y)))
        xs = np.flatnonzero(mask[y] > 0)
        if xs.size < 2:
            return None
        # Split row into contiguous components.
        cuts = np.where(np.diff(xs) > 1)[0]
        starts = np.r_[0, cuts + 1]
        ends = np.r_[cuts, len(xs) - 1]
        segments = [(int(xs[s]), int(xs[e])) for s, e in zip(starts, ends)]
        local = [s for s in segments if s[1] >= expected_x - half_window and s[0] <= expected_x + half_window]
        candidates = local or segments
        if not candidates:
            return None
        return min(candidates, key=lambda s: abs(((s[0] + s[1]) * 0.5) - expected_x))

    def _measure(self, node: ShapeNode, local_z: float, graph: ShapeGraph,
                 mask_result: MaskResult, px_per_cm: float) -> Optional[ProfileObservation]:
        bbox = mask_result.bbox
        ex, ey = self._project(node, local_z, graph, bbox)
        original = np.interp(local_z,
                             [p.z_cm for p in node.profile],
                             [p.diameter_cm for p in node.profile])
        expected_px = max(8.0, original * px_per_cm)
        seg = self._row_segment(mask_result.mask, int(round(ey)), ex, int(max(24, expected_px * 1.8)))
        if seg is None:
            return None
        width_px = float(seg[1] - seg[0] + 1)
        # Reject segments grossly inconsistent with the part's prior geometry.
        ratio = width_px / expected_px
        if ratio < 0.28 or ratio > 3.2:
            return None
        confidence = mask_result.confidence * max(0.0, 1.0 - abs(math.log(max(ratio, 1e-6))) / 2.0)
        return ProfileObservation(local_z, width_px / px_per_cm, width_px, min(1.0, confidence))

    def fit_graph(self, graph: ShapeGraph, image: np.ndarray, target_height_cm: float) -> ProfileFitReport:
        mask_result = self.segment(image)
        x0, y0, x1, y1 = mask_result.bbox
        bbox_h = max(1, y1 - y0)
        px_per_cm = bbox_h / max(float(target_height_cm), 1e-6)
        report = ProfileFitReport(image.shape[1], image.shape[0], mask_result.bbox,
                                  mask_result.area, mask_result.confidence, px_per_cm, {})
        for node_id, node in graph.nodes.items():
            if not node.profile or node.kind in {"detail", "assembly_only"}:
                report.nodes[node_id] = NodeFit(node_id, False, 0.0,
                                                reason="Nessun profilo radiale compilabile.")
                continue
            original = [p.diameter_cm for p in node.profile]
            obs: List[ProfileObservation] = []
            for p in node.profile:
                o = self._measure(node, p.z_cm, graph, mask_result, px_per_cm)
                if o:
                    obs.append(o)
            if len(obs) < max(2, math.ceil(len(node.profile) * 0.4)):
                report.nodes[node_id] = NodeFit(node_id, False, 0.0, obs, original,
                                                original[:], "Misure insufficienti: profilo originale conservato.")
                continue
            by_z = {round(o.z_cm, 6): o for o in obs}
            fitted = []
            confs = []
            for p in node.profile:
                o = by_z.get(round(p.z_cm, 6))
                if o is None:
                    # Interpolate measured neighbors when a single row is unavailable.
                    fitted.append(p.diameter_cm)
                    continue
                # Blend observation with prior. This prevents a single silhouette row
                # (especially at overlaps) from destroying the generated crochet geometry.
                alpha = self.smooth * o.confidence
                d = (1.0 - alpha) * p.diameter_cm + alpha * o.diameter_cm
                # Keep local topology stable; the fitter changes dimensions, not ordering.
                fitted.append(max(0.5, d))
                confs.append(o.confidence)
            for i in range(1, len(fitted)):
                # Limit abrupt changes between adjacent rounds/profile stations.
                prev = fitted[i - 1]
                fitted[i] = min(max(fitted[i], prev * 0.55), prev * 1.8)
            changed = any(abs(a - b) > 0.08 for a, b in zip(original, fitted))
            node.profile = [ProfilePoint(p.z_cm, round(d, 3)) for p, d in zip(node.profile, fitted)]
            confidence = float(np.mean(confs)) if confs else 0.0
            report.nodes[node_id] = NodeFit(node_id, changed, confidence, obs, original, fitted,
                                            "Profilo adattato alla silhouette; topologia invariata.")
        if report.mean_confidence < 0.45:
            report.warnings.append("Confidence media bassa: la foto o la proiezione del grafo non sono sufficienti per un fit affidabile.")
        report.warnings.append("Il fit usa una silhouette 2D: profondità, sovrapposizioni e parti nascoste restano stime.")
        return report


def fit_graph_to_image(graph: ShapeGraph, image: np.ndarray, target_height_cm: float) -> ProfileFitReport:
    return ProfileFitter().fit_graph(graph, image, target_height_cm)
