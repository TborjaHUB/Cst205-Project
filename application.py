import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QScrollArea, QLineEdit, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt
import requests
from io import BytesIO
from unsplash_api import UnsplashAPI


class ImageFetcherWorker(QThread):
    """Worker thread for fetching images from Unsplash without blocking the UI"""
    image_fetched = Signal(object)  # Emits PIL Image
    metadata_fetched = Signal(dict)  # Emits metadata dict
    error_occurred = Signal(str)  # Emits error message

    def __init__(self, query: str):
        super().__init__()
        self.query = query
        self.unsplash = UnsplashAPI()

    def run(self):
        try:
            # Get metadata and URL
            metadata = self.unsplash.get_image_with_metadata(self.query)
            if not metadata:
                self.error_occurred.emit(f"No images found for '{self.query}'")
                return

            # Fetch the actual image
            response = requests.get(metadata["url"], timeout=10)
            response.raise_for_status()

            # Convert to PIL Image
            img = Image.open(BytesIO(response.content)).convert("RGBA")

            # Emit signals
            self.image_fetched.emit(img)
            self.metadata_fetched.emit(metadata)

        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Error fetching image: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Error processing image: {str(e)}")


class Home(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dollar Store Photoshop")
        self.resize(900, 600)

        self.image = None
        self.fetcher_thread = None

        self.info = QLabel("WELCOME TO DOLLAR STORE PHOTOSHOP :)")
        self.info.setAlignment(Qt.AlignCenter)

        # Local file open button
        self.open_btn = QPushButton("Open Image")
        self.open_btn.clicked.connect(self.open_image)

        # Unsplash search widgets
        self.search_label = QLabel("Search Unsplash:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter keywords (e.g., 'nature', 'sunset', 'cat')")
        self.search_input.returnPressed.connect(self.fetch_unsplash_image)

        self.search_btn = QPushButton("Get Random Image")
        self.search_btn.clicked.connect(self.fetch_unsplash_image)

        # Image info label for displaying metadata
        self.image_info = QLabel("")
        self.image_info.setAlignment(Qt.AlignCenter)
        self.image_info.setVisible(False)

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

        # Layout for search widgets
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        # Main vertical layout
        v = QVBoxLayout()
        v.addWidget(self.info)
        v.addWidget(self.open_btn)
        v.addLayout(search_layout)
        v.addWidget(self.image_info)
        v.addWidget(self.scroll)
        self.setLayout(v)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return

        img = Image.open(path).convert("RGBA")
        self.image = img

        qimg = ImageQt(img)
        self.preview_label.setPixmap(QPixmap.fromImage(qimg))
        self.preview_label.setVisible(True)
        self.image_info.setVisible(False)
        self.info.setText("Loaded it brah")

    def fetch_unsplash_image(self):
        """Fetch a random image from Unsplash based on user's search query"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search keyword")
            return

        # Disable button during fetch
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Fetching...")
        self.info.setText("Fetching image from Unsplash...")

        # Create and start worker thread
        self.fetcher_thread = ImageFetcherWorker(query)
        self.fetcher_thread.image_fetched.connect(self.on_image_fetched)
        self.fetcher_thread.metadata_fetched.connect(self.on_metadata_fetched)
        self.fetcher_thread.error_occurred.connect(self.on_fetch_error)
        self.fetcher_thread.finished.connect(self.on_fetch_finished)
        self.fetcher_thread.start()

    def on_image_fetched(self, img: Image.Image):
        """Handle successful image fetch"""
        self.image = img
        qimg = ImageQt(img)
        self.preview_label.setPixmap(QPixmap.fromImage(qimg))
        self.preview_label.setVisible(True)

    def on_metadata_fetched(self, metadata: dict):
        """Handle metadata display"""
        author = metadata.get("author", "Unknown")
        description = metadata.get("description", "No description")
        # Truncate long descriptions
        if len(description) > 100:
            description = description[:97] + "..."

        info_text = f"<b>By {author}</b> | {description}"
        self.image_info.setText(info_text)
        self.image_info.setVisible(True)
        self.info.setText(f"✓ Loaded from Unsplash ('{self.search_input.text()}')")

    def on_fetch_error(self, error_message: str):
        """Handle fetch errors"""
        self.info.setText("Error fetching image")
        QMessageBox.critical(self, "Fetch Error", error_message)

    def on_fetch_finished(self):
        """Re-enable button after fetch completes"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Get Random Image")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Home()
    win.show()
    sys.exit(app.exec())