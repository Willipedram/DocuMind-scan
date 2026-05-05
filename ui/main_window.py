"""Main application window for the Phase 3 UI shell with file rendering."""

from __future__ import annotations

from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.file_loader import FileLoader, FileLoaderError


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocuMind Scan")
        self.resize(1440, 860)
        self.setMinimumSize(1120, 700)

        self.file_loader = FileLoader()
        self.loaded_pages: list = []
        self.current_page_index = 0
        self.zoom_level = 1.0

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        page_layout = QVBoxLayout(root)
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(10)

        content_splitter = QSplitter(Qt.Orientation.Horizontal, root)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.addWidget(self._build_sidebar())
        content_splitter.addWidget(self._build_document_viewer())
        content_splitter.addWidget(self._build_right_panel())
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 3)
        content_splitter.setStretchFactor(2, 2)
        content_splitter.setSizes([280, 720, 420])

        page_layout.addWidget(content_splitter, 1)
        page_layout.addWidget(self._build_bottom_status(), 0)

    def _build_sidebar(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.import_button = QPushButton("+ وارد کردن فایل", panel)
        self.import_button.setObjectName("primaryButton")
        self.import_button.setToolTip("Import PDF/JPG/PNG")
        self.import_button.setIcon(QIcon.fromTheme("document-open"))
        self.import_button.clicked.connect(self._on_import_clicked)

        self.file_list = QListWidget(panel)
        self.file_list.setObjectName("fileList")

        layout.addWidget(self._section_title("پروژه و فایل‌ها"))
        layout.addWidget(self._subtitle("اسناد ورودی را مدیریت کنید"))
        layout.addWidget(self.import_button)
        layout.addWidget(self._subheader("فهرست فایل‌ها"))
        layout.addWidget(self.file_list, 1)
        return panel

    def _build_document_viewer(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.page_label = QLabel("صفحه 0 / 0")
        self.page_label.setObjectName("subheader")

        controls = QHBoxLayout()
        self.prev_page_button = QPushButton("صفحه قبل")
        self.next_page_button = QPushButton("صفحه بعد")
        self.zoom_out_button = QPushButton("-")
        self.zoom_in_button = QPushButton("+")

        self.prev_page_button.clicked.connect(self._show_prev_page)
        self.next_page_button.clicked.connect(self._show_next_page)
        self.zoom_out_button.clicked.connect(lambda: self._change_zoom(-0.1))
        self.zoom_in_button.clicked.connect(lambda: self._change_zoom(0.1))

        for btn in [self.prev_page_button, self.next_page_button, self.zoom_out_button, self.zoom_in_button]:
            controls.addWidget(btn)

        self.viewer = QGraphicsView(panel)
        self.viewer.setObjectName("viewerPlaceholder")
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_scene = QGraphicsScene(self.viewer)
        self.viewer.setScene(self.viewer_scene)
        self.viewer_item: QGraphicsPixmapItem | None = None

        layout.addWidget(self._section_title("پیش‌نمایش سند"))
        layout.addWidget(self._subtitle("نمایش تصویر یا صفحه PDF انتخاب‌شده"))
        layout.addWidget(self.page_label)
        layout.addLayout(controls)
        layout.addWidget(self.viewer, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = self._make_card_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        self.file_info = QLabel("فایلی انتخاب نشده است")
        self.file_info.setObjectName("mutedText")
        self.file_info.setWordWrap(True)
        layout.addWidget(self._section_title("فیلدها و انتخاب‌ها"))
        layout.addWidget(self._subtitle("این بخش در فازهای بعدی کامل می‌شود"))
        layout.addWidget(self.file_info)
        layout.addStretch(1)
        return panel

    def _build_bottom_status(self) -> QWidget:
        bar = self._make_card_panel()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(14, 10, 14, 10)
        self.status_text = QLabel("وضعیت: آماده")
        self.progress = QProgressBar(bar)
        self.progress.setValue(0)
        bar_layout.addWidget(self.status_text)
        bar_layout.addWidget(self.progress, 1)
        return bar

    def _on_import_clicked(self) -> None:
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل",
            "",
            "Supported Files (*.pdf *.jpg *.jpeg *.png)",
        )
        if not selected_file:
            return

        file_path = Path(selected_file)
        try:
            self.status_text.setText("وضعیت: در حال بارگذاری")
            self.progress.setValue(30)
            self.loaded_pages = self.file_loader.load_pages(file_path)
            self.current_page_index = 0
            self.zoom_level = 1.0

            self.file_list.addItem(file_path.name)
            self.file_info.setText(f"فایل: {file_path.name}\nتعداد صفحات: {len(self.loaded_pages)}")
            self._render_current_page()
            self.status_text.setText("وضعیت: آماده نمایش")
            self.progress.setValue(100)
        except FileLoaderError as exc:
            self.status_text.setText("وضعیت: خطا در بارگذاری")
            self.progress.setValue(0)
            QMessageBox.warning(self, "خطا", str(exc))

    def _render_current_page(self) -> None:
        if not self.loaded_pages:
            return
        page = self.loaded_pages[self.current_page_index]
        qimage = ImageQt(page)
        pixmap = QPixmap.fromImage(qimage)

        self.viewer_scene.clear()
        self.viewer_item = self.viewer_scene.addPixmap(pixmap)
        self.viewer_scene.setSceneRect(self.viewer_item.boundingRect())
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
        panel = QFrame()
        panel.setObjectName("cardPanel")
        return panel

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label

    @staticmethod
    def _subtitle(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("subtitle")
        return label

    @staticmethod
    def _subheader(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("subheader")
        return label

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background-color: #0b1220; color: #e5e7eb; font-size: 13px; }
            QFrame#cardPanel { background-color: #121a2a; border: 1px solid #24324a; border-radius: 12px; }
            QLabel#sectionTitle { font-size: 18px; font-weight: 700; }
            QLabel#subtitle, QLabel#mutedText { color: #94a3b8; font-size: 12px; }
            QLabel#subheader { font-size: 13px; font-weight: 600; color: #cbd5e1; }
            QPushButton#primaryButton { background-color: #2563eb; border: 1px solid #3b82f6; border-radius: 10px; padding: 10px 12px; }
            QListWidget, QGraphicsView#viewerPlaceholder { background-color: #0f172a; border: 1px solid #24324a; border-radius: 10px; }
            QProgressBar { background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; }
            QProgressBar::chunk { background-color: #22c55e; border-radius: 8px; }
            """
        )
