import sys
from PyQt5.QtWidgets import QApplication
from MainWindow import MainWindow  

def main():
    # Configuración inicial de la aplicación
    app = QApplication(sys.argv)
    
    # Configuración de estilos globales (opcional)
    app.setStyle('Fusion')  # Puedes probar con 'Windows', 'Fusion', etc.
    
    # Crear la ventana principal
    window = MainWindow()
    window.show()
    
    # Ejecutar el bucle principal de la aplicación
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()