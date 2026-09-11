"""
Shape Graph for crochet/amigurumi reconstruction.

The graph is the bridge between visual understanding (AI/vision) and the
Crochet Geometry Engine:

    image/text -> semantic parts -> ShapeGraph -> per-part geometry -> pattern

It deliberately stores geometry in a lightweight, serialisable representation
rather than pretending to be a full CAD/mesh system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
import json
import math

from .engine import (
    Gauge,
    PatternProject,
    ProfilePoint,
    compile_project,
    interpolate_profile,
    egg_profile,
    sphere_profile,
    tapered_profile,
)


@dataclass(frozen=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def distance_to(self, other: "Vec3") -> float:
        d = self - other
        return math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: dict) -> "Vec3":
        return cls(float(data.get("x", 0)), float(data.get("y", 0)), float(data.get("z", 0)))


@dataclass(frozen=True)
class Euler:
    """Rotation in degrees, applied conceptually as XYZ local orientation."""

    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    def to_dict(self) -> dict:
        return {"rx": self.rx, "ry": self.ry, "rz": self.rz}

    @classmethod
    def from_dict(cls, data: dict) -> "Euler":
        return cls(float(data.get("rx", 0)), float(data.get("ry", 0)), float(data.get("rz", 0)))


@dataclass(frozen=True)
class ConnectionPoint:
    """A named attachment point in a part's local coordinate system."""

    name: str
    position: Vec3
    radius_cm: float = 0.0
    role: str = "join"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position.to_dict(),
            "radius_cm": self.radius_cm,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionPoint":
        return cls(
            name=str(data["name"]),
            position=Vec3.from_dict(data["position"]),
            radius_cm=float(data.get("radius_cm", 0)),
            role=str(data.get("role", "join")),
        )


