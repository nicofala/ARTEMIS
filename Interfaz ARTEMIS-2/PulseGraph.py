from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PulseGraph(FigureCanvas):
    def __init__(self, parent=None):
        self.t_vals = []
        self.braquial_vals = []
        self.tibial_vals = []
        fig = Figure(figsize=(6, 3))
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        
        # Nuevos atributos para almacenar los límites del eje Y
        self.y_min = None
        self.y_max = None


    def plot_dual_signal(self, t, signal1, signal2, label1="Braquial", label2="Tibial"):
        self.axes.clear()
        self.axes.plot(t, signal1, color='red', label=label1)
        self.axes.plot(t, signal2, color='blue', label=label2)
        self.axes.set_title("Señales Braquial y Tibial")
        self.axes.set_xlabel("Tiempo (s)")
        self.axes.set_ylabel("Amplitud")
        self.axes.legend(loc='upper right', bbox_to_anchor=(1.0, 1.0)) 
        # Aplicar límites fijos si ya fueron calculados
        if self.y_min is not None and self.y_max is not None:
            self.axes.set_ylim(self.y_min, self.y_max)
        self.axes.grid(True) # Esto activa la grilla
        self.draw()
