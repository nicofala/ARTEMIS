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
from MainExportar import export_image,exportar_hl7
from MainValidacion import validar, set_field_error_style
from MainInicioApp import init_app
from MainGrafico import leer_y_graficar, update_plot_window
from MainInicio import init_inicio 
from MainReport import init_report_page,show_report_page



class MainWindow(QWidget):        
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARTEMIS")
        self.setGeometry(50, 50, 1000, 500)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#FFCCCC"))
        self.setPalette(palette)

        self.setStyleSheet("""
            QLabel { 
                font-family: 'Verdana'; /* Cambia 'Verdana' a tu fuente preferida */
                font-size: 14pt;      /* Aumenta el tamaño de la fuente para las etiquetas */
                font-weight: bold;    /* Opcional: para que las etiquetas sean más visibles */
            } 
            QLineEdit { 
                font-family: 'Verdana'; /* Mismo cambio de fuente para los campos de texto */
                font-size: 14pt;      /* Aumenta el tamaño de la fuente para los campos de texto */
            }
            QPushButton {
                font-size: 14pt; /* Aumenta el tamaño de la fuente para los botones también */
            }
            #artemisTitleLabel {
                font-family: 'Brush Script MT'; /* Puedes cambiar la fuente aquí */
                font-size: 36pt;            /* ¡Ajusta este tamaño para que sea grande! */
                font-weight: bold;
                color: #800080; /* Opcional: un color diferente para el título, por ejemplo, púrpura */
            }
        """)


        self.stacked_layout = QStackedLayout()
        self.init_inicio()
        self.init_app()
        self.init_report_page() # Inicializar la página del informe
        self.setLayout(self.stacked_layout)
        
        # Atributos para almacenar los datos brutos y filtrados
        self.t_vals_raw = []
        self.braquial_vals_raw = []
        self.tibial_vals_raw = []
        self.braquial_vals_filt = []
        self.tibial_vals_filt = []
        
    def init_inicio(self):
        init_inicio(self) 
    
    def set_field_error_style(self, line_edit, is_error):
        set_field_error_style(self, line_edit, is_error)


    def validar(self):
        validar(self)

    def init_app(self):
        init_app(self)

    def init_report_page(self):
        init_report_page(self)

    def show_report_page(self):
        show_report_page(self)

    def leer_y_graficar(self):
        leer_y_graficar(self)
    
    def update_plot_window(self, start_time):
        update_plot_window(self, start_time)

    def exportar_hl7(self):
        exportar_hl7(self)
    
    def export_image(self):
        export_image(self)