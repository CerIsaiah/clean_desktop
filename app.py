import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QFileIconProvider, QStyle, QFrame, QTextEdit, QScrollArea
from PyQt5.QtGui import QIcon, QPixmap, QKeyEvent, QColor, QPainter, QImage, QFont, QPalette
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QFileInfo, QEvent, QRect, QTimer

import fitz  # PyMuPDF for PDF preview
from docx import Document  # python-docx for DOCX preview

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

class RoundedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roundedWidget")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#F0F0F0"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

class FileCard(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-radius: 20px;
            }
            QLabel {
                color: #333333;
            }
        """)

        self.title = QLabel("Desktop File")
        self.title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            background-color: transparent;
            color: #2C3E50;
            padding: 10px;
        """)
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        self.content_area = RoundedWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.layout.addWidget(self.content_area)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.content_layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.content_widget_layout = QVBoxLayout(self.content_widget)
        self.scroll_area.setWidget(self.content_widget)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.content_widget_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setVisible(False)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                font-size: 16px;
                line-height: 1.6;
                background-color: #F9F9F9;
                padding: 15px;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }
        """)
        self.content_widget_layout.addWidget(self.preview_text)

        self.file_info = QLabel()
        self.file_info.setStyleSheet("""
            font-size: 18px;
            background-color: transparent;
            color: #34495E;
            padding: 10px;
        """)
        self.file_info.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.file_info)

        self.update_file_info()

    def update_file_info(self):
        file_info = self.get_file_info()
        self.file_info.setText(f"{file_info['name']}\n{file_info['size']}")

        self.load_preview()

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
        
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        return {
            "name": os.path.basename(self.file_path),
            "size": size_str,
        }

    def load_preview(self):
        file_extension = os.path.splitext(self.file_path)[1].lower()
        
        if file_extension in ['.png', '.jpg', '.jpeg']:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.icon_label.setVisible(True)
                self.preview_text.setVisible(False)
            else:
                self.icon_label.setText("Error loading image")
        elif file_extension == '.pdf':
            try:
                with fitz.open(self.file_path) as doc:
                    text = ""
                    for page in doc:
                        text += page.get_text()
                        if len(text) > 1000:
                            break
                    self.preview_text.setText(text)
                    self.icon_label.setVisible(False)
                    self.preview_text.setVisible(True)
            except Exception as e:
                self.preview_text.setText(f"Error loading PDF: {str(e)}")
                self.icon_label.setVisible(False)
                self.preview_text.setVisible(True)
        elif file_extension == '.docx':
            try:
                doc = Document(self.file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                self.preview_text.setText(text[:1000] + "..." if len(text) > 1000 else text)
                self.icon_label.setVisible(False)
                self.preview_text.setVisible(True)
            except Exception as e:
                self.preview_text.setText(f"Error loading DOCX: {str(e)}")
                self.icon_label.setVisible(False)
                self.preview_text.setVisible(True)
        else:
            icon = self.get_file_icon(self.file_path)
            pixmap = icon.pixmap(QSize(200, 200))
            self.icon_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.icon_label.setVisible(True)
            self.preview_text.setVisible(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop File Swiper")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Undo button and label
        undo_container = QWidget()
        undo_layout = QVBoxLayout(undo_container)
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.on_undo)
        self.undo_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                border-radius: 15px;
                padding: 10px 20px;
                background-color: #3498DB;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #2573A7;
            }
        """)
        self.undo_label = QLabel("↑ Up Arrow")
        self.undo_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7F8C8D;
                margin-top: 5px;
            }
        """)
        self.undo_label.setAlignment(Qt.AlignCenter)
        undo_layout.addWidget(self.undo_button)
        undo_layout.addWidget(self.undo_label)
        undo_container.setLayout(undo_layout)
        self.layout.addWidget(undo_container, alignment=Qt.AlignRight)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack, 1)

        self.button_layout = QHBoxLayout()
        self.discard_button = QPushButton("Put in Clutter")
        self.keep_button = QPushButton("Keep on Desktop")
        self.discard_button.clicked.connect(self.on_discard)
        self.keep_button.clicked.connect(self.on_keep)
        button_style = """
            QPushButton {
                font-size: 22px;
                font-weight: bold;
                border-radius: 25px;
                padding: 15px 30px;
                border: none;
            }
            QPushButton:hover {
                background-color: %s;
            }
            QPushButton:pressed {
                background-color: %s;
            }
        """
        self.discard_button.setStyleSheet(button_style % ("#E74C3C", "#C0392B") + "QPushButton { background-color: #FF4040; color: white; }")
        self.keep_button.setStyleSheet(button_style % ("#F1C40F", "#F39C12") + "QPushButton { background-color: #FFC000; color: white; }")

        # Create vertical layouts for buttons and their labels
        discard_layout = QVBoxLayout()
        keep_layout = QVBoxLayout()

        # Add buttons to their respective layouts
        discard_layout.addWidget(self.discard_button)
        keep_layout.addWidget(self.keep_button)

        # Create and style labels for keyboard commands
        self.discard_label = QLabel("← Left Arrow")
        self.keep_label = QLabel("→ Right Arrow")
        label_style = """
            QLabel {
                font-size: 14px;
                color: #7F8C8D;
                margin-top: 5px;
            }
        """
        self.discard_label.setStyleSheet(label_style)
        self.keep_label.setStyleSheet(label_style)
        self.discard_label.setAlignment(Qt.AlignCenter)
        self.keep_label.setAlignment(Qt.AlignCenter)

        # Add labels to their respective layouts
        discard_layout.addWidget(self.discard_label)
        keep_layout.addWidget(self.keep_label)

        # Add the vertical layouts to the main button layout
        self.button_layout.addLayout(discard_layout)
        self.button_layout.addLayout(keep_layout)

        self.layout.addLayout(self.button_layout)

        self.desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        self.clutter_folder = os.path.join(self.desktop_path, "Desktop Clutter")
        if not os.path.exists(self.clutter_folder):
            os.makedirs(self.clutter_folder)

        self.file_loader = FileLoader(self.desktop_path)
        self.file_loader.file_loaded.connect(self.add_file)
        self.file_loader.start()

        self.undo_stack = []
        self.current_files = []

        self.is_fullscreen = False
        QApplication.instance().installEventFilter(self)

        # Set initial size based on screen size
        self.resize_window()

    def resize_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.5)
        height = int(screen.height() * 0.8)
        self.setGeometry((screen.width() - width) // 2, (screen.height() - height) // 2, width, height)

    def add_file(self, file_name, file_path):
        card = FileCard(file_path)
        self.stack.addWidget(card)
        self.current_files.append(file_path)
        if self.stack.count() == 1:
            self.stack.setCurrentIndex(0)

    def on_discard(self):
        self.move_file_to_clutter()
        self.move_to_next_file()

    def on_keep(self):
        if self.current_files:
            kept_file = self.current_files.pop(0)
            self.undo_stack.append(("keep", kept_file))
        self.move_to_next_file()

    def on_undo(self):
        if self.undo_stack:
            action, file_path = self.undo_stack.pop()
            if action == "discard":
                file_name = os.path.basename(file_path)
                new_path = os.path.join(self.desktop_path, file_name)
                try:
                    shutil.move(file_path, new_path)
                    print(f"Moved {file_name} back to Desktop")
                    self.add_file(file_name, new_path)
                except Exception as e:
                    print(f"Error moving file back: {str(e)}")
            elif action == "keep":
                self.current_files.insert(0, file_path)
                card = FileCard(file_path)
                self.stack.insertWidget(0, card)
                self.stack.setCurrentIndex(0)

    def move_file_to_clutter(self):
        if self.current_files:
            file_path = self.current_files.pop(0)
            file_name = os.path.basename(file_path)
            new_path = os.path.join(self.clutter_folder, file_name)
            
            try:
                shutil.move(file_path, new_path)
                print(f"Moved {file_name} to Desktop Clutter folder")
                self.undo_stack.append(("discard", new_path))
            except Exception as e:
                print(f"Error moving file: {str(e)}")

    def move_to_next_file(self):
        if self.stack.count() > 0:
            self.stack.removeWidget(self.stack.widget(0))
        
        if self.stack.count() > 0:
            self.stack.setCurrentIndex(0)
        else:
            self.close()

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.resize_window()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

    def highlight_label(self, label, color):
        label.setStyleSheet(f"QLabel {{ font-size: 14px; color: {color}; margin-top: 5px; font-weight: bold; }}")
        QTimer.singleShot(200, lambda: label.setStyleSheet("QLabel { font-size: 14px; color: #7F8C8D; margin-top: 5px; }"))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key_Left:
                self.on_discard()
                self.highlight_label(self.discard_label, "#FF4040")
                return True
            elif key_event.key() == Qt.Key_Right:
                self.on_keep()
                self.highlight_label(self.keep_label, "#FFC000")
                return True
            elif key_event.key() == Qt.Key_Up:
                self.on_undo()
                self.highlight_label(self.undo_label, "#3498DB")
                return True
            elif key_event.key() == Qt.Key_F11:
                self.toggle_fullscreen()
                return True
        elif event.type() == QEvent.Resize:
            # Adjust content size when window is resized
            for i in range(self.stack.count()):
                card = self.stack.widget(i)
                if isinstance(card, FileCard):
                    card.icon_label.setFixedSize(self.width() // 3, self.height() // 3)
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()  # Ensure the main window has focus to capture key events
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
   
    
    app.setStyle("Fusion")  # Use Fusion style for a modern look
    
    # Set a custom font for the entire application
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())