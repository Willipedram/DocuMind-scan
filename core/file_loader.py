"""File loading and document-to-image conversion utilities."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
from PIL import Image


class FileLoaderError(RuntimeError):
    """Raised when a document cannot be loaded for preview."""


class FileLoader:
    """Load image/PDF files and convert them into PIL image pages."""

    SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    SUPPORTED_PDF_EXTENSIONS = {".pdf"}

    def load_pages(self, file_path: Path) -> list[Image.Image]:
        suffix = file_path.suffix.lower()
        if suffix in self.SUPPORTED_PDF_EXTENSIONS:
            return self._load_pdf(file_path)
        if suffix in self.SUPPORTED_IMAGE_EXTENSIONS:
            return [self._load_image(file_path)]
        raise FileLoaderError(f"Unsupported file type: {file_path.suffix}")

    def _load_pdf(self, file_path: Path) -> list[Image.Image]:
        poppler_path = os.getenv("POPPLER_PATH")
        try:
            pages = convert_from_path(str(file_path), poppler_path=poppler_path or None)
            if not pages:
                raise FileLoaderError("PDF contains no pages")
            return pages
        except PDFInfoNotInstalledError as exc:
            raise FileLoaderError(
                "Unable to load PDF: Poppler is not installed or not configured. "
                "Install poppler and set POPPLER_PATH if needed."
            ) from exc
        except (PDFPageCountError, PDFSyntaxError) as exc:
            raise FileLoaderError(f"Unable to load PDF: invalid/corrupted PDF ({file_path.name})") from exc
        except Exception as exc:  # noqa: BLE001
            raise FileLoaderError(f"Unable to load PDF: {file_path.name}") from exc

    def _load_image(self, file_path: Path) -> Image.Image:
        cv_image = cv2.imread(str(file_path), cv2.IMREAD_COLOR)
        if cv_image is None:
            raise FileLoaderError(f"Unable to read image file: {file_path.name}")
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
