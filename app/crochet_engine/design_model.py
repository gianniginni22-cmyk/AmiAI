"""Amigurumi Design Model: semantic concept + technical multi-view template.

Pipeline:
    source image/text -> semantic design model -> optional amigurumi concept image
    -> Shape Graph / geometry engine

The design model is intentionally structured and deterministic-friendly. The
concept image is a visual aid, not ground truth.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

DESIGN_VIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "orientation": {"type": "string"},
        "visible_parts": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["orientation", "visible_parts", "notes"],
    "additionalProperties": False,
}

DESIGN_PART_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "role": {"type": "string"},
        "count": {"type": "integer"},
        "parent_id": {"type": ["string", "null"]},
        "symmetry_group": {"type": ["string", "null"]},
        "estimated_height_cm": {"type": ["number", "null"]},
        "estimated_width_cm": {"type": ["number", "null"]},
        "estimated_depth_cm": {"type": ["number", "null"]},
        "center_front": {"type": ["object", "null"], "properties": {"x": {"type": "number"}, "y": {"type": "number"}}, "required": ["x", "y"], "additionalProperties": False},
        "center_side": {"type": ["object", "null"], "properties": {"x": {"type": "number"}, "y": {"type": "number"}}, "required": ["x", "y"], "additionalProperties": False},
        "depth_hint": {"type": "string"},
        "confidence": {"type": "number"},
        "construction": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["id", "label", "role", "count", "parent_id", "symmetry_group", "estimated_height_cm", "estimated_width_cm", "estimated_depth_cm", "center_front", "center_side", "depth_hint", "confidence", "construction", "notes"],
    "additionalProperties": False,
}

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "semantic_summary": {"type": "string"},
        "pose": {"type": "string"},
        "style_target": {"type": "string"},
        "overall_confidence": {"type": "number"},
        "distinctive_features": {"type": "array", "items": {"type": "string"}},
        "views": {"type": "array", "items": DESIGN_VIEW_SCHEMA},
        "parts": {"type": "array", "items": DESIGN_PART_SCHEMA},
        "global_dimensions": {"type": "object", "properties": {"height_cm": {"type": "number"}, "width_cm": {"type": "number"}, "depth_cm": {"type": "number"}}, "required": ["height_cm", "width_cm", "depth_cm"], "additionalProperties": False},
        "symmetry_notes": {"type": "string"},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "concept_prompt": {"type": "string"},
    },
    "required": ["subject", "semantic_summary", "pose", "style_target", "overall_confidence", "distinctive_features", "views", "parts", "global_dimensions", "symmetry_notes", "uncertainties", "concept_prompt"],
    "additionalProperties": False,
}

DESIGN_SYSTEM_PROMPT = """Sei il DESIGN PLANNER di Amigurumi AI.

Obiettivo: trasformare immagine e/o descrizione in una rappresentazione tecnica intermedia chiamata AMIGURUMI DESIGN MODEL. Questa rappresentazione deve chiarire CHE COS'È il soggetto, COME DEVE APPARIRE come amigurumi e COME È SCOMPONIBILE, prima di costruire il pattern.

