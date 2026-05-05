"""Template management service for field layouts and auto-matching."""

from __future__ import annotations

import json
from pathlib import Path


class TemplateManager:
    """Save/load template JSON and detect similar document templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path("templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def save_template(self, template_name: str, columns: list[dict], document_type: str | None = None) -> Path:
        payload = {
            "template_name": template_name,
            "document_type": document_type or template_name,
            "columns": columns,
            "field_layout": [c.get("field_name", "") for c in columns],
        }
        target = self.template_dir / f"{template_name}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def load_template(self, template_name: str) -> dict:
        target = self.template_dir / f"{template_name}.json"
        return json.loads(target.read_text(encoding="utf-8"))

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.template_dir.glob("*.json"))

    def find_best_template(self, detected_field_names: list[str], threshold: float = 0.5) -> tuple[str | None, dict | None]:
        best_name = None
        best_payload = None
        best_score = 0.0

        detected_set = {name.strip() for name in detected_field_names if name.strip()}
        if not detected_set:
            return None, None

        for name in self.list_templates():
            payload = self.load_template(name)
            layout = payload.get("field_layout") or [c.get("field_name", "") for c in payload.get("columns", [])]
            layout_set = {n.strip() for n in layout if n.strip()}
            if not layout_set:
                continue
            intersection = len(detected_set.intersection(layout_set))
            union = len(detected_set.union(layout_set))
            score = (intersection / union) if union else 0.0
            if score > best_score:
                best_score = score
                best_name = name
                best_payload = payload

        if best_score >= threshold:
            return best_name, best_payload
        return None, None
