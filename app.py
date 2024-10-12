import sys
import os
import platform
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QSizePolicy, QTextEdit, QFileIconProvider, QScrollArea, QFrame
from PyQt5.QtGui import QIcon, QPixmap, QKeyEvent, QPalette, QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QFileInfo, QTimer, QEvent

import mimetypes
import datetime
import fitz  # PyMuPDF for PDF preview
from docx import Document  # python-docx for DOCX preview
import configparser

class FileLoader(QThread):
    file_loaded = pyqtSignal(str, str)

    def __init__(self, desktop_path):
        super().__init__()
        self.desktop_path = desktop_path

    def run(self):
        for file in os.listdir(self.desktop_path):
            file_path = os.path.join(self.desktop_path, file)
            if os.path.isfile(file_path):
                self.file_loaded.emit(file, file_path)

class PreviewLoader(QThread):
    preview_loaded = pyqtSignal(str, bool)

    def __init__(self, file_path, file_type, start_page=0, pages_to_load=2):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self.start_page = start_page
        self.pages_to_load = pages_to_load

    def run(self):
        preview_text = ""
        has_more = False

        if self.file_type == "application/pdf":
            try:
                with fitz.open(self.file_path) as doc:
                    total_pages = len(doc)
                    for i in range(self.start_page, min(self.start_page + self.pages_to_load, total_pages)):
                        preview_text += doc[i].get_text() + "\n--- Page Break ---\n"
                    has_more = self.start_page + self.pages_to_load < total_pages
            except Exception as e:
                preview_text = f"Error loading PDF: {str(e)}"

        elif self.file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = Document(self.file_path)
                total_paragraphs = len(doc.paragraphs)
                end_paragraph = min(self.start_page + self.pages_to_load * 10, total_paragraphs)
                for i in range(self.start_page, end_paragraph):
                    preview_text += doc.paragraphs[i].text + "\n"
                has_more = end_paragraph < total_paragraphs
            except Exception as e:
                preview_text = f"Error loading DOCX: {str(e)}"

        self.preview_loaded.emit(preview_text, has_more)

