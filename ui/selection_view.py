"""Interactive graphics view to support drag region selection."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsView


class SelectionGraphicsView(QGraphicsView):
    region_selected = Signal(int, int, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._origin: QPointF | None = None
        self._rubber_item: QGraphicsRectItem | None = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.scene() is not None:
            self._origin = self.mapToScene(event.position().toPoint())
            self._rubber_item = self.scene().addRect(QRectF(self._origin, self._origin), QPen(QColor("#f59e0b"), 2))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._origin and self._rubber_item:
            current = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._origin, current).normalized()
            self._rubber_item.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._origin and self._rubber_item:
            rect = self._rubber_item.rect().toRect()
            self.region_selected.emit(rect.x(), rect.y(), rect.width(), rect.height())
            self._origin = None
            self._rubber_item = None
        super().mouseReleaseEvent(event)
