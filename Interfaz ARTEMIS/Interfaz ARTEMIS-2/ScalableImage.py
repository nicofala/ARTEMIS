from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime



class ScalableImage(QLabel):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.original_pixmap = QPixmap(image_path)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def resizeEvent(self, event):
        if not self.original_pixmap.isNull():
            max_height = int(self.parent().height() * 0.75)  # Usa el 40% del alto disponible
            max_width = self.parent().width() // 2          # Usa la mitad del ancho disponible
            scaled = self.original_pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
        super().resizeEvent(event)
