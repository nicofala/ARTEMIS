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
from RealTimeGraph import RealTimeGraph


def leer_y_graficar(self):
    path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Text Files (*.txt)")
    if not path:
        return

    rt = self.graph_rt

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
    
    self.scroll_slider.setValue(0)

    try:
        self.subject_age_result = int(self.edad)
    except ValueError:
        self.subject_age_result = None

    # Usar la nueva función para filtrar, graficar y calcular VOP/CAVI
    procesar_y_graficar(
        self,
        self.t_vals_raw,
        self.braquial_vals_raw,
        self.tibial_vals_raw,
        float(self.altura)
    )

    # Y hacé esto en su lugar:
    arr_t = self.t_vals_raw
    arr_b = rt.filtro_pasabajo(rt.apply_notch(self.braquial_vals_raw))
    arr_ti = rt.filtro_pasabajo(rt.apply_notch(self.tibial_vals_raw))

    rt.curve_braquial.setData(arr_t, arr_b)
    rt.curve_tibial.setData(arr_t, arr_ti)

    # Ajustar la vista a toda la señal
    if len(arr_t) > 0:
        t_max = arr_t[-1]
        rt.plot_widget.setXRange(0, t_max)
    
def update_plot_window(self, start_time):
    end_time = start_time + 5  # Ventana de 5 segundos

    # Si hay datos filtrados, usalos
    if hasattr(self, "t_vals_filt") and self.t_vals_filt.size > 0:
        t_base = self.t_vals_filt
        braquial_base = self.braquial_vals_filt
        tibial_base = self.tibial_vals_filt
    # Si no, usá los datos raw
    elif hasattr(self, "t_vals_raw") and self.t_vals_raw.size > 0:
        t_base = self.t_vals_raw
        braquial_base = self.braquial_vals_raw
        tibial_base = self.tibial_vals_raw
    else:
        print("❌ No hay datos para graficar")
        return

    idx = np.where((t_base >= start_time) & (t_base <= end_time))[0]

    if idx.size > 1:
        t_window = t_base[idx]
        b_window = braquial_base[idx]
        t2_window = tibial_base[idx]
        self.graph_rt.clear()
        self.graph_rt.plot_dual_signal(t_window, b_window, t2_window)
    else:
        print("⚠️ No hay datos en la ventana de tiempo seleccionada.")


"""def update_plot_window(self, start_time):
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
            self.graph_rt.plot_dual_signal(t_window, b_window_filt, t_window_filt)
        #else:
            # Limpiar el gráfico si no hay datos en la ventana (o muy pocos)
            #self.graph_rt.clear() 
"""
            
def procesar_y_graficar(self, t_array, braquial_array, tibial_array, altura_cm):
    fs = 200
    self.t_vals_raw = t_array
    self.braquial_vals_raw = braquial_array
    self.tibial_vals_raw = tibial_array

    self.braquial_vals_filt = lowpass_filter(highpass_filter(self.braquial_vals_raw, fs), fs)
    self.tibial_vals_filt = lowpass_filter(highpass_filter(self.tibial_vals_raw, fs), fs)

    # Calcular límites del eje Y
    min_y = min(self.braquial_vals_filt.min(), self.tibial_vals_filt.min())
    max_y = max(self.braquial_vals_filt.max(), self.tibial_vals_filt.max())
    margin = (max_y - min_y) * 0.1
    self.graph_rt.y_min = min_y - margin
    self.graph_rt.y_max = max_y + margin

    # Mostrar primeros 5 segundos (o hasta lo que haya)
    self.update_plot_window(0)

    # Calcular VOP y frecuencia
    datos_dict = [
        {"t": t * 1000, "braquial": b, "tibial": ti}
        for t, b, ti in zip(t_array, braquial_array, tibial_array)
    ]
    vop_list, freq_bpm = calcular_vop(datos_dict, altura_cm, fs)

    if vop_list and hasattr(self, 'subject_sistolica') and hasattr(self, 'subject_diastolica'):
        self.subject_vop_result = np.median(vop_list)
        self.subject_fc_result = freq_bpm
        self.vop_box.setText(f"VOP: {self.subject_vop_result:.2f} m/s")
        self.fc_box.setText(f"Frecuencia: {freq_bpm:.0f} bpm")

        cavi = calcular_cavi(self.subject_vop_result, self.subject_sistolica, self.subject_diastolica)
        self.subject_cavi_result = cavi
        self.cavi_box.setText(f"CAVI: {cavi:.2f}" if cavi is not None else "CAVI: N/A")

        self.report_button.setEnabled(True)
        self.export_image_button.setEnabled(True)
    else:
        print(vop_list)
        self.vop_box.setText("VOP: -- m/s")
        self.fc_box.setText("Frecuencia: -- bpm")
        self.cavi_box.setText("CAVI: --")
        self.report_button.setEnabled(False)
        self.export_image_button.setEnabled(False)
