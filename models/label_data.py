"""Manual labeling data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LabeledRegion:
    document_name: str
    page_index: int
    label: str
    x: int
    y: int
    width: int
    height: int
