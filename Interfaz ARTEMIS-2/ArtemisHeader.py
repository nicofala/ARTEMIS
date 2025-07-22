from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt


class ArtemisHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # ARTEMIS title label
        title_label = QLabel("ARTEMIS")
        #title_label.setFont(QFont("Cursive Elegant", 48, QFont.Bold))
        title_label.setObjectName("artemisTitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white;") # Text color for ARTEMIS title

        layout.addWidget(title_label)
        layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins for the layout

        # Set the background color for the header widget itself
        self.setStyleSheet("background-color: #4B0082; padding: 10px;") # Dark purple background with padding
        self.setFixedHeight(70) # Fixed height for the header