Regole:
- Identifica il soggetto usando semantica + dettagli distintivi, non la sola silhouette.
- Non confondere soggetti con silhouette simili.
- Non inventare parti nascoste: usa confidence bassa e uncertainties quando non sono osservabili.
- Le quattro viste sono una ricostruzione concettuale tecnica, non una scansione 3D reale.
- Le coordinate center_front/center_side sono normalizzate rispetto all'immagine: x e y tra 0 e 1 quando osservabili.
- Le dimensioni sono stime relative al target fornito.
- count indica quante copie del pezzo esistono.
- symmetry_group identifica elementi ripetuti simmetricamente.
- construction descrive il modo probabile di realizzare il pezzo (es. corpo tubolare, sfera, disco, dettaglio ricamato), ma NON scrivere ancora il pattern.
- concept_prompt deve essere abbastanza preciso da permettere a un generatore di immagini di creare una versione amigurumi coerente col soggetto originale.
- L'immagine amigurumi generata in seguito è una visualizzazione di progetto, NON una ground truth e NON deve sostituire il modello strutturato.
"""


def build_design_prompt(description: str, height_cm: float, style: str, design: Dict[str, Any]) -> str:
    parts = []
    for p in design.get("parts", []):
        parts.append(f"- {p.get('label')} ({p.get('role')}), x{p.get('count', 1)}, simmetria={p.get('symmetry_group')}, costruzione={p.get('construction')}")
    features = ", ".join(design.get("distinctive_features", [])) or "nessuna caratteristica distintiva esplicita"
    return (
        f"Crea una rappresentazione fotografica/illustrativa di un amigurumi finito del soggetto '{design.get('subject', description or 'soggetto')}'. "
        f"Target altezza {height_cm} cm. Stile richiesto: {style}. "
        f"Mantieni identità, posa e caratteristiche distintive: {features}. "
        f"Sintesi semantica: {design.get('semantic_summary', '')}. "
        f"Parti strutturali: {'; '.join(parts)}. "
        "Aspetto chiaramente lavorato all'uncinetto, filato e imbottito, proporzioni coerenti, nessun testo, nessuna etichetta, sfondo neutro. "
        "Non trasformare il soggetto in un altro animale o oggetto solo perché la silhouette è simile."
    )


def fallback_design(description: str, height_cm: float, style: str, vision_parts: Optional[list] = None) -> Dict[str, Any]:
    vp = vision_parts or []
    subject = description.strip() or "soggetto dalla foto"
    parts = []
    for p in vp:
        parts.append({
            "id": p.get("id", "part"), "label": p.get("label", "parte"), "role": p.get("role", "other"),
            "count": 2 if p.get("symmetry_group") else 1, "parent_id": p.get("parent_id"),
            "symmetry_group": p.get("symmetry_group"), "estimated_height_cm": None, "estimated_width_cm": None,
            "estimated_depth_cm": None, "center_front": None, "center_side": None, "depth_hint": "non stimato",
            "confidence": float(p.get("confidence", .25)), "construction": "da definire", "notes": p.get("notes", "fallback")
        })
    if not parts:
        parts = [{"id":"body","label":"corpo/soggetto principale","role":"body","count":1,"parent_id":None,"symmetry_group":None,"estimated_height_cm":height_cm,"estimated_width_cm":height_cm*.75,"estimated_depth_cm":height_cm*.55,"center_front":{"x":.5,"y":.5},"center_side":{"x":.5,"y":.5},"depth_hint":"non stimato","confidence":.2,"construction":"forma principale","notes":"fallback locale"}]
    return {
        "subject": subject, "semantic_summary": "Modello locale provvisorio; non è un'analisi visuale AI.", "pose": "non determinata",
        "style_target": style, "overall_confidence": .2, "distinctive_features": [],
        "views": [{"orientation": x, "visible_parts": [p["id"] for p in parts], "notes": "ricostruzione provvisoria"} for x in ["frontale","posteriore","sinistra","destra"]],
        "parts": parts, "global_dimensions": {"height_cm":height_cm,"width_cm":round(height_cm*.75,2),"depth_cm":round(height_cm*.55,2)},
        "symmetry_notes": "non determinata", "uncertainties": ["Analisi visuale AI non disponibile."],
        "concept_prompt": f"Amigurumi del soggetto {subject}, stile {style}, altezza {height_cm} cm."
    }


def generate_concept_image(client, design: Dict[str, Any], description: str, height_cm: float, style: str) -> Optional[str]:
    """Return a data URL containing the generated concept image, or None.

    The image is deliberately generated from the structured design model rather
    than used as the source of truth. This keeps semantics in structured data.
    """
    prompt = build_design_prompt(description, height_cm, style, design)
    model = __import__("os").getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    response = client.images.generate(model=model, prompt=prompt, size="1024x1024", quality="medium")
    item = response.data[0]
    b64 = getattr(item, "b64_json", None)
    if not b64:
        return None
    return f"data:image/png;base64,{b64}"
