"""Lightweight incremental predictor for field positions."""

from __future__ import annotations

from collections import defaultdict

from models.label_data import LabeledRegion


class MLFieldPredictor:
    """A simple centroid-based incremental learner for field regions."""

    def __init__(self) -> None:
        self.samples_by_label: dict[str, list[LabeledRegion]] = defaultdict(list)

    def train(self, samples: list[LabeledRegion]) -> None:
        self.samples_by_label.clear()
        for sample in samples:
            self.samples_by_label[sample.label].append(sample)

    def incremental_update(self, sample: LabeledRegion) -> None:
        self.samples_by_label[sample.label].append(sample)

    def predict(self, label: str) -> tuple[int, int, int, int] | None:
        samples = self.samples_by_label.get(label, [])
        if not samples:
            return None
        x = int(sum(s.x for s in samples) / len(samples))
        y = int(sum(s.y for s in samples) / len(samples))
        w = int(sum(s.width for s in samples) / len(samples))
        h = int(sum(s.height for s in samples) / len(samples))
        return x, y, w, h
