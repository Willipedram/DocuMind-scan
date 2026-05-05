"""Domain model placeholders for document data."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Document:
    """Represents a document queued for OCR processing."""

    source_path: Path
    language_hint: str = "fa"