@dataclass
class ShapeNode:
    id: str
    name: str
    kind: str = "piece"
    primitive: str = "custom"
    position: Vec3 = field(default_factory=Vec3)
    rotation: Euler = field(default_factory=Euler)
    scale: Vec3 = field(default_factory=lambda: Vec3(1, 1, 1))
    profile: List[ProfilePoint] = field(default_factory=list)
    start_stitches: int = 6
    material: str = "yarn"
    symmetry_group: Optional[str] = None
    required: bool = True
    metadata: Dict[str, object] = field(default_factory=dict)
    connections: Dict[str, ConnectionPoint] = field(default_factory=dict)

    def add_connection(self, point: ConnectionPoint) -> "ShapeNode":
        if point.name in self.connections:
            raise ValueError(f"Connection point already exists: {self.id}.{point.name}")
        self.connections[point.name] = point
        return self

    @property
    def has_pattern_geometry(self) -> bool:
        return len(self.profile) >= 2 and self.kind not in {"detail", "assembly_only"}

    def world_connection(self, point_name: str) -> Vec3:
        if point_name not in self.connections:
            raise KeyError(f"Unknown connection point: {self.id}.{point_name}")
        local = self.connections[point_name].position
        # CORE-005: apply the node's local Euler pose to local connection offsets.
        # This is not a mesh transform; it is the deterministic rigid transform
        # needed by assembly/attachment calculations.
        rx, ry, rz = (math.radians(v) for v in (self.rotation.rx, self.rotation.ry, self.rotation.rz))
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        x, y, z = local.x, local.y, local.z
        # X rotation
        y, z = y * cx - z * sx, y * sx + z * cx
        # Y rotation
        x, z = x * cy + z * sy, -x * sy + z * cy
        # Z rotation
        x, y = x * cz - y * sz, x * sz + y * cz
        scaled = Vec3(x * self.scale.x, y * self.scale.y, z * self.scale.z)
        return self.position + scaled

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "primitive": self.primitive,
            "position": self.position.to_dict(),
            "rotation": self.rotation.to_dict(),
            "scale": self.scale.to_dict(),
            "profile": [{"z_cm": p.z_cm, "diameter_cm": p.diameter_cm, **({"width_cm": p.width_cm} if p.width_cm is not None else {}), **({"depth_cm": p.depth_cm} if p.depth_cm is not None else {})} for p in self.profile],
            "start_stitches": self.start_stitches,
            "material": self.material,
            "symmetry_group": self.symmetry_group,
            "required": self.required,
            "metadata": self.metadata,
            "connections": {k: v.to_dict() for k, v in self.connections.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeNode":
        node = cls(
            id=str(data["id"]),
            name=str(data["name"]),
            kind=str(data.get("kind", "piece")),
            primitive=str(data.get("primitive", "custom")),
            position=Vec3.from_dict(data.get("position", {})),
            rotation=Euler.from_dict(data.get("rotation", {})),
            scale=Vec3.from_dict(data.get("scale", {"x": 1, "y": 1, "z": 1})),
            profile=[ProfilePoint(float(p["z_cm"]), float(p["diameter_cm"]), float(p["width_cm"]) if p.get("width_cm") is not None else None, float(p["depth_cm"]) if p.get("depth_cm") is not None else None) for p in data.get("profile", [])],
            start_stitches=int(data.get("start_stitches", 6)),
            material=str(data.get("material", "yarn")),
            symmetry_group=data.get("symmetry_group"),
            required=bool(data.get("required", True)),
            metadata=dict(data.get("metadata", {})),
        )
        raw_connections = data.get("connections", {})
        values = raw_connections.values() if isinstance(raw_connections, dict) else raw_connections
        for cp in values:
            node.add_connection(ConnectionPoint.from_dict(cp))
        return node


@dataclass(frozen=True)
class ShapeEdge:
    id: str
    parent: str
    parent_point: str
    child: str
    child_point: str
    joint: str = "sew"
    seam_cm: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent": self.parent,
            "parent_point": self.parent_point,
            "child": self.child,
            "child_point": self.child_point,
            "joint": self.joint,
            "seam_cm": self.seam_cm,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeEdge":
        return cls(
            id=str(data["id"]),
            parent=str(data["parent"]),
            parent_point=str(data["parent_point"]),
            child=str(data["child"]),
            child_point=str(data["child_point"]),
            joint=str(data.get("joint", "sew")),
            seam_cm=float(data.get("seam_cm", 0)),
            notes=str(data.get("notes", "")),
        )


@dataclass
class GraphValidation:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class GraphPatternProject:
    name: str
    graph: "ShapeGraph"
    parts: Dict[str, PatternProject]
    checks: List[str]
    warnings: List[str]
    assembly: List[str]

    @property
    def pattern(self) -> str:
        chunks = [f"PROJECT — {self.name}", ""]
        for node_id, project in self.parts.items():
            chunks.append(f"### {self.graph.nodes[node_id].name}")
            chunks.append(project.pattern)
            chunks.append("")
        chunks.append("ASSEMBLY")
        chunks.extend(self.assembly)
        return "\n".join(chunks)


@dataclass
class ShapeGraph:
    name: str
    nodes: Dict[str, ShapeNode] = field(default_factory=dict)
    edges: Dict[str, ShapeEdge] = field(default_factory=dict)
    metadata: Dict[str, object] = field(default_factory=dict)

    def add_node(self, node: ShapeNode) -> "ShapeGraph":
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.id}")
        self.nodes[node.id] = node
        return self

    def add_edge(self, edge: ShapeEdge) -> "ShapeGraph":
        if edge.id in self.edges:
            raise ValueError(f"Duplicate edge id: {edge.id}")
        if edge.parent not in self.nodes or edge.child not in self.nodes:
            raise ValueError(f"Edge {edge.id} references an unknown node")
        self.edges[edge.id] = edge
        return self

    def connect(
        self,
        edge_id: str,
        parent: str,
        parent_point: str,
        child: str,
        child_point: str,
        joint: str = "sew",
        seam_cm: float = 0.0,
        notes: str = "",
    ) -> "ShapeGraph":
        return self.add_edge(ShapeEdge(edge_id, parent, parent_point, child, child_point, joint, seam_cm, notes))

    def children(self, node_id: str) -> List[str]:
        return [e.child for e in self.edges.values() if e.parent == node_id]

    def parents(self, node_id: str) -> List[str]:
        return [e.parent for e in self.edges.values() if e.child == node_id]

    def roots(self) -> List[str]:
        child_ids = {e.child for e in self.edges.values()}
        return [node_id for node_id in self.nodes if node_id not in child_ids]

    def validate(self, connection_tolerance_cm: float = 1.5) -> GraphValidation:
        result = GraphValidation()
        if not self.nodes:
            result.errors.append("Shape Graph vuoto.")
            return result

        for node_id, node in self.nodes.items():
            if not node.name.strip():
                result.errors.append(f"Nodo {node_id}: nome vuoto.")
            if node.start_stitches < 3:
                result.errors.append(f"Nodo {node_id}: start_stitches deve essere >= 3.")
            for point_name, point in node.connections.items():
                if point.radius_cm < 0:
                    result.errors.append(f"Nodo {node_id}.{point_name}: raggio negativo.")

        if len(self.roots()) == 0:
            result.errors.append("Il grafo non ha una radice: possibile ciclo totale.")

        # Connectivity / references / rough joint fit.
        for edge_id, edge in self.edges.items():
            if edge.parent not in self.nodes or edge.child not in self.nodes:
                result.errors.append(f"Arco {edge_id}: nodo inesistente.")
                continue
            parent = self.nodes[edge.parent]
            child = self.nodes[edge.child]
            if edge.parent_point not in parent.connections:
                result.errors.append(f"Arco {edge_id}: punto {edge.parent}.{edge.parent_point} inesistente.")
                continue
            if edge.child_point not in child.connections:
                result.errors.append(f"Arco {edge_id}: punto {edge.child}.{edge.child_point} inesistente.")
                continue
            p = parent.connections[edge.parent_point]
            c = child.connections[edge.child_point]
            if p.radius_cm and c.radius_cm:
                mismatch = abs(p.radius_cm - c.radius_cm)
                if mismatch > connection_tolerance_cm:
                    result.warnings.append(
                        f"Arco {edge_id}: diametri di giunzione diversi di {mismatch:.1f} cm."
                    )

        # Cycle detection with DFS.
        state: Dict[str, int] = {n: 0 for n in self.nodes}
        def visit(n: str) -> None:
            if state[n] == 1:
                result.errors.append(f"Ciclo rilevato nel grafo a partire da {n}.")
                return
            if state[n] == 2:
                return
            state[n] = 1
            for child in self.children(n):
                visit(child)
            state[n] = 2
        for root in self.roots():
            visit(root)
        # A graph with no roots is already reported above, but we still traverse
        # every node so cycles are explicitly diagnosed.
        for node_id in self.nodes:
            if state[node_id] == 0:
                visit(node_id)

        # Symmetry sanity check: mirrored members should exist in pairs.
        groups: Dict[str, List[ShapeNode]] = {}
        for node in self.nodes.values():
            if node.symmetry_group:
                groups.setdefault(node.symmetry_group, []).append(node)
        for group, members in groups.items():
            if len(members) < 2:
                result.warnings.append(f"Simmetria {group}: un solo elemento dichiarato.")
            elif len(members) % 2:
                result.warnings.append(f"Simmetria {group}: {len(members)} elementi, gruppo non bilanciato.")

        return result

    def compile(self, gauge: Gauge, include_details: bool = False) -> GraphPatternProject:
        validation = self.validate()
        checks = ["OK: Shape Graph valido." if validation.ok else "ERRORE: Shape Graph non valido."]
        checks.extend(validation.errors)
        checks.extend(f"ATTENZIONE: {w}" for w in validation.warnings)
        parts: Dict[str, PatternProject] = {}
        warnings = list(validation.warnings)

        for node_id, node in self.nodes.items():
            if not node.has_pattern_geometry:
                if include_details and node.kind == "detail":
                    checks.append(f"INFO: dettaglio {node.name} senza corpo geometrico, lasciato come componente.")
                continue
            try:
                sample_step = max(gauge.round_height_cm, 0.2)
                sampled_profile = interpolate_profile(node.profile, sample_step)
                parts[node_id] = compile_project(node.name, sampled_profile, gauge, node.start_stitches)
                # Add construction metadata to the generated pattern without
                # changing the deterministic stitch compiler.
                technique = str(node.metadata.get("technique", "spirale_sc"))
                construction = str(node.metadata.get("construction", ""))
                parts[node_id].pattern = (
                    parts[node_id].pattern.replace(
                        f"PATTERN — {node.name}",
                        f"PATTERN — {node.name}\nTecnica: {technique}\nCostruzione: {construction or 'forma lavorata in spirale' }",
                        1
                    )
                )
                warnings.extend(f"{node.name}: {w}" for w in parts[node_id].warnings)
            except (ValueError, IndexError) as exc:
                checks.append(f"ERRORE: compilazione {node.name}: {exc}")

        assembly = self.assembly_instructions()
        checks.append(f"OK: {len(parts)} pezzi con pattern compilabile su {len(self.nodes)} nodi.")
        checks.append(f"OK: {len(self.edges)} giunzioni definite.")
        return GraphPatternProject(self.name, self, parts, checks, warnings, assembly)

    def assembly_instructions(self) -> List[str]:
        lines: List[str] = []
        for edge in self.edges.values():
            parent = self.nodes[edge.parent]
            child = self.nodes[edge.child]
            pose = child.rotation
            pose_note = ""
            if any(abs(v) > 0.5 for v in (pose.rx, pose.ry, pose.rz)):
                pose_note = f" Orientamento locale: pitch {pose.rx:.0f}°, yaw {pose.ry:.0f}°, roll {pose.rz:.0f}°."
            lines.append(
                f"- Unisci {child.name} ({edge.child_point}) a {parent.name} ({edge.parent_point}) "
                f"con {edge.joint}" + (f"; cucitura ~{edge.seam_cm:.1f} cm" if edge.seam_cm else "") + "." + pose_note
            )
            if edge.notes:
                lines.append(f"  Nota: {edge.notes}")
        if not lines:
            lines.append("- Nessuna giunzione definita.")
        return lines

    def to_dict(self) -> dict:
        return {
            "version": "0.2",
            "name": self.name,
            "metadata": self.metadata,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeGraph":
        graph = cls(str(data.get("name", "Shape Graph")), metadata=dict(data.get("metadata", {})))
        for node in data.get("nodes", []):
            graph.add_node(ShapeNode.from_dict(node))
        for edge in data.get("edges", []):
            graph.add_edge(ShapeEdge.from_dict(edge))
        return graph

    @classmethod
    def from_json(cls, text: str) -> "ShapeGraph":
        return cls.from_dict(json.loads(text))


def _part(
    id: str,
    name: str,
    profile: Sequence[ProfilePoint],
    position: Vec3,
    primitive: str,
    symmetry_group: Optional[str] = None,
    start_stitches: int = 6,
    kind: str = "piece",
) -> ShapeNode:
    return ShapeNode(
        id=id,
        name=name,
        primitive=primitive,
        position=position,
        profile=list(profile),
        symmetry_group=symmetry_group,
        start_stitches=start_stitches,
        kind=kind,
    )


def dinosaur_shape_graph(scale: float = 1.0) -> ShapeGraph:
    """Return a concrete starter graph matching the uploaded dinosaur test case.

    Coordinates are approximate semantic anchors, not measurements extracted from
    pixels. The graph is intentionally editable so a future vision model can replace
    these values with estimated dimensions and poses.
    """
    s = float(scale)
    g = ShapeGraph(
        "Dinosauro amigurumi",
        metadata={"source": "vision_starter", "units": "cm", "confidence": 0.65},
    )

    body = _part("body", "Corpo", egg_profile(8.5*s, 10.5*s, .32*s), Vec3(0, 0, 5.2*s), "egg")
    body.add_connection(ConnectionPoint("neck", Vec3(0, 0, 5.2*s), 2.2*s, "join"))
    body.add_connection(ConnectionPoint("tail", Vec3(-4.0*s, 0, 3.2*s), 1.8*s, "join"))
    body.add_connection(ConnectionPoint("leg_fl", Vec3(-2.7*s, 1.9*s, 1.8*s), 1.2*s, "join"))
    body.add_connection(ConnectionPoint("leg_fr", Vec3(2.7*s, 1.9*s, 1.8*s), 1.2*s, "join"))
    body.add_connection(ConnectionPoint("leg_bl", Vec3(-2.7*s, -1.9*s, 1.8*s), 1.2*s, "join"))
    body.add_connection(ConnectionPoint("leg_br", Vec3(2.7*s, -1.9*s, 1.8*s), 1.2*s, "join"))
    g.add_node(body)

    neck = _part("neck", "Collo", tapered_profile(3.9*s, 2.8*s, 7.5*s, .32*s), Vec3(0, 0, 10.2*s), "tapered")
    neck.add_connection(ConnectionPoint("base", Vec3(0, 0, 0), 2.0*s, "join"))
    neck.add_connection(ConnectionPoint("head", Vec3(0, 0, 7.5*s), 1.8*s, "join"))
    g.add_node(neck)

    head = _part("head", "Testa", egg_profile(6.2*s, 5.0*s, .32*s), Vec3(0, 0, 17.7*s), "egg")
    head.add_connection(ConnectionPoint("neck", Vec3(0, 0, 0), 1.8*s, "join"))
    head.add_connection(ConnectionPoint("muzzle", Vec3(0, 0, 4.4*s), 1.4*s, "join"))
    head.add_connection(ConnectionPoint("eye_l", Vec3(-2.2*s, 1.9*s, 2.6*s), .2*s, "detail"))
    head.add_connection(ConnectionPoint("eye_r", Vec3(2.2*s, 1.9*s, 2.6*s), .2*s, "detail"))
    g.add_node(head)

    muzzle = _part("muzzle", "Muso", sphere_profile(3.2*s, 2.7*s, .30*s), Vec3(0, 0, 21.4*s), "sphere")
    muzzle.add_connection(ConnectionPoint("head", Vec3(0, 0, 0), 1.4*s, "join"))
    g.add_node(muzzle)

    tail = _part("tail", "Coda", tapered_profile(3.6*s, .8*s, 10.5*s, .32*s), Vec3(-4.0*s, 0, 3.2*s), "tapered")
    tail.add_connection(ConnectionPoint("base", Vec3(0, 0, 0), 1.8*s, "join"))
    g.add_node(tail)

    leg_positions = {
        "leg_fl": ("Zampa anteriore sinistra", Vec3(-2.7*s, 1.9*s, 0), "legs_front"),
        "leg_fr": ("Zampa anteriore destra", Vec3(2.7*s, 1.9*s, 0), "legs_front"),
        "leg_bl": ("Zampa posteriore sinistra", Vec3(-2.7*s, -1.9*s, 0), "legs_back"),
        "leg_br": ("Zampa posteriore destra", Vec3(2.7*s, -1.9*s, 0), "legs_back"),
    }
    for leg_id, (name, pos, sym) in leg_positions.items():
        leg = _part(leg_id, name, tapered_profile(2.8*s, 2.2*s, 5.0*s, .32*s), pos, "tapered", sym)
        leg.add_connection(ConnectionPoint("base", Vec3(0, 0, 5.0*s), 1.2*s, "join"))
        g.add_node(leg)

    # Decorative dorsal plates are represented as detail components. They don't
    # get a round-by-round pattern yet; their positions become sewing markers.
    for i, z in enumerate([7.5, 9.0, 10.5, 12.0, 13.5, 15.0, 16.5], start=1):
        plate = _part(
            f"plate_{i}", f"Placca dorsale {i}",
            tapered_profile(2.4*s, .4*s, 2.2*s, .35*s),
            Vec3(-.6*s, 0, z*s), "plate", kind="detail",
        )
        plate.metadata["side"] = "dorsal"
        plate.metadata["index"] = i
        plate.add_connection(ConnectionPoint("tip", Vec3(0, 0, 2.2*s), .4*s, "detail"))
        g.add_node(plate)

    g.connect("e_neck", "body", "neck", "neck", "base", "sew", 3.5*s, "Allineare l'asse del collo al centro del dorso.")
    g.connect("e_head", "neck", "head", "head", "neck", "sew", 3.0*s, "Imbottire prima della chiusura finale.")
    g.connect("e_muzzle", "head", "muzzle", "muzzle", "head", "sew", 2.5*s, "Centrare sul fronte della testa.")
    g.connect("e_tail", "body", "tail", "tail", "base", "sew", 2.8*s, "Inclinare leggermente verso il basso.")
    for leg_id, body_point in [("leg_fl", "leg_fl"), ("leg_fr", "leg_fr"), ("leg_bl", "leg_bl"), ("leg_br", "leg_br")]:
        g.connect(f"e_{leg_id}", "body", body_point, leg_id, "base", "sew", 2.0*s)
    for i in range(1, 8):
        g.connect(
            f"e_plate_{i}", "body", "neck", f"plate_{i}", "tip", "sew", 0,
            f"Posizionare la placca {i} lungo la linea dorsale; usare il disegno come guida.",
        )

    return g
