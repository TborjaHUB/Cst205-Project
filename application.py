import sys
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QScrollArea, QLineEdit, QComboBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt

class Home(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dollar Store Photoshop")
        self.resize(900, 600)

        self.image = None

        self.info = QLabel("WELCOME TO DOLLAR STORE PHOTOSHOP :)")
        self.info.setAlignment(Qt.AlignCenter)

        self.open_btn = QPushButton("Open Image")
        self.open_btn.clicked.connect(self.open_image)

        self.preview_label = QLabel("")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setVisible(False)

        assetspath = Path(__file__).parent / "assets"
        logopath = assetspath / "_dollarstore.png"
        if logopath.exists():
            myLOGO = QPixmap(str(logopath))
            if not myLOGO.isNull():
                self.preview_label.setPixmap(
                    myLOGO.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.preview_label.setVisible(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.preview_label)

            # Drop Down Menu Options
        self.drop_label = QLabel("Image Manipulation")
        self.drop_down_list = ["Choose an option", "Size Up", "Shrink", "Crop"]
        self.drop_combo_box = QComboBox()
        self.drop_combo_box.addItems(self.drop_down_list)

        self.drop_btn = QPushButton("Submit")


        v_drop_box = QVBoxLayout()
        v_drop_box.addWidget(self.drop_label)
        v_drop_box.addWidget(self.drop_combo_box)
        v_drop_box.addWidget(self.drop_btn)
        v_drop_box.setAlignment(Qt.AlignLeft)


        v = QVBoxLayout()
        v.addWidget(self.info)
        v.addWidget(self.open_btn)
        v.addLayout(v_drop_box)
        v.addWidget(self.scroll)

        self.setLayout(v)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return
        
         #Image being converted into openCV
        img = cv2.imread(path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        self.image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

        qimg = self.image
        self.preview_label.setPixmap(QPixmap.fromImage(qimg))
        self.preview_label.setVisible(True)
        self.info.setText("Loaded it brah")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Home()
    win.show()
    sys.exit(app.exec())