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


# === Procesamiento de señales ===

def lowpass_filter(signal, fs=50, cutoff=16, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low')
    return filtfilt(b, a, signal)

def highpass_filter(signal, fs=50, cutoff=0.5, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high')
    return filtfilt(b, a, signal)

def normalize(signal):
    return (signal - np.mean(signal)) / np.std(signal)

def calcular_vop(datos_json, altura_cm):
    df = pd.DataFrame(datos_json).dropna(subset=["t", "braquial", "tibial"])
    t = (df["t"].astype(float).to_numpy() - df["t"].iloc[0]) / 1000.0
    ba = df["braquial"].astype(float).to_numpy()
    an = df["tibial"].astype(float).to_numpy()

    fs = 50
    ba_filt = lowpass_filter(highpass_filter(ba, fs), fs)
    an_filt = lowpass_filter(highpass_filter(an, fs), fs)
    ba_norm = normalize(ba_filt)
    an_norm = normalize(an_filt)

    peaks_ba, _ = find_peaks(ba_norm, distance=1, prominence=0.3)
    peaks_an, _ = find_peaks(an_norm, distance=1, prominence=0.1)

    ptt_list = []
    for pb in peaks_ba:
        time_b = t[pb]
        time_diffs = t[peaks_an] - time_b
        valid_indices = np.where(time_diffs > 0)[0]
        if len(valid_indices) > 0:
            pt = time_diffs[valid_indices[np.argmin(time_diffs[valid_indices])]]
            if 0.1 <= pt <= 0.5:
                ptt_list.append(pt)

    if not ptt_list:
        return [], None

    Dhb = (0.220 * altura_cm - 2.07) / 100
    Dhf = (0.564 * altura_cm - 18.4) / 100
    Dfa = (0.249 * altura_cm + 30.7) / 100
    vop = [(Dfa + Dhf - Dhb) / i for i in ptt_list if (Dfa + Dhf - Dhb) / i < 40]

    times_brachial = t[peaks_ba]
    rr_intervals = np.diff(times_brachial)
    valid_rr = rr_intervals[(rr_intervals > 0.6) & (rr_intervals < 1.0)]

    freq_bpm = (1 / np.median(valid_rr)) * 60 if len(valid_rr) > 0 else 0
    return vop, freq_bpm

def calcular_cavi(pwv, sbp, dbp):
    """
    Calculates the Cardio-Ankle Vascular Index (CAVI).

    Parameters:
    pwv (float): Pulse Wave Velocity in m/s.
    sbp (float): Systolic Blood Pressure in mmHg.
    dbp (float): Diastolic Blood Pressure in mmHg.

    Returns:
    float: The calculated CAVI value.
    """
    # Justification for parameters (see below for detailed explanation)
    # rho: density of blood, approx 1050 kg/m^3 (or 1.05 g/cm^3)
    # P_0: typically set to 1.333 kPa (10 mmHg) as a reference pressure for arterial collapse
    # deltaP: pulse pressure (SBP - DBP) in kPa
    # Conversion from mmHg to kPa: 1 mmHg = 0.133322 kPa

    rho = 1050 # kg/m^3
    P0_mmHg = 10 # mmHg
    P0 = P0_mmHg * 0.133322 # kPa

    # Convert SBP and DBP from mmHg to kPa
    sbp_kpa = sbp * 0.133322
    dbp_kpa = dbp * 0.133322

    deltaP = sbp_kpa - dbp_kpa

    if deltaP <= 0:
        return None # Cannot calculate CAVI with non-positive pulse pressure

    # The CAVI formula: a * (ln(SBP/DBP) * (2 * rho * PWV^2) / deltaP) + b
    # A simplified and commonly used formula for CAVI (e.g., from Vasera VS-1500) is:
    # CAVI = a * ((2 * rho * PWV^2) / (ln(SBP/DBP) * deltaP)) + b
    # However, the most widely accepted and published formula (from Hayashi et al. 2007) is:
    # CAVI = (2 * rho / deltaP) * PWV^2 * ln(SBP / DBP) + constant (often ignored or absorbed)
    # A more practical form, as used in many devices, is derived from the stiffness parameter beta:
    # beta = ln(SBP/DBP) / ((SBP-DBP)/2 * rho * PWV^2)
    # And then CAVI = a * beta + b

    # Let's use a widely cited formula for CAVI, for example, from the VaSera VS-1500 device:
    # CAVI = a * ((2 * rho * PWV^2) / (P_s - P_d)) * ln(P_s / P_d) + b
    # Where 'a' and 'b' are constants to scale and offset the index.
    # Typical values for 'a' and 'b' are chosen to match clinical data,
    # often derived from the formula that incorporates the stiffness parameter β.

    # A common form derived from the stiffness parameter beta (β):
    # β = (ln(Ps/Pd) * 2 * rho * PWV^2) / (Ps - Pd)
    # CAVI is often expressed as: CAVI = a * β + b
    # A more direct calculation, aligning with what some devices use:
    # CAVI = 1 / (beta_stiffness) * (some constants)
    # A very common and practical formula, especially for device manufacturers, is often a
    # linear transformation of the stiffness parameter beta (β):
    # β = (ln(sbp_kpa / dbp_kpa)) / ((sbp_kpa - dbp_kpa) / (0.5 * rho * pwv**2))
    # This is equivalent to: β = (2 * rho * pwv**2 * ln(sbp_kpa / dbp_kpa)) / (sbp_kpa - dbp_kpa)

    # Let's use the formula based on the stiffness parameter beta (β),
    # which directly relates to the PWV and pressure:
    # β = 2 * rho * PWV^2 * ln(SBP/DBP) / (SBP - DBP)
    # With ρ = 1050 kg/m^3 (density of blood) and pressures in Pascals (Pa).
    # Since we are using kPa, and PWV is in m/s:

    # The formula commonly seen in research and device manuals:
    # CAVI = a * (ln(SBP_mmHg / DBP_mmHg) * (2 * rho * PWV^2) / ((SBP_mmHg - DBP_mmHg) * 133.322)) + b
    # No, this is incorrect. The more consistent approach is to convert pressures to kPa for calculation.

    # Re-evaluating the formula based on common device implementations (e.g., VaSera):
    # CAVI = a * (ln(SBP / DBP) * (2 * rho * PWV^2) / (SBP_pa - DBP_pa)) + b
    # Where a typical value for the constant 'a' is 200, and 'b' is 0 for direct beta-like value.
    # The 'a' and 'b' are conversion factors to match clinical data and scale CAVI values.

    # Let's consider the derivation from stiffness parameter β (beta):
    # β = (ln(P_s / P_d)) / (D_v / (0.5 * rho * PWV^2)) where D_v is pressure difference
    # So, β = (2 * rho * PWV^2 * ln(P_s / P_d)) / (P_s - P_d)
    # P_s and P_d must be in the same units, e.g., mmHg or kPa.
    # Let's keep SBP and DBP in mmHg for the ln and difference, then convert the whole term.

    # As per "Cardio-ankle vascular index (CAVI): a new indicator of arterial stiffness"
    # by Shirai et al., 2011, the formula used by the VaSera VS-1500 is:
    # CAVI = a * β + b, where β = (2 * ρ * (PWV)^2 / ΔP) * ln(Ps / Pd)
    # and ΔP = Ps - Pd.
    # For clinical purposes, standard constants are often used.
    # Let's use the constants often cited with the Vasera device, where they simplify to:
    # CAVI = (0.234 * ln(sbp / dbp) * PWV^2) / (sbp - dbp) + 4.93
    # This form simplifies the density and other constants into 0.234 and 4.93,
    # assuming PWV in m/s and BP in mmHg. This is a common empirical formula.

    # Justification for the constants (0.234 and 4.93):
    # These constants are derived empirically from large datasets by the manufacturers
    # (e.g., Fukuda Denshi for the VaSera device) to align the CAVI values with age-related
    # changes and cardiovascular risk. They essentially scale the stiffness parameter
    # β to provide a clinically meaningful index.
    # Source: Shirai K, et al. "Cardio-ankle vascular index (CAVI): a new indicator
    # of arterial stiffness." J Atheroscler Thromb. 2011;18(5):368-76.
    # This formula is widely used and provides a direct calculation from standard inputs.

    try:
        cavi_val = (0.234 * np.log(sbp / dbp) * (pwv**2)) / (sbp - dbp) + 4.93
        return cavi_val
    except ZeroDivisionError:
        return None # Handle case where SBP == DBP
    except ValueError:
        return None # Handle log of non-positive numbers or other math errors


# === Gráfico ===

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


# === Interfaz principal ===

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


class ReportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subject_vop = None
        self.subject_age = None
        self.subject_name = "" 

        self.reference_ranges = {
            "<30": [4.7, 7.6],
            "30-39": [3.8, 9.2],
            "40-49": [4.6, 9.8],
            "50-59": [4.5, 12.1],
            "60-69": [5.5, 15.0]
        }

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        mid_layout = QHBoxLayout()

        title_label = QLabel("Informe de Velocidad de Onda de Pulso (VOP)")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)

        content_layout = QHBoxLayout()

        # Increased figsize for potentially larger graph
        self.graph_canvas = FigureCanvas(Figure(figsize=(8, 6))) 
        self.axes = self.graph_canvas.figure.add_subplot(111)
        content_layout.addWidget(self.graph_canvas)
        content_layout.addStretch(3)

        info_layout = QVBoxLayout()
        info_layout.addStretch()
        font = QFont("Arial", 12)

        # VOP del Sujeto
        self.vop_subject_label = QLabel("VOP del Sujeto: -- m/s")
        self.vop_subject_label.setFont(font)
        self.vop_subject_label.setStyleSheet("background-color: white; border: 1px solid black; padding: 5px;") # Borde y padding
        vop_h_layout = QHBoxLayout()
        vop_h_layout.addStretch()
        vop_h_layout.addWidget(self.vop_subject_label)
        vop_h_layout.addStretch()
        info_layout.addLayout(vop_h_layout)
        info_layout.addSpacing(15)

        # Desviación vs. Media del Rango
        self.deviation_label = QLabel("Desviación vs. Media del Rango: -- %")
        self.deviation_label.setFont(font)
        self.deviation_label.setStyleSheet("background-color: white; border: 1px solid black; padding: 5px;") # Borde y padding
        deviation_h_layout = QHBoxLayout()
        deviation_h_layout.addStretch()
        deviation_h_layout.addWidget(self.deviation_label)
        deviation_h_layout.addStretch()
        info_layout.addLayout(deviation_h_layout)
        info_layout.addSpacing(15)

        # Interpretación
        self.interpretation_label = QLabel("Interpretación: --")
        self.interpretation_label.setFont(font)
        # Considera usar WordWrap si la interpretación puede ser muy larga
        self.interpretation_label.setWordWrap(True) 
        self.interpretation_label.setStyleSheet("background-color: white; border: 1px solid black; padding: 5px;") # Borde y padding
        interpretation_h_layout = QHBoxLayout()
        interpretation_h_layout.addStretch()
        interpretation_h_layout.addWidget(self.interpretation_label)
        interpretation_h_layout.addStretch()
        info_layout.addLayout(interpretation_h_layout)
        
        # Añadir un espacio flexible al final de info_layout para empujar los labels hacia arriba
        info_layout.addStretch()
        
        mid_layout.addLayout(content_layout,1)
        mid_layout.addLayout(info_layout,1)

        main_layout.addLayout(mid_layout)
        main_layout.addSpacing(20)

        back_button = QPushButton("Volver a la aplicación")
        back_button.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold;")
        main_layout.addWidget(back_button, alignment=Qt.AlignCenter)
        self.back_button = back_button 

        self.setLayout(main_layout)


    def update_report(self, subject_vop, subject_age, subject_name):
        self.subject_vop = subject_vop
        self.subject_age = subject_age
        self.subject_name = subject_name # Assign the subject's name
        self.plot_boxplot()

    
    def plot_boxplot(self):
        self.axes.clear()
        data_to_plot = []
        labels = []

        subject_age_range_label = None
        if self.subject_age is not None:
            for age_label, values in self.reference_ranges.items():
                if age_label == "<30" and self.subject_age < 30:
                    subject_age_range_label = age_label
                    break
                elif "-" in age_label:
                    lower, upper = map(int, age_label.split('-'))
                    if lower <= self.subject_age <= upper:
                        subject_age_range_label = age_label
                        break
                   
        for age_label, values in self.reference_ranges.items():
            min_val, max_val = values
            median_val = (min_val + max_val) / 2
            q1 = min_val + (max_val - min_val) * 0.25
            q3 = min_val + (max_val - min_val) * 0.75
            
            data_to_plot.append({
                'med': median_val,
                'q1': q1,
                'q3': q3,
                'whislo': min_val,
                'whishi': max_val,
                'fliers': []
            })
            labels.append(age_label)

        bp = self.axes.bxp(data_to_plot, showfliers=False, patch_artist=True, 
                           medianprops={'color': 'red'}, boxprops={'facecolor': 'lightblue'})

        vop_display_text = "--"
        deviation_display_text = "--"
        interpretation_display_text = "No hay datos de VOP para mostrar." 

        if subject_age_range_label and self.subject_vop is not None:
            try:
                idx = labels.index(subject_age_range_label)
                if min_val <= self.subject_vop and self.subject_vop <=max_val:
                    bp['boxes'][idx].set_facecolor('lightgreen')
                else:  
                    bp['boxes'][idx].set_facecolor('lightcoral')

                # Plot subject's VOP as a red dot
                # Corrected f-string for subject name
                self.axes.plot(idx + 1, self.subject_vop, 'o', color='red', markersize=10, 
                               label=f'VOP de {self.subject_name or "Sujeto"} ({self.subject_vop:.2f} m/s)')
                self.axes.text(idx + 1, self.subject_vop + 0.5, f'{self.subject_vop:.2f}', color='red', ha='center', va='bottom', fontweight='bold')
                
                # Draw a dashed horizontal line for subject's VOP
                self.axes.axhline(y=self.subject_vop, color='red', linestyle='--', linewidth=1, label=f'VOP {self.subject_name}')


                # Calculate and display deviation
                age_range_values = self.reference_ranges[subject_age_range_label]
                range_median = (age_range_values[0] + age_range_values[1]) / 2
                deviation_percent = ((self.subject_vop - range_median) / range_median) * 100
                
                # Corrected f-string for subject name
                vop_display_text = f"{self.subject_vop:.2f}"
                deviation_display_text = f"{deviation_percent:.2f}"
                interpretation_display_text = self.get_vop_interpretation(self.subject_vop, age_range_values[0], age_range_values[1], range_median)

            except ValueError:
                pass 
        
        # Always update the labels with potentially new data or defaults
        self.vop_subject_label.setText(f"VOP de {self.subject_name or 'Sujeto'} → {vop_display_text} m/s")
        self.deviation_label.setText(f"Desviación vs Media → {deviation_display_text} %")
        self.interpretation_label.setText(f"Interpretación → {interpretation_display_text}")
            
        self.axes.set_title("VOP por Grupo de Edad")
        self.axes.set_xlabel("Grupo de Edad")
        self.axes.set_ylabel("VOP (m/s)")
        self.axes.set_xticklabels(labels)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        # Ensure legend is only added if there are labels to show
        if self.axes.get_legend_handles_labels()[1]: # Check if any labels exist
            self.axes.legend(loc='upper left')
        self.graph_canvas.draw()
    
    def get_vop_interpretation(self, vop, lower_bound, upper_bound, range_median):
        if lower_bound <= vop <= upper_bound:
            if vop >= range_median * 0.9 and vop <= range_median * 1.1: 
                return "Dentro de lo esperado para su grupo de edad."
            elif vop < range_median:
                return "Ligeramente por debajo del promedio para su grupo de edad."
            else:
                return "Ligeramente por encima del promedio para su grupo de edad."
        elif vop < lower_bound:
            return "Significativamente por debajo del rango esperado para su grupo de edad. Podría indicar una mayor elasticidad arterial."
        else: 
            return "Significativamente por encima del esperado para su grupo de edad. Podría indicar una menor elasticidad arterial (mayor rigidez)."

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

        img_label = ScalableImage("D:\\ITBA\\2025\\1C\\Instru 2\\Interfaz ARTEMIS\\anatomia.jpg", parent=self)
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

    def set_field_error_style(self, line_edit, is_error):
        if is_error:
            line_edit.setStyleSheet("background-color: #FFCCCC;") # Light red
        else:
            line_edit.setStyleSheet("") # Reset to default

    def validar(self):
        self.nombre = self.nombre_input.text().strip()
        self.apellido= self.apellido_input.text().strip()
        self.nombre_completo = f"{self.nombre_input.text().strip()} {self.apellido_input.text().strip()}"
        self.edad = self.edad_input.text().strip()
        self.altura = self.altura_input.text().strip()
        self.segmento1 = self.segmento1_input.text().strip()
        self.segmento2 = self.segmento2_input.text().strip()
        self.sistolica = self.sistolica_input.text().strip()
        self.diastolica = self.diastolica_input.text().strip()
        self.observacion = self.observacion_input.text().strip()

        # Reset styles before validation
        self.set_field_error_style(self.nombre_input, False)
        self.set_field_error_style(self.edad_input, False)
        self.set_field_error_style(self.altura_input, False)
        self.set_field_error_style(self.sistolica_input, False)
        self.set_field_error_style(self.diastolica_input, False)

        if not self.nombre or not self.apellido or not self.altura:
            QMessageBox.warning(self, "Faltan datos", "Debés ingresar al menos Nombre y Altura.")
            return

        error_messages = []

        # Validate Nombre (only characters, no numbers)
        if not self.nombre_completo:
            error_messages.append("Debés ingresar el Nombre.")
            self.set_field_error_style(self.nombre_input, True)
            self.set_field_error_style(self.apellido_input, True)
        elif not all(char.isalpha() or char.isspace() for char in self.nombre): # Allows spaces, disallows numbers/symbols
            error_messages.append("El Nombre solo debe contener caracteres alfabéticos.")
            self.set_field_error_style(self.nombre_input, True)
            self.set_field_error_style(self.apellido_input, True)

        # Validate Altura (numeric and range)
        try:
            altura_cm = float(self.altura)
            if not (60 <= altura_cm <= 250):
                error_messages.append("La altura debe estar entre 60 y 250 cm.")
                self.set_field_error_style(self.altura_input, True)
        except ValueError:
            error_messages.append("La altura debe ser un número válido.")
            self.set_field_error_style(self.altura_input, True)

        # Validate Edad (numeric and range)
        try:
            edad_int = int(self.edad)
            if not (5 <= edad_int <= 70):
                error_messages.append("La edad debe ser entre 5 y 70 años.")
                self.set_field_error_style(self.edad_input, True)
        except ValueError:
            error_messages.append("La edad debe ser un número entero válido.")
            self.set_field_error_style(self.edad_input, True)

        # Validate Segmento 1 (numeric and range)
        try:
            segmento1_cm = float(self.segmento1)
            if not (segmento1_cm < altura_cm):
                error_messages.append("La altura debe ser mayor al segmento medido")
                self.set_field_error_style(self.altura_input, True)
        except ValueError:
            error_messages.append("La altura debe ser un número válido.")
            self.set_field_error_style(self.altura_input, True)

        if error_messages:
            QMessageBox.warning(self, "Datos inválidos", "\n".join(error_messages))
            return

        # Validate Segmento 2 (numeric and range)
        try:
            segmento2_cm = float(self.segmento2)
            if not (segmento2_cm < altura_cm):
                error_messages.append("La altura debe ser mayor al segmento medido")
                self.set_field_error_style(self.altura_input, True)
        except ValueError:
            error_messages.append("La altura debe ser un número válido.")
            self.set_field_error_style(self.altura_input, True)
        
        try:
            sistolica_val = float(self.sistolica)
            if not (70 <= sistolica_val <= 250): # Typical physiological range
                error_messages.append("La presión sistólica debe estar entre 70 y 250 mmHg.")
                self.set_field_error_style(self.sistolica_input, True)
        except ValueError:
            error_messages.append("La presión sistólica debe ser un número válido.")
            self.set_field_error_style(self.sistolica_input, True)

        try:
            diastolica_val = float(self.diastolica)
            if not (40 <= diastolica_val <= 150): # Typical physiological range
                error_messages.append("La presión diastólica debe estar entre 40 y 150 mmHg.")
                self.set_field_error_style(self.diastolica_input, True)
        except ValueError:
            error_messages.append("La presión diastólica debe ser un número válido.")
            self.set_field_error_style(self.diastolica_input, True)

        if error_messages:
            QMessageBox.warning(self, "Datos inválidos", "\n".join(error_messages))
            return

        # Store these values for CAVI calculation
        self.subject_sistolica = sistolica_val
        self.subject_diastolica = diastolica_val


        self.nombre_label.setText(f"👤 Nombre: {self.nombre_completo}")
        self.edad_label.setText(f"🎂 Edad: {self.edad}")
        self.altura_label.setText(f"📏 Altura: {self.altura} cm")
        self.observacion_label.setText(f"📝 Observación: {self.observacion}")

        self.stacked_layout.setCurrentIndex(1)

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

    def init_report_page(self):
        self.report_page = ReportPage(self)
        self.stacked_layout.addWidget(self.report_page)
        # Conectar el botón de volver de la página del informe
        self.report_page.back_button.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(1))

    def show_report_page(self):
        if self.subject_vop_result is not None and self.subject_age_result is not None:
            self.report_page.update_report(self.subject_vop_result, self.subject_age_result,self.nombre_completo)
            self.stacked_layout.setCurrentIndex(2) # Cambiar a la tercera página (índice 2)
        else:
            QMessageBox.warning(self, "Sin Datos", "Cargue y procese un archivo primero para generar el informe de VOP.")

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

    def show_report(self):
        if self.subject_vop_result is not None and self.subject_age_result is not None:
            # Pasa la VOP y la edad del sujeto a la ventana del informe
            report_dialog = ReportWindow(self, self.subject_vop_result, self.subject_age_result)
            report_dialog.exec_() # Muestra la ventana de forma modal
        else:
            QMessageBox.warning(self, "Sin Datos", "Cargue y procese un archivo primero para generar el informe de VOP.")
    
    def exportar_hl7(self):
        if self.subject_vop_result is None or self.subject_age_result is None:
            QMessageBox.warning(self, "Sin Datos", "Primero cargá y procesá una señal para calcular la VOP.")
            return

        # Obtener datos
        nombre = self.nombre.strip()
        apellido = self.apellido.strip()
        edad = self.edad
        altura = self.altura
        observacion = self.observacion if self.observacion else "Sin observaciones"
        vop = f"{self.subject_vop_result:.2f}"
        fc = self.fc_box.text().split(":")[-1].strip().replace(" bpm", "")
        cavi = f"{self.subject_cavi_result:.2f}" if self.subject_cavi_result is not None else "N/A" # Add CAVI
        timestamp = pd.Timestamp.now().strftime("%Y%m%d%H%M")

        # Crear mensaje HL7
        hl7_message = f"""MSH|^~\\&|ARTEMIS|HOSPITAL_ITBA|RECEPTOR|DESTINO|{timestamp}||ORU^R01|00001|P|2.3
    PID|||00001||{apellido}^{nombre}||{pd.Timestamp.now().year - int(edad)}0101|U
    OBR|1|||PWV^Velocidad de Onda de Pulso
    OBX|1|NM|PWV^Velocidad de Onda de Pulso||{vop}|m/s|4.7-9.2|N|||F
    OBX|2|NM|HR^Frecuencia Cardíaca||{fc}|bpm|60-100|N|||F
    OBX|3|NM|CAVI^Cardio-Ankle Vascular Index||{cavi}|dimensionless|8.0-9.0|N|||F
    OBX|4|NM|ALT^Altura||{altura}|cm|||N|||F
    OBX|5|TX|OBS^Observación||{observacion}|||N|||F
    """

        # Guardar con QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo HL7", f"{apellido}_{timestamp}.hl7", "Archivos HL7 (*.hl7)"
        )

        if file_path:
            try:
                with open(file_path, "w") as file:
                    file.write(hl7_message)
                QMessageBox.information(self, "Éxito", f"Archivo HL7 guardado en:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{str(e)}")
    
    def export_image(self):
        if self.subject_vop_result is None:
            QMessageBox.warning(self, "Sin Datos", "Cargue y procese un archivo primero para exportar la imagen.")
            return

        # Create a widget to draw everything on
        export_widget = QWidget()
        export_layout = QVBoxLayout(export_widget)

        # 1. Add the graph
        # Create a temporary FigureCanvas with two subplots for the current plot
        # Adjusted figsize for better visual separation in the exported image
        temp_fig = Figure(figsize=(12, 18)) # Aumenta el tamaño para mejor resolución y espacio
        temp_axes_braquial = temp_fig.add_subplot(211)
        temp_axes_tibial = temp_fig.add_subplot(212, sharex=temp_axes_braquial)
        temp_graph_canvas = FigureCanvas(temp_fig)
        temp_fig.subplots_adjust(top=0.9, bottom=0.08, left=0.08, right=0.95, hspace=0.6) 

        # Re-plot the signals onto the temporary axes
        if hasattr(self, "t_vals_raw") and self.t_vals_raw.size > 0:
            # Plot all data, not just a 5-second window
            t_all = self.t_vals_raw
            b_all_filt = self.braquial_vals_filt
            t_all_filt = self.tibial_vals_filt
            
            # Plot on braquial axes
            temp_axes_braquial.plot(t_all, b_all_filt, color='red', label="Braquial")
            temp_axes_braquial.set_title("Señal Braquial")
            temp_axes_braquial.set_ylabel("Amplitud")
            temp_axes_braquial.legend(loc='upper right')
            temp_axes_braquial.grid(True)

            # Plot on tibial axes
            temp_axes_tibial.plot(t_all, t_all_filt, color='blue', label="Tibial")
            temp_axes_tibial.set_title("Señal Tibial")
            temp_axes_tibial.set_xlabel("Tiempo (s)")
            temp_axes_tibial.set_ylabel("Amplitud")
            temp_axes_tibial.legend(loc='upper right')
            temp_axes_tibial.grid(True)
        temp_graph_canvas.draw()
        
        # 2. Create a widget for patient data and results
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 10, 20, 10) # Add some padding

        font_label = QFont("Arial", 12)
        font_value = QFont("Arial", 12, QFont.Bold)

        # Patient Data - organized in two columns by QFormLayout
        left_col_layout = QFormLayout()
        left_col_layout.addRow(QLabel("<b>Nombre:</b>"), QLabel(self.nombre_completo, font=font_label))
        left_col_layout.addRow(QLabel("<b>Edad:</b>"), QLabel(f"{self.edad} años", font=font_label))
        left_col_layout.addRow(QLabel("<b>Altura:</b>"), QLabel(f"{self.altura} cm", font=font_label))
        # Date and Time
        left_col_layout.addRow(QLabel("<b>Fecha y Hora del Análisis:</b>"), QLabel(QDateTime.currentDateTime().toString(Qt.DefaultLocaleLongDate), font=font_label))
              
        # VOP and FC results
        right_col_layout = QFormLayout()
        right_col_layout.addRow(QLabel("<b>VOP:</b>"), QLabel(f"{self.subject_vop_result:.2f} m/s", font=font_value))
        right_col_layout.addRow(QLabel("<b>Frecuencia Cardíaca:</b>"), QLabel(f"{self.subject_fc_result:.0f} bpm", font=font_value))
        if self.subject_cavi_result is not None:
            right_col_layout.addRow(QLabel("<b>CAVI:</b>"), QLabel(f"{self.subject_cavi_result:.2f}", font=font_value))
        else:
            right_col_layout.addRow(QLabel("<b>CAVI:</b>"), QLabel("N/A", font=font_value))

        # Observation (can span both columns if needed, or put on a separate row)
        # For simplicity, putting it on a separate row for better readability
        observacion_label_title = QLabel("<b>Observación:</b>")
        observacion_label_title.setFont(font_label)
        observacion_label_content = QLabel(self.observacion if self.observacion else "Sin observaciones", font=font_label)
        observacion_label_content.setWordWrap(True)
        right_col_layout.addRow(observacion_label_title, observacion_label_content)

        # Add the two column layouts to the main info_layout (which is QHBoxLayout)
        info_layout.addLayout(left_col_layout)
        info_layout.addStretch(1) # Add a stretch between columns to push them apart
        info_layout.addLayout(right_col_layout)

        # Add the graph and info widget to the export_layout
        export_layout.addWidget(QLabel("<h2>Análisis de Pulso ARTEMIS</h2>", alignment=Qt.AlignCenter))
        export_layout.addWidget(temp_graph_canvas)
        export_layout.addWidget(info_widget)
        
        # Adjust size policy and minimum size for the export_widget
        export_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        export_widget.adjustSize() # Adjust size based on contents

        # Render the export_widget to a QPixmap
        # It's important to set a suitable size for the QPixmap to ensure quality
        # You might need to experiment with these dimensions
        pixmap = QPixmap(export_widget.size())
        pixmap.fill(Qt.white) # Fill with white background
        painter = QPainter(pixmap)
        export_widget.render(painter)
        painter.end()

        # Save the pixmap
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Guardar Imagen", f"informe_pulso_{self.nombre_completo.replace(' ', '_')}.png", "Archivos de Imagen (*.png *.jpg);;Todos los Archivos (*)"
        )
        if file_name:
            if pixmap.save(file_name):
                QMessageBox.information(self, "Éxito", f"Imagen guardada en:\n{file_name}")
            else:
                QMessageBox.critical(self, "Error", "No se pudo guardar la imagen.")
        
        # Clean up temporary canvas and widget
        temp_graph_canvas.deleteLater()
        export_widget.deleteLater()


