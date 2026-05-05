"""Smart field detection engine based on OCR boxes/text."""

from __future__ import annotations

from models.field import DetectedField
from models.ocr_result import OCRPageResult
from utils.text_normalizer import normalize_persian_text


class FieldDetector:
    """Detect key-value fields and multiline values from OCR output."""

    KEY_SEPARATORS = (":", "：")

    def detect_fields(self, page_result: OCRPageResult) -> list[DetectedField]:
        lines = self._sorted_boxes(page_result)
        detected: list[DetectedField] = []
        current_field: DetectedField | None = None

        for box in lines:
            text = normalize_persian_text(box.text)
            if self._looks_like_key_line(text):
                if current_field:
                    detected.append(current_field)
                field_name, value = self._split_key_value(text)
                current_field = DetectedField(
                    field_name=field_name,
                    value=value,
                    position=self._to_rect(box.bbox),
                )
            elif current_field and text:
                current_field.value = normalize_persian_text(f"{current_field.value} {text}".strip())
            elif text:
                detected.append(DetectedField(field_name="متن", value=text, position=self._to_rect(box.bbox)))

        if current_field:
            detected.append(current_field)
        return detected

    def _sorted_boxes(self, page_result: OCRPageResult):
        return sorted(page_result.boxes, key=lambda b: (min(p[1] for p in b.bbox), min(p[0] for p in b.bbox)))

    def _looks_like_key_line(self, text: str) -> bool:
        return any(sep in text for sep in self.KEY_SEPARATORS)

    def _split_key_value(self, text: str) -> tuple[str, str]:
        for sep in self.KEY_SEPARATORS:
            if sep in text:
                key, value = text.split(sep, 1)
                return normalize_persian_text(key), normalize_persian_text(value)
        return text, ""

    def _to_rect(self, points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)
