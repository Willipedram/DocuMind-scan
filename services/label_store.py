"""Persistence for manually labeled OCR regions."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from models.label_data import LabeledRegion


class LabelStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/labeled_regions.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[LabeledRegion]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [LabeledRegion(**item) for item in data]

    def save_all(self, items: list[LabeledRegion]) -> None:
        payload = [asdict(item) for item in items]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def append(self, item: LabeledRegion) -> None:
        items = self.load()
        items.append(item)
        self.save_all(items)
