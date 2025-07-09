from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



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
