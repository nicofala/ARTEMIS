import sys
import json
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import butter, filtfilt, find_peaks
from ArtemisHeader import ArtemisHeader
from ScalableImage import ScalableImage
from PulseGraph import PulseGraph
from ReportPage import ReportPage
from ReportWindow import ReportWindow
from Procesamiento import lowpass_filter, highpass_filter, calcular_cavi, calcular_vop, normalize
from MainReport import init_report_page, show_report_page


def init_app(self):
        self.artemis_header_app = ArtemisHeader(self)

        self.graph = PulseGraph(self)
        self.scroll_slider = QSlider(Qt.Horizontal)
        self.scroll_slider.setEnabled(False)
        self.scroll_slider.setMinimum(0)
        # El slider maneja valores enteros, por lo que multiplicamos y dividimos por 100 para simular decimales.
        self.scroll_slider.valueChanged.connect(lambda val: self.update_plot_window(val / 100.0)) 
        
        # Datos del paciente en pantalla 2
        self.nombre_label = QLabel()
        self.edad_label = QLabel()
        self.altura_label = QLabel()
        self.observacion_label = QLabel()
        self.fecha_hora_label = QLabel() # New label for date and time

        datos_container_widget = QWidget()
        datos_container_widget.setFixedHeight(80) # Ajusta este valor a la altura deseada (ej. 80px)
        
        datos_layout = QHBoxLayout(datos_container_widget)
        datos_layout.setContentsMargins(10, 10, 10, 10) # Margen interno si quieres
        datos_container_widget.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 5px;") 

        for label in [self.nombre_label, self.edad_label, self.altura_label, self.observacion_label]:
            label.setStyleSheet("font-weight: bold;")
            datos_layout.addWidget(label)

        # Add stretch to push labels to the left/distribute space evenly
        datos_layout.addStretch(1) 

        # Recuadros para VOP y FC
        self.vop_box = QLabel("VOP: -- m/s")
        self.fc_box = QLabel("Frecuencia: -- bpm")
        self.cavi_box = QLabel("CAVI: --") # New QLabel for CAVI
        for box in [self.vop_box, self.fc_box, self.cavi_box]:
            box.setAlignment(Qt.AlignCenter)
            box.setFixedHeight(50)
            box.setStyleSheet("""
                background-color: #dbeafe;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            """)

        resultado_layout = QVBoxLayout()
        resultado_layout.addWidget(self.vop_box, stretch=1)
        resultado_layout.addWidget(self.fc_box, stretch=1)
        resultado_layout.addWidget(self.cavi_box, stretch=1) # Add CAVI box
        resultado_layout.addSpacing(10)
        
        #Exportar Imagen
        self.export_image_button = QPushButton("Exportar Imagen")
        self.export_image_button.setStyleSheet("background-color: #00ADB5; color: white; font-weight: bold;")
        self.export_image_button.clicked.connect(self.export_image)
        self.export_image_button.setEnabled(False) # Disable until data is loaded
        resultado_layout.addWidget(self.export_image_button)

        # Botones
        volver_btn = QPushButton("Volver")
        volver_btn.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(0))
        volver_btn.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold;")

        start_button = QPushButton("Cargar archivo")
        start_button.setStyleSheet("background-color: #007bff; color: white;")
        start_button.clicked.connect(self.leer_y_graficar)

        salir_button = QPushButton("Salir")
        salir_button.setStyleSheet("background-color: #dc3545; color: white;")
        salir_button.clicked.connect(self.close)

        # Botón para el informe
        self.report_button = QPushButton("Ver Informe VOP")
        self.report_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        
        # Conectar el botón al nuevo método show_report
        self.report_button.clicked.connect(self.show_report_page)
        self.report_button.setEnabled(False) # Deshabilitado hasta que se carguen datos

        export_hl7_button = QPushButton("Exportar HL7")
        export_hl7_button.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold;")
        export_hl7_button.clicked.connect(self.exportar_hl7)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(volver_btn)
        btn_layout.addWidget(start_button)
        btn_layout.addWidget(self.report_button) # Agrega el botón al layout de botones
        btn_layout.addWidget(export_hl7_button)
        btn_layout.addWidget(salir_button)

        # Layout para la parte derecha (info del paciente, resultados, botones)
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addLayout(resultado_layout)
        right_panel_layout.addSpacing(10)

        # Layout para el gráfico y el slider
        graph_and_slider_layout = QVBoxLayout()
        graph_and_slider_layout.addWidget(self.graph, stretch=3)
        graph_and_slider_layout.addWidget(self.scroll_slider, stretch=1) # Agregar el slider al layout

        # Layout principal de la segunda pantalla
        hbox = QHBoxLayout()
        hbox.addLayout(graph_and_slider_layout, stretch=3) # Usar el nuevo layout aquí
        hbox.addSpacing(10)
        hbox.addLayout(right_panel_layout, stretch=2)

        # Main layout for the second screen
        main_app_layout = QVBoxLayout()
        main_app_layout.addWidget(self.artemis_header_app) # Add the reusable header
        main_app_layout.addWidget(datos_container_widget) # Top third for data
        main_app_layout.addLayout(hbox, stretch=1) # Middle third for graph/VOP/FC (more space)
        main_app_layout.addSpacing(20)
        main_app_layout.addLayout(btn_layout, stretch=1) # Bottom third for buttons
        
        contenedor = QWidget()
        contenedor.setLayout(main_app_layout)
        self.stacked_layout.addWidget(contenedor)