class FileCard(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget {
                background-color: #F3ECE0;
                border-radius: 20px;
            }
            QLabel {
                color: #333333;
            }
        """)

        self.title = QLabel("desktop blsh")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold; background-color: transparent; color: #2C3E50;")
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_area.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 15px;
            min-height: 350px;
            padding: 15px;
        """)

        self.icon_background = QFrame()
        self.icon_background.setStyleSheet("""
            background-color: #F3ECE0;
            border-radius: 15px;
            margin: 10px;
        """)
        self.icon_layout = QVBoxLayout(self.icon_background)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(250, 250)
        self.icon_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)

        self.content_layout.addWidget(self.icon_background)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setVisible(False)
        self.preview_text.setStyleSheet("""
            font-size: 16px;
            line-height: 1.5;
            background-color: #FFFFFF;
            padding: 10px;
            border-radius: 10px;
        """)
        self.content_layout.addWidget(self.preview_text)

        self.layout.addWidget(self.content_area)

        self.file_info = QLabel()
        self.file_info.setStyleSheet("font-size: 18px; background-color: transparent; color: #34495E;")
        self.file_info.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.file_info)

        self.update_file_info()

    def update_file_info(self):
        file_info = self.get_file_info()
        self.file_info.setText(f"{file_info['name']}\nSize: {file_info['size']}")

        icon = self.get_file_icon(self.file_path)
        pixmap = icon.pixmap(QSize(200, 200))
        self.icon_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if file_info["type"] in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            self.load_preview()
        else:
            self.preview_text.setVisible(False)
            self.icon_background.setVisible(True)
            self.preview_text.setText(f"Type: {file_info['type']}\nModified: {file_info['modified']}")

    def get_file_icon(self, file_path):
        icon_provider = QFileIconProvider()
        file_info = QFileInfo(file_path)
        icon = icon_provider.icon(file_info)
        
        if icon.isNull():
            return QApplication.style().standardIcon(QStyle.SP_FileIcon)
        
        return icon

    def get_file_info(self):
        file_stats = os.stat(self.file_path)
        file_size = file_stats.st_size
        last_modified = datetime.datetime.fromtimestamp(file_stats.st_mtime)
        mime_type, _ = mimetypes.guess_type(self.file_path)
        
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        return {
            "name": os.path.basename(self.file_path),
            "type": mime_type if mime_type else "Unknown",
            "size": size_str,
            "modified": last_modified.strftime("%Y-%m-%d %H:%M:%S")
        }

    def load_preview(self):
        file_info = self.get_file_info()
        self.preview_loader = PreviewLoader(self.file_path, file_info["type"])
        self.preview_loader.preview_loaded.connect(self.on_preview_loaded)
        self.preview_loader.start()

    def on_preview_loaded(self, preview_text, has_more):
        self.preview_text.setText(preview_text)
        self.preview_text.setVisible(True)
        self.icon_background.setVisible(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop File Swiper")
        self.setGeometry(100, 100, 450, 750)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        self.button_layout = QHBoxLayout()
        self.discard_button = QPushButton("No")
        self.keep_button = QPushButton("Yes")
        self.discard_button.clicked.connect(self.on_discard)
        self.keep_button.clicked.connect(self.on_keep)
        self.discard_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border-radius: 25px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #FF4040;
            }
        """)
        self.keep_button.setStyleSheet("""
            QPushButton {
                background-color: #FFD93D;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border-radius: 25px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #FFC000;
            }
        """)
        self.button_layout.addWidget(self.discard_button)
        self.button_layout.addWidget(self.keep_button)
        self.layout.addLayout(self.button_layout)

        self.arrow_layout = QHBoxLayout()
        self.left_arrow_text = QLabel("← User said No")
        self.right_arrow_text = QLabel("User said Yes →")
        arrow_style = "font-size: 18px; color: #888; font-weight: bold;"
        self.left_arrow_text.setStyleSheet(arrow_style)
        self.right_arrow_text.setStyleSheet(arrow_style)
        self.arrow_layout.addWidget(self.left_arrow_text, alignment=Qt.AlignCenter)
        self.arrow_layout.addWidget(self.right_arrow_text, alignment=Qt.AlignCenter)
        self.layout.addLayout(self.arrow_layout)

        self.desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        self.file_loader = FileLoader(self.desktop_path)
        self.file_loader.file_loaded.connect(self.add_file)
        self.file_loader.start()

        QApplication.instance().installEventFilter(self)

    def add_file(self, file_name, file_path):
        card = FileCard(file_path)
        self.stack.addWidget(card)
        if self.stack.count() == 1:
            self.stack.setCurrentIndex(0)

    def on_discard(self):
        self.left_arrow_text.setStyleSheet("font-size: 18px; color: #FF6B6B; font-weight: bold;")
        QTimer.singleShot(300, lambda: self.left_arrow_text.setStyleSheet("font-size: 18px; color: #888; font-weight: bold;"))
        self.move_to_next_file()

    def on_keep(self):
        self.right_arrow_text.setStyleSheet("font-size: 18px; color: #FFD93D; font-weight: bold;")
        QTimer.singleShot(300, lambda: self.right_arrow_text.setStyleSheet("font-size: 18px; color: #888; font-weight: bold;"))
        self.move_to_next_file()

    def move_to_next_file(self):
        current_index = self.stack.currentIndex()
        if current_index < self.stack.count() - 1:
            self.stack.setCurrentIndex(current_index + 1)
        else:
            self.stack.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key_Left:
                self.on_discard()
                return True
            elif key_event.key() == Qt.Key_Right:
                self.on_keep()
                return True
        return super().eventFilter(obj, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())