"""Template management service for export field selections."""

from __future__ import annotations

import json
from pathlib import Path


class TemplateManager:
    """Save and load user column selection templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path("templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def save_template(self, template_name: str, columns: list[dict]) -> Path:
        payload = {
            "template_name": template_name,
            "columns": columns,
        }
        target = self.template_dir / f"{template_name}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def load_template(self, template_name: str) -> dict:
        target = self.template_dir / f"{template_name}.json"
        return json.loads(target.read_text(encoding="utf-8"))

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.template_dir.glob("*.json"))
