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
from ScalableImage import ScalableImage
from Procesamiento import lowpass_filter, highpass_filter, calcular_cavi, calcular_vop, normalize



def leer_y_graficar(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Text Files (*.txt)")
        if not path:
            return

        try:
            altura_cm = float(self.altura)
        except ValueError:
            QMessageBox.warning(self, "Entrada inválida", "La altura debe ser un número válido.")
            return

        datos = []
        try:
            with open(path, 'r') as archivo:
                for linea in archivo:
                    if "Datos recibidos de Arduino:" in linea:
                        try:
                            json_str = linea.strip().split("Datos recibidos de Arduino: ")[1]
                            dato = json.loads(json_str)
                            if all(k in dato for k in ["t", "braquial", "tibial"]):
                                datos.append({
                                    "t": float(dato["t"]),
                                    "braquial": float(dato["braquial"]),
                                    "tibial": float(dato["tibial"])
                                })
                        except Exception:
                            continue
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo {path}")
            return

        if not datos:
            QMessageBox.warning(self, "Sin datos", "No se encontraron datos válidos.")
            return

        fs=50
        t0 = datos[0]["t"]
        self.t_vals_raw = np.array([(d["t"]-t0) / 1000 for d in datos])
        self.braquial_vals_raw = np.array([d["braquial"] for d in datos])
        self.tibial_vals_raw = np.array([d["tibial"] for d in datos])
        
        # Guardar las señales filtradas una sola vez
        self.braquial_vals_filt = lowpass_filter(highpass_filter(self.braquial_vals_raw, fs), fs)
        self.tibial_vals_filt = lowpass_filter(highpass_filter(self.tibial_vals_raw, fs), fs)

        # Calcular los límites del eje Y de todas las señales filtradas
        all_signals_min = min(np.min(self.braquial_vals_filt), np.min(self.tibial_vals_filt))
        all_signals_max = max(np.max(self.braquial_vals_filt), np.max(self.tibial_vals_filt))

        # Añadir un pequeño margen para que la línea no esté pegada al borde
        margin = (all_signals_max - all_signals_min) * 0.1 
        self.graph.y_min = all_signals_min - margin
        self.graph.y_max = all_signals_max + margin

        # Mostrar los primeros 5 segundos
        self.update_plot_window(0)

        # Ajustar slider de scroll
        duracion = self.t_vals_raw[-1]
        if duracion > 5:
            # Multiplicar por 100 para que el slider maneje enteros y luego dividir en update_plot_window
            self.scroll_slider.setMaximum(int((duracion - 5) * 100)) 
            self.scroll_slider.setEnabled(True)
        else:
            self.scroll_slider.setEnabled(False)
            self.scroll_slider.setValue(0) # Resetear el slider si no es necesario

        vop_list, freq_bpm = calcular_vop(datos, altura_cm)
        if vop_list and hasattr(self, 'subject_sistolica') and hasattr(self, 'subject_diastolica'):
            vop_median = np.median(vop_list)
            self.vop_box.setText(f"VOP: {vop_median:.2f} m/s")
            self.fc_box.setText(f"Frecuencia: {freq_bpm:.0f} bpm")
            
            # Calculate CAVI
            cavi_value = calcular_cavi(vop_median, self.subject_sistolica, self.subject_diastolica)
            self.subject_cavi_result = cavi_value # Store for display/report

            if cavi_value is not None:
                self.cavi_box.setText(f"CAVI: {cavi_value:.2f}") # New QLabel for CAVI
            else:
                self.cavi_box.setText("CAVI: N/A")

            # Update current date and time
            self.fecha_hora_label.setText(f"Fecha y Hora: {QDateTime.currentDateTime().toString(Qt.DefaultLocaleLongDate)}")
            
            # Guardar la VOP y edad del sujeto para el informe y exportación
            self.subject_vop_result = vop_median
            self.subject_fc_result = freq_bpm

            try:
                self.subject_age_result = int(self.edad)
            except ValueError:
                self.subject_age_result = None # Manejar caso donde la edad no es un número
            self.report_button.setEnabled(True) # Habilitar el botón del informe
            self.export_image_button.setEnabled(True) # Habilitar el botón de exportación
        else:
            self.vop_box.setText("VOP: -- m/s")
            self.fc_box.setText("Frecuencia: -- bpm")
            self.cavi_box.setText("CAVI: --") # Initialize CAVI display
            self.subject_vop_result = None
            self.subject_age_result = None
            self.subject_cavi_result = None # Reset CAVI
            self.report_button.setEnabled(False) # Deshabilitar el botón si no hay VOP
            self.export_image_button.setEnabled(False) # Deshabilitar el botón de exportación
    
def update_plot_window(self, start_time):
        # Usar los datos filtrados para graficar
        if not hasattr(self, "t_vals_raw") or not self.t_vals_raw.size > 0:
            return 
        
        end_time = start_time + 5 # Ventana de 5 segundos
        
        # Encontrar los índices de los datos dentro de la ventana de tiempo
        idx = np.where((self.t_vals_raw >= start_time) & (self.t_vals_raw <= end_time))[0]

        if idx.size > 1:
            t_window = self.t_vals_raw[idx]
            b_window_filt = self.braquial_vals_filt[idx]
            t_window_filt = self.tibial_vals_filt[idx]
            self.graph.plot_dual_signal(t_window, b_window_filt, t_window_filt)
        else:
            # Limpiar el gráfico si no hay datos en la ventana (o muy pocos)
            self.graph.axes.clear()
            self.graph.axes.set_title("Señales Braquial y Tibial")
            self.graph.axes.set_xlabel("Tiempo (s)")
            self.graph.axes.set_ylabel("Amplitud")
            self.graph.draw()
