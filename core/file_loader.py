"""File loading and document-to-image conversion utilities."""

from __future__ import annotations

import os
import sys
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

    def get_pdf_backend_diagnostics(self) -> str:
        """Return a short diagnostics string for PDF backend availability."""
        lines = [f"Python executable: {sys.executable}"]
        poppler_path = os.getenv("POPPLER_PATH")
        lines.append(f"POPPLER_PATH: {poppler_path or 'not set'}")
        try:
            import pypdfium2  # noqa: F401
            lines.append("pypdfium2: available")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"pypdfium2: unavailable ({exc})")
        return " | ".join(lines)

    def _load_pdf(self, file_path: Path) -> list[Image.Image]:
        poppler_path = os.getenv("POPPLER_PATH")
        try:
            pages = convert_from_path(str(file_path), poppler_path=poppler_path or None)
            if pages:
                return pages
        except PDFInfoNotInstalledError:
            pages, fallback_error = self._fallback_pdfium(file_path)
            if pages:
                return pages
            raise FileLoaderError(
                "Unable to load PDF: Poppler is not installed and PDFium fallback failed. "
                f"Details: {fallback_error or 'unknown error'}. "
                f"Diagnostics: {self.get_pdf_backend_diagnostics()}"
            )
        except (PDFPageCountError, PDFSyntaxError) as exc:
            raise FileLoaderError(f"Unable to load PDF: invalid/corrupted PDF ({file_path.name})") from exc
        except Exception as exc:  # noqa: BLE001
            raise FileLoaderError(f"Unable to load PDF: {file_path.name} ({exc})") from exc

        raise FileLoaderError(f"Unable to load PDF: {file_path.name}")

    def _fallback_pdfium(self, file_path: Path) -> tuple[list[Image.Image], str | None]:
        try:
            import pypdfium2 as pdfium
        except Exception as exc:  # noqa: BLE001
            return [], str(exc)

        result: list[Image.Image] = []
        try:
            pdf = pdfium.PdfDocument(str(file_path))
            for i in range(len(pdf)):
                page = pdf[i]
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()
                result.append(pil_image.convert("RGB"))
            pdf.close()
            return result, None
        except Exception as exc:  # noqa: BLE001
            return [], str(exc)

    def _load_image(self, file_path: Path) -> Image.Image:
        cv_image = cv2.imread(str(file_path), cv2.IMREAD_COLOR)
        if cv_image is None:
            raise FileLoaderError(f"Unable to read image file: {file_path.name}")
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
