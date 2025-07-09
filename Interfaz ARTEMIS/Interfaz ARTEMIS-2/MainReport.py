from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QDialog, QSpacerItem,
    QFileDialog, QStackedLayout, QGroupBox, QFrame, QSlider, QSizePolicy 
)


from ReportPage import ReportPage

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
