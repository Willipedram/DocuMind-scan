"""Data models for OCR output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OCRBox:
    bbox: list[tuple[int, int]]
    text: str
    confidence: float


@dataclass(slots=True)
class OCRPageResult:
    page_index: int
    full_text: str
    boxes: list[OCRBox]
