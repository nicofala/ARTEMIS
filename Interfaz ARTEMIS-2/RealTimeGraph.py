from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from collections import deque
import numpy as np
from scipy.signal import iirnotch, filtfilt, butter
   

class RealTimeGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.fs = 200  # Frecuencia de muestreo en Hz
        self.f0 = 50   # Frecuencia de la red eléctrica (Notch)
        self.Q = 30    # Factor de calidad del filtro notch
        self.b_notch, self.a_notch = iirnotch(self.f0, self.Q, self.fs)

        self.timestamps = deque()
        self.braquial_vals = deque()
        self.tibial_vals = deque()
        self.start_time = None

        self.plot_widget = PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Señales en tiempo real")
        self.plot_widget.setLabel('left', "Voltaje", units='V')
        self.plot_widget.setLabel('bottom', "Tiempo", units='s')
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setMouseEnabled(x=True, y=False)

        self.curve_braquial = self.plot_widget.plot(pen=mkPen(color='r', width=2), name="Braquial")
        self.curve_tibial = self.plot_widget.plot(pen=mkPen(color='b', width=2), name="Tibial")

        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def apply_notch(self, arr):
        if len(arr) < 15:  # mínimo requerido para filtrar sin error
            return arr
        return filtfilt(self.b_notch, self.a_notch, arr)

    def filtro_pasabajo(self, arr, cutoff=20, order=4):
        if len(arr) < (order + 1):  # validación para butter()
            return arr
        b, a = butter(order, cutoff / (0.5 * self.fs), btype='low')
        padlen = max(len(b), len(a)) * 3
        if len(arr) < padlen:
            return arr  # evitar ValueError en filtfilt
        return filtfilt(b, a, arr)
    
    def plot_dual_signal(self, t, signal1, signal2, label1="Braquial", label2="Tibial"):
        self.clear()  # Método personalizado para limpiar pyqtgraph
        # Aplicar límites fijos si ya fueron calculados
        if hasattr(self, 'y_min') and hasattr(self, 'y_max'):
            self.plot_widget.setYRange(self.y_min, self.y_max)

        self.plot_widget.showGrid(x=True, y=True)

    def update_plot(self, timestamp_ms, v_braquial, v_tibial):
        if self.start_time is None:
            self.start_time = timestamp_ms

        t = (timestamp_ms - self.start_time) / 1000.0
        self.timestamps.append(t)
        self.braquial_vals.append(v_braquial)
        self.tibial_vals.append(v_tibial)

        # Esperar al menos 20 datos antes de filtrar y graficar
        if len(self.braquial_vals) < 20:
            return

        arr_t = np.array(self.timestamps)
        arr_b = self.filtro_pasabajo(self.apply_notch(np.array(self.braquial_vals)))
        arr_ti = self.filtro_pasabajo(self.apply_notch(np.array(self.tibial_vals)))

        self.curve_braquial.setData(arr_t, arr_b)
        self.curve_tibial.setData(arr_t, arr_ti)

        # Ventana de visualización: últimos 5 segundos
        if t > 5:
            self.plot_widget.setXRange(t - 5, t + 0.5)
        else:
            self.plot_widget.setXRange(0, 5)

    def clear(self):
        self.timestamps.clear()
        self.braquial_vals.clear()
        self.tibial_vals.clear()
        self.start_time = None
        self.curve_braquial.setData([], [])
        self.curve_tibial.setData([], [])
