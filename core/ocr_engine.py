"""EasyOCR engine for Persian + English text extraction."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from easyocr import Reader
from PIL import Image

from models.ocr_result import OCRBox, OCRPageResult


class OCREngine:
    """OCR engine wrapper for extracting text, boxes, and confidence."""

    def __init__(self, languages: Iterable[str] | None = None) -> None:
        self.languages = list(languages or ["fa", "en"])
        self.reader = Reader(self.languages, gpu=False)

    def extract_page(self, page_image: Image.Image, page_index: int) -> OCRPageResult:
        np_image = np.array(page_image.convert("RGB"))
        raw_results = self.reader.readtext(np_image, detail=1)

        boxes: list[OCRBox] = []
        texts: list[str] = []

        for result in raw_results:
            bbox_raw, text, confidence = result
            bbox = [(int(point[0]), int(point[1])) for point in bbox_raw]
            boxes.append(OCRBox(bbox=bbox, text=text, confidence=float(confidence)))
            texts.append(text)

        return OCRPageResult(page_index=page_index, full_text="\n".join(texts), boxes=boxes)
