import sys
import json
import numpy as np
import pandas as pd
import websocket
from Conexión import WebSocketThread
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime,  pyqtSignal, QThread, QTimer
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
from MainGrafico import leer_y_graficar, update_plot_window, procesar_y_graficar
from MainInicio import init_inicio 
from MainReport import init_report_page,show_report_page
from RealTimeGraph import RealTimeGraph
from datetime import datetime

class MainWindow(QWidget):        
    def iniciar_medicion_tiempo_real(self):
        if self.websocket_thread is None or not self.websocket_thread.isRunning():
            self.websocket_thread = WebSocketThread("ws://172.20.10.2:81")  # Dirección de tu ESP32
            self.websocket_thread.data_received.connect(self.on_data_received_rt)
            self.websocket_thread.connection_status.connect(self.on_connection_status_rt)
            self.websocket_thread.start()

            self.t0_rt = None  # Tiempo base para normalizar

            # ✅ Limpiar gráfico
            if hasattr(self, 'graph_rt'):
                self.graph_rt.clear()

            self.timestamps_rt = []
            self.braquial_vals_rt = []
            self.tibial_vals_rt = []
            self.measuring = True

            self.iniciar_medicion_button.setText("Midiendo...")
            self.iniciar_medicion_button.setEnabled(False)
        else:
            QMessageBox.information(self, "Estado", "Ya hay una medición en curso.")
        
    def on_connection_status_rt(self, status):
        print(f"[Estado WebSocket] {status}")
        if status == "Conectado":
            duracion = 35  # segundos
            comando = {"action": "start_measurement", "duration": duracion}
            self.websocket_thread.send_command(comando)

            # Configurar un temporizador para detener medición
            self.timer_medicion = QTimer()
            self.timer_medicion.timeout.connect(self.finalizar_medicion_rt)
            self.timer_medicion.setSingleShot(True)
            self.timer_medicion.start(duracion * 1000)

    def on_data_received_rt(self, data):
        if "pin32" in data and "pin35" in data and "timestamp" in data:
            timestamp = data["timestamp"]

            # Establecer t0 una vez
            if self.t0_rt is None:
                self.t0_rt = timestamp

            t = timestamp - self.t0_rt  # normalizar a partir de 0

            v_braquial = (data["pin32"] / 4095.0) * 3.3
            v_tibial = (data["pin35"] / 4095.0) * 3.3

            self.timestamps_rt.append(timestamp / 1000)
            self.braquial_vals_rt.append(v_braquial)
            self.tibial_vals_rt.append(v_tibial)

            # Usar el nuevo gráfico con PyQtGraph
            self.graph_rt.update_plot(t, v_braquial, v_tibial)

    def finalizar_medicion_rt(self):
        if self.websocket_thread:
            self.websocket_thread.send_command({"action": "stop_measurement"})
            self.websocket_thread.stop()
            self.websocket_thread = None

        self.iniciar_medicion_button.setText("Iniciar medición en tiempo real")
        self.iniciar_medicion_button.setEnabled(True)
        self.measuring = False

        try:
            t_array = np.array(self.timestamps_rt)
            b_array = np.array(self.braquial_vals_rt)
            t_array_ = np.array(self.tibial_vals_rt)
            altura_cm = float(self.altura)  # Usar atributo de altura cargada

            procesar_y_graficar(self, t_array, b_array, t_array_, altura_cm)

        except Exception as e:
            print(f"[ERROR procesamiento final] {e}")
            self.vop_box.setText("VOP: Error")
            self.fc_box.setText("Frecuencia: --")
            self.cavi_box.setText("CAVI: --")
            self.report_button.setEnabled(False)
            self.export_image_button.setEnabled(False)
        
        # Guardar archivo de texto al finalizar
        timestamp_str = datetime.now().strftime("%Y%m%d_M%H%M%S")
        filename = f"mediciones_{timestamp_str}.txt"
        try:
            with open(filename, 'w') as f:
                for line in self.logged_lines:
                    f.write(line + '\n')
            print(f"Archivo guardado: {filename}")
        except Exception as e:
            print(f"Error al guardar archivo: {e}")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARTEMIS")
        self.setGeometry(50, 50, 1000, 500)
        self.websocket_thread = None
        self.measuring = False
        """self.graph_rt = None"""  # Gráfico para medición en vivo
        self.graph_rt = RealTimeGraph()
        self.timestamps = []
        self.braquial_vals_rt = []
        self.tibial_vals_rt = []


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