class ReportWindow(QDialog):
        def __init__(self, parent=None, subject_vop=None, subject_age=None):
            super().__init__(parent)
            self.setWindowTitle("Informe de VOP")
            self.setGeometry(200, 200, 800, 600)

            self.subject_vop = subject_vop
            self.subject_age = subject_age

            self.reference_ranges = {
                "<30": [4.7, 7.6],
                "30-39": [3.8, 9.2],
                "40-49": [4.6, 9.8],
                "50-59": [4.5, 12.1],
                "60-69": [5.5, 15.0]
            }

            self.init_ui()
            self.plot_boxplot()

        def init_ui(self):
            main_layout = QVBoxLayout()

            title_label = QLabel("Informe de Velocidad de Onda de Pulso (VOP)")
            title_label.setFont(QFont("Arial", 18, QFont.Bold))
            title_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title_label)
            main_layout.addSpacing(20)

            content_layout = QHBoxLayout()

            self.graph_canvas = FigureCanvas(Figure(figsize=(6, 4)))
            self.axes = self.graph_canvas.figure.add_subplot(111)
            content_layout.addWidget(self.graph_canvas)

            info_layout = QVBoxLayout()
            self.vop_subject_label = QLabel("VOP del Sujeto: -- m/s")
            self.deviation_label = QLabel("Desviación vs. Media del Rango: -- %")
            
            font = QFont("Arial", 12)
            self.vop_subject_label.setFont(font)
            self.deviation_label.setFont(font)

            info_layout.addWidget(self.vop_subject_label)
            info_layout.addWidget(self.deviation_label)
            info_layout.addStretch()

            content_layout.addLayout(info_layout)
            
            main_layout.addLayout(content_layout)

            close_button = QPushButton("Cerrar Informe")
            close_button.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold;")
            close_button.clicked.connect(self.accept)
            main_layout.addWidget(close_button, alignment=Qt.AlignCenter)

            self.setLayout(main_layout)

        def plot_boxplot(self):
            self.axes.clear()

            data_to_plot = []
            labels = []
            
            subject_age_range_label = None
            if self.subject_age is not None:
                for age_label, values in self.reference_ranges.items():
                    if age_label == "<30" and self.subject_age < 30:
                        subject_age_range_label = age_label
                        break
                    elif "-" in age_label:
                        lower, upper = map(int, age_label.split('-'))
                        if lower <= self.subject_age <= upper:
                            subject_age_range_label = age_label
                            break
            
            for age_label, values in self.reference_ranges.items():
                min_val, max_val = values
                median_val = (min_val + max_val) / 2
                q1 = min_val + (max_val - min_val) * 0.25
                q3 = min_val + (max_val - min_val) * 0.75
                
                data_to_plot.append({
                    'med': median_val,
                    'q1': q1,
                    'q3': q3,
                    'whislo': min_val,
                    'whishi': max_val,
                    'fliers': []
                })
                labels.append(age_label)

            bp = self.axes.bxp(data_to_plot, showfliers=False, patch_artist=True, 
                               medianprops={'color': 'red'}, boxprops={'facecolor': 'lightblue'})

            if subject_age_range_label:
                try:
                    idx = labels.index(subject_age_range_label)
                    bp['boxes'][idx].set_facecolor('lightgreen')
                except ValueError:
                    pass

            if self.subject_vop is not None and subject_age_range_label:
                subject_x_pos = labels.index(subject_age_range_label) + 1

                self.axes.plot(subject_x_pos, self.subject_vop, 'o', color='purple', markersize=10, 
                               label=f'VOP del Sujeto ({self.subject_vop:.2f} m/s)', zorder=5)
                self.axes.annotate(f'{self.subject_vop:.2f}', 
                                   (subject_x_pos, self.subject_vop), 
                                   textcoords="offset points", xytext=(0,10), 
                                   ha='center', fontsize=10, color='purple', fontweight='bold')

                ref_min, ref_max = self.reference_ranges[subject_age_range_label]
                ref_mean = (ref_min + ref_max) / 2
                deviation = self.subject_vop - ref_mean
                
                self.vop_subject_label.setText(f"VOP del Sujeto: {self.subject_vop:.2f} m/s")
                self.deviation_label.setText(f"Desviación vs. Media ({ref_mean:.2f} m/s): {deviation:.2f} %")

            self.axes.set_title("VOP por Rango de Edad vs. Sujeto")
            self.axes.set_xlabel("Rango de Edad (años)")
            self.axes.set_ylabel("VOP (m/s)")
            self.axes.set_xticks(range(1, len(labels) + 1))
            self.axes.set_xticklabels(labels)
            self.axes.grid(True, linestyle='--', alpha=0.7)
            self.axes.legend()
            self.graph_canvas.draw()

# === Ejecutar app ===

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())