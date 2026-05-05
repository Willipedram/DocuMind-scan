"""Main application window with OCR, field detection, and selection templates."""

from __future__ import annotations

from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.field_detector import FieldDetector
from core.file_loader import FileLoader, FileLoaderError
from core.ocr_engine import OCREngine
from models.field import DetectedField
from models.ocr_result import OCRPageResult
from services.template_manager import TemplateManager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocuMind Scan")
        self.resize(1440, 860)
        self.file_loader = FileLoader()
        self.ocr_engine = OCREngine(["fa", "en"])
        self.field_detector = FieldDetector()
        self.template_manager = TemplateManager()

        self.loaded_pages: list = []
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.ocr_results_by_page: dict[int, OCRPageResult] = {}
        self.detected_fields: list[DetectedField] = []

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        splitter = QSplitter(Qt.Orientation.Horizontal, root)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_document_viewer())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)
        layout.addWidget(splitter, 1)
        layout.addWidget(self._build_bottom_status(), 0)

    def _build_sidebar(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        self.import_button = QPushButton("+ وارد کردن فایل")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setIcon(QIcon.fromTheme("document-open"))
        self.import_button.clicked.connect(self._on_import_clicked)
        self.ocr_button = QPushButton("OCR + تشخیص فیلد")
        self.ocr_button.clicked.connect(self._run_ocr_current_page)
        self.file_list = QListWidget()
        layout.addWidget(self._section_title("فایل‌ها"))
        layout.addWidget(self.import_button)
        layout.addWidget(self.ocr_button)
        layout.addWidget(self.file_list, 1)
        return panel

    def _build_document_viewer(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        self.page_label = QLabel("صفحه 0 / 0")
        controls = QHBoxLayout()
        for text, fn in [("صفحه قبل", self._show_prev_page), ("صفحه بعد", self._show_next_page), ("-", lambda: self._change_zoom(-0.1)), ("+", lambda: self._change_zoom(0.1))]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            controls.addWidget(b)
        self.viewer = QGraphicsView(panel)
        self.viewer_scene = QGraphicsScene(self.viewer)
        self.viewer.setScene(self.viewer_scene)
        layout.addWidget(self._section_title("پیش‌نمایش"))
        layout.addWidget(self.page_label)
        layout.addLayout(controls)
        layout.addWidget(self.viewer, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        self.file_info = QLabel("فایلی انتخاب نشده است")
        self.fields_table = QTableWidget(0, 4)
        self.fields_table.setHorizontalHeaderLabels(["انتخاب", "نام فیلد", "نام ستون Excel", "موقعیت"])
        self.fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        save_btn = QPushButton("ذخیره قالب")
        load_btn = QPushButton("بارگذاری قالب")
        save_btn.clicked.connect(self._save_template)
        load_btn.clicked.connect(self._load_template)

        self.ocr_text_preview = QTextEdit()
        self.ocr_text_preview.setReadOnly(True)

        layout.addWidget(self._section_title("انتخاب ستون‌ها"))
        layout.addWidget(self.file_info)
        layout.addWidget(self.fields_table, 2)
        layout.addWidget(save_btn)
        layout.addWidget(load_btn)
        layout.addWidget(self._subheader("متن OCR"))
        layout.addWidget(self.ocr_text_preview, 1)
        return panel

    def _build_bottom_status(self) -> QWidget:
        bar = self._make_card_panel()
        row = QHBoxLayout(bar)
        self.status_text = QLabel("وضعیت: آماده")
        self.progress = QProgressBar()
        row.addWidget(self.status_text)
        row.addWidget(self.progress, 1)
        return bar

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل", "", "Supported Files (*.pdf *.jpg *.jpeg *.png)")
        if not path:
            return
        fp = Path(path)
        try:
            self.loaded_pages = self.file_loader.load_pages(fp)
            self.current_page_index = 0
            self.zoom_level = 1.0
            self.ocr_results_by_page.clear()
            self.file_list.addItem(fp.name)
            self.file_info.setText(f"فایل: {fp.name} | صفحات: {len(self.loaded_pages)}")
            self._render_current_page()
        except FileLoaderError as exc:
            QMessageBox.warning(self, "خطا", str(exc))

    def _run_ocr_current_page(self) -> None:
        if not self.loaded_pages:
            return
        result = self.ocr_engine.extract_page(self.loaded_pages[self.current_page_index], self.current_page_index)
        self.ocr_results_by_page[self.current_page_index] = result
        self.detected_fields = self.field_detector.detect_fields(result)
        self._populate_fields_table(self.detected_fields)
        self.ocr_text_preview.setPlainText(result.full_text)
        self._render_current_page()

    def _populate_fields_table(self, fields: list[DetectedField]) -> None:
        self.fields_table.setRowCount(0)
        for row, field in enumerate(fields):
            self.fields_table.insertRow(row)

            select_item = QTableWidgetItem()
            select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            select_item.setCheckState(Qt.CheckState.Checked)
            self.fields_table.setItem(row, 0, select_item)
            self.fields_table.setItem(row, 1, QTableWidgetItem(field.field_name))
            self.fields_table.setItem(row, 2, QTableWidgetItem(field.field_name))
            self.fields_table.setItem(row, 3, QTableWidgetItem(str(field.position)))

    def _selected_columns_payload(self) -> list[dict]:
        payload: list[dict] = []
        for row in range(self.fields_table.rowCount()):
            checked = self.fields_table.item(row, 0).checkState() == Qt.CheckState.Checked
            if not checked:
                continue
            payload.append(
                {
                    "field_name": self.fields_table.item(row, 1).text(),
                    "column_name": self.fields_table.item(row, 2).text(),
                    "position": self.fields_table.item(row, 3).text(),
                }
            )
        return payload

    def _save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "ذخیره قالب", "نام قالب:")
        if not ok or not name.strip():
            return
        cols = self._selected_columns_payload()
        path = self.template_manager.save_template(name.strip(), cols)
        self.status_text.setText(f"وضعیت: قالب ذخیره شد ({path.name})")

    def _load_template(self) -> None:
        names = self.template_manager.list_templates()
        if not names:
            QMessageBox.information(self, "اطلاع", "قالبی موجود نیست")
            return
        name, ok = QInputDialog.getItem(self, "بارگذاری قالب", "انتخاب قالب:", names, 0, False)
        if not ok:
            return
        payload = self.template_manager.load_template(name)
        columns = payload.get("columns", [])
        self.fields_table.setRowCount(0)
        for row, col in enumerate(columns):
            self.fields_table.insertRow(row)
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Checked)
            self.fields_table.setItem(row, 0, chk)
            self.fields_table.setItem(row, 1, QTableWidgetItem(col.get("field_name", "")))
            self.fields_table.setItem(row, 2, QTableWidgetItem(col.get("column_name", "")))
            self.fields_table.setItem(row, 3, QTableWidgetItem(str(col.get("position", ""))))
        self.status_text.setText(f"وضعیت: قالب '{name}' بارگذاری شد")

    def _render_current_page(self) -> None:
        if not self.loaded_pages:
            return
        page = self.loaded_pages[self.current_page_index]
        pixmap = QPixmap.fromImage(ImageQt(page))
        self.viewer_scene.clear()
        self.viewer_scene.addPixmap(pixmap)

        result = self.ocr_results_by_page.get(self.current_page_index)
        if result:
            pen = QPen(QColor("#22c55e"))
            pen.setWidth(2)
            brush = QBrush(QColor("#f8fafc"))
            for box in result.boxes:
                xs = [p[0] for p in box.bbox]
                ys = [p[1] for p in box.bbox]
                x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
                self.viewer_scene.addRect(x, y, w, h, pen)
                t = QGraphicsSimpleTextItem(f"{box.confidence:.2f}")
                t.setBrush(brush)
                t.setPos(x, max(0, y - 18))
                self.viewer_scene.addItem(t)

        self.viewer.resetTransform()
        self.viewer.scale(self.zoom_level, self.zoom_level)
        self.page_label.setText(f"صفحه {self.current_page_index + 1} / {len(self.loaded_pages)}")

    def _show_prev_page(self) -> None:
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self._render_current_page()

    def _show_next_page(self) -> None:
        if self.current_page_index < len(self.loaded_pages) - 1:
            self.current_page_index += 1
            self._render_current_page()

    def _change_zoom(self, delta: float) -> None:
        self.zoom_level = max(0.2, min(3.0, self.zoom_level + delta))
        self._render_current_page()

    @staticmethod
    def _make_card_panel() -> QFrame:
        p = QFrame()
        p.setObjectName("cardPanel")
        return p

    @staticmethod
    def _section_title(text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("sectionTitle")
        l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return l

    @staticmethod
    def _subheader(text: str) -> QLabel:
        return QLabel(text)

    def _apply_styles(self) -> None:
        self.setStyleSheet("QWidget { background:#0b1220; color:#e5e7eb; } QFrame#cardPanel { background:#121a2a; border:1px solid #24324a; border-radius:12px; }")
