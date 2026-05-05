"""Detected field data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DetectedField:
    field_name: str
    value: str
    position: tuple[int, int, int, int]
