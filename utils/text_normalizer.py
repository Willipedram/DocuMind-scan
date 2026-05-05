"""Persian text and number normalization helpers."""

from __future__ import annotations

import re

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"

_DIGIT_TRANS = str.maketrans({
    **{p: e for p, e in zip(PERSIAN_DIGITS, ENGLISH_DIGITS)},
    **{a: e for a, e in zip(ARABIC_DIGITS, ENGLISH_DIGITS)},
})


def normalize_persian_text(text: str) -> str:
    text = text.translate(_DIGIT_TRANS)
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text).strip()
    return text
