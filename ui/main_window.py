"""Main application window with OCR, templates, Excel export, and batch processing."""

from __future__ import annotations

import time
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGraphicsScene, QGraphicsSimpleTextItem,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QSplitter, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.field_detector import FieldDetector
from core.file_loader import FileLoader, FileLoaderError
from core.ocr_engine import OCREngine
from models.field import DetectedField
from models.ocr_result import OCRPageResult
from services.excel_exporter import ExcelExporter
from services.template_manager import TemplateManager
from services.label_store import LabelStore
from core.ml_field_predictor import MLFieldPredictor
from models.label_data import LabeledRegion
from ui.selection_view import SelectionGraphicsView
from utils.logging_config import setup_logging


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocuMind Scan")
        self.resize(1440, 860)
        self.logger = setup_logging()

        self.file_loader = FileLoader()
        self.ocr_engine = OCREngine(["fa", "en"])
        self.field_detector = FieldDetector()
        self.template_manager = TemplateManager()
        self.excel_exporter = ExcelExporter()

        self.loaded_pages: list = []
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.ocr_results_by_page: dict[int, OCRPageResult] = {}
        self.detected_fields: list[DetectedField] = []
        self.current_document_name = ""
        self.batch_files: list[Path] = []
        self.label_store = LabelStore()
        self.ml_predictor = MLFieldPredictor()
        self.ml_predictor.train(self.label_store.load())
        self.last_selected_region: tuple[int,int,int,int] | None = None

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        root = QWidget(self); self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        splitter = QSplitter(Qt.Orientation.Horizontal, root)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_document_viewer())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 3); splitter.setStretchFactor(2, 2)
        layout.addWidget(splitter, 1); layout.addWidget(self._build_bottom_status(), 0)

    def _build_sidebar(self) -> QWidget:
        panel = self._make_card_panel(); layout = QVBoxLayout(panel)
        self.import_button = QPushButton("+ وارد کردن فایل")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setIcon(QIcon.fromTheme("document-open"))
        self.import_button.clicked.connect(self._on_import_clicked)

        self.batch_import_button = QPushButton("+ افزودن دسته‌ای")
        self.batch_import_button.clicked.connect(self._on_batch_import_clicked)

        self.batch_run_button = QPushButton("پردازش دسته‌ای")
        self.batch_run_button.clicked.connect(self._run_batch_processing)

        self.ocr_button = QPushButton("OCR + تشخیص فیلد"); self.ocr_button.clicked.connect(self._run_ocr_current_page)
        self.export_button = QPushButton("خروجی Excel"); self.export_button.clicked.connect(self._export_selected_to_excel)
        self.label_button = QPushButton("برچسب‌گذاری ناحیه"); self.label_button.clicked.connect(self._assign_label_to_region)
        self.predict_button = QPushButton("پیش‌بینی جایگاه فیلد"); self.predict_button.clicked.connect(self._predict_label_position)
        self.file_list = QListWidget()
        layout.addWidget(self._section_title("فایل‌ها"))
        for w in [self.import_button, self.batch_import_button, self.batch_run_button, self.ocr_button, self.export_button, self.label_button, self.predict_button, self.file_list]:
            layout.addWidget(w)
        return panel

    def _build_document_viewer(self) -> QWidget:
        panel = self._make_card_panel(); layout = QVBoxLayout(panel)
        self.page_label = QLabel("صفحه 0 / 0")
        controls = QHBoxLayout()
        for text, fn in [("صفحه قبل", self._show_prev_page), ("صفحه بعد", self._show_next_page), ("-", lambda: self._change_zoom(-0.1)), ("+", lambda: self._change_zoom(0.1))]:
            b = QPushButton(text); b.clicked.connect(fn); controls.addWidget(b)
        self.viewer = SelectionGraphicsView(panel); self.viewer_scene = QGraphicsScene(self.viewer); self.viewer.setScene(self.viewer_scene)
        self.viewer.region_selected.connect(self._on_region_selected)
        layout.addWidget(self._section_title("پیش‌نمایش")); layout.addWidget(self.page_label); layout.addLayout(controls); layout.addWidget(self.viewer, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = self._make_card_panel(); layout = QVBoxLayout(panel)
        self.file_info = QLabel("فایلی انتخاب نشده است")
        self.eta_label = QLabel("ETA: --")
        self.fields_table = QTableWidget(0, 4)
        self.fields_table.setHorizontalHeaderLabels(["انتخاب", "نام فیلد", "نام ستون Excel", "موقعیت"])
        self.fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        save_btn = QPushButton("ذخیره قالب"); load_btn = QPushButton("بارگذاری قالب")
        save_btn.clicked.connect(self._save_template); load_btn.clicked.connect(self._load_template)
        self.ocr_text_preview = QTextEdit(); self.ocr_text_preview.setReadOnly(True)
        for w in [self._section_title("انتخاب ستون‌ها"), self.file_info, self.eta_label, self.fields_table, save_btn, load_btn, self._subheader("متن OCR"), self.ocr_text_preview]:
            layout.addWidget(w)
        return panel

    def _build_bottom_status(self) -> QWidget:
        bar = self._make_card_panel(); row = QHBoxLayout(bar)
        self.status_text = QLabel("وضعیت: آماده"); self.progress = QProgressBar()
        row.addWidget(self.status_text); row.addWidget(self.progress, 1)
        return bar

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل", "", "Supported Files (*.pdf *.jpg *.jpeg *.png)")
        if not path: return
        self._load_single_file(Path(path))

    def _on_batch_import_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب چند فایل", "", "Supported Files (*.pdf *.jpg *.jpeg *.png)")
        if not files:
            return
        self.batch_files = [Path(f) for f in files]
        self.file_list.clear()
        for fp in self.batch_files:
            QListWidgetItem(f"{fp.name} | pending", self.file_list)
        self.logger.info("[INFO] %s files added to batch queue", len(self.batch_files))

    def _load_single_file(self, fp: Path) -> None:
        try:
            self.loaded_pages = self.file_loader.load_pages(fp)
            self.current_document_name = fp.name
            self.current_page_index = 0; self.zoom_level = 1.0
            self.ocr_results_by_page.clear(); self.detected_fields = []
            self.file_info.setText(f"فایل: {fp.name} | صفحات: {len(self.loaded_pages)}")
            self._render_current_page()
        except FileLoaderError as exc:
            QMessageBox.warning(self, "خطا", str(exc))

    def _run_batch_processing(self) -> None:
        if not self.batch_files:
            QMessageBox.information(self, "اطلاع", "ابتدا فایل‌های دسته‌ای را اضافه کنید")
            return

        self.logger.info("[INFO] Batch processing started")
        start = time.time()
        total = len(self.batch_files)
        done = 0

        for idx, fp in enumerate(self.batch_files):
            self.logger.info("[PROCESS] Processing %s (%s/%s)", fp.name, idx + 1, total)
            try:
                self._load_single_file(fp)
                if not self.loaded_pages:
                    raise RuntimeError("No pages loaded")

                result = self.ocr_engine.extract_page(self.loaded_pages[0], 0)
                self.detected_fields = self.field_detector.detect_fields(result)
                self._populate_fields_table(self.detected_fields)

                self.file_list.item(idx).setText(f"{fp.name} | success")
                self.logger.info("[SUCCESS] Processed %s", fp.name)
            except Exception as exc:  # noqa: BLE001
                self.file_list.item(idx).setText(f"{fp.name} | error")
                self.logger.error("[ERROR] Failed %s: %s", fp.name, exc)

            done += 1
            self.progress.setValue(int((done / total) * 100))
            elapsed = time.time() - start
            avg = elapsed / done
            eta = int(avg * (total - done))
            self.eta_label.setText(f"ETA: {eta}s")
            self.status_text.setText(f"وضعیت: پردازش {done}/{total}")

        self.logger.info("[INFO] Batch processing completed")

    # existing methods below

    def _on_region_selected(self, x: int, y: int, w: int, h: int) -> None:
        self.last_selected_region = (x, y, w, h)
        self.status_text.setText(f"وضعیت: ناحیه انتخاب شد ({x},{y},{w},{h})")

    def _assign_label_to_region(self) -> None:
        if not self.last_selected_region:
            QMessageBox.information(self, "اطلاع", "ابتدا یک ناحیه روی سند انتخاب کنید")
            return
        label, ok = QInputDialog.getText(self, "برچسب ناحیه", "نام برچسب:")
        if not ok or not label.strip():
            return
        x, y, w, h = self.last_selected_region
        sample = LabeledRegion(
            document_name=self.current_document_name or "unknown",
            page_index=self.current_page_index,
            label=label.strip(),
            x=x, y=y, width=w, height=h,
        )
        self.label_store.append(sample)
        self.ml_predictor.incremental_update(sample)
        self.logger.info("[SUCCESS] Labeled region saved for '%s'", label.strip())
        self.status_text.setText(f"وضعیت: برچسب '{label.strip()}' ذخیره شد")

    def _predict_label_position(self) -> None:
        label, ok = QInputDialog.getText(self, "پیش‌بینی", "نام برچسب:")
        if not ok or not label.strip():
            return
        pred = self.ml_predictor.predict(label.strip())
        if not pred:
            QMessageBox.information(self, "اطلاع", "برای این برچسب داده آموزشی وجود ندارد")
            return
        x, y, w, h = pred
        pen = QPen(QColor("#f59e0b")); pen.setWidth(2)
        self.viewer_scene.addRect(x, y, w, h, pen)
        self.status_text.setText(f"وضعیت: پیش‌بینی انجام شد برای '{label.strip()}'")

    def _run_ocr_current_page(self) -> None:
        if not self.loaded_pages: return
        result = self.ocr_engine.extract_page(self.loaded_pages[self.current_page_index], self.current_page_index)
        self.ocr_results_by_page[self.current_page_index] = result
        self.detected_fields = self.field_detector.detect_fields(result)
        self._populate_fields_table(self.detected_fields)
        self.ocr_text_preview.setPlainText(result.full_text)
        self._auto_apply_or_prompt_template()
        self._render_current_page()


    def _auto_apply_or_prompt_template(self) -> None:
        field_names = [f.field_name for f in self.detected_fields]
        template_name, payload = self.template_manager.find_best_template(field_names)
        if payload:
            self._apply_template_payload(payload)
            self.status_text.setText(f"وضعیت: قالب '{template_name}' به‌صورت خودکار اعمال شد")
            self.logger.info("[INFO] Auto-applied template: %s", template_name)
            return

        self.logger.info("[INFO] No matching template found for document")
        ask = QMessageBox.question(
            self,
            "قالب موجود نیست",
            "برای این نوع سند قالبی پیدا نشد. آیا قالب جدید ایجاد شود؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ask == QMessageBox.StandardButton.Yes:
            name, ok = QInputDialog.getText(self, "ایجاد قالب", "نام قالب جدید:")
            if ok and name.strip():
                self.template_manager.save_template(name.strip(), self._selected_columns_payload(), document_type=name.strip())
                self.status_text.setText(f"وضعیت: قالب جدید '{name.strip()}' ذخیره شد")
                self.logger.info("[SUCCESS] New template created: %s", name.strip())

    def _apply_template_payload(self, payload: dict) -> None:
        self.fields_table.setRowCount(0)
        for row, col in enumerate(payload.get("columns", [])):
            self.fields_table.insertRow(row)
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Checked)
            self.fields_table.setItem(row, 0, chk)
            self.fields_table.setItem(row, 1, QTableWidgetItem(col.get("field_name", "")))
            self.fields_table.setItem(row, 2, QTableWidgetItem(col.get("column_name", "")))
            self.fields_table.setItem(row, 3, QTableWidgetItem(str(col.get("position", ""))))

    def _populate_fields_table(self, fields: list[DetectedField]) -> None:
        self.fields_table.setRowCount(0)
        for row, field in enumerate(fields):
            self.fields_table.insertRow(row)
            select_item = QTableWidgetItem(); select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable); select_item.setCheckState(Qt.CheckState.Checked)
            self.fields_table.setItem(row, 0, select_item)
            self.fields_table.setItem(row, 1, QTableWidgetItem(field.field_name))
            self.fields_table.setItem(row, 2, QTableWidgetItem(field.field_name))
            self.fields_table.setItem(row, 3, QTableWidgetItem(str(field.position)))

    def _selected_columns_payload(self) -> list[dict]:
        payload=[]
        for row in range(self.fields_table.rowCount()):
            if self.fields_table.item(row,0).checkState()!=Qt.CheckState.Checked: continue
            payload.append({"field_name":self.fields_table.item(row,1).text(),"column_name":self.fields_table.item(row,2).text(),"position":self.fields_table.item(row,3).text()})
        return payload

    def _save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "ذخیره قالب", "نام قالب:")
        if ok and name.strip(): self.template_manager.save_template(name.strip(), self._selected_columns_payload(), document_type=name.strip())

    def _load_template(self) -> None:
        names=self.template_manager.list_templates()
        if not names: return
        name, ok=QInputDialog.getItem(self,"بارگذاری قالب","انتخاب قالب:",names,0,False)
        if not ok:return
        payload=self.template_manager.load_template(name)
        self.fields_table.setRowCount(0)
        for row,col in enumerate(payload.get("columns",[])):
            self.fields_table.insertRow(row)
            chk=QTableWidgetItem(); chk.setFlags(chk.flags()|Qt.ItemFlag.ItemIsUserCheckable); chk.setCheckState(Qt.CheckState.Checked)
            self.fields_table.setItem(row,0,chk); self.fields_table.setItem(row,1,QTableWidgetItem(col.get("field_name",""))); self.fields_table.setItem(row,2,QTableWidgetItem(col.get("column_name",""))); self.fields_table.setItem(row,3,QTableWidgetItem(str(col.get("position",""))))

    def _export_selected_to_excel(self) -> None:
        if not self.current_document_name: return
        save_path,_=QFileDialog.getSaveFileName(self,"ذخیره فایل Excel","output.xlsx","Excel (*.xlsx)")
        if not save_path:return
        out=self.excel_exporter.export_row(Path(save_path),self._selected_columns_payload(),{f.field_name:f.value for f in self.detected_fields},self.current_document_name)
        self.status_text.setText(f"وضعیت: خروجی Excel ذخیره شد ({out.name})")

    def _render_current_page(self) -> None:
        if not self.loaded_pages:return
        pixmap=QPixmap.fromImage(ImageQt(self.loaded_pages[self.current_page_index]))
        self.viewer_scene.clear(); self.viewer_scene.addPixmap(pixmap)
        result=self.ocr_results_by_page.get(self.current_page_index)
        if result:
            pen=QPen(QColor("#22c55e")); pen.setWidth(2); brush=QBrush(QColor("#f8fafc"))
            for box in result.boxes:
                xs=[p[0] for p in box.bbox]; ys=[p[1] for p in box.bbox]
                x,y,w,h=min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)
                self.viewer_scene.addRect(x,y,w,h,pen)
                t=QGraphicsSimpleTextItem(f"{box.confidence:.2f}"); t.setBrush(brush); t.setPos(x,max(0,y-18)); self.viewer_scene.addItem(t)
        self.viewer.resetTransform(); self.viewer.scale(self.zoom_level,self.zoom_level); self.page_label.setText(f"صفحه {self.current_page_index + 1} / {len(self.loaded_pages)}")

    def _show_prev_page(self) -> None:
        if self.current_page_index>0: self.current_page_index-=1; self._render_current_page()
    def _show_next_page(self) -> None:
        if self.current_page_index < len(self.loaded_pages)-1: self.current_page_index+=1; self._render_current_page()
    def _change_zoom(self, delta: float) -> None:
        self.zoom_level=max(0.2,min(3.0,self.zoom_level+delta)); self._render_current_page()

    @staticmethod
    def _make_card_panel() -> QFrame:
        p=QFrame(); p.setObjectName("cardPanel"); return p
    @staticmethod
    def _section_title(text: str) -> QLabel:
        l=QLabel(text); l.setObjectName("sectionTitle"); l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); return l
    @staticmethod
    def _subheader(text: str) -> QLabel:
        return QLabel(text)
    def _apply_styles(self) -> None:
        self.setStyleSheet("QWidget { background:#0b1220; color:#e5e7eb; } QFrame#cardPanel { background:#121a2a; border:1px solid #24324a; border-radius:12px; }")
