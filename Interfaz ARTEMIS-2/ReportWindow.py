
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


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
