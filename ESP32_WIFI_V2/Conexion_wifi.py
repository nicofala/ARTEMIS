import sys
import json
import websocket
from collections import deque
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, QSpinBox, QSplitter
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont
from websocket import WebSocketApp
import threading
import pyqtgraph as pg
import numpy as np
from datetime import datetime

class WebSocketThread(QThread):
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ws = None
        self.running = False

        # Datos para guardar
        self.logged_lines = []  # Guardamos las líneas en formato string
        
    def run(self):
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.data_received.emit(data)
            except json.JSONDecodeError:
                pass
                
        def on_error(ws, error):
            self.connection_status.emit(f"Error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            self.connection_status.emit("Desconectado")
            
        def on_open(ws):
            self.connection_status.emit("Conectado")
            
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            self.ws.run_forever()
        except Exception as e:
            self.connection_status.emit(f"Error de conexión: {e}")
    
    def send_command(self, command):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                self.ws.send(json.dumps(command))
            except Exception as e:
                self.connection_status.emit(f"Error enviando comando: {e}")
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

class ESP32Controller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.websocket_thread = None
        self.measuring = False
        self.measurement_timer = QTimer()
        self.measurement_timer.timeout.connect(self.stop_measurements)
        self.measurement_timer.setSingleShot(True)
        
        # Datos para el plotter (ventana de 5 segundos)
        self.window_size = 5000  # 5 segundos en ms
        self.max_points = 50     # Máximo 50 puntos en pantalla
        self.timestamps = deque()
        self.data_a0 = deque()
        self.data_a1 = deque()
        self.start_time = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Controlador ESP32 - Mediciones Analógicas")
        self.setGeometry(100, 100, 1000, 700) # Aumentamos el tamaño para el gráfico
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Usamos QSplitter para dividir la ventana principal
        main_splitter = QSplitter(Qt.Vertical)
        
        # Contenedor para la parte superior (controles y datos numéricos)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Configuración de conexión
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("URL WebSocket:"))
        self.url_input = QLineEdit("ws://192.168.1.100:81")  # Cambia por la IP de tu ESP32
        conn_layout.addWidget(self.url_input)
        
        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        top_layout.addLayout(conn_layout)
        
        # Estado de conexión
        self.status_label = QLabel("Desconectado")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        top_layout.addWidget(self.status_label)
        
        # Configuración de duración
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duración (segundos):"))
        self.duration_input = QSpinBox()
        self.duration_input.setMinimum(1)
        self.duration_input.setMaximum(3600)  # Máximo 1 hora
        self.duration_input.setValue(7)  # 10 segundos por defecto
        duration_layout.addWidget(self.duration_input)
        top_layout.addLayout(duration_layout)
        
        # Botón para iniciar/detener mediciones
        self.measure_btn = QPushButton("Iniciar Mediciones")
        self.measure_btn.clicked.connect(self.toggle_measurements)
        self.measure_btn.setEnabled(False)
        top_layout.addWidget(self.measure_btn)
        
        # Área de datos
        data_layout = QHBoxLayout()
        
        # Pin 34
        pin32_layout = QVBoxLayout()
        pin32_layout.addWidget(QLabel("Pin 32 (Voltaje):"))
        self.pin32_value = QLabel("0")
        self.pin32_value.setFont(QFont("Arial", 16))
        self.pin32_value.setStyleSheet("border: 1px solid gray; padding: 10px;")
        pin32_layout.addWidget(self.pin32_value)
        
        # Pin 35
        pin35_layout = QVBoxLayout()
        pin35_layout.addWidget(QLabel("Pin 35 (Voltaje):"))
        self.pin35_value = QLabel("0")
        self.pin35_value.setFont(QFont("Arial", 16))
        self.pin35_value.setStyleSheet("border: 1px solid gray; padding: 10px;")
        pin35_layout.addWidget(self.pin35_value)
        
        data_layout.addLayout(pin32_layout)
        data_layout.addLayout(pin35_layout)
        top_layout.addLayout(data_layout)
        
        # Log de datos
        top_layout.addWidget(QLabel("Log de datos:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        top_layout.addWidget(self.log_text)

        # Configuración del gráfico
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w') # Fondo blanco
        self.plot_widget.setTitle("Mediciones de Voltaje en Tiempo Real")
        self.plot_widget.setLabel('left', "Voltaje", units='V')
        self.plot_widget.setLabel('bottom', "Tiempo", units='s')
        self.plot_widget.addLegend() # Añadir leyenda
        self.plot_widget.showGrid(x=True, y=True) # Mostrar cuadrícula
        self.plot_widget.setMouseEnabled(x=True, y=False)  # Activar scroll horizontal

        # Curvas para los datos de los pines
        self.curve_a0 = self.plot_widget.plot(pen=pg.mkPen(color=(255, 0, 0), width=2), name="Pin 34") # Rojo
        self.curve_a1 = self.plot_widget.plot(pen=pg.mkPen(color=(0, 0, 255), width=2), name="Pin 35") # Azul

        # Añadir los widgets al splitter
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(self.plot_widget)

        # Establecer el layout principal con el splitter
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(main_splitter)
        
    def toggle_connection(self):
        if self.websocket_thread is None or not self.websocket_thread.isRunning():
            self.connect_websocket()
        else:
            self.disconnect_websocket()
    
    def connect_websocket(self):
        url = self.url_input.text().strip()
        if not url:
            return
            
        self.websocket_thread = WebSocketThread(url)
        self.websocket_thread.data_received.connect(self.on_data_received)
        self.websocket_thread.connection_status.connect(self.on_connection_status)
        self.websocket_thread.start()
        
        self.connect_btn.setText("Desconectar")
        
    def disconnect_websocket(self):
        if self.websocket_thread:
            if self.measuring:
                self.stop_measurements()
            self.websocket_thread.stop()
            self.websocket_thread.wait()
            self.websocket_thread = None
            
        self.connect_btn.setText("Conectar")
        self.measure_btn.setEnabled(False)
        self.status_label.setText("Desconectado")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
    def on_connection_status(self, status):
        self.status_label.setText(status)
        if status == "Conectado":
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.measure_btn.setEnabled(True)
        else:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.measure_btn.setEnabled(False)
            
    def on_data_received(self, data):
        if "pin32" in data and "pin35" in data and "timestamp" in data:
            # Convertir valores analógicos a voltaje (0-4095 -> 0-3.3V)
            voltage_a0 = (data["pin32"] / 4095.0) * 3.3
            voltage_a1 = (data["pin35"] / 4095.0) * 3.3
            
            # Actualizar displays
            self.pin32_value.setText(f"{voltage_a0:.3f} V")
            self.pin35_value.setText(f"{voltage_a1:.3f} V")
            
            # Actualizar datos del gráfico
            self.update_plot_data(data["timestamp"], voltage_a0, voltage_a1)
            
            # Agregar al log en el formato solicitado
            json_obj = {
            "t": data["timestamp"],
            "braquial": voltage_a0,
            "tibial": voltage_a1
            }
            line = f'Datos recibidos de Arduino: {json.dumps(json_obj)}'
            self.log_text.append(line)
            self.logged_lines.append(line)  # Guardar en lista para archivo

            
    def update_plot_data(self, timestamp, voltage_a0, voltage_a1):
        if self.start_time is None:
            self.start_time = timestamp

        relative_time = (timestamp - self.start_time) / 1000.0

        self.timestamps.append(relative_time)
        self.data_a0.append(voltage_a0)
        self.data_a1.append(voltage_a1)

        # Actualizar curvas
        self.curve_a0.setData(list(self.timestamps), list(self.data_a0))
        self.curve_a1.setData(list(self.timestamps), list(self.data_a1))

        # Desplazar la ventana visible para mostrar los últimos datos, sin borrar los anteriores
        if self.timestamps:
            current_time = self.timestamps[-1]
            if current_time > 5.0:  # solo cuando pasamos los 5 segundos
                window_start = current_time - 5.0
                self.plot_widget.setXRange(window_start, current_time + 0.5)
            else:
                self.plot_widget.setXRange(0, 5)
                
    def toggle_measurements(self):
        if not self.measuring:
            self.start_measurements()
        else:
            self.stop_measurements()
            
    def start_measurements(self):
        self.logged_lines = []

        if self.websocket_thread:
            # Limpiar datos anteriores
            self.clear_plot_data()
            
            duration = self.duration_input.value()
            command = {"action": "start_measurement", "duration": duration}
            self.websocket_thread.send_command(command)
            self.measuring = True
            self.measure_btn.setText(f"Midiendo... ({duration}s)")
            self.measure_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
            self.measure_btn.setEnabled(False)
            self.duration_input.setEnabled(False)
            
            # Iniciar timer para detener automáticamente
            self.measurement_timer.start(duration * 1000)  # Convertir a ms
            
    def clear_plot_data(self):
        """Limpiar datos del gráfico para una nueva medición"""
        self.timestamps.clear()
        self.data_a0.clear()
        self.data_a1.clear()
        self.start_time = None
        
        # Limpiar las curvas
        self.curve_a0.setData([], [])
        self.curve_a1.setData([], [])
            
        self.log_text.clear()
            
    def stop_measurements(self):
        if self.websocket_thread:
            command = {"action": "stop_measurement"}
            self.websocket_thread.send_command(command)
            
        self.measuring = False
        self.measurement_timer.stop()
        self.measure_btn.setText("Iniciar Mediciones")
        self.measure_btn.setStyleSheet("")
        self.measure_btn.setEnabled(True)
        self.duration_input.setEnabled(True)

        # Guardar archivo de texto al finalizar
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mediciones_{timestamp_str}.txt"
        try:
            with open(filename, 'w') as f:
                for line in self.logged_lines:
                    f.write(line + '\n')
            print(f"Archivo guardado: {filename}")
        except Exception as e:
            print(f"Error al guardar archivo: {e}")

            
    def closeEvent(self, event):
        if self.measurement_timer:
            self.measurement_timer.stop()
        if self.websocket_thread:
            self.disconnect_websocket()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ESP32Controller()
    window.show()
    sys.exit(app.exec_())