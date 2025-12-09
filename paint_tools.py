import numpy as np
import cv2

from PySide6.QtWidgets import QLabel, QPushButton, QGridLayout
from PySide6.QtCore import Qt, QPoint, QRect, Signal


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


class PaintMixin:
    def setup_painting(self):
        
        self.brush_enabled = False
        self.brush_color_rgb = (255, 255, 255)
        self.brush_size = 8
        self.paint_base: np.ndarray | None = None

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

        #image paintable
        self.preview_label = DrawingLabel("")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setVisible(False)
        self.preview_label.draw_line.connect(self.on_draw_line)

        return brush_title, color_grid

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