from PyQt5.QtCore import QThread, pyqtSignal
import websocket
import json
import time

class WebSocketThread(QThread):
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ws = None
        self.running = False
        self.last_data = None

    def run(self):
        self.running = True
        self.connection_status.emit("Conectando...")
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            self.ws.run_forever()
        except Exception as e:
            self.connection_status.emit(f"Error: {str(e)}")

    def on_open(self, ws):
        self.connection_status.emit("Conectado")

    def on_message(self, ws, message):
        try:
            json_obj = json.loads(message)
            self.last_data = json_obj
            self.data_received.emit(json_obj)
        except Exception as e:
            print(f"[WebSocket Error] Mensaje no JSON válido: {message}")

    def on_error(self, ws, error):
        self.connection_status.emit(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.connection_status.emit("Desconectado")

    def send_command(self, command):
        try:
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(json.dumps(command))
            else:
                print("[WebSocket] No conectado para enviar comando")
        except Exception as e:
            print(f"[WebSocket] Error al enviar comando: {e}")

    def stop(self):
        self.running = False
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
        self.quit()
        self.wait()
