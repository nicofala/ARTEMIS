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
