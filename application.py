import sys
from colormaps import opencv_colormaps
from functions import return_color_map, to_sepia, to_grayscale
import numpy as np
import cv2
import requests
from io import BytesIO
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QScrollArea, QLineEdit, QComboBox,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QCheckBox,
    QGridLayout
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QPoint, QRect, QSize, Signal
from PIL import Image

from unsplash_api import UnsplashAPI
from paint_tools import PaintMixin #our brush!!!


class Home(PaintMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dollar Store Photoshop")
        self.resize(1000, 680)

        self.img: np.ndarray | None = None
        self.unsplash = UnsplashAPI()
        self.logo_pix: QPixmap | None = None
        self.current_source_text: str | None = None

        self.zoom = 1.0
        self.manual_zoom = False
        self.last_scale = 1.0

        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self.open_image)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Unsplash (e.g., sunset, cat)")
        self.search_btn = QPushButton("Fetch")
        self.search_btn.clicked.connect(self.fetch_unsplash_image)

        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)

        self.back_btn = QPushButton("Back to Home")
        self.back_btn.clicked.connect(self.reset_to_home)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.open_btn)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(self.search_btn)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.zoom_in_btn)
        top_bar.addWidget(self.zoom_out_btn)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.back_btn)

        # FIlters code
        self.drop_label = QLabel("Filters")
        self.drop_down_list = ["Choose a filter", "Grayscale", "Sepia", "Invert"]
        for i in opencv_colormaps:
            self.drop_down_list.append(i)

        self.drop_combo_box = QComboBox()
        self.drop_combo_box.addItems(self.drop_down_list)

        self.drop_btn = QPushButton("Submit")
        self.drop_btn.clicked.connect(self.manipulate_image)

        # Revert button
        self.revert_btn = QPushButton("Revert Image")
        self.revert_btn.clicked.connect(self.revert_image)

        # Resize code
        self.resize_btn = QPushButton("Resize…")
        self.resize_btn.clicked.connect(self.open_resize_dialog)

        brush_title, color_grid = self.setup_painting()

        # SAVING button
        self.save_btn = QPushButton("Save…")
        self.save_btn.clicked.connect(self.save_image)

        tools_col = QVBoxLayout()
        tools_col.addWidget(self.drop_label)
        tools_col.addWidget(self.drop_combo_box)
        tools_col.addWidget(self.drop_btn)
        tools_col.addWidget(self.revert_btn)
        tools_col.addSpacing(16)
        tools_col.addWidget(QLabel("Size"))
        tools_col.addWidget(self.resize_btn)
        tools_col.addSpacing(16)
        tools_col.addWidget(brush_title)
        tools_col.addLayout(color_grid)
        tools_col.addWidget(self.paint_toggle_btn)
        tools_col.addWidget(self.clear_paint_btn)
        tools_col.addSpacing(16)
        tools_col.addWidget(QLabel("Export"))
        tools_col.addWidget(self.save_btn)
        tools_col.addStretch(1)

        self.editor_panel = QWidget()
        self.editor_panel.setLayout(tools_col)
        self.editor_panel.setFixedWidth(180)
        self.editor_panel.setVisible(False)

        assets_path = Path(__file__).parent / "assets"
        logo_path = assets_path / "_dollarstore.png"
        if logo_path.exists():
            lpix = QPixmap(str(logo_path))
            if not lpix.isNull():
                self.logo_pix = lpix
                self.preview_label.setPixmap(
                    lpix.scaled(420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.preview_label.setVisible(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.preview_label)

        self.status = QLabel("Welcome to Dollar Store Photoshop! :)")
        self.status.setAlignment(Qt.AlignCenter)

        body = QHBoxLayout()
        body.addWidget(self.editor_panel)
        body.addWidget(self.scroll, 1)

        main = QVBoxLayout()
        main.addLayout(top_bar)
        main.addLayout(body, 1)
        main.addWidget(self.status)
        self.setLayout(main)

    def enter_edit_mode(self, source_text: str):
        self.editor_panel.setVisible(True)
        self.current_source_text = source_text

    def reset_to_home(self):
        self.img = None
        self.paint_base = None
        self.drop_combo_box.setCurrentIndex(0)
        self.editor_panel.setVisible(False)
        self.current_source_text = None
        self.manual_zoom = False
        self.zoom = 1.0
        self.last_scale = 1.0
        self.preview_label.set_allow_draw(False)
        if self.logo_pix is not None:
            self.preview_label.setPixmap(
                self.logo_pix.scaled(420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.preview_label.setVisible(True)
        else:
            self.preview_label.clear()
            self.preview_label.setVisible(False)
        self.status.setText("Welcome to Dollar Store Photoshop! :)")

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return

        img_bgr = cv2.imread(path)
        if img_bgr is None:
            self.status.setText("Could not load image.")
            return

        self.img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self.orig_img = self.img.copy()
        self.paint_base = self.img.copy()
        self.manual_zoom = False
        self.zoom = 1.0
        self.last_scale = 1.0
        self.show_image(self.img)
        self.enter_edit_mode("File")

    def fetch_unsplash_image(self):
        query = self.search_input.text().strip()
        if not query:
            self.status.setText("Type something to search Unsplash.")
            return

        self.status.setText(f"Searching Unsplash for “{query}”…")
        QApplication.processEvents()

        try:
            data = self.unsplash.get_image_with_metadata(query)
        except Exception as e:
            self.status.setText(f"Unsplash error: {e}")
            return

        if not data or "url" not in data:
            self.status.setText("No image found on Unsplash.")
            return

        image_url = data["url"]
        author = data.get("author", "Unknown")

        try:
            resp = requests.get(image_url, timeout=10)
            resp.raise_for_status()
            pil_img = Image.open(BytesIO(resp.content)).convert("RGB")
            img_rgb = np.array(pil_img)
        except Exception as e:
            self.status.setText(f"Download/process error: {e}")
            return

        self.img = img_rgb
        self.orig_img = self.img.copy()
        self.paint_base = self.img.copy()
        self.manual_zoom = False
        self.zoom = 1.0
        self.last_scale = 1.0
        self.show_image(self.img)
        self.enter_edit_mode(f"Unsplash by {author}")

    # Zoomin/out
    def zoom_in(self):
        if self.img is None:
            return
        self.manual_zoom = True
        self.zoom = min(self.zoom * 1.25, 16.0)
        self.show_image(self.img)

    def zoom_out(self):
        if self.img is None:
            return
        self.manual_zoom = True
        self.zoom = max(self.zoom / 1.25, 0.0625)
        self.show_image(self.img)

    # filters
    def manipulate_image(self):
        if self.img is None:
            self.status.setText("Load an image first.")
            return

        option = self.drop_combo_box.currentText()
        if option == "Choose a filter":
            self.status.setText("pick something")
            return

        img = self.img.copy()


        match option:
            case "Bone Color":
                img = to_bone_color(img)
            case "Grayscale":
                img = to_grayscale(img)
            case "Sepia":
                img = to_sepia(img)
            case _:
                # Everything else
                bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                new_bgr = cv2.applyColorMap(gray, return_color_map(option))
                img = cv2.cvtColor(new_bgr, cv2.COLOR_BGR2RGB)


        self.img = img
        self.paint_base = self.img.copy()
        self.last_scale = 1.0
        self.show_image(self.img)
        self.status.setText(f"Applied filter: {option}")

    # Revert image
    def revert_image(self):
        self.img = self.orig_img
        self.show_image(self.img)
        self.status.setText("Reverted to original image")



    #resize image
    def open_resize_dialog(self):
        if self.img is None:
            self.status.setText("Load an image first.")
            return

        h, w, _ = self.img.shape
        aspect = w / h if h else 1.0

        dlg = QDialog(self)
        dlg.setWindowTitle("Resize Image (Exact)")
        form = QFormLayout(dlg)

        w_spin = QSpinBox(); w_spin.setRange(1, 20000); w_spin.setValue(w)
        h_spin = QSpinBox(); h_spin.setRange(1, 20000); h_spin.setValue(h)
        lock_aspect = QCheckBox("lock aspect ratio"); lock_aspect.setChecked(True)

        def on_width_change(val):
            if lock_aspect.isChecked():
                new_h = max(1, int(round(val / aspect)))
                h_spin.blockSignals(True); h_spin.setValue(new_h); h_spin.blockSignals(False)

        def on_height_change(val):
            if lock_aspect.isChecked():
                new_w = max(1, int(round(val * aspect)))
                w_spin.blockSignals(True); w_spin.setValue(new_w); w_spin.blockSignals(False)

        w_spin.valueChanged.connect(on_width_change)
        h_spin.valueChanged.connect(on_height_change)

        form.addRow("Width (px):", w_spin)
        form.addRow("Height (px):", h_spin)
        form.addRow(lock_aspect)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            new_w = w_spin.value()
            new_h = h_spin.value()
            upscaling = (new_w * new_h) > (w * h)
            interp = cv2.INTER_CUBIC if upscaling else cv2.INTER_AREA
            resized = cv2.resize(self.img, (new_w, new_h), interpolation=interp)
            self.img = resized
            self.paint_base = self.img.copy()
            self.last_scale = 1.0
            self.show_image(self.img)
            self.status.setText(f"Resized to {new_w}×{new_h}")

    #SAVE YOUR PHOTO
    def save_image(self):
        if self.img is None:
            self.status.setText("Theres nothing to save dumbass!!")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;TIFF (*.tiff *.tif)"
        )
        if not path:
            return

        if "." not in Path(path).name:
            if selected_filter.startswith("PNG"):
                path += ".png"
            elif selected_filter.startswith("JPEG"):
                path += ".jpg"
            elif selected_filter.startswith("BMP"):
                path += ".bmp"
            else:
                path += ".tiff"
        try:
            Image.fromarray(self.img).save(path, quality=95)
            self.status.setText(f"Saved: {path}")
        except Exception as e:
            self.status.setText(f"Save failed: {e}")

    def show_image(self, img_rgb: np.ndarray, preserve_scale: bool = False):
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        base = QPixmap.fromImage(qimg)

        if self.manual_zoom:
            scale = self.zoom
        else:
            if preserve_scale:
                scale = self.last_scale
            else:
                vw = max(1, self.scroll.viewport().width() - 20)
                vh = max(1, self.scroll.viewport().height() - 20)
                scale = min(vw / max(w, 1), vh / max(h, 1))
                self.last_scale = scale

        disp = base.scaled(
            int(w * scale), int(h * scale),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(disp)
        self.preview_label.set_scale(scale)
        self.preview_label.setVisible(True)

        zoom_pct = max(1, int(round(scale * 100)))
        src = self.current_source_text or "—"
        self.status.setText(f"{src} • {w}×{h} • {zoom_pct}%")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.manual_zoom and self.img is not None:
            self.last_scale = 1.0
            self.show_image(self.img)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Home()
    win.show()
    sys.exit(app.exec())