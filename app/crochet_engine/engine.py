"""
Crochet Geometry Engine
-----------------------
Parametric engine for turning a radial 3D profile into a count-valid
amigurumi round-by-round crochet pattern.

The engine intentionally separates:
1. geometry (target width by height),
2. gauge conversion (cm -> stitches/rounds),
3. discrete stitch-count planning,
4. increase/decrease distribution,
5. pattern compilation,
6. validation.

It does not claim that geometry alone guarantees a physically perfect
crocheted object: yarn behavior, stuffing pressure, tension, and joining
parts still require a swatch/prototype.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Sequence
import math


@dataclass(frozen=True)
class Gauge:
    stitches_per_10cm: float = 30.0
    rounds_per_10cm: float = 32.0

    @property
    def stitch_width_cm(self) -> float:
        return 10.0 / self.stitches_per_10cm

    @property
    def round_height_cm(self) -> float:
        return 10.0 / self.rounds_per_10cm

    def stitches_for_circumference(self, circumference_cm: float) -> float:
        return circumference_cm / self.stitch_width_cm

    def rounds_for_height(self, height_cm: float) -> int:
        return max(1, round(height_cm / self.round_height_cm))


@dataclass(frozen=True)
class ProfilePoint:
    z_cm: float
    diameter_cm: float
    # Optional anisotropic cross-section. diameter_cm remains the effective
    # diameter used by the legacy radial compiler, while width/depth preserve
    # the actual design intent for validation/export.
    width_cm: float | None = None
    depth_cm: float | None = None


@dataclass
class RoundPlan:
    round_no: int
    before: int
    after: int
    increases: int = 0
    decreases: int = 0
    plain: int = 0
    operations: List[str] = field(default_factory=list)
    stitch_count_ok: bool = True


@dataclass
class ShapePlan:
    name: str
    height_cm: float
    profile: List[ProfilePoint]
    rounds: List[RoundPlan]
    max_stitches: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class PatternProject:
    name: str
    gauge: Gauge
    shape: ShapePlan
    pattern: str
    checks: List[str]
    warnings: List[str]


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def interpolate_profile(points: Sequence[ProfilePoint], step_cm: float) -> List[ProfilePoint]:
    """Resample a diameter profile at a regular vertical interval."""
    if not points:
        raise ValueError("Profile cannot be empty.")
    pts = sorted(points, key=lambda p: p.z_cm)
    if pts[0].z_cm != 0:
        raise ValueError("Profile must start at z=0.")
    if any(p.diameter_cm <= 0 for p in pts):
        raise ValueError("All diameters must be positive.")
    if any(b.z_cm <= a.z_cm for a, b in zip(pts, pts[1:])):
        raise ValueError("Profile z values must be strictly increasing.")
    height = pts[-1].z_cm
    out = []
    z = 0.0
    i = 0
    while z < height - 1e-9:
        while i < len(pts)-2 and z > pts[i+1].z_cm:
            i += 1
        a, b = pts[i], pts[i+1]
        t = (z-a.z_cm)/(b.z_cm-a.z_cm)
        out.append(ProfilePoint(round(z, 4), lerp(a.diameter_cm, b.diameter_cm, t)))
        z += step_cm
    out.append(ProfilePoint(height, pts[-1].diameter_cm))
    return out


def _even_positions(total_slots: int, count: int) -> List[int]:
    """Choose count operation slots spread around a round."""
    if count <= 0:
        return []
    if count > total_slots:
        raise ValueError("Cannot place more special operations than operation slots.")
    positions = []
    used = set()
    for k in range(count):
        p = int(math.floor((k + 0.5) * total_slots / count)) % total_slots
        while p in used:
            p = (p + 1) % total_slots
        used.add(p)
        positions.append(p)
    return sorted(positions)


def distribute_delta(before: int, after: int, max_delta: int = 6) -> RoundPlan:
    """
    Create a count-valid round from `before` to `after`.

    For increases, there are `before` base-stitch slots: plain or increase.
    For decreases, there are `before - decreases` operation slots because each
    decrease consumes two base stitches and each plain stitch consumes one.
    """
    delta = after - before
    if delta > max_delta or delta < -max_delta:
        raise ValueError(f"Delta {delta} exceeds max_delta={max_delta}.")

    if delta >= 0:
        inc = delta
        dec = 0
        plain = before - inc
        if plain < 0:
            raise ValueError("Too many increases for source stitch count.")
        ops = ["mb"] * before
        for p in _even_positions(before, inc):
            ops[p] = "aum"
    else:
        dec = -delta
        inc = 0
        plain = before - 2 * dec
        if plain < 0:
            raise ValueError("Too many decreases for source stitch count.")
        operation_slots = plain + dec
        ops = ["mb"] * operation_slots
        for p in _even_positions(operation_slots, dec):
            ops[p] = "dim"

    produced = sum(2 if x == "aum" else 1 for x in ops)
    return RoundPlan(
        round_no=0, before=before, after=after,
        increases=inc, decreases=dec, plain=plain,
        operations=ops, stitch_count_ok=(produced == after)
    )


def compress_operations(ops: Sequence[str]) -> str:
    """Compress a linear operation sequence into human-readable pattern text."""
    if not ops:
        return ""
    # If all same, emit simple form.
    tokens = []
    i = 0
    while i < len(ops):
        j = i + 1
        while j < len(ops) and ops[j] == ops[i]:
            j += 1
        n = j - i
        word = {"mb": "mb", "aum": "aum", "dim": "dim"}[ops[i]]
        tokens.append(f"{n} {word}" if n > 1 else word)
        i = j
    return ", ".join(tokens)


def round_instruction(r: RoundPlan) -> str:
    if not r.stitch_count_ok:
        return f"ERRORE DI CONTEGGIO: {r.before} -> {r.after}"
    if r.increases:
        # Prefer a compact repeated block when mathematically exact.
        n = r.increases
        plain = r.plain
        if n > 0 and plain % n == 0:
            p = plain // n
            if p == 0:
                return f"(aum) × {n}"
            return f"({p} mb, aum) × {n}"
        return compress_operations(r.operations)
    if r.decreases:
        n = r.decreases
        plain = r.plain
        if n > 0 and plain % n == 0:
            p = plain // n
            if p == 0:
                return f"(dim) × {n}"
            return f"({p} mb, dim) × {n}"
        return compress_operations(r.operations)
    return f"{r.before} mb"


def diameter_to_stitches(diameter_cm: float, gauge: Gauge) -> int:
    circumference = math.pi * diameter_cm
    return max(3, round(gauge.stitches_for_circumference(circumference)))


def profile_to_counts(profile: Sequence[ProfilePoint], gauge: Gauge,
                      start_stitches: int = 6, max_delta: int = 6) -> List[int]:
    raw = [diameter_to_stitches(p.diameter_cm, gauge) for p in profile]
    counts = [max(start_stitches, raw[0])]
    for target in raw[1:]:
        prev = counts[-1]
        # Move toward target at a maximum of max_delta per round.
        if target > prev:
            nxt = min(target, prev + max_delta)
        elif target < prev:
            nxt = max(target, prev - max_delta)
        else:
            nxt = prev
        # Ensure decreases are possible.
        if nxt < math.ceil(prev / 2):
            nxt = math.ceil(prev / 2)
        counts.append(nxt)
    return counts


def plan_profile(name: str, profile: Sequence[ProfilePoint], gauge: Gauge,
                 start_stitches: int = 6, max_delta: int = 6) -> ShapePlan:
    sampled = list(profile)
    counts = profile_to_counts(sampled, gauge, start_stitches, max_delta)
    rounds = []
    warnings = []
    for i, (before, after) in enumerate(zip(counts, counts[1:]), start=1):
        r = distribute_delta(before, after, max_delta)
        r.round_no = i + 1
        rounds.append(r)
        if not r.stitch_count_ok:
            warnings.append(f"Giro {r.round_no}: conteggio non valido.")
    if max(counts) >= 60:
        warnings.append("Diametro grande: valuta un anello iniziale da 8 o più maglie.")
    return ShapePlan(
        name=name,
        height_cm=sampled[-1].z_cm,
        profile=sampled,
        rounds=rounds,
        max_stitches=max(counts),
        warnings=warnings
    )


def sphere_profile(diameter_cm: float, height_cm: float, step_cm: float = 0.31) -> List[ProfilePoint]:
    """Sphere-like diameter profile, widest at mid-height."""
    out = []
    z = 0.0
    while z < height_cm:
        x = (z / height_cm) * 2 - 1
        d = diameter_cm * math.sqrt(max(0.0, 1.0 - x*x))
        d = max(diameter_cm * 0.18, d)
        out.append(ProfilePoint(z, d))
        z += step_cm
    out.append(ProfilePoint(height_cm, diameter_cm * 0.18))
    return out


def egg_profile(width_cm: float, height_cm: float, step_cm: float = 0.31) -> List[ProfilePoint]:
    """Egg/oval profile: widest below the equator."""
    out = []
    z = 0.0
    while z < height_cm:
        t = z / height_cm
        # Smooth bell/egg curve, slightly fuller in lower half.
        base = math.sin(math.pi * (0.12 + 0.88*t))
        bias = 1.0 + 0.22*(1-t)
        d = max(width_cm*0.18, width_cm*base*bias)
        out.append(ProfilePoint(z, d))
        z += step_cm
    out.append(ProfilePoint(height_cm, width_cm*0.18))
    return out


def tapered_profile(base_diameter_cm: float, tip_diameter_cm: float,
                    height_cm: float, step_cm: float = 0.31) -> List[ProfilePoint]:
    out=[]
    z=0.0
    while z < height_cm:
        t=z/height_cm
        # Smooth taper.
        s=smoothstep(t)
        d=lerp(base_diameter_cm, tip_diameter_cm, s)
        out.append(ProfilePoint(z,d))
        z+=step_cm
    out.append(ProfilePoint(height_cm, tip_diameter_cm))
    return out


def compile_project(name: str, profile: Sequence[ProfilePoint], gauge: Gauge,
                    start_stitches: int = 6) -> PatternProject:
    shape = plan_profile(name, profile, gauge, start_stitches=start_stitches)
    lines = [
        f"PATTERN — {name}",
        f"Altezza target: {shape.height_cm:.1f} cm",
        f"Gauge: {gauge.stitches_per_10cm:.1f} maglie/10 cm; {gauge.rounds_per_10cm:.1f} giri/10 cm",
        f"Massimo: {shape.max_stitches} maglie",
        "",
        "MATERIALI: filato adatto al gauge, uncinetto coerente con il campione, imbottitura, ago da lana e marcapunti.",
        "ABBREVIAZIONI: mb = maglia bassa; aum = aumento; dim = diminuzione invisibile; AM = anello magico.",
        "ISTRUZIONI: lavorare in spirale continua salvo diversa indicazione; usare un marcapunti all'inizio del giro.",
        "",
    ]
    # Round 1 is the starting ring.
    lines.append(f"Giro 1: {start_stitches} mb nell'AM ({start_stitches})")
    for r in shape.rounds:
        lines.append(f"Giro {r.round_no}: {round_instruction(r)} ({r.after})")
    lines += [
        "",
        "FINITURA DEL PEZZO:",
        "Tagliare il filo lasciando una coda sufficiente per la cucitura, fermare e nascondere il filo.",
        "Imbottire progressivamente mentre la forma si chiude; non comprimere eccessivamente per non deformare la sagoma.",
        "Se il pezzo è indicato come componente da assemblare, lasciare una coda di cucitura invece di nasconderla completamente.",
        "",
        "CONTROLLO:",
        "Ogni giro deve terminare con il numero di maglie tra parentesi.",
        "Le diminuzioni sono intese come diminuzioni invisibili per amigurumi.",
        "Fare un campione: la tensione reale può cambiare diametro e altezza.",
    ]
    checks = validate_project(shape)
    return PatternProject(name, gauge, shape, "\n".join(lines), checks, shape.warnings)


def validate_project(shape: ShapePlan) -> List[str]:
    checks = []
    ok = True
    prev = None
    for r in shape.rounds:
        expected = r.before + r.increases - r.decreases
        if expected != r.after or not r.stitch_count_ok:
            ok = False
            checks.append(f"ERRORE: giro {r.round_no}: {r.before} + {r.increases} - {r.decreases} != {r.after}")
        if r.decreases and r.plain < 0:
            ok = False
            checks.append(f"ERRORE: troppe diminuzioni al giro {r.round_no}.")
        prev = r.after
    if ok:
        checks.append("OK: conteggi di tutti i giri coerenti.")
    if shape.max_stitches > 0:
        checks.append(f"OK: massimo {shape.max_stitches} maglie.")
    checks.append("NOTA: il validatore numerico non sostituisce un campione fisico.")
    return checks
