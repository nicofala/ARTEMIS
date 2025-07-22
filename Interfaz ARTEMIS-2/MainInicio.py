from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime

from scipy.signal import butter, filtfilt, find_peaks
from ArtemisHeader import ArtemisHeader
from ScalableImage import ScalableImage


     
     
def init_inicio(self):
        self.artemis_header = ArtemisHeader(self) # Instantiate the reusable header
        
        # Set a minimum height for the QLineEdits
        min_input_height = 35 # Adjust this value as needed for desired height
        self.nombre_input = QLineEdit()
        self.nombre_input.setMinimumHeight(min_input_height)
        self.nombre_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.apellido_input = QLineEdit()
        self.apellido_input.setMinimumHeight(min_input_height)
        self.apellido_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.edad_input = QLineEdit()
        self.edad_input.setMinimumHeight(min_input_height)
        self.edad_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.altura_input = QLineEdit()
        self.altura_input.setMinimumHeight(min_input_height)
        self.altura_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.segmento1_input = QLineEdit()
        self.segmento1_input.setMinimumHeight(min_input_height)
        self.segmento1_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.segmento2_input = QLineEdit()
        self.segmento2_input.setMinimumHeight(min_input_height)
        self.segmento2_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.sistolica_input = QLineEdit()
        self.sistolica_input.setMinimumHeight(min_input_height)
        self.sistolica_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.diastolica_input = QLineEdit()
        self.diastolica_input.setMinimumHeight(min_input_height)
        self.diastolica_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # For "Observación", consider QTextEdit if multi-line input is expected
        self.observacion_input = QLineEdit()
        self.observacion_input.setMinimumHeight(min_input_height) # Make it taller
        self.observacion_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        form = QFormLayout()
        form.addRow("Nombre:", self.nombre_input)
        form.addRow("Apellido:", self.apellido_input)
        form.addRow("Edad:", self.edad_input)
        form.addRow("Altura (cm):", self.altura_input)
        form.addRow("Segmento 2(cm):", self.segmento1_input)
        form.addRow("Segmento 3(cm):", self.segmento2_input)
        form.addRow("Presión Sistólica (mmHg):", self.sistolica_input)
        form.addRow("Presión Diastólica (mmHg):", self.diastolica_input)
        form.addRow("Observación:", self.observacion_input)

        img_label = ScalableImage("anatomia.jpg", parent=self)
        #img_label.setScaledContents(True)  # Hace que la imagen se ajuste al tamaño del QLabel
        img_label.setAlignment(Qt.AlignCenter) # Centrar la imagen
        #img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Main layout for the initial screen
        layout = QVBoxLayout()
        layout.addWidget(self.artemis_header) # Add the reusable header at the top
        layout.addSpacing(15) # Space between header and image/form
        
        # We'll put the image and the form side-by-side in a QHBoxLayout
        image_and_form_hbox = QHBoxLayout()
        
        # Image part
        image_vbox = QVBoxLayout()
        image_vbox.addWidget(img_label, alignment=Qt.AlignCenter)
        image_vbox.addStretch(1) # Push image to top if this column has extra space
        image_and_form_hbox.addLayout(image_vbox, stretch=1) # Give image some stretch

        # Form part
        form_vbox = QVBoxLayout()
        form_vbox.addLayout(form)
        form_vbox.addSpacing(20)

        self.continuar_btn = QPushButton("Continuar")
        self.continuar_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.continuar_btn.clicked.connect(self.validar)
        
        # Add the button to the same vertical layout as the form
        form_vbox.addWidget(self.continuar_btn, alignment=Qt.AlignCenter)
        form_vbox.addStretch(1) # Push form to top if this column has extra space
        image_and_form_hbox.addLayout(form_vbox, stretch=2) # Give form more stretch

        layout.addLayout(image_and_form_hbox, stretch=1)
        layout.addStretch(1) 
        
        contenedor = QWidget()
        contenedor.setLayout(layout)
        self.stacked_layout.addWidget(contenedor)
