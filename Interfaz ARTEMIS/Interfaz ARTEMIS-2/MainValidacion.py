from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)


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
