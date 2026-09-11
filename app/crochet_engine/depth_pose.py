"""Monocular depth and pose estimation for ShapeGraph.

This module is deliberately uncertainty-aware: a single photograph cannot recover
true metric depth. It estimates *relative* depth, local pose, visibility and
occlusion cues, then writes those estimates back into ShapeGraph metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

import cv2
import numpy as np

from .shape_graph import ShapeGraph, ShapeNode, Vec3, Euler


@dataclass
class PoseEstimate:
    node_id: str
    depth_cm: float
    relative_depth: float
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    visibility: float
    occlusion: float
    confidence: float
    anchor_px: Tuple[float, float] = (0.0, 0.0)
    apparent_width_px: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "depth_cm": round(self.depth_cm, 3),
            "relative_depth": round(self.relative_depth, 3),
            "yaw_deg": round(self.yaw_deg, 2),
            "pitch_deg": round(self.pitch_deg, 2),
            "roll_deg": round(self.roll_deg, 2),
            "visibility": round(self.visibility, 3),
            "occlusion": round(self.occlusion, 3),
            "confidence": round(self.confidence, 3),
            "anchor_px": [round(self.anchor_px[0], 1), round(self.anchor_px[1], 1)],
            "apparent_width_px": round(self.apparent_width_px, 1),
            "notes": self.notes,
        }


@dataclass
class DepthPoseReport:
    image_width: int
    image_height: int
    subject_bbox: Tuple[int, int, int, int]
    mask_area: int
    mask_confidence: float
    metric_scale_px_per_cm: float
    estimates: Dict[str, PoseEstimate] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        values = [e.confidence for e in self.estimates.values()]
        return float(np.mean(values)) if values else 0.0

    def to_dict(self) -> dict:
        return {
            "image": {"width": self.image_width, "height": self.image_height},
            "subject_bbox": list(self.subject_bbox),
            "mask_area": self.mask_area,
            "mask_confidence": round(self.mask_confidence, 3),
            "metric_scale_px_per_cm": round(self.metric_scale_px_per_cm, 3),
            "mean_confidence": round(self.mean_confidence, 3),
            "estimates": {k: v.to_dict() for k, v in self.estimates.items()},
            "warnings": self.warnings,
        }


class DepthPoseEstimator:
    """Estimate relative 3D pose from one RGB image + semantic ShapeGraph."""

    def __init__(self, min_area_ratio: float = 0.01):
        self.min_area_ratio = min_area_ratio

    def segment(self, image: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int], int, float]:
        if image is None or image.size == 0:
            raise ValueError("Immagine vuota.")
        if image.ndim == 2:
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        else:
            bgr = image.copy()
        h, w = bgr.shape[:2]
        # Work on a small proxy image: pose estimation needs coarse silhouette,
        # not pixel-perfect matting. This keeps the endpoint responsive on phone photos.
        max_dim = 720
        scale = min(1.0, max_dim / float(max(h, w)))
        if scale < 1.0:
            small = cv2.resize(bgr, (max(2, int(w * scale)), max(2, int(h * scale))), interpolation=cv2.INTER_AREA)
        else:
            small = bgr
        sh, sw = small.shape[:2]
        mask0 = np.zeros((sh, sw), np.uint8)
        margin_x, margin_y = max(2, int(sw * .03)), max(2, int(sh * .03))
        rect = (margin_x, margin_y, max(2, sw - 2 * margin_x), max(2, sh - 2 * margin_y))
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(small, mask0, rect, bgd, fgd, 2, cv2.GC_INIT_WITH_RECT)
            fg_small = np.where((mask0 == cv2.GC_FGD) | (mask0 == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        except cv2.error:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            _, fg_small = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
        fg_small = cv2.morphologyEx(fg_small, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        fg_small = cv2.morphologyEx(fg_small, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg_small, 8)
        if n <= 1:
            raise ValueError("Impossibile isolare il soggetto.")
        idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area_small = int(stats[idx, cv2.CC_STAT_AREA])
        if area_small < self.min_area_ratio * sh * sw:
            raise ValueError("La maschera del soggetto è troppo piccola.")
        mask_small = np.where(labels == idx, 255, 0).astype(np.uint8)
        # Return mask at original resolution so downstream modules share coordinates.
        mask = cv2.resize(mask_small, (w, h), interpolation=cv2.INTER_NEAREST)
        ys, xs = np.where(mask > 0)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))
        area = int(np.count_nonzero(mask))
        confidence = min(1.0, 0.45 + (area / float(h * w)) * 2.5)
        return mask, bbox, area, confidence

    @staticmethod
    def _anchor(node: ShapeNode, graph: ShapeGraph, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        x0, y0, x1, y1 = bbox
        a = node.metadata.get("image_anchor_px")
        if isinstance(a, dict):
            ax, ay = float(a.get("x", .5)), float(a.get("y", .5))
            # AI may supply normalized [0,1] anchors or raw pixels.
            if 0 <= ax <= 1 and 0 <= ay <= 1:
                return x0 + ax * (x1 - x0), y0 + ay * (y1 - y0)
            return ax, ay
        xs = [n.position.x for n in graph.nodes.values() if n.profile and n.kind != "detail"] or [0.0]
        zs = [n.position.z for n in graph.nodes.values() if n.profile and n.kind != "detail"] or [0.0]
        xmin, xmax = min(xs), max(xs)
        zmin, zmax = min(zs), max(zs)
        tx = (node.position.x - xmin) / max(xmax - xmin, 1e-6)
        ty = 1 - (node.position.z - zmin) / max(zmax - zmin, 1e-6)
        return x0 + tx * (x1 - x0), y0 + ty * (y1 - y0)

    @staticmethod
    def _row_width(mask: np.ndarray, x: float, y: float, half_window: int = 70) -> Optional[float]:
        h, w = mask.shape
        yy = max(0, min(h - 1, int(round(y))))
        xs = np.flatnonzero(mask[yy] > 0)
        if xs.size < 2:
            return None
        candidates = []
        cuts = np.where(np.diff(xs) > 1)[0]
        starts = np.r_[0, cuts + 1]
        ends = np.r_[cuts, len(xs) - 1]
        for s, e in zip(starts, ends):
            a, b = int(xs[s]), int(xs[e])
            if b >= x - half_window and a <= x + half_window:
                candidates.append((a, b))
        if not candidates:
            return None
        a, b = min(candidates, key=lambda ab: abs((ab[0] + ab[1]) / 2 - x))
        return float(b - a + 1)

    @staticmethod
    def _angle_deg(dx: float, dy: float) -> float:
        return math.degrees(math.atan2(dy, dx))

    def estimate(self, graph: ShapeGraph, image: np.ndarray, target_height_cm: float) -> DepthPoseReport:
        mask, bbox, area, mask_conf = self.segment(image)
        h, w = image.shape[:2]
        x0, y0, x1, y1 = bbox
        px_per_cm = max(1e-6, (y1 - y0) / max(float(target_height_cm), 1e-6))
        report = DepthPoseReport(w, h, bbox, area, mask_conf, px_per_cm)

        # Reference apparent width for robust relative-depth estimation.
        widths = []
        anchors = {}
        for node_id, node in graph.nodes.items():
            if not node.profile or node.kind in {"detail", "assembly_only"}:
                continue
            a = self._anchor(node, graph, bbox)
            anchors[node_id] = a
            ww = self._row_width(mask, *a)
            if ww:
                widths.append(ww)
        median_width = float(np.median(widths)) if widths else max(20.0, (x1 - x0) * .18)

        # Parent-child image vectors provide a useful pose cue.
        parents = {e.child: e.parent for e in graph.edges.values() if e.child in graph.nodes}
        for node_id, node in graph.nodes.items():
            if not node.profile or node.kind in {"detail", "assembly_only"}:
                continue
            ax, ay = anchors[node_id]
            width_px = self._row_width(mask, ax, ay)
            if width_px is None:
                width_px = median_width
                visibility = .35
            else:
                visibility = min(1.0, .55 + width_px / max(median_width, 1.0) * .35)

            # Apparent width is affected by yaw. Use a conservative bounded model:
            # frontal parts are wider; strongly foreshortened parts are narrower.
            width_ratio = max(.35, min(2.5, width_px / max(median_width, 1.0)))
            yaw = math.degrees(math.acos(max(-1.0, min(1.0, min(1.0, width_ratio)))))
            if width_ratio >= 1:
                yaw = 0.0
            else:
                yaw = min(65.0, yaw)

            pitch = float(node.rotation.rx)
            roll = float(node.rotation.rz)
            if node_id in parents and parents[node_id] in anchors:
                px, py = anchors[parents[node_id]]
                dx, dy = ax - px, ay - py
                # Image down is +y; crochet z-up therefore flips the vertical sign.
                pitch = max(-75.0, min(75.0, -self._angle_deg(dx, dy) + 90.0))
                if abs(dx) > 4:
                    roll = max(-60.0, min(60.0, self._angle_deg(dx, dy)))

            # Relative depth is intentionally normalized, not presented as measured truth.
            relative_depth = max(-1.0, min(1.0, math.log(width_ratio) * -0.85))
            depth_cm = max(0.0, target_height_cm * .45 + relative_depth * target_height_cm * .20)

            # Occlusion cue: small visible width + nearby semantic node = likely overlap.
            occlusion = max(0.0, min(1.0, 1.0 - visibility))
            conf = mask_conf * (.45 + .55 * visibility) * (0.75 if node.metadata.get("image_anchor_px") else 0.58)
            notes = "Profondità relativa da silhouette; non è una misura metrica." if not node.metadata.get("depth_hint") else "Stima fusa con depth_hint semantico."
            est = PoseEstimate(node_id, depth_cm, relative_depth, yaw, pitch, roll,
                               visibility, occlusion, min(1.0, conf), (ax, ay), width_px, notes)
            report.estimates[node_id] = est

            # Write estimates back to the graph for downstream assembly/geometry.
            node.metadata["depth_pose"] = est.to_dict()
            node.rotation = Euler(est.pitch_deg, est.yaw_deg, est.roll_deg)
            node.metadata["estimated_depth_cm"] = round(depth_cm, 3)
            node.metadata["visibility"] = round(visibility, 3)
            node.metadata["occlusion"] = round(occlusion, 3)

        if not report.estimates:
            report.warnings.append("Nessuna parte con profilo disponibile per la stima depth/pose.")
        if report.mean_confidence < .45:
            report.warnings.append("Confidence depth/pose bassa: usa una seconda vista o lascia che la visione AI fornisca anchor/depth_hint.")
        report.warnings.append("Una singola foto non determina la profondità reale: le stime sono relative e uncertainty-aware.")
        return report


def estimate_depth_pose(graph: ShapeGraph, image: np.ndarray, target_height_cm: float) -> DepthPoseReport:
    return DepthPoseEstimator().estimate(graph, image, target_height_cm)
