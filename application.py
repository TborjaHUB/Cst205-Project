import sys
from colormaps import opencv_colormaps
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

#canavs setup
class DrawingLabel(QLabel):
    draw_line = Signal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._allow_draw = False
        self._scale = 1.0
        self._last_pos: QPoint | None = None

    def set_allow_draw(self, allow: bool):
        self._allow_draw = allow
        self._last_pos = None  

    def set_scale(self, s: float):
        self._scale = max(1e-9, float(s))

    def _pixmap_rect_in_widget(self) -> QRect:
        pm = self.pixmap()
        if pm is None or pm.isNull():
            return QRect()
        lw, lh = self.width(), self.height()
        pw, ph = pm.width(), pm.height()
        ox = max(0, (lw - pw) // 2)
        oy = max(0, (lh - ph) // 2)
        return QRect(ox, oy, pw, ph)

    def _to_image_xy(self, p: QPoint) -> tuple[int, int] | None:
        pm_rect = self._pixmap_rect_in_widget()
        if not pm_rect.contains(p):
            return None
        local = p - pm_rect.topLeft()
        x = int(local.x() / self._scale)
        y = int(local.y() / self._scale)
        return x, y

    def mousePressEvent(self, event):
        if not self._allow_draw or self.pixmap() is None:
            return super().mousePressEvent(event)
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        pos = event.position().toPoint()
        if self._to_image_xy(pos) is None:
            return
        self._last_pos = pos

    def mouseMoveEvent(self, event):
        if not self._allow_draw or self.pixmap() is None or self._last_pos is None:
            return super().mouseMoveEvent(event)
        cur = event.position().toPoint()
        a = self._to_image_xy(self._last_pos)
        b = self._to_image_xy(cur)
        if a is not None and b is not None:
            x0, y0 = a
            x1, y1 = b
            self.draw_line.emit(x0, y0, x1, y1)
        self._last_pos = cur

    def mouseReleaseEvent(self, event):
        if not self._allow_draw or self.pixmap() is None or self._last_pos is None:
            return super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            cur = event.position().toPoint()
            a = self._to_image_xy(self._last_pos)
            b = self._to_image_xy(cur)
            if a is not None and b is not None:
                self.draw_line.emit(a[0], a[1], b[0], b[1])
        self._last_pos = None


class Home(QWidget):
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

        # brush states
        self.brush_enabled = False
        self.brush_color_rgb = (255, 255, 255)  
        self.brush_size = 8                     
        self.paint_base: np.ndarray | None = None  

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

        # Resize code
        self.resize_btn = QPushButton("Resize…")
        self.resize_btn.clicked.connect(self.open_resize_dialog)

        #Brush code
        brush_title = QLabel("Brush")
        self.paint_toggle_btn = QPushButton("Start Painting")
        self.paint_toggle_btn.setCheckable(True)
        self.paint_toggle_btn.toggled.connect(self.toggle_painting)

        colors = [
            ("White", (255, 255, 255)),
            ("Black", (0, 0, 0)),
            ("Red",   (255, 0, 0)),
            ("Green", (0, 255, 0)),
            ("Blue",  (0, 0, 255)),
            ("Yellow",(255, 255, 0)),
        ]
        self.color_btns: list[QPushButton] = []
        color_grid = QGridLayout()
        color_grid.setHorizontalSpacing(6)
        color_grid.setVerticalSpacing(6)
        for i, (name, rgb) in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: rgb({rgb[0]},{rgb[1]},{rgb[2]});")
            btn.clicked.connect(lambda _, c=rgb: self.set_brush_color(c))
            self.color_btns.append(btn)
            r, cidx = divmod(i, 3) 
            color_grid.addWidget(btn, r, cidx)

        self.clear_paint_btn = QPushButton("Clean up your damn mess")
        self.clear_paint_btn.clicked.connect(self.clear_paint)

        # SAVING button
        self.save_btn = QPushButton("Save…")
        self.save_btn.clicked.connect(self.save_image)

        tools_col = QVBoxLayout()
        tools_col.addWidget(self.drop_label)
        tools_col.addWidget(self.drop_combo_box)
        tools_col.addWidget(self.drop_btn)
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

        #image paintable
        self.preview_label = DrawingLabel("")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setVisible(False)
        self.preview_label.draw_line.connect(self.on_draw_line)

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

    # Brush code
    def toggle_painting(self, enabled: bool):
        self.brush_enabled = enabled
        self.preview_label.set_allow_draw(enabled)
        self.paint_toggle_btn.setText("Stop Painting" if enabled else "Start Painting")
        if enabled and self.img is not None:
            self.paint_base = self.img.copy()
        self.status.setText("Painting is on yo" if enabled else "Painting disabled.")

    def set_brush_color(self, rgb: tuple[int, int, int]):
        self.brush_color_rgb = rgb
        if not self.brush_enabled:
            self.paint_toggle_btn.setChecked(True)

    def clear_paint(self):
        if self.paint_base is not None:
            self.img = self.paint_base.copy()
            self.show_image(self.img) 
            self.status.setText("Cleaned up your mess brah.")

    def on_draw_line(self, x0: int, y0: int, x1: int, y1: int):
        if self.img is None:
            return
        H, W, _ = self.img.shape
        x0 = max(0, min(x0, W - 1)); y0 = max(0, min(y0, H - 1))
        x1 = max(0, min(x1, W - 1)); y1 = max(0, min(y1, H - 1))
        color_rgb = (int(self.brush_color_rgb[0]),
                     int(self.brush_color_rgb[1]),
                     int(self.brush_color_rgb[2]))
        cv2.line(self.img, (x0, y0), (x1, y1), color_rgb,
                 thickness=self.brush_size, lineType=cv2.LINE_AA)
        self.show_image(self.img, preserve_scale=True)

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

        if option == "Grayscale":
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        elif option == "Invert":
            img = 255 - img

        elif option == "Sepia":
            sepia_bgr_kernel = np.array([
                [0.131, 0.534, 0.272],  
                [0.168, 0.686, 0.349], 
                [0.189, 0.769, 0.393],  
            ], dtype=np.float32)
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR).astype(np.float32)
            sep = cv2.transform(bgr, sepia_bgr_kernel)
            sep = np.clip(sep, 0, 255).astype(np.uint8)
            img = cv2.cvtColor(sep, cv2.COLOR_BGR2RGB)

        elif option == "Bone":
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            bone_bgr = cv2.applyColorMap(gray, cv2.COLORMAP_BONE)
            img = cv2.cvtColor(bone_bgr, cv2.COLOR_BGR2RGB)

        self.img = img
        self.paint_base = self.img.copy()  
        self.last_scale = 1.0            
        self.show_image(self.img)
        self.status.setText(f"Applied filter: {option}")

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
